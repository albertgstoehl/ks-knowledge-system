from src.services.jina_client import JinaClient
from src.services.archive_service import ArchiveService
from src.models import Bookmark
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import subprocess
import tempfile
import glob
import os
from typing import Optional, AsyncGenerator

logger = logging.getLogger(__name__)


def parse_vtt_to_text(vtt_path: str) -> str:
    """Extract plain text from VTT subtitle file."""
    import html
    lines = []
    with open(vtt_path) as f:
        for line in f:
            line = line.strip()
            # Skip timestamps, WEBVTT header, empty lines
            if not line or line.startswith("WEBVTT") or "-->" in line:
                continue
            # Skip style blocks and cue identifiers
            if line.startswith("Kind:") or line.startswith("Language:"):
                continue
            # Decode HTML entities
            line = html.unescape(line)
            lines.append(line)
    # Deduplicate consecutive identical lines (VTT often has overlapping captions)
    deduped = []
    for line in lines:
        if not deduped or line != deduped[-1]:
            deduped.append(line)
    return " ".join(deduped)


def fetch_youtube_data(video_id: str) -> dict:
    """Fetch YouTube video data using yt-dlp.

    Returns dict with 'title' and 'transcript' keys.
    Either can be None if unavailable.
    """
    result_data = {"title": None, "transcript": None}

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "subs")

            # Cookies file path - works in both dev and docker
            cookies_path = "/app/data/youtube-cookies.txt"
            if not os.path.exists(cookies_path):
                cookies_path = os.path.join(os.path.dirname(__file__), "../../data/youtube-cookies.txt")

            cmd = [
                "yt-dlp",
                "--skip-download",
                "--write-auto-subs",
                "--write-subs",
                "--sub-langs", "en.*,en",
                "--sub-format", "vtt",
                "--write-info-json",
                "--output", output_path,
                f"https://youtube.com/watch?v={video_id}"
            ]

            if os.path.exists(cookies_path):
                cmd.insert(1, "--cookies")
                cmd.insert(2, cookies_path)

            subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            # Get title from info JSON
            import json
            info_files = glob.glob(os.path.join(tmpdir, "*.info.json"))
            if info_files:
                with open(info_files[0]) as f:
                    info = json.load(f)
                    result_data["title"] = info.get("title")
                    logger.info(f"Got title for {video_id}: {result_data['title'][:50] if result_data['title'] else 'None'}")

            # Find .vtt file for transcript
            vtt_files = glob.glob(os.path.join(tmpdir, "*.vtt"))
            if vtt_files:
                text = parse_vtt_to_text(vtt_files[0])
                if text:
                    result_data["transcript"] = text
                    logger.info(f"Got transcript for {video_id} ({len(text)} chars)")

            if not result_data["transcript"]:
                logger.warning(f"No subtitles found for {video_id}: {result.stderr[:200] if result.stderr else 'no output'}")

    except subprocess.TimeoutExpired:
        logger.warning(f"yt-dlp timeout for {video_id}")
    except Exception as e:
        logger.warning(f"Could not fetch YouTube data for {video_id}: {e}")

    return result_data

class BackgroundJobService:
    def __init__(self, jina_api_key: str = None, oauth_token: str = None):
        self.jina_client = JinaClient(api_key=jina_api_key)
        self.archive_service = ArchiveService()
        self.llm_service = None  # Lazy load
        self.oauth_token = oauth_token

    def _get_llm_service(self):
        """Lazy load LLM service"""
        if self.llm_service is None:
            try:
                from src.services.llm_service import LLMService
                self.llm_service = LLMService(oauth_token=self.oauth_token)
            except ValueError as e:
                logger.warning(f"LLM service not available: {e}")
                self.llm_service = False  # Mark as unavailable
        return self.llm_service if self.llm_service is not False else None

    async def process_new_bookmark(self, bookmark_id: int, session: AsyncSession):
        """Process a new bookmark: fetch metadata, generate embedding, archive"""
        logger.info(f"Processing bookmark {bookmark_id}")

        # Fetch bookmark
        bookmark = await session.get(Bookmark, bookmark_id)
        if not bookmark:
            logger.error(f"Bookmark {bookmark_id} not found")
            return

        # 1. For YouTube videos, get data from yt-dlp; otherwise use Jina
        if bookmark.video_id:
            logger.info(f"Fetching YouTube data for {bookmark.video_id}")
            yt_data = fetch_youtube_data(bookmark.video_id)
            bookmark.title = yt_data["title"] or "Untitled"
            full_content = yt_data["transcript"] or ""
            jina_description = ""
            if not full_content:
                # Fallback to Jina if no transcript
                logger.info("No transcript, falling back to Jina")
                metadata = await self.jina_client.extract_metadata(bookmark.url)
                full_content = metadata.get("content", "")
                jina_description = metadata.get("description", "")
        else:
            logger.info(f"Extracting metadata for {bookmark.url}")
            metadata = await self.jina_client.extract_metadata(bookmark.url)
            bookmark.title = metadata.get("title", "Untitled")
            jina_description = metadata.get("description", "")
            full_content = metadata.get("content", "")

        # Store full content for note creation
        bookmark.content = full_content

        # 1.5. Generate LLM summary if available (skip videos - transcript is the content)
        llm_service = self._get_llm_service()
        if llm_service and full_content and not bookmark.video_id:
            logger.info(f"Generating LLM summary for bookmark {bookmark_id}")
            llm_summary = await llm_service.summarize_content(full_content, bookmark.url)
            if llm_summary:
                bookmark.description = llm_summary
                logger.info(f"Using LLM summary ({len(llm_summary)} chars)")
            else:
                bookmark.description = jina_description
                logger.info("LLM summary empty, using Jina description")
        else:
            bookmark.description = jina_description
            logger.info("LLM service unavailable, using Jina description")

        # 2. Submit to Web Archive (skip videos, thesis, pinned)
        if not bookmark.is_thesis and not bookmark.pinned and not bookmark.video_id:
            logger.info(f"Submitting to Web Archive: {bookmark.url}")
            archive_result = await self.archive_service.submit_to_archive(bookmark.url)
            if archive_result and "snapshot_url" in archive_result:
                bookmark.archive_url = archive_result["snapshot_url"]
            elif archive_result and "error_type" in archive_result:
                logger.warning(f"Archive failed for bookmark {bookmark_id}: {archive_result['error_type']}")
        else:
            logger.info(f"Skipping archive for bookmark {bookmark_id} (thesis={bookmark.is_thesis}, pinned={bookmark.pinned})")

        await session.commit()
        logger.info(f"Completed processing bookmark {bookmark_id}")

    async def process_bookmark_with_progress(self, bookmark_id: int, session: AsyncSession) -> AsyncGenerator[str, None]:
        """Process bookmark with progress updates for SSE streaming"""
        logger.info(f"Processing bookmark {bookmark_id} with progress")

        bookmark = await session.get(Bookmark, bookmark_id)
        if not bookmark:
            yield "error:Bookmark not found"
            return

        # Step 1: Get content (yt-dlp for videos, Jina for others)
        if bookmark.video_id:
            yield "Fetching YouTube data..."
            yt_data = fetch_youtube_data(bookmark.video_id)
            bookmark.title = yt_data["title"] or "Untitled"
            full_content = yt_data["transcript"] or ""
            jina_description = ""
            if not full_content:
                yield "No transcript, trying Jina..."
                metadata = await self.jina_client.extract_metadata(bookmark.url)
                full_content = metadata.get("content", "")
                jina_description = metadata.get("description", "")
        else:
            yield "Extracting content..."
            metadata = await self.jina_client.extract_metadata(bookmark.url)
            bookmark.title = metadata.get("title", "Untitled")
            jina_description = metadata.get("description", "")
            full_content = metadata.get("content", "")

        bookmark.content = full_content

        # Step 2: Generate summary (skip videos - transcript is the content)
        if not bookmark.video_id:
            yield "Generating summary..."
            llm_service = self._get_llm_service()
            if llm_service and full_content:
                llm_summary = await llm_service.summarize_content(full_content, bookmark.url)
                bookmark.description = llm_summary if llm_summary else jina_description
            else:
                bookmark.description = jina_description
        else:
            bookmark.description = f"YouTube video: {bookmark.title}"

        await session.commit()
        yield "done"

        # Archive in background after responding (skip videos, thesis, pinned)
        if not bookmark.is_thesis and not bookmark.pinned and not bookmark.video_id:
            archive_result = await self.archive_service.submit_to_archive(bookmark.url)
            if archive_result and "snapshot_url" in archive_result:
                bookmark.archive_url = archive_result["snapshot_url"]
                await session.commit()

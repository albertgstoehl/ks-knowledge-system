# YouTube Transcript via yt-dlp

**Date:** 2025-12-25
**Status:** Approved

## Problem

The `youtube-transcript-api` library fails on cloud IPs because YouTube blocks them. Transcripts silently fall back to Jina content (which is just page HTML, not useful).

## Solution

Replace `youtube-transcript-api` with `yt-dlp`, which is more resilient to YouTube blocking.

## How It Works

```
YouTube URL → yt-dlp --write-auto-subs → .vtt file → parse to plain text
```

yt-dlp downloads subtitle files without downloading the video. VTT files are parsed to plain text.

**Fallback chain:**
1. Try yt-dlp for transcript
2. If no subtitles available → fall back to Jina content

## Implementation

### New function in `background_jobs.py`

```python
def fetch_youtube_transcript_ytdlp(video_id: str) -> Optional[str]:
    """Fetch YouTube transcript using yt-dlp."""
    import subprocess
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "subs")

        result = subprocess.run([
            "yt-dlp",
            "--skip-download",
            "--write-auto-subs",
            "--write-subs",
            "--sub-langs", "en.*",
            "--sub-format", "vtt",
            "--output", output_path,
            f"https://youtube.com/watch?v={video_id}"
        ], capture_output=True, timeout=60)

        vtt_file = find_vtt_file(tmpdir)
        if vtt_file:
            return parse_vtt_to_text(vtt_file)

    return None

def find_vtt_file(directory: str) -> Optional[str]:
    """Find .vtt file in directory."""
    import glob
    files = glob.glob(os.path.join(directory, "*.vtt"))
    return files[0] if files else None

def parse_vtt_to_text(vtt_path: str) -> str:
    """Extract plain text from VTT subtitle file."""
    lines = []
    with open(vtt_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("WEBVTT") or "-->" in line:
                continue
            lines.append(line)
    return " ".join(lines)

def fetch_youtube_transcript(video_id: str) -> Optional[str]:
    """Fetch YouTube transcript using yt-dlp."""
    try:
        return fetch_youtube_transcript_ytdlp(video_id)
    except subprocess.TimeoutExpired:
        logger.warning(f"yt-dlp timeout for {video_id}")
        return None
    except Exception as e:
        logger.warning(f"Could not fetch transcript for {video_id}: {e}")
        return None
```

### Dockerfile addition

```dockerfile
RUN pip install yt-dlp
```

## Files to Modify

| File | Change |
|------|--------|
| `src/services/background_jobs.py` | Replace transcript function with yt-dlp version |
| `requirements.txt` | Remove `youtube-transcript-api` |
| `Dockerfile` | Add `yt-dlp` installation |

## Testing

1. Rebuild Docker image
2. Deploy to k3s
3. Retry scrape on the monkey video
4. Verify transcript content (should be speech, not HTML)

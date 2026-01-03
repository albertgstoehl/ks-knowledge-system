import os
import logging
from typing import Optional
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, oauth_token: Optional[str] = None):
        """Initialize LLM service with Claude Code OAuth token

        The claude-agent-sdk uses CLAUDE_CODE_OAUTH_TOKEN from environment
        automatically. We set it here if provided explicitly.
        """
        if oauth_token:
            os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = oauth_token

        # Verify token is available
        if not os.getenv("CLAUDE_CODE_OAUTH_TOKEN"):
            raise ValueError("CLAUDE_CODE_OAUTH_TOKEN is required")

        self.model = "haiku"  # claude-agent-sdk uses 'haiku' or 'sonnet'
        logger.info(f"Initialized LLM service with model: {self.model}")

    async def summarize_content(self, content: str, url: str) -> str:
        """
        Generate a 2-3 sentence summary of webpage content.

        Args:
            content: Full page content from Jina AI (markdown format)
            url: URL of the page (for context)

        Returns:
            Concise 2-3 sentence summary
        """
        if not content or not content.strip():
            return ""

        # Truncate very long content to avoid token limits
        max_chars = 10000
        truncated_content = content[:max_chars]
        if len(content) > max_chars:
            truncated_content += "\n\n[Content truncated...]"

        prompt = f"""Summarize this webpage in 2-3 clear, informative sentences. Focus on the main topic and key points.

URL: {url}

Content:
{truncated_content}

Summary (2-3 sentences):"""

        try:
            options = ClaudeAgentOptions(
                model=self.model,
                max_turns=1,  # Just one response
                allowed_tools=[],  # Disable all tools - we just want text summary
                system_prompt="You are a helpful assistant that summarizes web content. Output ONLY the summary text - no tool use, no preamble."
            )

            summary_text = ""
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            summary_text += block.text

            summary = summary_text.strip()
            logger.info(f"Generated summary for {url}: {len(summary)} chars")
            return summary

        except Exception as e:
            logger.error(f"LLM summarization failed for {url}: {e}")
            return ""

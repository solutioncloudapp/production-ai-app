"""Output filter for response validation and formatting."""

import re
from typing import List, Optional

import structlog

from app.models import ChatResponse, SourceDocument

logger = structlog.get_logger()


class OutputFilter:
    """Third line of defense: validates and formats AI output.

    Responsibilities:
    - Response format validation
    - Source citation verification
    - Length limiting
    - Markdown sanitization
    - JSON structure validation
    """

    MAX_RESPONSE_LENGTH = 4000
    MAX_SOURCES = 5

    def __init__(self):
        """Initialize output filter."""
        logger.info("Initialized output filter")

    def format(
        self,
        content: str,
        sources: List[SourceDocument],
        conversation_id: Optional[str] = None,
    ) -> ChatResponse:
        """Format and validate AI response.

        Args:
            content: Raw AI response content.
            sources: Source documents used.
            conversation_id: Optional conversation ID.

        Returns:
            Formatted ChatResponse.
        """
        # Sanitize content
        sanitized = self._sanitize_markdown(content)

        # Limit length
        if len(sanitized) > self.MAX_RESPONSE_LENGTH:
            sanitized = sanitized[: self.MAX_RESPONSE_LENGTH] + "..."
            logger.warning("Response truncated", original_length=len(content))

        # Limit sources
        limited_sources = sources[: self.MAX_SOURCES]

        # Verify citations
        sanitized = self._verify_citations(sanitized, limited_sources)

        response = ChatResponse(
            text=sanitized,
            sources=limited_sources,
            conversation_id=conversation_id,
        )

        logger.info(
            "Output formatted",
            content_length=len(sanitized),
            num_sources=len(limited_sources),
        )

        return response

    def _sanitize_markdown(self, content: str) -> str:
        """Sanitize markdown content.

        Removes potentially harmful markdown while preserving formatting.

        Args:
            content: Raw markdown content.

        Returns:
            Sanitized markdown.
        """
        # Remove HTML tags
        sanitized = re.sub(r"<[^>]+>", "", content)

        # Remove data URIs
        sanitized = re.sub(r"data:[^;]+;base64,[^\s]+", "[removed]", sanitized)

        # Remove javascript: links
        sanitized = re.sub(r"javascript:[^\s]+", "", sanitized)

        return sanitized

    def _verify_citations(
        self, content: str, sources: List[SourceDocument]
    ) -> str:
        """Verify that citations reference actual sources.

        Args:
            content: Content with citations.
            sources: Available sources.

        Returns:
            Content with verified citations.
        """
        # Find all citations like [1], [2], etc.
        citations = re.findall(r"\[(\d+)\]", content)

        # Remove citations that reference non-existent sources
        valid_citations = {str(i + 1) for i in range(len(sources))}
        for citation in citations:
            if citation not in valid_citations:
                content = content.replace(f"[{citation}]", "")

        return content

    def validate_json_response(self, content: str) -> Optional[dict]:
        """Validate and parse JSON response.

        Args:
            content: JSON string content.

        Returns:
            Parsed dict or None if invalid.
        """
        import json

        try:
            # Try to extract JSON from content
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return None
        except json.JSONDecodeError:
            logger.warning("Invalid JSON response", content=content[:100])
            return None

    def format_error(self, error: str, detail: Optional[str] = None) -> str:
        """Format error message for user display.

        Args:
            error: Error type.
            detail: Optional error detail.

        Returns:
            User-friendly error message.
        """
        messages = {
            "rate_limit": "Too many requests. Please wait a moment.",
            "timeout": "Request timed out. Please try again.",
            "service_error": "Service temporarily unavailable.",
            "invalid_input": "Invalid input. Please check your query.",
        }

        user_message = messages.get(error, "An error occurred. Please try again.")

        if detail and logger.isEnabledFor(10):  # DEBUG level
            user_message += f" ({detail})"

        return user_message

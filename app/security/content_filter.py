"""Content filter for policy compliance checking."""

from typing import List

import structlog

from app.models import ContentFilterResult

logger = structlog.get_logger()


class ContentFilter:
    """Second line of defense: filters content for policy violations.

    Checks:
    - Toxic or harmful language
    - Hate speech or discrimination
    - Sexual content
    - Violence or self-harm
    - Illegal activities
    """

    # Toxicity keywords (simplified - production would use ML model)
    TOXIC_PATTERNS = [
        "hate", "kill", "murder", "suicide", "bomb",
        "terrorist", "extremist", "racist", "sexist",
    ]

    # Sexual content indicators
    SEXUAL_PATTERNS = [
        "sexual", "porn", "explicit", "nude", "naked",
    ]

    # Violence indicators
    VIOLENCE_PATTERNS = [
        "violence", "torture", "abuse", "assault", "weapon",
    ]

    def __init__(self):
        """Initialize content filter."""
        logger.info("Initialized content filter")

    def check(self, content: str) -> ContentFilterResult:
        """Check content for policy violations.

        Args:
            content: Content to check.

        Returns:
            ContentFilterResult with safety status and flags.
        """
        content_lower = content.lower()
        flags = []

        # Check toxicity
        if any(p in content_lower for p in self.TOXIC_PATTERNS):
            flags.append("toxicity")

        # Check sexual content
        if any(p in content_lower for p in self.SEXUAL_PATTERNS):
            flags.append("sexual_content")

        # Check violence
        if any(p in content_lower for p in self.VIOLENCE_PATTERNS):
            flags.append("violence")

        # Check for self-harm indicators
        if self._check_self_harm(content_lower):
            flags.append("self_harm")

        if flags:
            logger.warning(
                "Content flagged",
                flags=flags,
                content_length=len(content),
            )
            return ContentFilterResult(
                is_safe=False,
                sanitized_content=self._sanitize(content),
                flags=flags,
            )

        return ContentFilterResult(
            is_safe=True,
            sanitized_content=content,
        )

    def _check_self_harm(self, content: str) -> bool:
        """Check for self-harm indicators.

        Args:
            content: Lowercased content.

        Returns:
            True if self-harm indicators found.
        """
        self_harm_phrases = [
            "hurt myself", "end my life", "kill myself",
            "self harm", "suicidal", "don't want to live",
        ]
        return any(phrase in content for phrase in self_harm_phrases)

    def _sanitize(self, content: str) -> str:
        """Sanitize flagged content.

        Args:
            content: Original content.

        Returns:
            Sanitized content with flagged portions removed.
        """
        # In production, this would use more sophisticated redaction
        # For now, return a safe default message
        return "I cannot provide that information. Please ask something else."

    def check_batch(self, contents: List[str]) -> List[ContentFilterResult]:
        """Check multiple content items.

        Args:
            contents: List of content strings.

        Returns:
            List of filter results.
        """
        return [self.check(content) for content in contents]

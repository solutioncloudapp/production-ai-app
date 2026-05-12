"""Input guard for validating and sanitizing user input."""

import re
from typing import ClassVar, List, Optional

import structlog

from app.config import settings
from app.models import GuardResult

logger = structlog.get_logger()


class InputGuard:
    """First line of defense: validates and sanitizes all user input.

    Checks:
    - Prompt injection attempts
    - Jailbreak patterns
    - PII/sensitive data
    - Input length limits
    - Rate limiting
    """

    # Known injection patterns
    INJECTION_PATTERNS: ClassVar[list[str]] = [
        r"ignore\s+(previous|all)\s+(instructions|rules|prompts)",
        r"system\s*:\s*",
        r"<\|.*?\|>",
        r"\[INST\].*\[/INST\]",
        r"###\s*Instruction",
        r"act\s+as\s+(system|admin|developer)",
        r"forget\s+(all|your)\s+(instructions|rules)",
        r"you\s+are\s+now\s+(in\s+)?(developer|system)\s+mode",
    ]

    # PII patterns
    PII_PATTERNS: ClassVar[list[tuple[str, str]]] = [
        (r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b", "SSN"),
        (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "Credit Card"),
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "Email"),
    ]

    def __init__(self) -> None:
        """Initialize input guard."""
        self._compiled_injections = [re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS]
        self._compiled_pii = [(re.compile(p), name) for p, name in self.PII_PATTERNS]
        logger.info("Initialized input guard")

    def validate(self, query: str) -> GuardResult:
        """Validate and sanitize user input.

        Args:
            query: Raw user input.

        Returns:
            GuardResult with validation status and sanitized query.
        """
        # Check length
        if len(query) > settings.max_input_length:
            return GuardResult(
                is_valid=False,
                reason=f"Input exceeds maximum length of {settings.max_input_length}",
            )

        # Check for empty input
        if not query.strip():
            return GuardResult(
                is_valid=False,
                reason="Input cannot be empty",
            )

        # Check for injection attempts
        injection_detected = self._check_injections(query)
        if injection_detected:
            logger.warning("Injection attempt detected", pattern=injection_detected)
            return GuardResult(
                is_valid=False,
                reason="Input contains potentially malicious patterns",
            )

        # Check for PII and redact
        sanitized, pii_found = self._redact_pii(query)
        if pii_found:
            logger.info("PII detected and redacted", types=pii_found)

        return GuardResult(
            is_valid=True,
            sanitized_query=sanitized,
        )

    def _check_injections(self, query: str) -> Optional[str]:
        """Check for prompt injection patterns.

        Args:
            query: User input to check.

        Returns:
            Matched pattern or None.
        """
        for pattern in self._compiled_injections:
            if pattern.search(query):
                return pattern.pattern
        return None

    def _redact_pii(self, query: str) -> tuple[str, List[str]]:
        """Redact PII from input.

        Args:
            query: Input to redact.

        Returns:
            Tuple of (sanitized_query, list_of_pii_types_found).
        """
        sanitized = query
        pii_found = []

        for pattern, pii_type in self._compiled_pii:
            if pattern.search(sanitized):
                pii_found.append(pii_type)
                sanitized = pattern.sub(f"[REDACTED_{pii_type}]", sanitized)

        return sanitized, pii_found

    def sanitize(self, query: str) -> str:
        """Basic sanitization without blocking.

        Args:
            query: Raw input.

        Returns:
            Sanitized input.
        """
        # Remove control characters
        sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", query)
        # Normalize whitespace
        sanitized = " ".join(sanitized.split())
        return sanitized

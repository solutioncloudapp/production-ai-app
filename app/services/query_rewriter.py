"""Query rewriter for multi-turn context injection and intent clarification."""

from typing import List, Optional

import structlog
from langchain_openai import ChatOpenAI

from app.config import settings
from app.prompts.registry import prompt_registry
from app.services.conversation import conversation_memory

logger = structlog.get_logger()


class QueryRewriter:
    """Rewrites queries with conversation context and intent clarification.

    Handles:
    - Multi-turn context injection (resolving pronouns, references)
    - Intent clarification for ambiguous queries
    - Query expansion for better retrieval
    """

    def __init__(self):
        """Initialize query rewriter."""
        self.llm = ChatOpenAI(model=settings.openai_model, temperature=0.1)
        logger.info("Initialized query rewriter")

    async def rewrite(
        self,
        query: str,
        conversation_id: Optional[str] = None,
    ) -> str:
        """Rewrite query with conversation context.

        Args:
            query: Original user query.
            conversation_id: Optional conversation ID for context.

        Returns:
            Rewritten query with resolved context.
        """
        if not conversation_id:
            return query

        summary, recent_messages = await conversation_memory.get_context(
            conversation_id
        )

        if not recent_messages:
            return query

        # Build context from recent messages
        context_lines = []
        for msg in recent_messages:
            context_lines.append(f"{msg.role}: {msg.content}")
        context = "\n".join(context_lines)

        prompt = prompt_registry.get("query_rewrite")
        messages = prompt.format_messages(
            context=context,
            query=query,
            summary=summary or "",
        )

        response = await self.llm.ainvoke(messages)
        rewritten = response.content.strip()

        logger.info(
            "Query rewritten",
            original=query[:50],
            rewritten=rewritten[:50],
        )

        return rewritten

    async def expand(self, query: str) -> List[str]:
        """Expand query into multiple related queries for broader retrieval.

        Args:
            query: Original query.

        Returns:
            List of expanded queries.
        """
        prompt = prompt_registry.get("query_expand")
        messages = prompt.format_messages(query=query)

        response = await self.llm.ainvoke(messages)
        expansions = [
            q.strip()
            for q in response.content.split("\n")
            if q.strip() and not q.strip().startswith("1.")
        ]

        # Always include original query
        if query not in expansions:
            expansions.insert(0, query)

        logger.info(
            "Query expanded",
            original=query[:50],
            num_expansions=len(expansions),
        )

        return expansions[:5]

    async def clarify(self, query: str) -> tuple[str, bool]:
        """Check if query needs clarification and suggest clarifying question.

        Args:
            query: User query.

        Returns:
            Tuple of (clarifying_question, needs_clarification).
        """
        prompt = prompt_registry.get("query_clarify")
        messages = prompt.format_messages(query=query)

        response = await self.llm.ainvoke(messages)
        result = response.content.strip()

        if result.lower().startswith("clear"):
            return "", False

        return result, True

    async def normalize(self, query: str) -> str:
        """Normalize query for consistent processing.

        Removes unnecessary whitespace, normalizes casing for keywords.

        Args:
            query: Raw query.

        Returns:
            Normalized query.
        """
        normalized = " ".join(query.split())
        logger.debug("Query normalized", original=query[:50], normalized=normalized[:50])
        return normalized


# Singleton instance
query_rewriter = QueryRewriter()

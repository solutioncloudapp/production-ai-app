"""Query decomposer for breaking complex queries into sub-questions."""

from typing import List

import structlog
from langchain_openai import ChatOpenAI

from app.config import settings
from app.prompts.registry import prompt_registry

logger = structlog.get_logger()


class QueryDecomposer:
    """Breaks complex queries into independent sub-questions.

    Features:
    - LLM-based decomposition
    - Fallback to single query for simple inputs
    - Deduplication of sub-questions
    """

    def __init__(self, max_sub_queries: int = 4):
        """Initialize query decomposer.

        Args:
            max_sub_queries: Maximum number of sub-questions to generate.
        """
        self.llm = ChatOpenAI(model=settings.openai_model, temperature=0.1)
        self.max_sub_queries = max_sub_queries
        logger.info(
            "Initialized query decomposer",
            max_sub_queries=max_sub_queries,
        )

    async def decompose(self, query: str) -> List[str]:
        """Decompose query into sub-questions.

        Args:
            query: Complex query to decompose.

        Returns:
            List of sub-questions. Returns original query if simple.
        """
        # Quick heuristic: short queries are likely simple
        if len(query.split()) <= 5:
            logger.debug("Query too short to decompose", query=query)
            return [query]

        prompt = prompt_registry.get("query_decompose")
        messages = prompt.format_messages(query=query)

        response = await self.llm.ainvoke(messages)
        sub_queries = self._parse_response(response.content)

        # Deduplicate while preserving order
        seen = set()
        unique_queries = []
        for sq in sub_queries:
            normalized = sq.lower().strip()
            if normalized not in seen and normalized:
                seen.add(normalized)
                unique_queries.append(sq)

        # Limit to max sub-queries
        result = unique_queries[: self.max_sub_queries]

        # Ensure original query is included if decomposition seems off
        if not result or (len(result) == 1 and result[0] == query):
            result = [query]

        logger.info(
            "Query decomposed",
            original=query[:50],
            num_sub_queries=len(result),
        )

        return result

    def _parse_response(self, response: str) -> List[str]:
        """Parse LLM response into list of sub-queries.

        Handles various formatting styles.

        Args:
            response: Raw LLM response.

        Returns:
            List of parsed sub-queries.
        """
        lines = response.strip().split("\n")
        queries = []

        for line in lines:
            # Remove numbering and bullet points
            cleaned = line.strip()
            cleaned = cleaned.lstrip("0123456789.-* ")
            cleaned = cleaned.strip('"').strip("'")

            if cleaned and len(cleaned) > 3:
                queries.append(cleaned)

        return queries

    async def decompose_with_context(
        self, query: str, context: str
    ) -> List[str]:
        """Decompose query with additional context.

        Useful for document-specific queries where context helps
        generate better sub-questions.

        Args:
            query: Query to decompose.
            context: Additional context for decomposition.

        Returns:
            List of context-aware sub-questions.
        """
        enhanced_query = f"Given context: {context[:500]}\n\nQuery: {query}"
        return await self.decompose(enhanced_query)

"""Query router for intent classification and tool selection."""

from typing import ClassVar, Dict, List, cast

import structlog
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import settings
from app.models import IntentType, RouteResult
from app.prompts.registry import prompt_registry

logger = structlog.get_logger()


class RouteDecision(BaseModel):
    """Structured route decision output."""

    intent: str = Field(description="Detected intent type")
    confidence: float = Field(description="Confidence score 0-1")
    tools: List[str] = Field(description="Recommended tools to use")
    reasoning: str = Field(description="Brief reasoning for the decision")


class QueryRouter:
    """Routes queries to appropriate handlers based on intent.

    Supported intents:
    - general: Standard RAG pipeline
    - document: Document-specific queries
    - code: Code-related queries
    - web_search: Queries requiring web search
    - conversational: Chit-chat and conversational queries
    """

    # Intent-to-tools mapping
    INTENT_TOOLS: ClassVar[Dict[IntentType, List[str]]] = {
        IntentType.GENERAL: ["vector_search"],
        IntentType.DOCUMENT: ["vector_search", "document_search"],
        IntentType.CODE: ["code_search", "vector_search"],
        IntentType.WEB_SEARCH: ["web_search"],
        IntentType.CONVERSATIONAL: [],
    }

    def __init__(self) -> None:
        """Initialize query router."""
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0,
        )
        logger.info("Initialized query router")

    async def route(self, query: str) -> RouteResult:
        """Route query to appropriate intent and tools.

        Args:
            query: User query.

        Returns:
            RouteResult with intent, confidence, and tools.
        """
        prompt = prompt_registry.get("query_route")
        messages = prompt.format_messages(query=query)

        # Use structured output for reliable parsing
        structured_llm = self.llm.with_structured_output(RouteDecision)
        response = cast(RouteDecision, await structured_llm.ainvoke(messages))

        # Map string intent to enum
        try:
            intent = IntentType(response.intent)
        except ValueError:
            logger.warning(
                "Unknown intent detected",
                intent=response.intent,
                defaulting_to=IntentType.GENERAL,
            )
            intent = IntentType.GENERAL

        tools = self.INTENT_TOOLS.get(intent, ["vector_search"])

        result = RouteResult(
            intent=intent,
            confidence=response.confidence,
            tools=tools,
        )

        logger.info(
            "Query routed",
            query=query[:50],
            intent=intent.value,
            confidence=round(result.confidence, 2),
            tools=tools,
        )

        return result

    async def route_batch(self, queries: List[str]) -> List[RouteResult]:
        """Route multiple queries in batch.

        Args:
            queries: List of queries to route.

        Returns:
            List of route results.
        """
        results = []
        for query in queries:
            result = await self.route(query)
            results.append(result)
        return results

    def route_sync(self, query: str) -> RouteResult:
        """Synchronous routing using keyword matching fallback.

        Used when LLM is unavailable.

        Args:
            query: User query.

        Returns:
            RouteResult based on keyword matching.
        """
        query_lower = query.lower()

        # Keyword-based routing fallback
        if any(kw in query_lower for kw in ["code", "function", "api", "python", "javascript"]):
            return RouteResult(
                intent=IntentType.CODE,
                confidence=0.7,
                tools=["code_search", "vector_search"],
            )
        elif any(kw in query_lower for kw in ["current", "latest", "today", "news", "weather"]):
            return RouteResult(
                intent=IntentType.WEB_SEARCH,
                confidence=0.7,
                tools=["web_search"],
            )
        elif any(kw in query_lower for kw in ["hi", "hello", "help", "thanks"]):
            return RouteResult(
                intent=IntentType.CONVERSATIONAL,
                confidence=0.8,
                tools=[],
            )
        else:
            return RouteResult(
                intent=IntentType.GENERAL,
                confidence=0.6,
                tools=["vector_search"],
            )


# Singleton instance
query_router = QueryRouter()

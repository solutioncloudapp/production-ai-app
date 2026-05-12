"""Adaptive router for dynamic tool selection based on query analysis."""

from typing import Any, Callable, ClassVar, Dict, List, Optional, cast

import structlog
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import settings
from app.models import IntentType, RouteResult
from app.services.query_router import query_router

logger = structlog.get_logger()


class ToolSelection(BaseModel):
    """Structured tool selection output."""

    primary_tool: str = Field(description="Primary tool to use")
    fallback_tools: List[str] = Field(description="Fallback tools in order")
    confidence: float = Field(description="Confidence in selection 0-1")
    reasoning: str = Field(description="Reasoning for tool selection")


class AdaptiveRouter:
    """Dynamically selects tools based on query intent and complexity.

    Features:
    - Intent-based routing
    - Complexity-aware tool selection
    - Fallback chain configuration
    - Self-correction on failed tool execution
    """

    # Available tools and their capabilities
    TOOL_CAPABILITIES: ClassVar[Dict[str, List[str]]] = {
        "vector_search": ["document_retrieval", "semantic_search"],
        "web_search": ["real_time_data", "current_events", "external_info"],
        "code_search": ["code_lookup", "api_documentation", "examples"],
        "document_search": ["full_text_search", "metadata_filter"],
    }

    def __init__(self) -> None:
        """Initialize adaptive router."""
        self.llm = ChatOpenAI(model=settings.openai_model, temperature=0)
        self._tool_registry: Dict[str, Callable[..., Any]] = {}
        logger.info("Initialized adaptive router")

    def register_tool(self, name: str, handler: Callable[..., Any]) -> None:
        """Register a tool handler.

        Args:
            name: Tool name.
            handler: Callable that executes the tool.
        """
        self._tool_registry[name] = handler
        logger.info("Registered tool", name=name)

    async def route(self, query: str) -> RouteResult:
        """Route query with adaptive tool selection.

        Args:
            query: User query.

        Returns:
            RouteResult with intent and selected tools.
        """
        # Get base route from query router
        base_route = await query_router.route(query)

        # Enhance with adaptive tool selection
        enhanced_tools = await self._select_tools(query, base_route)

        result = RouteResult(
            intent=base_route.intent,
            confidence=base_route.confidence,
            tools=enhanced_tools,
        )

        logger.info(
            "Adaptive routing complete",
            intent=result.intent.value,
            tools=result.tools,
        )

        return result

    async def _select_tools(self, query: str, base_route: RouteResult) -> List[str]:
        """Select tools adaptively based on query characteristics.

        Args:
            query: User query.
            base_route: Base route from query router.

        Returns:
            Enhanced list of tools.
        """
        tools = list(base_route.tools)  # Copy base tools

        # Add fallback tools based on intent
        fallback_map = {
            IntentType.GENERAL: ["vector_search"],
            IntentType.DOCUMENT: ["vector_search", "document_search"],
            IntentType.CODE: ["vector_search"],
            IntentType.WEB_SEARCH: ["vector_search"],
            IntentType.CONVERSATIONAL: [],
        }

        fallbacks = fallback_map.get(base_route.intent, [])
        for tool in fallbacks:
            if tool not in tools:
                tools.append(tool)

        # Complexity-based enhancement
        if self._is_complex_query(query):
            tools = self._add_complexity_tools(tools)

        return tools[:4]  # Limit to 4 tools max

    def _is_complex_query(self, query: str) -> bool:
        """Determine if query is complex.

        Args:
            query: User query.

        Returns:
            True if query is complex.
        """
        # Multiple question marks or conjunctions suggest complexity
        complex_indicators = [
            query.count("?") > 1,
            any(
                word in query.lower()
                for word in [
                    "compare",
                    "difference",
                    "versus",
                    "vs",
                    "pros and cons",
                    "advantages and disadvantages",
                    "how does",
                    "why does",
                    "explain how",
                ]
            ),
            len(query.split()) > 20,
        ]
        return any(complex_indicators)

    def _add_complexity_tools(self, tools: List[str]) -> List[str]:
        """Add tools for complex queries.

        Args:
            tools: Current tool list.

        Returns:
            Enhanced tool list.
        """
        enhanced = list(tools)
        if "vector_search" not in enhanced:
            enhanced.insert(0, "vector_search")
        return enhanced

    async def execute_tool(self, tool_name: str, **kwargs: Any) -> Optional[Dict[str, Any]]:
        """Execute a registered tool.

        Args:
            tool_name: Name of tool to execute.
            **kwargs: Tool-specific arguments.

        Returns:
            Tool execution result or None.
        """
        handler = self._tool_registry.get(tool_name)
        if not handler:
            logger.warning("Tool not found", tool=tool_name)
            return None

        try:
            result = await handler(**kwargs)
            logger.info("Tool executed", tool=tool_name)
            return cast(Optional[Dict[str, Any]], result)
        except Exception as e:
            logger.error("Tool execution failed", tool=tool_name, error=str(e))
            return None


# Singleton instance
adaptive_router = AdaptiveRouter()

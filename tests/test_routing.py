"""Tests for query routing."""

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.adaptive_router import AdaptiveRouter
from app.models import IntentType, RouteResult
from app.services.query_router import QueryRouter


@pytest.fixture
def query_router():
    """Create query router instance."""
    return QueryRouter()


@pytest.fixture
def adaptive_router():
    """Create adaptive router instance."""
    return AdaptiveRouter()


class TestQueryRouter:
    """Tests for QueryRouter."""

    @pytest.mark.asyncio
    async def test_route_code_query(self, query_router):
        """Test routing for code-related queries."""
        with patch.object(query_router.llm, "with_structured_output") as mock_output:
            mock_output.return_value.ainvoke = AsyncMock(return_value=AsyncMock(
                intent="code",
                confidence=0.9,
                tools=["code_search"],
                reasoning="Code-related query",
            ))

            result = await query_router.route("How do I write a Python function?")

            assert result.intent == IntentType.CODE
            assert "code_search" in result.tools

    @pytest.mark.asyncio
    async def test_route_web_search_query(self, query_router):
        """Test routing for web search queries."""
        with patch.object(query_router.llm, "with_structured_output") as mock_output:
            mock_output.return_value.ainvoke = AsyncMock(return_value=AsyncMock(
                intent="web_search",
                confidence=0.85,
                tools=["web_search"],
                reasoning="Requires current data",
            ))

            result = await query_router.route("What is the weather today?")

            assert result.intent == IntentType.WEB_SEARCH
            assert "web_search" in result.tools

    @pytest.mark.asyncio
    async def test_route_conversational_query(self, query_router):
        """Test routing for conversational queries."""
        with patch.object(query_router.llm, "with_structured_output") as mock_output:
            mock_output.return_value.ainvoke = AsyncMock(return_value=AsyncMock(
                intent="conversational",
                confidence=0.95,
                tools=[],
                reasoning="Simple greeting",
            ))

            result = await query_router.route("Hello, how are you?")

            assert result.intent == IntentType.CONVERSATIONAL
            assert result.tools == []

    def test_route_sync_fallback_code(self, query_router):
        """Test synchronous fallback routing for code queries."""
        result = query_router.route_sync("How to write a python function?")

        assert result.intent == IntentType.CODE
        assert "code_search" in result.tools

    def test_route_sync_fallback_web(self, query_router):
        """Test synchronous fallback routing for web search queries."""
        result = query_router.route_sync("What is the latest news today?")

        assert result.intent == IntentType.WEB_SEARCH
        assert "web_search" in result.tools

    def test_route_sync_fallback_general(self, query_router):
        """Test synchronous fallback routing for general queries."""
        result = query_router.route_sync("Tell me about machine learning")

        assert result.intent == IntentType.GENERAL
        assert "vector_search" in result.tools


class TestAdaptiveRouter:
    """Tests for AdaptiveRouter."""

    @pytest.mark.asyncio
    async def test_route_with_tool_selection(self, adaptive_router):
        """Test adaptive routing with tool selection."""
        with patch.object(adaptive_router, "_select_tools") as mock_select:
            mock_select.return_value = ["vector_search", "document_search"]

            with patch("app.agents.adaptive_router.query_router") as mock_router:
                mock_router.route = AsyncMock(return_value=RouteResult(
                    intent=IntentType.DOCUMENT,
                    confidence=0.8,
                    tools=["vector_search"],
                ))

                result = await adaptive_router.route("Find the document about Python")

                assert result.intent == IntentType.DOCUMENT
                assert len(result.tools) >= 1

    def test_is_complex_query(self, adaptive_router):
        """Test complex query detection."""
        # Multiple questions
        assert adaptive_router._is_complex_query("What is Python? How does it work?")

        # Comparison query
        assert adaptive_router._is_complex_query("Compare Python and JavaScript")

        # Long query
        assert adaptive_router._is_complex_query(" ".join(["word"] * 25))

        # Simple query
        assert not adaptive_router._is_complex_query("What is Python?")

    def test_register_tool(self, adaptive_router):
        """Test tool registration."""
        mock_handler = AsyncMock()
        adaptive_router.register_tool("test_tool", mock_handler)

        assert "test_tool" in adaptive_router._tool_registry
        assert adaptive_router._tool_registry["test_tool"] == mock_handler

    @pytest.mark.asyncio
    async def test_execute_tool(self, adaptive_router):
        """Test tool execution."""
        mock_handler = AsyncMock(return_value={"result": "success"})
        adaptive_router.register_tool("test_tool", mock_handler)

        result = await adaptive_router.execute_tool("test_tool", query="test")

        assert result == {"result": "success"}
        mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_missing_tool(self, adaptive_router):
        """Test execution of unregistered tool."""
        result = await adaptive_router.execute_tool("nonexistent")
        assert result is None

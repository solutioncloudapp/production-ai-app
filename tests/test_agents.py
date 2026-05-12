"""Tests for agents layer."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.document_grader import DocumentGrader
from app.agents.query_decomposer import QueryDecomposer
from app.models import SourceDocument
from app.prompts.registry import prompt_registry


@pytest.fixture(autouse=True)
def init_prompts():
    prompt_registry.initialize()


class TestDocumentGrader:
    """Tests for DocumentGrader."""

    @pytest.fixture
    def grader(self):
        g = DocumentGrader()
        g.llm = MagicMock()
        return g

    @pytest.mark.asyncio
    async def test_grade_empty_documents(self, grader):
        result = await grader.grade("test query", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_grade_filters_irrelevant(self, grader):
        docs = [
            SourceDocument(id="doc1", content="Python programming language", score=0.9),
            SourceDocument(id="doc2", content="Recipe for chocolate cake", score=0.9),
        ]

        async def mock_ainvoke(*args, **kwargs):
            return MagicMock(grade="RELEVANT", score=0.9, reason="Directly addresses query")

        grader.llm.with_structured_output.return_value.ainvoke = mock_ainvoke

        result = await grader.grade("What is Python?", docs)

        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_grade_adds_metadata(self, grader):
        doc = SourceDocument(id="doc1", content="Python is a programming language", score=0.5)

        async def mock_ainvoke(*args, **kwargs):
            return MagicMock(grade="RELEVANT", score=0.9, reason="Direct answer")

        grader.llm.with_structured_output.return_value.ainvoke = mock_ainvoke

        result = await grader.grade("What is Python?", [doc])

        assert result[0].metadata["grade"] == "RELEVANT"
        assert result[0].metadata["grade_score"] == 0.9


class TestQueryDecomposer:
    """Tests for QueryDecomposer."""

    @pytest.fixture
    def decomposer(self):
        d = QueryDecomposer()
        d.llm = MagicMock()
        return d

    @pytest.mark.asyncio
    async def test_short_query_not_decomposed(self, decomposer):
        result = await decomposer.decompose("Python?")
        assert result == ["Python?"]

    @pytest.mark.asyncio
    async def test_simple_query_returns_original(self, decomposer):
        result = await decomposer.decompose("What is Python")
        assert result == ["What is Python"]

    @pytest.mark.asyncio
    async def test_complex_query_decomposed(self, decomposer):
        decomposer.llm.ainvoke = AsyncMock(
            return_value=MagicMock(content="1. What is Python?\n2. What are Python's main features?")
        )

        result = await decomposer.decompose("What is Python and what are its main features and use cases?")

        assert len(result) >= 1
        assert len(result) <= 4  # max_sub_queries

    @pytest.mark.asyncio
    async def test_deduplication(self, decomposer):
        decomposer.llm.ainvoke = AsyncMock(
            return_value=MagicMock(content="1. What is Python?\n2. What is Python?\n3. How does Python work?")
        )

        result = await decomposer.decompose("What is Python and how does it work? What is Python?")

        # Should deduplicate
        queries_lower = [q.lower() for q in result]
        assert len(queries_lower) == len(set(queries_lower))

    @pytest.mark.asyncio
    async def test_decompose_with_context(self, decomposer):
        with patch.object(decomposer, "decompose") as mock_decompose:
            mock_decompose.return_value = ["Sub-query 1", "Sub-query 2"]

            await decomposer.decompose_with_context("How does this work?", "This is about Python programming")

            assert mock_decompose.called
            # Check that context was included in the enhanced query
            call_args = mock_decompose.call_args[0][0]
            assert "Python programming" in call_args

    def test_parse_response_numbered_list(self, decomposer):
        response = "1. First question\n2. Second question\n3. Third question"
        result = decomposer._parse_response(response)
        assert len(result) == 3
        assert "First question" in result[0]

    def test_parse_response_bullet_list(self, decomposer):
        response = "- First question\n- Second question\n* Third question"
        result = decomposer._parse_response(response)
        assert len(result) == 3

    def test_parse_response_removes_empty(self, decomposer):
        response = "1. Valid question\n\n\n2. Another question"
        result = decomposer._parse_response(response)
        assert len(result) == 2
        assert all(len(q) > 3 for q in result)

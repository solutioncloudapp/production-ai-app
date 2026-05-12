"""Tests for retrieval components."""

from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.documents import Document

from app.components.hybrid_retriever import HybridRetriever

try:
    from app.components.reranker import SENTENCE_TRANSFORMERS_AVAILABLE, CrossEncoderReranker
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from app.models import SourceDocument


@pytest.fixture
def sample_documents():
    """Create sample documents for testing."""
    return [
        Document(
            page_content="Python is a programming language",
            metadata={"id": "doc_1", "source": "test"},
        ),
        Document(
            page_content="JavaScript is used for web development",
            metadata={"id": "doc_2", "source": "test"},
        ),
        Document(
            page_content="Machine learning enables AI systems",
            metadata={"id": "doc_3", "source": "test"},
        ),
    ]


@pytest.fixture
def mock_vector_retriever():
    """Create mock vector retriever."""
    mock = AsyncMock()
    mock.ainvoke = AsyncMock(
        return_value=[
            Document(
                page_content="Python is a programming language",
                metadata={"id": "doc_1", "score": 0.9},
            ),
            Document(
                page_content="Machine learning enables AI systems",
                metadata={"id": "doc_3", "score": 0.7},
            ),
        ]
    )
    return mock


class TestCrossEncoderReranker:
    """Tests for CrossEncoderReranker."""

    @pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
    @pytest.mark.asyncio
    async def test_rerank_empty(self):
        """Test reranking with empty document list."""
        reranker = CrossEncoderReranker()
        result = await reranker.rerank("test query", [])
        assert result == []

    @pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
    @pytest.mark.asyncio
    async def test_rerank_orders_by_score(self, sample_documents):
        """Test that reranking orders documents by score."""
        reranker = CrossEncoderReranker()

        with patch.object(reranker.model, "predict") as mock_predict:
            mock_predict.return_value = [0.3, 0.9, 0.5]

            result = await reranker.rerank("python", sample_documents)

            assert len(result) == 3
            assert result[0].metadata["id"] == "doc_2"  # Highest score
            assert result[1].metadata["id"] == "doc_3"
            assert result[2].metadata["id"] == "doc_1"


class TestHybridRetriever:
    """Tests for HybridRetriever."""

    @pytest.mark.asyncio
    async def test_retrieve_combines_sources(self, mock_vector_retriever, sample_documents):
        """Test that hybrid retriever combines vector and BM25 results."""
        mock_reranker = AsyncMock()
        mock_reranker.rerank = AsyncMock(return_value=sample_documents)

        retriever = HybridRetriever(
            vector_retriever=mock_vector_retriever,
            documents=sample_documents,
            top_k=5,
            reranker=mock_reranker,
        )

        results = await retriever.retrieve("python programming")

        assert len(results) <= 5
        mock_vector_retriever.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_returns_source_documents(self, mock_vector_retriever, sample_documents):
        """Test that results are properly formatted as SourceDocuments."""
        mock_reranker = AsyncMock()
        mock_reranker.rerank = AsyncMock(return_value=sample_documents)

        retriever = HybridRetriever(
            vector_retriever=mock_vector_retriever,
            documents=sample_documents,
            top_k=5,
            reranker=mock_reranker,
        )

        results = await retriever.retrieve("test")

        for result in results:
            assert isinstance(result, SourceDocument)
            assert hasattr(result, "id")
            assert hasattr(result, "content")
            assert hasattr(result, "score")

"""Tests for semantic cache."""

from unittest.mock import patch

import pytest

from app.models import SourceDocument
from app.services.semantic_cache import SemanticCache


@pytest.fixture
def cache():
    """Create cache instance for testing."""
    return SemanticCache(
        similarity_threshold=0.95,
        ttl_seconds=3600,
    )


@pytest.fixture
def sample_embedding():
    """Create sample embedding vector."""
    return [0.1] * 1536  # Standard embedding dimension


@pytest.fixture
def sample_source():
    """Create sample source document."""
    return SourceDocument(
        id="test_doc",
        content="Test content",
        score=0.9,
    )


class TestSemanticCache:
    """Tests for SemanticCache."""

    @pytest.mark.asyncio
    async def test_store_and_lookup(self, cache, sample_embedding, sample_source):
        """Test storing and retrieving from cache."""
        query = "What is Python?"

        with patch.object(cache, "_get_embedding") as mock_embed:
            mock_embed.return_value = sample_embedding

            # Store
            await cache.store(
                query=query,
                response="Python is a programming language",
                sources=[sample_source],
            )

            # Lookup with same query
            result = await cache.lookup(query)

            assert result is not None
            assert result.response == "Python is a programming language"

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache, sample_embedding):
        """Test cache miss for dissimilar query."""
        query1 = "What is Python?"
        query2 = "Tell me about the weather"

        with patch.object(cache, "_get_embedding") as mock_embed:
            mock_embed.return_value = sample_embedding

            await cache.store(
                query=query1,
                response="Python answer",
                sources=[],
            )

            # Different embedding for lookup
            mock_embed.return_value = [0.9] * 1536

            result = await cache.lookup(query2)
            assert result is None

    @pytest.mark.asyncio
    async def test_invalidate(self, cache, sample_embedding, sample_source):
        """Test cache invalidation."""
        query = "Test query"

        with patch.object(cache, "_get_embedding") as mock_embed:
            mock_embed.return_value = sample_embedding

            await cache.store(
                query=query,
                response="Test response",
                sources=[sample_source],
            )

            # Should exist
            assert await cache.lookup(query) is not None

            # Invalidate
            await cache.invalidate(query)

            # Should be gone
            assert await cache.lookup(query) is None

    @pytest.mark.asyncio
    async def test_clear(self, cache, sample_embedding, sample_source):
        """Test clearing all cache entries."""
        with patch.object(cache, "_get_embedding") as mock_embed:
            mock_embed.return_value = sample_embedding

            await cache.store(
                query="query1",
                response="response1",
                sources=[sample_source],
            )
            await cache.store(
                query="query2",
                response="response2",
                sources=[sample_source],
            )

            await cache.clear()

            assert await cache.lookup("query1") is None
            assert await cache.lookup("query2") is None

    def test_get_stats(self, cache):
        """Test cache statistics."""
        stats = cache.get_stats()

        assert "entries" in stats
        assert "threshold" in stats
        assert "ttl_seconds" in stats
        assert stats["threshold"] == 0.95
        assert stats["ttl_seconds"] == 3600

    def test_cosine_similarity(self, cache):
        """Test cosine similarity calculation."""
        # Identical vectors
        vec = [1.0, 0.0, 0.0]
        assert cache._cosine_similarity(vec, vec) == pytest.approx(1.0)

        # Orthogonal vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        assert cache._cosine_similarity(vec1, vec2) == pytest.approx(0.0)

"""Semantic cache using embedding similarity for cache lookups."""

import hashlib
from typing import List, Optional

import numpy as np
import structlog
from langchain_openai import OpenAIEmbeddings

from app.config import settings
from app.models import CacheEntry, SourceDocument

logger = structlog.get_logger()


class SemanticCache:
    """Cache responses based on semantic similarity of queries.

    Uses embedding similarity to find cached responses for
    semantically similar queries, not just exact matches.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.95,
        ttl_seconds: int = 3600,
    ):
        """Initialize semantic cache.

        Args:
            similarity_threshold: Minimum similarity for cache hit.
            ttl_seconds: Time-to-live for cache entries.
        """
        self.embeddings = OpenAIEmbeddings(model=settings.openai_embedding_model)
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, CacheEntry] = {}
        self._embeddings_cache: dict[str, List[float]] = {}
        logger.info(
            "Initialized semantic cache",
            threshold=similarity_threshold,
            ttl=ttl_seconds,
        )

    async def lookup(self, query: str) -> Optional[CacheEntry]:
        """Look up cached response for semantically similar query.

        Args:
            query: The query to look up.

        Returns:
            Cached entry if found with sufficient similarity, None otherwise.
        """
        query_embedding = await self._get_embedding(query)

        best_match = None
        best_score = 0.0

        for _cache_key, entry in self._cache.items():
            score = self._cosine_similarity(query_embedding, entry.query_embedding)
            if score > best_score and score >= self.similarity_threshold:
                best_score = score
                best_match = entry

        if best_match:
            logger.info(
                "Semantic cache hit",
                query=query[:50],
                similarity=round(best_score, 4),
            )
            return best_match

        logger.debug("Semantic cache miss", query=query[:50])
        return None

    async def store(
        self,
        query: str,
        response: str,
        sources: List[SourceDocument],
    ) -> str:
        """Store response in semantic cache.

        Args:
            query: Original query.
            response: Generated response.
            sources: Source documents used.

        Returns:
            Cache key for the stored entry.
        """
        query_embedding = await self._get_embedding(query)
        cache_key = self._generate_key(query)

        self._cache[cache_key] = CacheEntry(
            query_embedding=query_embedding,
            response=response,
            sources=sources,
            ttl_seconds=self.ttl_seconds,
        )

        logger.info("Stored in semantic cache", key=cache_key[:16])
        return cache_key

    async def invalidate(self, query: str) -> bool:
        """Invalidate cache entry for a query.

        Args:
            query: Query to invalidate.

        Returns:
            True if entry was found and removed.
        """
        cache_key = self._generate_key(query)
        if cache_key in self._cache:
            del self._cache[cache_key]
            logger.info("Invalidated cache entry", key=cache_key[:16])
            return True
        return False

    async def clear(self):
        """Clear all cache entries."""
        self._cache.clear()
        self._embeddings_cache.clear()
        logger.info("Cleared semantic cache")

    def get_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats.
        """
        return {
            "entries": len(self._cache),
            "threshold": self.similarity_threshold,
            "ttl_seconds": self.ttl_seconds,
        }

    async def _get_embedding(self, text: str) -> List[float]:
        """Get or compute embedding for text.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector.
        """
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key not in self._embeddings_cache:
            embedding = await self.embeddings.aembed_query(text)
            self._embeddings_cache[cache_key] = embedding
        return self._embeddings_cache[cache_key]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            a: First vector.
            b: Second vector.

        Returns:
            Cosine similarity score.
        """
        a_arr = np.array(a)
        b_arr = np.array(b)
        return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))

    def _generate_key(self, query: str) -> str:
        """Generate cache key from query.

        Args:
            query: Query string.

        Returns:
            Cache key.
        """
        return hashlib.sha256(query.lower().strip().encode()).hexdigest()


# Singleton instance
semantic_cache = SemanticCache(
    similarity_threshold=settings.cache_similarity_threshold,
    ttl_seconds=settings.cache_ttl_seconds,
)

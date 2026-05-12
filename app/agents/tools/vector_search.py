"""Vector search tool for semantic document retrieval."""

from typing import Any, Dict, List, Optional

import structlog
from langchain_core.tools import tool

logger = structlog.get_logger()


class VectorSearchTool:
    """Tool for semantic vector search over documents."""

    def __init__(self, retriever: Optional[Any] = None) -> None:
        """Initialize vector search tool.

        Args:
            retriever: Vector store retriever instance.
        """
        self.retriever = retriever
        logger.info("Initialized vector search tool")

    def set_retriever(self, retriever: Any) -> None:
        """Set the retriever instance.

        Args:
            retriever: Vector store retriever.
        """
        self.retriever = retriever

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search documents using vector similarity.

        Args:
            query: Search query.
            top_k: Number of results to return.
            filter_metadata: Optional metadata filters.

        Returns:
            List of matching documents with scores.
        """
        if not self.retriever:
            logger.error("Retriever not configured")
            return []

        try:
            results = await self.retriever.ainvoke(query, k=top_k)
            return [
                {
                    "content": doc.page_content,
                    "score": doc.metadata.get("score", 0.0),
                    "metadata": doc.metadata,
                }
                for doc in results
            ]
        except Exception as e:
            logger.error("Vector search failed", error=str(e))
            return []


@tool
async def vector_search(query: str, top_k: int = 5) -> str:
    """Search the document vector store for relevant information.

    Args:
        query: The search query.
        top_k: Number of results to return.

    Returns:
        Formatted search results.
    """
    # This would be connected to the actual retriever
    return f"Vector search results for: {query}"

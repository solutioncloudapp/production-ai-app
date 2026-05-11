"""Cross-encoder reranker for post-retrieval ranking."""

from typing import List

import structlog
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

logger = structlog.get_logger()


class CrossEncoderReranker:
    """Reranks retrieved documents using a cross-encoder model."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """Initialize the reranker.

        Args:
            model_name: HuggingFace cross-encoder model name.
        """
        self.model = CrossEncoder(model_name)
        self.model_name = model_name
        logger.info("Initialized cross-encoder reranker", model=model_name)

    async def rerank(
        self, query: str, documents: List[Document], top_k: int = 10
    ) -> List[Document]:
        """Rerank documents based on query relevance.

        Args:
            query: The search query.
            documents: List of documents to rerank.
            top_k: Number of top documents to return.

        Returns:
            Reranked list of documents with updated scores.
        """
        if not documents:
            return []

        # Prepare pairs for cross-encoder
        pairs = [[query, doc.page_content] for doc in documents]

        # Get relevance scores
        scores = self.model.predict(pairs, show_progress_bar=False)

        # Attach scores to documents
        for doc, score in zip(documents, scores, strict=True):
            doc.metadata["rerank_score"] = float(score)
            doc.metadata["score"] = float(score)

        # Sort by score descending
        reranked = sorted(documents, key=lambda d: d.metadata["score"], reverse=True)

        logger.info(
            "Reranking complete",
            num_documents=len(documents),
            top_score=float(scores.max()) if len(scores) > 0 else 0,
        )

        return reranked[:top_k]

    def rerank_sync(
        self, query: str, documents: List[Document], top_k: int = 10
    ) -> List[Document]:
        """Synchronous version of rerank.

        Args:
            query: The search query.
            documents: List of documents to rerank.
            top_k: Number of top documents to return.

        Returns:
            Reranked list of documents.
        """
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self.rerank(query, documents, top_k)
        )

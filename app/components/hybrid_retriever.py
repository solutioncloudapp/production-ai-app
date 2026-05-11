"""Hybrid retriever combining vector search with BM25."""

from typing import List

import structlog
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from app.components.reranker import CrossEncoderReranker
from app.models import SourceDocument

logger = structlog.get_logger()


class HybridRetriever:
    """Combines dense vector search with sparse BM25 for better recall."""

    def __init__(
        self,
        vector_retriever,
        documents: List[Document],
        top_k: int = 10,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3,
    ):
        self.vector_retriever = vector_retriever
        self.bm25_retriever = BM25Retriever.from_documents(documents)
        self.reranker = CrossEncoderReranker()
        self.top_k = top_k
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight

    async def retrieve(self, query: str) -> List[SourceDocument]:
        """Retrieve documents using hybrid search with reranking.

        Args:
            query: The search query.

        Returns:
            List of ranked source documents.
        """
        logger.info("Starting hybrid retrieval", query=query)

        # Get results from both retrievers in parallel
        vector_docs = await self.vector_retriever.ainvoke(query)
        bm25_docs = self.bm25_retriever.invoke(query)

        # Combine and deduplicate
        combined = self._merge_results(vector_docs, bm25_docs)

        # Rerank with cross-encoder
        reranked = await self.reranker.rerank(query, combined)

        # Convert to SourceDocument format
        results = [
            SourceDocument(
                id=doc.metadata.get("id", str(i)),
                content=doc.page_content,
                score=doc.metadata.get("score", 0.0),
                metadata=doc.metadata,
            )
            for i, doc in enumerate(reranked[: self.top_k])
        ]

        logger.info("Hybrid retrieval complete", num_results=len(results))
        return results

    def _merge_results(
        self, vector_docs: List[Document], bm25_docs: List[Document]
    ) -> List[Document]:
        """Merge and deduplicate results from both retrievers.

        Uses reciprocal rank fusion for combining rankings.

        Args:
            vector_docs: Results from vector search.
            bm25_docs: Results from BM25 search.

        Returns:
            Merged and deduplicated document list.
        """
        doc_map = {}

        for rank, doc in enumerate(vector_docs):
            doc_id = doc.metadata.get("id", doc.page_content[:50])
            score = self.vector_weight / (rank + 1)
            if doc_id in doc_map:
                doc_map[doc_id]["score"] += score
            else:
                doc_map[doc_id] = {"doc": doc, "score": score}

        for rank, doc in enumerate(bm25_docs):
            doc_id = doc.metadata.get("id", doc.page_content[:50])
            score = self.bm25_weight / (rank + 1)
            if doc_id in doc_map:
                doc_map[doc_id]["score"] += score
            else:
                doc_map[doc_id] = {"doc": doc, "score": score}

        merged = sorted(doc_map.values(), key=lambda x: x["score"], reverse=True)
        return [item["doc"] for item in merged]

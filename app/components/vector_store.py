"""ChromaDB vector store for document storage and retrieval."""

import uuid
from typing import Any, Dict, List, Optional

import chromadb
import structlog
from chromadb.config import Settings as ChromaSettings
from langchain_core.documents import Document

from app.config import settings

logger = structlog.get_logger()


class ChromaVectorStore:
    """ChromaDB-backed vector store for semantic search.

    Features:
    - Persistent storage
    - Metadata filtering
    - Batch operations
    - Collection management
    """

    def __init__(self, collection_name: str = "documents") -> None:
        """Initialize ChromaDB vector store.

        Args:
            collection_name: Name of the ChromaDB collection.
        """
        self.collection_name = collection_name
        self._client: Any = None
        self._collection: Any = None
        logger.info(
            "Initialized ChromaDB vector store",
            collection=collection_name,
        )

    async def initialize(self) -> None:
        """Initialize or get the collection."""
        if self._client is None:
            try:
                self._client = chromadb.HttpClient(
                    host=settings.chroma_host,
                    port=settings.chroma_port,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
            except Exception as e:
                logger.warning(
                    "ChromaDB HTTP connection failed, using persistent fallback",
                    error=str(e),
                )
                self._client = chromadb.Client(
                    settings=ChromaSettings(
                        is_persistent=True,
                        persist_directory="./data/chroma",
                        anonymized_telemetry=False,
                    )
                )
        try:
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                "Collection ready",
                name=self.collection_name,
                count=self._collection.count(),
            )
        except Exception as e:
            logger.warning(
                "Failed to get collection, recreating",
                error=str(e),
            )
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )

    async def add_documents(
        self,
        documents: List[Document],
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Add documents to the vector store.

        Args:
            documents: List of LangChain Documents.
            ids: Optional list of IDs. Generated if not provided.

        Returns:
            List of document IDs.
        """
        if not self._collection:
            await self.initialize()

        doc_ids = ids or [str(uuid.uuid4())[:12] for _ in documents]
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]

        self._collection.add(
            documents=texts,
            ids=doc_ids,
            metadatas=metadatas,
        )

        logger.info(
            "Added documents to vector store",
            count=len(documents),
        )

        return doc_ids

    async def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Add raw texts to the vector store.

        Args:
            texts: List of text strings.
            metadatas: Optional list of metadata dicts.
            ids: Optional list of IDs.

        Returns:
            List of document IDs.
        """
        documents = [
            Document(page_content=text, metadata=metadatas[i] if metadatas else {}) for i, text in enumerate(texts)
        ]
        return await self.add_documents(documents, ids)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """Search for similar documents.

        Args:
            query: Search query.
            top_k: Number of results.
            filter_metadata: Optional metadata filter.

        Returns:
            List of matching Documents.
        """
        if not self._collection:
            await self.initialize()

        where = filter_metadata if filter_metadata else None

        results = self._collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where,
        )

        documents = []
        for i in range(len(results["ids"][0])):
            doc = Document(
                page_content=results["documents"][0][i],
                metadata={
                    "id": results["ids"][0][i],
                    "score": results["distances"][0][i] if "distances" in results else 0.0,
                    **(results["metadatas"][0][i] if results.get("metadatas") else {}),
                },
            )
            documents.append(doc)

        logger.debug(
            "Vector search complete",
            query=query[:50],
            results=len(documents),
        )

        return documents

    async def delete(self, ids: List[str]) -> bool:
        """Delete documents by ID.

        Args:
            ids: List of document IDs to delete.

        Returns:
            True if successful.
        """
        if not self._collection:
            await self.initialize()

        self._collection.delete(ids=ids)
        logger.info("Deleted documents", count=len(ids))
        return True

    async def clear(self) -> None:
        """Clear all documents from the collection."""
        if not self._collection:
            await self.initialize()

        all_ids = self._collection.get()["ids"]
        if all_ids:
            self._collection.delete(ids=all_ids)
        logger.info("Cleared vector store")

    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics.

        Returns:
            Dictionary with stats.
        """
        if not self._collection:
            return {"count": 0, "collection": self.collection_name}

        return {
            "count": self._collection.count(),
            "collection": self.collection_name,
        }

    async def to_langchain_retriever(self) -> "ChromaRetriever":
        """Create a LangChain-compatible retriever.

        Returns:
            Async-compatible retriever wrapper.
        """
        return ChromaRetriever(self)


class ChromaRetriever:
    """LangChain-compatible async retriever wrapper for ChromaDB."""

    def __init__(self, vector_store: ChromaVectorStore, top_k: int = 10):
        """Initialize retriever.

        Args:
            vector_store: ChromaDB vector store instance.
            top_k: Number of documents to retrieve.
        """
        self.vector_store = vector_store
        self.top_k = top_k

    async def ainvoke(self, query: str, k: Optional[int] = None) -> List[Document]:
        """Async invoke for LangChain compatibility.

        Args:
            query: Search query.
            k: Optional override for top_k.

        Returns:
            List of matching Documents.
        """
        return await self.vector_store.search(query, top_k=k or self.top_k)

    def invoke(self, query: str, k: Optional[int] = None) -> List[Document]:
        """Sync invoke for LangChain compatibility.

        Args:
            query: Search query.
            k: Optional override for top_k.

        Returns:
            List of matching Documents.
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.ainvoke(query, k))

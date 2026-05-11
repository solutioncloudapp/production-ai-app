"""Main RAG pipeline orchestrating retrieval, grading, and generation."""

import time
from typing import List, Optional

import structlog
from langchain_openai import ChatOpenAI

from app.agents.document_grader import DocumentGrader
from app.agents.query_decomposer import QueryDecomposer
from app.components.hybrid_retriever import HybridRetriever
from app.config import settings
from app.models import (
    PipelineResult,
    RouteResult,
    SourceDocument,
)
from app.prompts.registry import prompt_registry
from app.services.query_rewriter import query_rewriter
from app.services.semantic_cache import semantic_cache
from observability.tracer import tracer

logger = structlog.get_logger()


class RAGPipeline:
    """Main RAG pipeline with self-correcting retrieval."""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.1,
        )
        self.grader = DocumentGrader()
        self.decomposer = QueryDecomposer()
        self.retriever: Optional[HybridRetriever] = None

    def set_retriever(self, retriever: HybridRetriever):
        """Set the hybrid retriever instance.

        Args:
            retriever: The hybrid retriever to use.
        """
        self.retriever = retriever

    async def execute(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        route: Optional[RouteResult] = None,
    ) -> PipelineResult:
        """Execute the full RAG pipeline.

        Pipeline stages:
        1. Check semantic cache
        2. Rewrite query with conversation context
        3. Decompose complex queries
        4. Retrieve and grade documents
        5. Generate response
        6. Store in cache

        Args:
            query: User query.
            conversation_id: Optional conversation ID for context.
            route: Optional routing result.

        Returns:
            PipelineResult with response and metadata.
        """
        start_time = time.time()

        with tracer.start_span("rag_pipeline") as span:
            span.set_attribute("query_length", len(query))
            span.set_attribute("conversation_id", conversation_id or "none")

            # Stage 1: Check cache
            cached = await semantic_cache.lookup(query)
            if cached:
                span.set_attribute("cache_hit", True)
                logger.info("Cache hit", query=query[:50])
                return PipelineResult(
                    response=cached.response,
                    sources=cached.sources,
                    cache_hit=True,
                )

            span.set_attribute("cache_hit", False)

            # Stage 2: Rewrite query with context
            rewritten_query = await query_rewriter.rewrite(
                query, conversation_id=conversation_id
            )
            span.set_attribute("rewritten_query", rewritten_query)

            # Stage 3: Decompose if complex
            sub_queries = await self.decomposer.decompose(rewritten_query)
            span.set_attribute("num_sub_queries", len(sub_queries))

            # Stage 4: Retrieve and grade
            all_docs = []
            for sq in sub_queries:
                if self.retriever:
                    docs = await self.retriever.retrieve(sq)
                    graded = await self.grader.grade(sq, docs)
                    all_docs.extend(graded)

            # Deduplicate and rank
            unique_docs = self._deduplicate(all_docs)
            span.set_attribute("num_documents", len(unique_docs))

            # Stage 5: Generate response
            prompt = prompt_registry.get("rag_generation")
            context = "\n\n".join(doc.content for doc in unique_docs[:5])

            messages = prompt.format_messages(
                context=context,
                query=rewritten_query,
            )

            response = await self.llm.ainvoke(messages)
            response_text = response.content

            # Get token counts
            input_tokens = response.response_metadata.get("token_usage", {}).get(
                "prompt_tokens", 0
            )
            output_tokens = response.response_metadata.get("token_usage", {}).get(
                "completion_tokens", 0
            )

            # Stage 6: Cache result
            await semantic_cache.store(
                query=query,
                response=response_text,
                sources=unique_docs[:5],
            )

            latency = (time.time() - start_time) * 1000

            span.set_attribute("input_tokens", input_tokens)
            span.set_attribute("output_tokens", output_tokens)
            span.set_attribute("latency_ms", latency)

            logger.info(
                "Pipeline complete",
                latency_ms=latency,
                num_docs=len(unique_docs),
                cache_hit=False,
            )

            return PipelineResult(
                response=response_text,
                sources=unique_docs[:5],
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_hit=False,
                latency_ms=latency,
            )

    def _deduplicate(self, documents: List[SourceDocument]) -> List[SourceDocument]:
        """Remove duplicate documents keeping highest score.

        Args:
            documents: List of documents possibly with duplicates.

        Returns:
            Deduplicated list sorted by score.
        """
        seen = {}
        for doc in documents:
            if doc.id not in seen or doc.score > seen[doc.id].score:
                seen[doc.id] = doc
        return sorted(seen.values(), key=lambda d: d.score, reverse=True)

    async def shutdown(self):
        """Clean shutdown of pipeline resources."""
        logger.info("Shutting down RAG pipeline")


# Singleton instance
rag_pipeline = RAGPipeline()

"""Document grader with self-correction loop for relevance scoring."""

from typing import List

import structlog
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import settings
from app.models import SourceDocument
from app.prompts.registry import prompt_registry

logger = structlog.get_logger()


class GradeResult(BaseModel):
    """Result from document grading."""

    grade: str = Field(description="RELEVANT, PARTIAL, or IRRELEVANT")
    score: float = Field(description="Numeric score 0-1")
    reason: str = Field(description="Brief reason for the grade")


class DocumentGrader:
    """Grades document relevance with self-correction capability.

    Features:
    - LLM-based relevance scoring
    - Self-correction on low-confidence grades
    - Batch grading support
    """

    def __init__(self, confidence_threshold: float = 0.7, max_retries: int = 2):
        """Initialize document grader.

        Args:
            confidence_threshold: Threshold for self-correction trigger.
            max_retries: Maximum self-correction attempts.
        """
        self.llm = ChatOpenAI(model=settings.openai_model, temperature=0)
        self.confidence_threshold = confidence_threshold
        self.max_retries = max_retries
        logger.info(
            "Initialized document grader",
            threshold=confidence_threshold,
            max_retries=max_retries,
        )

    async def grade(
        self, query: str, documents: List[SourceDocument]
    ) -> List[SourceDocument]:
        """Grade documents for relevance to query.

        Filters out irrelevant documents and scores remaining ones.

        Args:
            query: User query.
            documents: List of documents to grade.

        Returns:
            Filtered and scored documents.
        """
        if not documents:
            return []

        graded = []
        for doc in documents:
            result = await self._grade_with_correction(query, doc.content)

            if result.grade == "IRRELEVANT":
                logger.debug("Document filtered as irrelevant", doc_id=doc.id)
                continue

            # Update document with grade info
            doc.metadata["grade"] = result.grade
            doc.metadata["grade_score"] = result.score
            doc.metadata["grade_reason"] = result.reason
            doc.score = result.score

            graded.append(doc)

        # Sort by grade score descending
        graded.sort(key=lambda d: d.score, reverse=True)

        logger.info(
            "Document grading complete",
            total=len(documents),
            passed=len(graded),
            filtered=len(documents) - len(graded),
        )

        return graded

    async def _grade_with_correction(
        self, query: str, content: str
    ) -> GradeResult:
        """Grade with self-correction loop.

        If confidence is low, re-evaluate with modified prompt.

        Args:
            query: User query.
            content: Document content.

        Returns:
            GradeResult with grade and confidence.
        """
        result = await self._grade_once(query, content)

        # Self-correction: if score is near threshold, re-evaluate
        if (
            abs(result.score - self.confidence_threshold) < 0.1
            and result.grade != "IRRELEVANT"
        ):
            logger.debug(
                "Low confidence grade, applying self-correction",
                score=result.score,
            )
            result = await self._grade_with_stricter_criteria(query, content)

        return result

    async def _grade_once(self, query: str, content: str) -> GradeResult:
        """Single grading pass.

        Args:
            query: User query.
            content: Document content.

        Returns:
            GradeResult.
        """
        prompt = prompt_registry.get("document_grade")
        messages = prompt.format_messages(query=query, document=content[:2000])

        response = await self.llm.with_structured_output(GradeResult).ainvoke(
            messages
        )

        # Map grade to numeric score
        score_map = {
            "RELEVANT": 0.9,
            "PARTIAL": 0.5,
            "IRRELEVANT": 0.1,
        }
        response.score = score_map.get(response.grade, 0.5)

        return response

    async def _grade_with_stricter_criteria(
        self, query: str, content: str
    ) -> GradeResult:
        """Re-grade with stricter criteria for borderline cases.

        Args:
            query: User query.
            content: Document content.

        Returns:
            Updated GradeResult.
        """
        stricter_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a strict document grader. Re-evaluate the document relevance with higher standards.

Only grade as RELEVANT if the document directly and comprehensively addresses the query.
Otherwise, downgrade to PARTIAL or IRRELEVANT."""),
            ("human", "Query: {query}\n\nDocument: {document}"),
        ])

        messages = stricter_prompt.format_messages(
            query=query, document=content[:2000]
        )
        response = await self.llm.with_structured_output(GradeResult).ainvoke(
            messages
        )

        score_map = {
            "RELEVANT": 0.9,
            "PARTIAL": 0.5,
            "IRRELEVANT": 0.1,
        }
        response.score = score_map.get(response.grade, 0.5)

        return response

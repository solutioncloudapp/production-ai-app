"""Offline evaluation pipeline for batch testing against golden dataset."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import structlog
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import BaseModel, Field

from app.config import settings
from app.models import EvalResult
from app.prompts.registry import prompt_registry

logger = structlog.get_logger()


class EvalMetrics(BaseModel):
    """Aggregated evaluation metrics."""

    total_tests: int
    passed_tests: int
    avg_relevance: float = Field(ge=0, le=5)
    avg_faithfulness: float = Field(ge=0, le=5)
    avg_answer_relevance: float = Field(ge=0, le=5)
    avg_latency_ms: float
    pass_rate: float = Field(ge=0, le=100)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OfflineEvaluator:
    """Runs batch evaluation against golden dataset.

    Metrics:
    - Relevance: How relevant is the answer to the question
    - Faithfulness: Is the answer faithful to the context
    - Answer Relevance: How well does the answer address the question
    - Latency: Response time
    """

    def __init__(self):
        """Initialize offline evaluator."""
        self.llm = ChatOpenAI(model=settings.eval_model, temperature=0)
        self.embeddings = OpenAIEmbeddings(model=settings.openai_embedding_model)
        self._dataset: List[Dict] = []
        logger.info("Initialized offline evaluator")

    def load_dataset(self, path: Optional[str] = None) -> int:
        """Load golden dataset from JSON file.

        Args:
            path: Path to dataset file.

        Returns:
            Number of test cases loaded.
        """
        dataset_path = Path(path or settings.eval_dataset_path)
        with open(dataset_path) as f:
            self._dataset = json.load(f)
        logger.info("Loaded golden dataset", num_cases=len(self._dataset))
        return len(self._dataset)

    async def evaluate_all(self) -> tuple[List[EvalResult], EvalMetrics]:
        """Run evaluation on all test cases.

        Returns:
            Tuple of (individual results, aggregated metrics).
        """
        if not self._dataset:
            self.load_dataset()

        results = []
        for case in self._dataset:
            result = await self._evaluate_case(case)
            results.append(result)

        metrics = self._compute_metrics(results)
        return results, metrics

    async def evaluate_subset(
        self, category: Optional[str] = None, difficulty: Optional[str] = None
    ) -> tuple[List[EvalResult], EvalMetrics]:
        """Evaluate a subset of test cases.

        Args:
            category: Filter by category.
            difficulty: Filter by difficulty.

        Returns:
            Tuple of (results, metrics).
        """
        if not self._dataset:
            self.load_dataset()

        subset = self._dataset
        if category:
            subset = [c for c in subset if c.get("category") == category]
        if difficulty:
            subset = [c for c in subset if c.get("difficulty") == difficulty]

        results = []
        for case in subset:
            result = await self._evaluate_case(case)
            results.append(result)

        metrics = self._compute_metrics(results)
        return results, metrics

    async def _evaluate_case(self, case: Dict) -> EvalResult:
        """Evaluate a single test case.

        Args:
            case: Test case from golden dataset.

        Returns:
            EvalResult with scores.
        """
        start_time = time.time()
        query = case["query"]
        expected = case["expected_answer"]

        # Simulate getting actual answer (in production, call the pipeline)
        actual = await self._get_answer(query)

        # Evaluate relevance
        relevance = await self._score_relevance(query, actual)

        # Evaluate faithfulness
        faithfulness = await self._score_faithfulness(expected, actual)

        # Evaluate answer relevance
        answer_relevance = await self._score_answer_relevance(query, actual)

        latency = (time.time() - start_time) * 1000

        return EvalResult(
            query=query,
            expected_answer=expected,
            actual_answer=actual,
            relevance_score=relevance,
            faithfulness_score=faithfulness,
            answer_relevance_score=answer_relevance,
            latency_ms=latency,
        )

    async def _get_answer(self, query: str) -> str:
        """Get answer from the system (mock for evaluation).

        Args:
            query: Test query.

        Returns:
            Generated answer.
        """
        # In production, this would call the actual RAG pipeline
        # For evaluation, we use a simple generation
        prompt = f"Answer the following question concisely: {query}"
        response = await self.llm.ainvoke([("user", prompt)])
        return response.content

    async def _score_relevance(self, question: str, answer: str) -> float:
        """Score answer relevance to question.

        Args:
            question: Original question.
            answer: Generated answer.

        Returns:
            Relevance score 1-5.
        """
        prompt = prompt_registry.get("eval_relevance")
        messages = prompt.format_messages(question=question, answer=answer)
        response = await self.llm.ainvoke(messages)

        # Extract numeric score
        score_str = response.content.strip()
        try:
            return float(score_str[0]) if score_str[0].isdigit() else 3.0
        except (ValueError, IndexError):
            return 3.0

    async def _score_faithfulness(self, context: str, answer: str) -> float:
        """Score answer faithfulness to context.

        Args:
            context: Source context.
            answer: Generated answer.

        Returns:
            Faithfulness score 1-5.
        """
        prompt = prompt_registry.get("eval_faithfulness")
        messages = prompt.format_messages(context=context, answer=answer)
        response = await self.llm.ainvoke(messages)

        score_str = response.content.strip()
        try:
            return float(score_str[0]) if score_str[0].isdigit() else 3.0
        except (ValueError, IndexError):
            return 3.0

    async def _score_answer_relevance(self, question: str, answer: str) -> float:
        """Score how well answer addresses the question.

        Args:
            question: Original question.
            answer: Generated answer.

        Returns:
            Answer relevance score 1-5.
        """
        # Embedding-based similarity as proxy
        q_embed = await self.embeddings.aembed_query(question)
        a_embed = await self.embeddings.aembed_query(answer)

        # Cosine similarity scaled to 1-5
        import numpy as np

        similarity = float(np.dot(q_embed, a_embed) / (np.linalg.norm(q_embed) * np.linalg.norm(a_embed)))
        return round(1 + similarity * 4, 2)

    def _compute_metrics(self, results: List[EvalResult]) -> EvalMetrics:
        """Compute aggregated metrics from results.

        Args:
            results: List of individual evaluation results.

        Returns:
            Aggregated EvalMetrics.
        """
        if not results:
            return EvalMetrics(
                total_tests=0,
                passed_tests=0,
                avg_relevance=0,
                avg_faithfulness=0,
                avg_answer_relevance=0,
                avg_latency_ms=0,
                pass_rate=0,
            )

        passed = sum(1 for r in results if r.relevance_score >= 3.0 and r.faithfulness_score >= 3.0)

        return EvalMetrics(
            total_tests=len(results),
            passed_tests=passed,
            avg_relevance=sum(r.relevance_score for r in results) / len(results),
            avg_faithfulness=sum(r.faithfulness_score for r in results) / len(results),
            avg_answer_relevance=sum(r.answer_relevance_score for r in results) / len(results),
            avg_latency_ms=sum(r.latency_ms for r in results) / len(results),
            pass_rate=(passed / len(results)) * 100,
        )

    def save_results(self, results: List[EvalResult], metrics: EvalMetrics, path: str = "evaluation/eval_results"):
        """Save evaluation results to file.

        Args:
            results: Individual results.
            metrics: Aggregated metrics.
            path: Output directory.
        """
        output_dir = Path(path)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Save individual results
        results_path = output_dir / f"results_{timestamp}.json"
        with open(results_path, "w") as f:
            json.dump([r.model_dump() for r in results], f, indent=2, default=str)

        # Save metrics
        metrics_path = output_dir / f"metrics_{timestamp}.json"
        with open(metrics_path, "w") as f:
            json.dump(metrics.model_dump(), f, indent=2, default=str)

        logger.info(
            "Evaluation results saved",
            results_path=str(results_path),
            metrics_path=str(metrics_path),
        )


# Singleton instance
offline_evaluator = OfflineEvaluator()

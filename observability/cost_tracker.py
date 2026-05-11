"""Cost tracking per query and per component."""

from datetime import datetime
from typing import Dict, List, Optional

import structlog

from app.models import CostRecord

logger = structlog.get_logger()

# Token cost per model (per 1M tokens)
MODEL_COSTS = {
    "gpt-4o": {"input": 5.0, "output": 15.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    "gpt-4": {"input": 30.0, "output": 60.0},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    "text-embedding-3-small": {"input": 0.02, "output": 0},
    "text-embedding-3-large": {"input": 0.13, "output": 0},
}


class CostTracker:
    """Tracks and reports costs per query and per component.

    Features:
    - Per-query cost calculation
    - Per-model cost aggregation
    - Per-conversation cost tracking
    - Budget alerts
    - Cost breakdown by component
    """

    def __init__(self, budget_limit: float = 100.0):
        """Initialize cost tracker.

        Args:
            budget_limit: Daily budget limit in USD.
        """
        self.budget_limit = budget_limit
        self._records: List[CostRecord] = []
        self._conversation_costs: Dict[str, float] = {}
        self._daily_cost: float = 0.0
        self._last_reset: datetime = datetime.utcnow()
        logger.info(
            "Initialized cost tracker",
            budget_limit=budget_limit,
        )

    def initialize(self):
        """Initialize cost tracker."""
        logger.info("Cost tracker initialized")

    def record(
        self,
        conversation_id: Optional[str],
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> CostRecord:
        """Record a cost entry.

        Args:
            conversation_id: Optional conversation ID.
            model: Model name used.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Recorded CostRecord.
        """
        cost = self._calculate_cost(model, input_tokens, output_tokens)

        record = CostRecord(
            conversation_id=conversation_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )

        self._records.append(record)
        self._daily_cost += cost

        if conversation_id:
            self._conversation_costs[conversation_id] = (
                self._conversation_costs.get(conversation_id, 0) + cost
            )

        # Check budget
        if self._daily_cost > self.budget_limit:
            logger.warning(
                "Budget exceeded",
                daily_cost=self._daily_cost,
                limit=self.budget_limit,
            )

        logger.debug(
            "Cost recorded",
            model=model,
            cost=round(cost, 6),
            daily_total=round(self._daily_cost, 4),
        )

        return record

    def get_conversation_cost(self, conversation_id: str) -> float:
        """Get total cost for a conversation.

        Args:
            conversation_id: Conversation ID.

        Returns:
            Total cost in USD.
        """
        return self._conversation_costs.get(conversation_id, 0.0)

    def get_daily_cost(self) -> float:
        """Get total cost for today.

        Returns:
            Daily cost in USD.
        """
        self._check_reset()
        return self._daily_cost

    def get_model_breakdown(self) -> Dict[str, Dict]:
        """Get cost breakdown by model.

        Returns:
            Dictionary with per-model cost stats.
        """
        breakdown: Dict[str, Dict] = {}
        for record in self._records:
            if record.model not in breakdown:
                breakdown[record.model] = {
                    "cost": 0.0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "queries": 0,
                }
            breakdown[record.model]["cost"] += record.cost_usd
            breakdown[record.model]["input_tokens"] += record.input_tokens
            breakdown[record.model]["output_tokens"] += record.output_tokens
            breakdown[record.model]["queries"] += 1

        return breakdown

    def get_budget_status(self) -> Dict:
        """Get current budget status.

        Returns:
            Dictionary with budget info.
        """
        self._check_reset()
        remaining = self.budget_limit - self._daily_cost
        return {
            "daily_cost": round(self._daily_cost, 4),
            "budget_limit": self.budget_limit,
            "remaining": round(remaining, 4),
            "utilization_pct": round(
                (self._daily_cost / self.budget_limit) * 100, 2
            ) if self.budget_limit > 0 else 0,
        }

    def _calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate cost for token usage.

        Args:
            model: Model name.
            input_tokens: Input token count.
            output_tokens: Output token count.

        Returns:
            Cost in USD.
        """
        pricing = MODEL_COSTS.get(model, {"input": 1.0, "output": 2.0})
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    def _check_reset(self):
        """Reset daily cost if day has changed."""
        now = datetime.utcnow()
        if now.date() > self._last_reset.date():
            self._daily_cost = 0.0
            self._last_reset = now
            logger.info("Daily cost reset")

    def reset(self):
        """Reset all cost tracking."""
        self._records.clear()
        self._conversation_costs.clear()
        self._daily_cost = 0.0
        self._last_reset = datetime.utcnow()
        logger.info("Cost tracker reset")


# Singleton instance
cost_tracker = CostTracker()

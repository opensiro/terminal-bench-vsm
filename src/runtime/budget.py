"""budget — enforcement for S1 (CONTRACT §2 budget)."""
from __future__ import annotations
import time
from dataclasses import dataclass, field


@dataclass
class BudgetTracker:
    """Tracks time/tokens/actions against budget ceiling."""

    time_seconds: int
    tokens: int
    actions: int
    _start: float = field(default_factory=time.time)
    _tokens_used: int = 0
    _actions_taken: int = 0

    def elapsed(self) -> float:
        return time.time() - self._start

    @property
    def time_exhausted(self) -> bool:
        return self.elapsed() >= self.time_seconds

    @property
    def tokens_exhausted(self) -> bool:
        return self._tokens_used >= self.tokens

    @property
    def actions_exhausted(self) -> bool:
        return self._actions_taken >= self.actions

    @property
    def exhausted(self) -> bool:
        return self.time_exhausted or self.tokens_exhausted or self.actions_exhausted

    def consume(self, tokens: int = 0, actions: int = 1):
        self._tokens_used += tokens
        self._actions_taken += actions

    def remaining_time(self) -> float:
        return max(0, self.time_seconds - self.elapsed())

    def summary(self) -> dict:
        return {
            "time_used": round(self.elapsed(), 2),
            "tokens_used": self._tokens_used,
            "actions_taken": self._actions_taken,
        }

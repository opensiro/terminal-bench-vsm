"""types — S2 coordinator data structures (PIPELINES.md §2)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AttemptRecord:
    """One attempt in retry history (for oscillation/contradiction detection)."""
    attempt_num: int
    failure_class: str          # class id from taxonomy (or "Unknown")
    policy_applied: str         # policy id (or "EscalateToS3")
    verdict: str                # task_failed | budget_exhausted | task_resolved | unknown
    env_changes: list[str] = field(default_factory=list)


@dataclass
class RetryHistory:
    """Per-task retry history (PIPELINES.md §3 — oscillation needs sequence)."""
    task_id: str
    attempts: list[AttemptRecord] = field(default_factory=list)

    def add(self, record: AttemptRecord) -> None:
        self.attempts.append(record)

    @property
    def attempt_count(self) -> int:
        return len(self.attempts)

    @property
    def last(self) -> AttemptRecord | None:
        return self.attempts[-1] if self.attempts else None


@dataclass
class ResourceClaim:
    """Resource claim for multi-agent conflict detection (PIPELINES.md §4).

    Two attempts with overlapping claims conflict (queue, not parallel).
    """
    task_id: str
    workspace: str              # task-scoped workspace path
    git_ref: str | None = None  # git ref being operated on (None = no git)
    ports: list[int] = field(default_factory=list)  # ports held by the task


@dataclass
class AuthorizationResult:
    """Result of S2 authorize_retry (PIPELINES.md §2 — 4-check pipeline)."""
    authorized: bool
    blocked_by: str | None = None  # anti_repeat | oscillation | resource_overlap | output_contradiction | circumvent_recovery | None
    reason: str = ""

    @property
    def blocked(self) -> bool:
        return not self.authorized

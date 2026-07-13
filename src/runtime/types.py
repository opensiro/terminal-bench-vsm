"""types — S1 input/output contracts (T2 CONTRACT §2, §3)."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Verdict(str, Enum):
    TASK_RESOLVED = "task_resolved"
    TASK_FAILED = "task_failed"
    BUDGET_EXHAUSTED = "budget_exhausted"
    UNKNOWN = "unknown"


@dataclass
class Budget:
    time_seconds: int
    tokens: int
    actions: int


@dataclass
class RecoveryDirective:
    failure_class: str | None = None
    policy_applied: str | None = None
    env_changes: list[str] = field(default_factory=list)
    policy_attempt: int = 0


@dataclass
class S1Input:
    """S1 input contract (CONTRACT §2)."""

    task_prompt: str
    task_spec: str | None = None
    tools_transport: str = "stdio"
    tools_config_ref: str | None = None
    workspace: Path = Path(".")
    shell: str = "bash"
    git_available: bool = True
    budget: Budget = field(default_factory=lambda: Budget(300, 100000, 50))
    recovery_directive: RecoveryDirective | None = None


@dataclass
class TraceEntry:
    """Single trace entry (CONTRACT §3)."""

    idx: int
    action: dict[str, Any]  # {tool, args}
    observation: str
    ts: str
    cost: dict[str, float] = field(default_factory=lambda: {"tokens": 0, "time_seconds": 0.0})


@dataclass
class FailureObservation:
    """Failure observation for S3-classifier (CONTRACT §6)."""

    kind: str  # error_string | exit_code | timeout | signal
    value: Any
    source: str = "stderr"
    command: str | None = None
    action: str | None = None
    deadline_seconds: int | None = None
    at_action: int = 0


@dataclass
class Artifact:
    """Filesystem/git change (CONTRACT §3)."""

    path: str
    op: str  # created | modified | deleted


@dataclass
class S1Output:
    """S1 output contract (CONTRACT §3)."""

    trace: list[TraceEntry] = field(default_factory=list)
    verdict: Verdict = Verdict.UNKNOWN
    artifacts: list[Artifact] = field(default_factory=list)
    failure_observations: list[FailureObservation] = field(default_factory=list)
    cost: dict[str, float] = field(default_factory=lambda: {"time_used": 0.0, "tokens_used": 0, "actions_taken": 0})

"""store — SessionStore: per-task shared state for multi-agent S1 (VSM-007).

In-memory store (not persisted). Thread-safe (RLock) for concurrent sub-agents.
TTL-based cleanup: sessions expire after ttl seconds.

Shared state structure (from session_sync/README.md contract):
  - plan: list[dict]            # steps from planner
  - artifacts: list[str]        # created/modified paths
  - exploration_map: dict       # {path: status}
  - intermediate_results: dict  # {step_id: result}
  - verifier_feedback: dict     # {step_id: {pass: bool, reason: str}}
"""
from __future__ import annotations
import threading
import time
from dataclasses import dataclass, field
from typing import Any


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _new_shared_state() -> dict[str, Any]:
    """Initialize empty shared_state structure."""
    return {
        "plan": [],                 # list of step dicts from planner
        "artifacts": [],            # created/modified paths
        "exploration_map": {},      # {path: status}
        "intermediate_results": {}, # {step_id: result}
        "verifier_feedback": {},    # {step_id: {pass: bool, reason: str}}
    }


@dataclass
class Session:
    """Per-task session for multi-agent coordination (VSM-007 Split).

    Fields match session_sync/README.md contract.
    """
    task_id: str
    agents: list[str]              # ["planner", "executor", "verifier"]
    shared_state: dict[str, Any] = field(default_factory=_new_shared_state)
    created: str = field(default_factory=_now_iso)
    ttl: int = 3600                # seconds; cleanup after expiry

    @property
    def expired(self) -> bool:
        """Check if session has exceeded its TTL."""
        created_ts = time.mktime(time.strptime(self.created, "%Y-%m-%dT%H:%M:%S"))
        return (time.time() - created_ts) > self.ttl


class SessionStore:
    """Thread-safe in-memory session store for multi-agent S1.

    Isolation: per-task (task_id keyed). Does not leak between tasks.
    TTL: sessions auto-expire; get() returns None for expired sessions.
    """

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._lock = threading.RLock()

    def create(
        self, task_id: str, agents: list[str], ttl: int = 3600
    ) -> Session:
        """Create a new session. Raises if task_id already has an active session."""
        with self._lock:
            self._cleanup_expired_locked()
            if task_id in self._sessions:
                raise ValueError(f"session already exists for task_id={task_id}")
            session = Session(task_id=task_id, agents=list(agents), ttl=ttl)
            self._sessions[task_id] = session
            return session

    def get(self, task_id: str) -> Session | None:
        """Get session by task_id. Returns None if not found or expired."""
        with self._lock:
            session = self._sessions.get(task_id)
            if session is None:
                return None
            if session.expired:
                del self._sessions[task_id]
                return None
            return session

    def update(self, task_id: str, key: str, value: Any) -> None:
        """Update shared_state[key] = value. Raises if session or key not found."""
        with self._lock:
            session = self._sessions.get(task_id)
            if session is None:
                raise KeyError(f"session not found: task_id={task_id}")
            if key not in session.shared_state:
                raise KeyError(f"shared_state key not found: {key}")
            session.shared_state[key] = value

    def read(self, task_id: str, key: str) -> Any:
        """Read shared_state[key]. Raises if session or key not found."""
        with self._lock:
            session = self._sessions.get(task_id)
            if session is None:
                raise KeyError(f"session not found: task_id={task_id}")
            if key not in session.shared_state:
                raise KeyError(f"shared_state key not found: {key}")
            return session.shared_state[key]

    def append(self, task_id: str, key: str, value: Any) -> None:
        """Append value to a list in shared_state[key]. Raises if session/key not found or key is not a list."""
        with self._lock:
            session = self._sessions.get(task_id)
            if session is None:
                raise KeyError(f"session not found: task_id={task_id}")
            if key not in session.shared_state:
                raise KeyError(f"shared_state key not found: {key}")
            target = session.shared_state[key]
            if not isinstance(target, list):
                raise TypeError(f"shared_state[{key}] is not a list (got {type(target).__name__})")
            target.append(value)

    def close(self, task_id: str) -> None:
        """Close and remove a session (cleanup after task completion)."""
        with self._lock:
            self._sessions.pop(task_id, None)

    def cleanup_expired(self) -> int:
        """Remove all expired sessions. Returns count removed."""
        with self._lock:
            return self._cleanup_expired_locked()

    def _cleanup_expired_locked(self) -> int:
        """Internal: remove expired sessions (caller holds lock)."""
        expired_ids = [
            tid for tid, s in self._sessions.items() if s.expired
        ]
        for tid in expired_ids:
            del self._sessions[tid]
        return len(expired_ids)

    @property
    def active_count(self) -> int:
        """Number of active (non-expired) sessions."""
        with self._lock:
            self._cleanup_expired_locked()
            return len(self._sessions)

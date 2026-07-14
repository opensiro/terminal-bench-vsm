"""state_bus — inter-process shared state for agent runtime (VSM-013).

File-based shared state (JSON in <root>/<task_id>/state.json), process-safe via
atomic writes (write temp → rename). Per-task namespace, TTL cleanup.

Generalizes session_sync.SessionStore (VSM-007, in-process) to multi-process:
goose-agents run as subprocesses and exchange state via the filesystem, not
in-memory. This is the coordination substrate for full agentization (VSM-012).

API mirrors SessionStore (create/get/update/read/append/close) + recovery-cycle
fields (s1_output, s3_classification, s3star_audit, s2_authorization,
recovery_directive, retry_history) so orchestrator.protocol can use it directly.

Atomicity: each write serializes the whole TaskState to a temp file then renames
(POSIX atomic). This avoids partial reads from concurrent agents. For multi-write
transactions, use the lock() context manager (flock on a .lock sidecar file).

Stateless (CONTRACT §5): the bus holds per-task state during a recovery cycle;
it is NOT cross-task memory. Each task gets a fresh namespace.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
import fcntl
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _empty_recovery_state() -> dict[str, Any]:
    """Empty recovery-cycle state. Agents read inputs, write outputs here.

    Schema (consumed by protocol.py steps):
      task_input:        {task_prompt, workspace, budget, ...}  — orchestrator writes
      s1_output:         {verdict, trace, failure_observations, cost}  — S1 agent writes
      s3_classification: {failure_class, recovery_policy, confidence, evidence}  — S3 agent
      s3star_audit:      {passed, findings, algedonic}  — S3* agent (cross-provider)
      recovery_result:   {applied, env_changes, blocked}  — recovery executor
      s2_authorization:  {authorized, blocked_by, reason}  — S2 agent
      recovery_directive:{failure_class, policy_applied, env_changes, policy_attempt}
      retry_history:     [list of attempt records]
    """
    return {
        "task_input": None,
        "s1_output": None,
        "s3_classification": None,
        "s3star_audit": None,
        "recovery_result": None,
        "s2_authorization": None,
        "recovery_directive": None,
        "retry_history": [],
    }


@dataclass
class TaskState:
    """Per-task state in the bus. Serialized to <root>/<task_id>/state.json."""

    task_id: str
    agents: list[str] = field(default_factory=list)
    recovery: dict[str, Any] = field(default_factory=_empty_recovery_state)
    created: str = field(default_factory=_now_iso)
    ttl: int = 3600

    @property
    def expired(self) -> bool:
        created_ts = time.mktime(time.strptime(self.created, "%Y-%m-%dT%H:%M:%S"))
        return (time.time() - created_ts) > self.ttl

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "agents": self.agents,
            "recovery": self.recovery,
            "created": self.created,
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TaskState":
        return cls(
            task_id=d["task_id"],
            agents=d.get("agents", []),
            recovery=d.get("recovery") or _empty_recovery_state(),
            created=d.get("created") or _now_iso(),
            ttl=d.get("ttl", 3600),
        )


class StateBus:
    """File-based inter-process shared state for agent runtime.

    Each task_id maps to a directory <root>/<task_id>/ containing:
      state.json  — the TaskState (atomic-written on each update)
      .lock       — flock sidecar for multi-write transactions

    Isolation: per-task. TTL: auto-expire on read if expired.

    Args:
        root: base directory for all task states. Default: system temp.
    """

    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root else Path(tempfile.gettempdir()) / "agent_state_bus"
        self.root.mkdir(parents=True, exist_ok=True)

    def _task_dir(self, task_id: str) -> Path:
        return self.root / task_id

    def _state_path(self, task_id: str) -> Path:
        return self._task_dir(task_id) / "state.json"

    def _lock_path(self, task_id: str) -> Path:
        return self._task_dir(task_id) / ".lock"

    # ── Atomic load/store ──

    def _load(self, task_id: str) -> TaskState | None:
        """Load TaskState from disk. Returns None if missing/expired."""
        path = self._state_path(task_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            state = TaskState.from_dict(data)
            if state.expired:
                self._remove(task_id)
                return None
            return state
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def _store(self, state: TaskState) -> None:
        """Atomically write TaskState to disk (temp file → rename)."""
        task_dir = self._task_dir(state.task_id)
        task_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state.to_dict(), ensure_ascii=False, indent=2) + "\n"
        # Atomic write: temp in same dir (rename is atomic on POSIX same-fs)
        fd, tmp = tempfile.mkstemp(dir=task_dir, suffix=".tmp")
        try:
            os.write(fd, payload.encode("utf-8"))
            os.close(fd)
            os.replace(tmp, self._state_path(state.task_id))
        except Exception:
            os.close(fd) if not _fd_closed(fd) else None
            Path(tmp).unlink(missing_ok=True)
            raise

    def _remove(self, task_id: str) -> None:
        """Remove a task directory (cleanup)."""
        import shutil
        shutil.rmtree(self._task_dir(task_id), ignore_errors=True)

    # ── Public API (mirrors SessionStore) ──

    def create(self, task_id: str, agents: list[str], ttl: int = 3600) -> TaskState:
        """Create a new task state. Raises if task_id already active."""
        existing = self._load(task_id)
        if existing is not None:
            raise ValueError(f"task state already exists: task_id={task_id}")
        state = TaskState(task_id=task_id, agents=list(agents), ttl=ttl)
        self._store(state)
        return state

    def get(self, task_id: str) -> TaskState | None:
        """Get task state. Returns None if not found or expired."""
        return self._load(task_id)

    def update(self, task_id: str, key: str, value: Any) -> None:
        """Set recovery[key] = value. Atomic read-modify-write under lock."""
        with self.lock(task_id):
            state = self._load(task_id)
            if state is None:
                raise KeyError(f"task state not found: task_id={task_id}")
            state.recovery[key] = value
            self._store(state)

    def read(self, task_id: str, key: str) -> Any:
        """Read recovery[key]. Raises if task/key not found."""
        state = self._load(task_id)
        if state is None:
            raise KeyError(f"task state not found: task_id={task_id}")
        if key not in state.recovery:
            raise KeyError(f"recovery key not found: {key}")
        return state.recovery[key]

    def read_all(self, task_id: str) -> dict[str, Any]:
        """Read the entire recovery dict. Empty dict if task missing."""
        state = self._load(task_id)
        return dict(state.recovery) if state else {}

    def append(self, task_id: str, key: str, value: Any) -> None:
        """Append to recovery[key] (must be a list). Atomic under lock."""
        with self.lock(task_id):
            state = self._load(task_id)
            if state is None:
                raise KeyError(f"task state not found: task_id={task_id}")
            target = state.recovery.get(key)
            if not isinstance(target, list):
                raise TypeError(f"recovery[{key}] is not a list (got {type(target).__name__})")
            target.append(value)
            self._store(state)

    def close(self, task_id: str) -> None:
        """Close and remove a task state (cleanup)."""
        self._remove(task_id)

    # ── Locking ──

    @contextmanager
    def lock(self, task_id: str, timeout: float = 10.0) -> Iterator[None]:
        """Exclusive lock for multi-write transactions (flock).

        Blocks up to timeout seconds. Use for atomic read-modify-write across
        multiple keys. Single update()/append() already lock internally.
        """
        task_dir = self._task_dir(task_id)
        task_dir.mkdir(parents=True, exist_ok=True)
        lock_path = self._lock_path(task_id)
        lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
        deadline = time.time() + timeout
        try:
            while True:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.time() > deadline:
                        raise TimeoutError(f"state_bus lock timeout: task_id={task_id}")
                    time.sleep(0.05)
            yield
        finally:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            except OSError:
                pass
            os.close(lock_fd)

    # ── Maintenance ──

    def cleanup_expired(self) -> int:
        """Remove all expired task states. Returns count removed."""
        removed = 0
        if not self.root.exists():
            return 0
        for task_dir in self.root.iterdir():
            if not task_dir.is_dir():
                continue
            state = self._load(task_dir.name)
            if state is None:  # expired or corrupt
                # _load already removed it if expired; corrupt → remove
                if task_dir.exists():
                    self._remove(task_dir.name)
                removed += 1
        return removed

    @property
    def active_count(self) -> int:
        """Number of active (non-expired) task states."""
        if not self.root.exists():
            return 0
        count = 0
        for task_dir in self.root.iterdir():
            if task_dir.is_dir() and self._load(task_dir.name) is not None:
                count += 1
        return count


def _fd_closed(fd: int) -> bool:
    """Check if a file descriptor is already closed (best-effort)."""
    try:
        os.fstat(fd)
        return False
    except OSError:
        return True

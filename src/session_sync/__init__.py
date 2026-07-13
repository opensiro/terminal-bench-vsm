"""session_sync — shared state for multi-agent S1 (VSM-007: OSM Split).

Activated by VSM-007 (OSM Split S1 → planner + executor + verifier).
Before Split: placeholder (mono-agent — not needed).
After Split: SessionStore provides per-task shared state between sub-agents.

Contract (from README.md):
  session = {
    task_id, agents, shared_state, created, ttl
  }

Isolation: per-task, does not leak between tasks.
TTL: cleanup after task completion.
"""
from .store import SessionStore, Session

__all__ = ["SessionStore", "Session"]

"""coord tools — S2 coordination: state-bus access + conflict/retry checks (VSM-013).

Exposes the state-bus (inter-process shared state) to the S2 goose-agent via MCP
tools, plus deterministic conflict-detection and retry-authorization checks that
wrap the existing s2.coordinator logic (the agent decides; these tools provide
the structured facts).

Tools:
  state_bus_read(task_id, key)      → read one key from the task's state-bus
  state_bus_write(task_id, key, val)→ write one key (atomic)
  conflict_check(task_id)           → detect resource/contention conflicts
  retry_authorize(task_id)          → 4-check: anti-repeat, conflict, oscillation, authorize
"""
from __future__ import annotations

import json
from typing import Any

from ..state_bus import StateBus


def register_coord_tools(server, state_bus_root: str | None = None):
    """Register S2 coordination tools onto the MCP server.

    Args:
        server: MCPServer to register tools onto.
        state_bus_root: root dir for StateBus (default: temp/agent_state_bus).
    """
    bus = StateBus(root=state_bus_root)

    def state_bus_read(task_id: str, key: str = "") -> dict:
        """Read from the task's shared state. If key empty, read all."""
        try:
            if key:
                return {"value": bus.read(task_id, key), "exit_code": 0}
            return {"value": bus.read_all(task_id), "exit_code": 0}
        except KeyError as e:
            return {"error": str(e), "exit_code": 1}

    server.register(
        "state_bus_read",
        "read shared state for a task from the state-bus",
        {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "key": {"type": "string", "description": "state key (empty = read all)"},
            },
            "required": ["task_id"],
        },
        state_bus_read,
    )

    def state_bus_write(task_id: str, key: str, value: Any) -> dict:
        """Write to the task's shared state (atomic)."""
        try:
            bus.update(task_id, key, value)
            return {"exit_code": 0}
        except (KeyError, ValueError) as e:
            return {"error": str(e), "exit_code": 1}

    server.register(
        "state_bus_write",
        "write a key to the task's shared state (atomic)",
        {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "key": {"type": "string"},
                "value": {"description": "JSON value to write"},
            },
            "required": ["task_id", "key", "value"],
        },
        state_bus_write,
    )

    def conflict_check(task_id: str) -> dict:
        """Detect resource overlaps / output contradictions for a task.

        Wraps s2.conflict.ConflictDetector over the retry_history in state-bus.
        """
        try:
            from s2.conflict import ConflictDetector
            from s2.types import ResourceClaim
            state = bus.read_all(task_id)
            history = state.get("retry_history", [])
            # Resource conflicts require ResourceClaim records; if absent, no conflict.
            # This is a fact-finding tool for the S2 agent, not the decision itself.
            overlaps = []
            detector = ConflictDetector()
            # Build claims from history env_changes (best-effort, structural)
            claims = []
            for h in history:
                env = h.get("env_changes") or []
                for change in env:
                    if "workspace" in str(change) or "git_ref" in str(change):
                        claims.append(ResourceClaim(
                            task_id=task_id, workspace=str(change), git_ref="main",
                        ))
            for i, a in enumerate(claims):
                for b in claims[i + 1:]:
                    if detector.detect_resource_overlap(a, b):
                        overlaps.append({"claim_a": str(a), "claim_b": str(b)})
            return {"overlaps": overlaps, "count": len(overlaps), "exit_code": 0}
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}", "exit_code": 1}

    server.register(
        "conflict_check",
        "detect resource/output conflicts in the task retry history",
        {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]},
        conflict_check,
    )

    def retry_authorize(task_id: str, failure_class: str = "", policy_applied: str = "",
                        policy_attempt: int = 0) -> dict:
        """Run the 4-check retry authorization (anti-repeat → conflict → oscillation → authorize).

        Wraps s2.coordinator.S2Coordinator.authorize_retry. Returns the structured
        authorization result for the S2 agent to act on.
        """
        try:
            from s2.coordinator import S2Coordinator
            from s2.types import RetryHistory, AttemptRecord
            from classifier.classifier import FailureClassifier
            from pathlib import Path
            # Locate taxonomy (sibling of agent_runtime)
            taxonomy = Path(__file__).resolve().parent.parent.parent / "failure_taxonomy.yaml"
            classifier = FailureClassifier(str(taxonomy))
            s2 = S2Coordinator(get_anti_repeat_limit=classifier.get_anti_repeat_limit)

            # Rebuild RetryHistory from state-bus
            state = bus.read_all(task_id)
            history = RetryHistory(task_id=task_id)
            for h in state.get("retry_history", []):
                history.add(AttemptRecord(
                    attempt_num=h.get("attempt", 0),
                    failure_class=h.get("failure_class", ""),
                    policy_applied=h.get("policy_applied", ""),
                    verdict=h.get("verdict", ""),
                ))
            auth = s2.authorize_retry(
                failure_class=failure_class,
                policy_applied=policy_applied,
                policy_attempt=policy_attempt,
                history=history,
            )
            return {
                "authorized": auth.authorized,
                "blocked_by": auth.blocked_by,
                "reason": auth.reason,
                "exit_code": 0,
            }
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}", "exit_code": 1}

    server.register(
        "retry_authorize",
        "run 4-check retry authorization (anti-repeat, conflict, oscillation, authorize)",
        {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "failure_class": {"type": "string"},
                "policy_applied": {"type": "string"},
                "policy_attempt": {"type": "integer", "default": 0},
            },
            "required": ["task_id", "failure_class", "policy_applied"],
        },
        retry_authorize,
    )

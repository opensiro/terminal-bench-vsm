"""audit_tools — S3* audit tools (VSM-013).

Exposes read-only state access + the audit check to the S3* goose-agent. S3*
runs on a DIFFERENT provider (VSM-001 cross-provider constraint), so these tools
provide the structured facts the agent audits — the agent judges independence.

Tools:
  state_bus_read(task_id, key)   → read-only state access (no write)
  audit_check(classification, observations) → run the deterministic audit

Note: S3* gets state_bus_read (read-only) — it must NOT be able to mutate the
state-bus. There is no state_bus_write registered for the audit role.
"""
from __future__ import annotations

from pathlib import Path
from ..state_bus import StateBus


def register_audit_tools(server, state_bus_root: str | None = None):
    """Register S3* audit tools (read-only state + audit check)."""
    bus = StateBus(root=state_bus_root)

    def state_bus_read(task_id: str, key: str = "") -> dict:
        """Read-only access to the task's shared state (for audit)."""
        try:
            if key:
                return {"value": bus.read(task_id, key), "exit_code": 0}
            return {"value": bus.read_all(task_id), "exit_code": 0}
        except KeyError as e:
            return {"error": str(e), "exit_code": 1}

    server.register(
        "state_bus_read",
        "read-only access to task shared state (for audit)",
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

    def audit_check(classification: dict, observations: list) -> dict:
        """Run the deterministic audit over a classification.

        Wraps audit.auditor.S3StarAuditor.audit_classification. Returns findings
        for the S3* agent to reason about independently.
        """
        try:
            from audit.auditor import S3StarAuditor
            from audit.config import AuditConfig
            # Provider constraint: S3* must differ from S1. The agent process
            # runs with AGENT_PROVIDER env (set by goose_runner); the audit
            # config validates the documented constraint.
            config = AuditConfig()  # defaults validate cross-provider at deploy
            auditor = S3StarAuditor(config)
            taxonomy_path = Path(__file__).resolve().parent.parent.parent / "failure_taxonomy.yaml"
            from classifier.classifier import FailureClassifier
            clf = FailureClassifier(str(taxonomy_path))
            taxonomy_classes = [
                {"id": c.id, "category": c.category, "signals": c.signals,
                 "recovery_policy": c.recovery_policy}
                for c in clf.classes
            ]
            result = auditor.audit_classification(classification, observations, taxonomy_classes)
            return {
                "passed": result.passed,
                "findings": [
                    {"severity": f.severity, "type": f.type, "message": f.message}
                    for f in result.findings
                ],
                "algedonic": result.algedonic,
                "exit_code": 0,
            }
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}", "exit_code": 1}

    server.register(
        "audit_check",
        "audit a classification against observations (independent check)",
        {
            "type": "object",
            "properties": {
                "classification": {"type": "object", "description": "S3 classification result"},
                "observations": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["classification", "observations"],
        },
        audit_check,
    )

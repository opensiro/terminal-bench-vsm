"""classifier_tools — S3 classification tools (VSM-013).

Exposes the failure taxonomy + signal matching to the S3 goose-agent. The agent
reasons over observations; these tools provide the deterministic facts (taxonomy
structure, signal-match candidates) so the agent's classification is grounded.

Note (VSM-012 Q1): the human accepted that S3 becomes an LLM agent and loses
strict regex determinism. These tools keep the taxonomy + signal data available
so the agent can ground its reasoning in the same evidence the old Python
classifier used — the LLM judges, but with structured facts in hand.

Tools:
  taxonomy_read()              → list all failure classes + their signals/policies
  signal_match(observations)   → match observations against taxonomy signals
  policy_select(failure_class) → get the recovery policy for a class
"""
from __future__ import annotations

from pathlib import Path


def register_classifier_tools(server, workspace: str):
    """Register S3 classification tools onto the MCP server."""

    def _taxonomy_path() -> Path:
        return Path(__file__).resolve().parent.parent.parent / "failure_taxonomy.yaml"

    def taxonomy_read() -> dict:
        """List all failure classes with their signals, categories, policies."""
        try:
            from classifier.classifier import FailureClassifier
            clf = FailureClassifier(str(_taxonomy_path()))
            classes = []
            for c in clf.classes:
                classes.append({
                    "id": c.id,
                    "category": c.category,
                    "signals": c.signals,
                    "recovery_policy": c.recovery_policy,
                })
            return {"classes": classes, "count": len(classes), "exit_code": 0}
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}", "exit_code": 1}

    server.register(
        "taxonomy_read",
        "list all failure classes with their signals and recovery policies",
        {"type": "object", "properties": {}, "required": []},
        taxonomy_read,
    )

    def signal_match(observations: list) -> dict:
        """Match observations against taxonomy signals.

        Returns candidate classes ranked by evidence strength. The S3 agent uses
        this to ground its classification decision.
        """
        try:
            from classifier.classifier import FailureClassifier
            clf = FailureClassifier(str(_taxonomy_path()))
            result = clf.classify(observations)
            return {
                "failure_class": result.failure_class,
                "recovery_policy": result.recovery_policy,
                "confidence": result.confidence,
                "ambiguous": result.ambiguous,
                "alternative_classes": result.alternative_classes,
                "reason": result.reason,
                "exit_code": 0,
            }
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}", "exit_code": 1}

    server.register(
        "signal_match",
        "match observations against taxonomy signals (candidate classes)",
        {
            "type": "object",
            "properties": {
                "observations": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "failure observations (kind, value, source, ...)",
                },
            },
            "required": ["observations"],
        },
        signal_match,
    )

    def policy_select(failure_class: str) -> dict:
        """Get the recovery policy for a failure class."""
        try:
            from classifier.classifier import FailureClassifier
            clf = FailureClassifier(str(_taxonomy_path()))
            policy = clf.get_policy_for_class(failure_class)
            limit = clf.get_anti_repeat_limit(failure_class)
            return {
                "failure_class": failure_class,
                "recovery_policy": policy,
                "anti_repeat_limit": limit,
                "exit_code": 0,
            }
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}", "exit_code": 1}

    server.register(
        "policy_select",
        "get the recovery policy and anti-repeat limit for a failure class",
        {
            "type": "object",
            "properties": {"failure_class": {"type": "string"}},
            "required": ["failure_class"],
        },
        policy_select,
    )

"""types — classifier data structures."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Evidence:
    """Matched signal evidence for a classification decision."""

    signal: str           # matched signal string from taxonomy
    observation_value: str  # observation value that matched
    observation_kind: str   # error_string | exit_code | timeout | signal
    at_action: int          # trace action index


@dataclass
class Classification:
    """Result of classifying a set of failure_observations."""

    failure_class: str          # class id from taxonomy (or "Unknown")
    recovery_policy: str        # policy id from taxonomy (or "EscalateToS3")
    confidence: str             # "high" | "medium" | "low"
    evidence: list[Evidence] = field(default_factory=list)
    matched_signals: list[str] = field(default_factory=list)
    ambiguous: bool = False     # multiple classes matched equally well
    alternative_classes: list[str] = field(default_factory=list)
    reason: str = ""            # human-readable explanation


@dataclass
class TaxonomyClass:
    """Parsed class from failure_taxonomy.yaml."""

    id: str
    category: str
    description: str
    signals: list[str]
    recovery_policy: str
    recovery_steps: list[str]
    s2_anti_repeat: str

"""classifier — S3 failure classifier (T3 CLASSIFIER.md implementation).

Pipeline: observations → match signals → select class → policy → directive.

Match order (from taxonomy classifier_guidance):
  1. code (SyntaxError/TestFailure/FileLocalizationError — точные паттерны)
  2. dependency (ImportError/DependencyConflict/CompilationError)
  3. git (GitConflict/GitAuthFailure)
  4. resource (TimeoutExpired/HangDetected/ResourceLimit/PermissionDenied)
  5. network (NetworkError)
  6. environment (ToolNotFound)
  7. spec (AmbiguousSpec — diagnostic)
  8. fallback (Unknown — last)

Multi-match resolution: prefer class whose signals match more specifically
(literal match > substring match; more matched signals = higher confidence).
"""
from __future__ import annotations
import re
from typing import Any
from .types import TaxonomyClass, Classification, Evidence
from .taxonomy_loader import load_taxonomy, parse_classes, get_match_order


class FailureClassifier:
    """S3 failure classifier: observations → class → policy + evidence."""

    def __init__(self, taxonomy_path: str):
        self._raw = load_taxonomy(taxonomy_path)
        self._classes = parse_classes(self._raw)
        self._by_id = {c.id: c for c in self._classes}
        self._by_category: dict[str, list[TaxonomyClass]] = {}
        for c in self._classes:
            self._by_category.setdefault(c.category, []).append(c)
        self._match_order = get_match_order(self._raw)

    @property
    def classes(self) -> list[TaxonomyClass]:
        return list(self._classes)

    def classify(self, observations: list[dict[str, Any]]) -> Classification:
        """Classify failure_observations → Classification.

        observations: list of dicts with kind, value, source, at_action
        (T2 CONTRACT §6 format).
        """
        if not observations:
            return Classification(
                failure_class="Unknown",
                recovery_policy="EscalateToS3",
                confidence="low",
                reason="no observations to classify",
            )

        # Collect matches per class
        matches: dict[str, list[Evidence]] = {}
        for obs in observations:
            kind = obs.get("kind", "error_string")
            value = str(obs.get("value", ""))
            at_action = obs.get("at_action", 0)
            if not value:
                continue

            for cls in self._classes:
                if cls.id == "Unknown" or cls.id == "AmbiguousSpec":
                    continue
                for signal in cls.signals:
                    if self._signal_matches(signal, value, kind, obs):
                        evidence = Evidence(
                            signal=signal,
                            observation_value=value,
                            observation_kind=kind,
                            at_action=at_action,
                        )
                        matches.setdefault(cls.id, []).append(evidence)
                        break  # one signal match per class per observation

        if not matches:
            return Classification(
                failure_class="Unknown",
                recovery_policy="EscalateToS3",
                confidence="low",
                reason="no signals matched any class",
            )

        # Rank by match_order category, then by number of evidence (more = higher confidence)
        ranked = self._rank_matches(matches)

        best_id = ranked[0][0]
        best_evidence = matches[best_id]
        best_class = self._by_id[best_id]

        # Check ambiguity: if top-2 have same evidence count, mark ambiguous
        ambiguous = False
        alternatives = []
        if len(ranked) >= 2 and ranked[1][1] == len(best_evidence):
            ambiguous = True
            alternatives = [r[0] for r in ranked[1:]]

        confidence = self._compute_confidence(len(best_evidence), len(observations), ambiguous)

        return Classification(
            failure_class=best_id,
            recovery_policy=best_class.recovery_policy,
            confidence=confidence,
            evidence=best_evidence,
            matched_signals=[e.signal for e in best_evidence],
            ambiguous=ambiguous,
            alternative_classes=alternatives,
            reason=f"matched {len(best_evidence)} signal(s) from class {best_id} (category: {best_class.category})",
        )

    def _signal_matches(self, signal: str, value: str, kind: str, obs: dict) -> bool:
        """Check if a signal matches an observation value."""
        signal_lower = signal.lower()
        value_lower = value.lower()
        # Substring match (case-insensitive)
        if signal_lower in value_lower:
            return True
        # Regex match if signal looks like a regex (contains regex metachars)
        if any(c in signal for c in r"\[]{}()*+?|^$."):
            try:
                if re.search(signal, value, re.IGNORECASE):
                    return True
            except re.error:
                pass
        return False

    def _rank_matches(self, matches: dict[str, list[Evidence]]) -> list[tuple[str, int]]:
        """Rank matched classes by match_order (category priority) then evidence count."""
        ranked = []
        for cls_id, evidence_list in matches.items():
            cls = self._by_id.get(cls_id)
            if cls is None:
                continue
            cat_priority = self._match_order.index(cls.category) if cls.category in self._match_order else 99
            ranked.append((cls_id, len(evidence_list), cat_priority))

        # Sort: lower category priority first (code=0, fallback=7), then more evidence
        ranked.sort(key=lambda x: (x[2], -x[1]))
        return [(r[0], r[1]) for r in ranked]

    def _compute_confidence(self, evidence_count: int, obs_count: int, ambiguous: bool) -> str:
        """Compute confidence level: high | medium | low.

        Coverage-based: a single specific signal match that covers the full
        observation set (ratio >= 0.5) is high confidence. This aligns with
        CLASSIFIER.md "literal match > regex" — a precise substring hit on
        every observation is strong evidence.
        """
        if ambiguous:
            return "low"
        if evidence_count >= 1 and evidence_count / max(obs_count, 1) >= 0.5:
            return "high"
        if evidence_count >= 1:
            return "medium"
        return "low"

    def get_policy_for_class(self, class_id: str) -> str:
        """Get recovery_policy for a class id."""
        cls = self._by_id.get(class_id)
        if cls is None:
            return "EscalateToS3"
        return cls.recovery_policy

    def get_anti_repeat_limit(self, class_id: str) -> int:
        """Parse anti-repeat limit from s2_anti_repeat string."""
        cls = self._by_id.get(class_id)
        if cls is None:
            return 2
        text = cls.s2_anti_repeat.lower()
        # Try to find N in patterns like ">N раз" or ">N times"
        m = re.search(r">\s*(\d+)", text)
        if m:
            return int(m.group(1))
        return 2  # default

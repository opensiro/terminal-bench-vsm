"""auditor — S3* independent audit (VSM-005 §5).

S3* independently audits S3-classifier decisions. Does NOT trust self-reports.
Checks: classification consistency, signal coverage, structural defects,
uncertainty-reaction viability. Cross-provider (config point).

Audit triggers:
- After each classification (if audit cadence = per_classification)
- On oscillation detection (S2 flags class flip-flop)
- On unknown share > threshold
- On S2 uncertainty probing (VSM-005 §5)
"""
from __future__ import annotations
import re
from typing import Any
from .config import AuditConfig
from .types import AuditFinding, AuditResult, Severity, FindingType


class S3StarAuditor:
    """S3* auditor: independently verifies S3-classifier decisions."""

    def __init__(self, config: AuditConfig | None = None):
        self.config = config or AuditConfig()
        self._history: list[dict[str, Any]] = []  # classification history for oscillation

    def audit_classification(
        self,
        classification: dict[str, Any],
        observations: list[dict[str, Any]],
        taxonomy_classes: list[dict[str, Any]] | None = None,
    ) -> AuditResult:
        """Audit a single S3-classifier decision.

        classification: S3's Classification (as dict: failure_class, recovery_policy,
                        confidence, evidence, matched_signals, ambiguous, reason)
        observations: the failure_observations that were classified
        taxonomy_classes: list of class dicts from taxonomy (id, signals, category)
        """
        result = AuditResult()

        # 0. Provider constraint check (critical invariant)
        provider_error = self.config.validate_provider_constraint()
        if provider_error:
            result.add(AuditFinding(
                finding_type=FindingType.PROVIDER_VIOLATION,
                severity=Severity.CRITICAL,
                message=provider_error,
            ))

        cls_id = classification.get("failure_class", "Unknown")
        confidence = classification.get("confidence", "low")
        evidence = classification.get("evidence", [])
        ambiguous = classification.get("ambiguous", False)

        # 1. Classification consistency: does evidence actually support the class?
        if self.config.audit_classification_consistency:
            if cls_id != "Unknown" and not evidence:
                result.add(AuditFinding(
                    finding_type=FindingType.CLASSIFICATION_CONSISTENCY,
                    severity=Severity.CRITICAL,
                    message=f"class={cls_id} but no evidence provided",
                    detail="S3 classified without evidence — violates evidence_required",
                    classification_id=cls_id,
                ))
            elif cls_id != "Unknown" and evidence:
                # Verify: do the matched signals actually appear in observations?
                for ev in evidence:
                    signal = ev.get("signal", "")
                    obs_values = [str(o.get("value", "")) for o in observations]
                    found_in_obs = any(signal.lower() in v.lower() for v in obs_values)
                    if not found_in_obs:
                        result.add(AuditFinding(
                            finding_type=FindingType.CLASSIFICATION_CONSISTENCY,
                            severity=Severity.WARN,
                            message=f"evidence signal '{signal}' not found in observations",
                            detail="S3 may have hallucinated the match",
                            classification_id=cls_id,
                        ))

        # 2. Signal coverage: are there observations that didn't match any class?
        if self.config.audit_signal_coverage and taxonomy_classes and observations:
            unmatched_obs = []
            for obs in observations:
                value = str(obs.get("value", ""))
                if not value:
                    continue
                matched = False
                for cls in taxonomy_classes:
                    if cls.get("id") in ("Unknown", "AmbiguousSpec"):
                        continue
                    for signal in (cls.get("signals") or []):
                        if signal.lower() in value.lower():
                            matched = True
                            break
                    if matched:
                        break
                if not matched:
                    unmatched_obs.append(value[:50])
            if unmatched_obs:
                severity = Severity.WARN if len(unmatched_obs) > 1 else Severity.INFO
                result.add(AuditFinding(
                    finding_type=FindingType.SIGNAL_COVERAGE,
                    severity=severity,
                    message=f"{len(unmatched_obs)} observation(s) unmatched by any class signal",
                    detail=f"unmatched: {unmatched_obs[:3]}",
                    classification_id=cls_id,
                ))

        # 3. Structural defects: taxonomy gaps, misclassification patterns
        if self.config.audit_structural_defects:
            if cls_id == "Unknown":
                result.add(AuditFinding(
                    finding_type=FindingType.STRUCTURAL_DEFECT,
                    severity=Severity.WARN,
                    message="classification=Unknown — possible taxonomy gap",
                    detail="if unknown share > threshold, S4 should expand taxonomy",
                    classification_id=cls_id,
                ))
            if ambiguous:
                alternatives = classification.get("alternative_classes", [])
                result.add(AuditFinding(
                    finding_type=FindingType.STRUCTURAL_DEFECT,
                    severity=Severity.WARN,
                    message=f"ambiguous classification: alternatives={alternatives}",
                    detail="multiple classes matched equally — classifier may need refinement",
                    classification_id=cls_id,
                ))

        # 4. Uncertainty-reaction audit (VSM-005 §5)
        if self.config.audit_uncertainty_reaction:
            if confidence == "low":
                result.add(AuditFinding(
                    finding_type=FindingType.UNCERTAINTY_REACTION,
                    severity=Severity.WARN,
                    message="low confidence classification — uncertainty reaction may be needed",
                    detail="S2 probing or S4 expansion may be appropriate",
                    classification_id=cls_id,
                ))

        # Track history for oscillation
        self._history.append({"class": cls_id, "policy": classification.get("recovery_policy", "")})
        self._check_oscillation(result)

        return result

    def _check_oscillation(self, result: AuditResult):
        """Check classification history for oscillation patterns."""
        if len(self._history) < 4:
            return
        recent = self._history[-self.config.oscillation_window:]
        classes = [h["class"] for h in recent]
        # Detect A→B→A→B pattern
        if len(classes) >= 4:
            if classes[-1] == classes[-3] and classes[-2] == classes[-4] and classes[-1] != classes[-2]:
                result.add(AuditFinding(
                    finding_type=FindingType.STRUCTURAL_DEFECT,
                    severity=Severity.CRITICAL,
                    message=f"oscillation detected: {classes[-4]}→{classes[-3]}→{classes[-2]}→{classes[-1]}",
                    detail="classifier flip-flopping between classes — possible misclassification or structural gap",
                ))
                result.algedonic = True

    def audit_unknown_share(self, classifications: list[dict[str, Any]]) -> AuditResult:
        """Audit the share of Unknown classifications over a window."""
        result = AuditResult()
        if not classifications:
            return result
        unknown_count = sum(1 for c in classifications if c.get("failure_class") == "Unknown")
        share = unknown_count / len(classifications)
        if share > self.config.unknown_share_threshold:
            result.add(AuditFinding(
                finding_type=FindingType.STRUCTURAL_DEFECT,
                severity=Severity.CRITICAL,
                message=f"unknown share {share:.1%} > threshold {self.config.unknown_share_threshold:.1%}",
                detail="taxonomy gap — S4 should expand (new_failure_class_introduction)",
            ))
            result.algedonic = True
        else:
            result.add(AuditFinding(
                finding_type=FindingType.SIGNAL_COVERAGE,
                severity=Severity.OK,
                message=f"unknown share {share:.1%} within threshold",
            ))
        return result

    def reset_history(self):
        """Clear classification history (e.g., between tasks)."""
        self._history.clear()

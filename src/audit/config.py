"""config — S3* audit configuration (cross-provider, VSM-005)."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AuditConfig:
    """S3* audit configuration.

    Cross-provider constraint (VSM-001/VSM-005): S3* MUST use a different
    model provider than S1. This is a config point — the actual provider
    is set at deployment, not hardcoded.
    """

    # Cross-provider: S3* must differ from S1 provider
    s1_provider: str = "inherit"        # S1's provider (for comparison)
    s3star_provider: str = "cross_provider"  # S3* provider (MUST differ)
    provider_must_differ: bool = True   # critical invariant

    # Audit scope
    audit_classification_consistency: bool = True
    audit_signal_coverage: bool = True
    audit_structural_defects: bool = True
    audit_uncertainty_reaction: bool = True   # VSM-005 §5

    # Thresholds
    unknown_share_threshold: float = 0.15      # from taxonomy
    min_confidence_for_trust: str = "medium"   # below = flagged
    oscillation_window: int = 5                # check last N classifications

    # Independence rules
    read_only: bool = True                     # S3* never mutates
    never_trust_self_reports: bool = True      # re-verify S3 claims

    def validate_provider_constraint(self) -> str | None:
        """Returns error message if provider constraint violated, None if OK."""
        if not self.provider_must_differ:
            return None
        if self.s1_provider == self.s3star_provider:
            return f"CRITICAL: S3* provider ({self.s3star_provider}) same as S1 ({self.s1_provider}) — violates cross-provider invariant"
        return None

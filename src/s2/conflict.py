"""conflict — ConflictDetector for multi-agent conflict detection (PIPELINES.md §4).

Three trigger categories from vsm.yaml system_2.conflict_detection:
  - resource_overlaps: two attempts compete for same workspace/git_ref/ports
  - output_contradictions: two runs of same task give different verdicts/recovery-paths
  - custom_triggers: solver diverges from recovery policy, S3/S1 divergence, non-determinism
"""
from __future__ import annotations
from .types import AttemptRecord, ResourceClaim


class ConflictDetector:
    """Detects conflicts between attempts (multi-agent / parallel retries)."""

    def detect_resource_overlap(
        self, claim_a: ResourceClaim, claim_b: ResourceClaim
    ) -> bool:
        """Check if two resource claims overlap (PIPELINES.md §4 resource_overlaps).

        Overlap = same workspace, same git_ref, or shared port.
        Same task_id is NOT an overlap (a task can hold its own resources).
        """
        if claim_a.task_id == claim_b.task_id:
            return False  # same task — not a conflict
        if claim_a.workspace == claim_b.workspace:
            return True
        if claim_a.git_ref and claim_b.git_ref and claim_a.git_ref == claim_b.git_ref:
            return True
        shared_ports = set(claim_a.ports) & set(claim_b.ports)
        return bool(shared_ports)

    def detect_output_contradiction(
        self, attempt_a: AttemptRecord, attempt_b: AttemptRecord
    ) -> bool:
        """Check if two runs of same task give contradictory outputs (§4 output_contradictions).

        Contradiction patterns:
        - Same failure_class but different verdicts (flaky/env difference).
        - Different failure_classes (classifier non-determinism).
        - Same verdict but different recovery policies (recovery-path non-determinism).
        """
        if attempt_a.verdict != attempt_b.verdict:
            return True
        if attempt_a.failure_class != attempt_b.failure_class:
            return True
        if attempt_a.policy_applied != attempt_b.policy_applied:
            return True
        return False

    def detect_circumvent_recovery(
        self, policy_applied: str, solver_actions: list[dict]
    ) -> bool:
        """Check if solver diverged from prescribed recovery policy (§4 custom_trigger 1).

        circumvent_recovery = solver tried a different path instead of the
        prescribed policy. Detection heuristic: solver actions don't align with
        the policy's expected env_changes.

        For now: heuristic stub. A real implementation would compare solver's
        actual tool calls against the policy's expected actions (from
        recovery_policies/policies.yaml).
        """
        # future: compare solver_actions against policy expected_actions
        # for now, return False (no circumvent detection beyond anti-repeat)
        return False

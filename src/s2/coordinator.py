"""coordinator — S2Coordinator: arbiter for retry authorization (PIPELINES.md §2).

4-check pipeline:
  1. ANTI-REPEAT — policy_attempt < limit (limit from taxonomy s2_anti_repeat)
  2. CONFLICT — resource_overlaps (multi-agent), output_contradictions, custom_triggers
  3. OSCILLATION — A→B→A→B pattern in retry history
  4. AUTHORIZE — all checks pass → authorized=True

S2 is the ONLY component that authorizes retry. S3 proposes (directive),
S2 verifies and launches. This separates control (S3) from coordination (S2).
"""
from __future__ import annotations
from typing import Callable
from .types import AttemptRecord, RetryHistory, ResourceClaim, AuthorizationResult
from .conflict import ConflictDetector


class S2Coordinator:
    """S2 arbiter: authorizes retry after 4-check pipeline.

    Args:
        get_anti_repeat_limit: callable(class_id) -> int. Typically
            classifier.get_anti_repeat_limit.
        conflict_detector: ConflictDetector instance (or default).
    """

    def __init__(
        self,
        get_anti_repeat_limit: Callable[[str], int] | None = None,
        conflict_detector: ConflictDetector | None = None,
    ):
        self._get_limit = get_anti_repeat_limit or (lambda _cls: 2)
        self._conflict = conflict_detector or ConflictDetector()
        self._resource_registry: dict[str, ResourceClaim] = {}  # task_id → claim

    def authorize_retry(
        self,
        failure_class: str,
        policy_applied: str,
        policy_attempt: int,
        history: RetryHistory,
        resource_claim: ResourceClaim | None = None,
    ) -> AuthorizationResult:
        """Run 4-check pipeline. Returns AuthorizationResult.

        Args:
            failure_class: classified failure class (from S3).
            policy_applied: recovery policy id (from S3).
            policy_attempt: current attempt number for this policy (0-based).
            history: per-task retry history (for oscillation/contradiction).
            resource_claim: resource claim for conflict detection (multi-agent).
        """
        # ── Check 1: ANTI-REPEAT ──
        limit = self._get_limit(failure_class)
        if policy_attempt >= limit:
            return AuthorizationResult(
                authorized=False,
                blocked_by="anti_repeat",
                reason=(
                    f"anti-repeat limit exceeded: policy={policy_applied} "
                    f"attempt={policy_attempt} limit={limit} "
                    f"(circumvent_recovery — S3-mark flaky → S4 expansion)"
                ),
            )

        # ── Check 2: CONFLICT ──
        if resource_claim:
            # Register claim and check for overlaps with other tasks
            for other_task_id, other_claim in self._resource_registry.items():
                if other_task_id == resource_claim.task_id:
                    continue
                if self._conflict.detect_resource_overlap(resource_claim, other_claim):
                    return AuthorizationResult(
                        authorized=False,
                        blocked_by="resource_overlap",
                        reason=(
                            f"resource overlap with task={other_task_id} "
                            f"(workspace/git_ref/ports) — queue, not parallel"
                        ),
                    )
            # Register this task's claim
            self._resource_registry[resource_claim.task_id] = resource_claim

        # output_contradictions: check history for contradictory attempts
        if history.attempt_count >= 2:
            last = history.attempts[-1]
            prev = history.attempts[-2]
            if self._conflict.detect_output_contradiction(prev, last):
                return AuthorizationResult(
                    authorized=False,
                    blocked_by="output_contradiction",
                    reason=(
                        f"output contradiction: attempt {prev.attempt_num} vs "
                        f"{last.attempt_num} — different verdict/class/policy "
                        f"(classifier non-determinism — S3 investigates)"
                    ),
                )

        # ── Check 3: OSCILLATION ──
        osc = self._detect_oscillation(history)
        if osc:
            return AuthorizationResult(
                authorized=False,
                blocked_by="oscillation",
                reason=osc,
            )

        # ── Check 4: AUTHORIZE ──
        return AuthorizationResult(
            authorized=True,
            reason=(
                f"all checks passed: anti_repeat(ok) conflict(ok) "
                f"oscillation(ok) — retry authorized"
            ),
        )

    def _detect_oscillation(self, history: RetryHistory) -> str | None:
        """Detect A→B→A→B pattern in retry history (PIPELINES.md §3).

        Returns reason string if oscillation detected, None otherwise.
        Also detects no-progress: >3 retries without verdict change.
        """
        if history.attempt_count < 4:
            return None

        recent = history.attempts[-4:]
        classes = [a.failure_class for a in recent]

        # A→B→A→B pattern (class flip-flop)
        if classes[0] == classes[2] and classes[1] == classes[3] and classes[0] != classes[1]:
            return (
                f"oscillation detected: {classes[0]}→{classes[1]}→"
                f"{classes[0]}→{classes[1]} (class flip-flop — S3* audit, "
                f"possible misclassification or structural gap)"
            )

        # No-progress: >3 retries all task_failed without verdict change
        if history.attempt_count >= 4:
            recent_verdicts = [a.verdict for a in history.attempts[-4:]]
            if all(v == "task_failed" for v in recent_verdicts):
                return (
                    f"no-progress: {len(recent_verdicts)} retries all task_failed "
                    f"(oscillation — S3* audit, S4 expansion may be needed)"
                )

        return None

    def register_resource(self, task_id: str, claim: ResourceClaim) -> None:
        """Register a resource claim for a task (multi-agent isolation)."""
        self._resource_registry[task_id] = claim

    def release_resource(self, task_id: str) -> None:
        """Release a task's resource claim (after completion/abort)."""
        self._resource_registry.pop(task_id, None)

    def check_custom_triggers(
        self, policy_applied: str, solver_actions: list[dict]
    ) -> str | None:
        """Check custom_triggers from vsm.yaml system_2 (PIPELINES.md §4).

        Returns trigger name if fired, None otherwise.
        Currently: circumvent_recovery (solver diverges from policy).
        """
        if self._conflict.detect_circumvent_recovery(policy_applied, solver_actions):
            return "circumvent_recovery"
        return None

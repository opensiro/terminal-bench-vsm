"""orchestrator — recovery cycle: S1 → S3 → S3* → recovery → S2 → retry.

Implements S1-dispatcher CONTRACT.md §4 lifecycle:
  1. S1 invoke (solver runs under budget)
  2. If task_resolved/budget_exhausted → return
  3. S3 classify failure_observations → failure_class + recovery_policy
  4. S3* audit classification (independent, cross-provider)
  5. If algedonic → return (escalate to S5)
  6. Recovery executor applies policy to environment
  7. S2 authorize retry (4-check: anti-repeat → conflict → oscillation → authorize)
  8. If not authorized → return
  9. Prepare retry: new S1Input with RecoveryDirective, reduced budget
  10. Loop → step 1

Termination: task_resolved | budget_exhausted | max_retries | algedonic | not_authorized.

Budget: orchestrator tracks cumulative cost from S1Output.cost, reduces budget
for each retry. If remaining budget ≤ 0 → BUDGET_EXHAUSTED.

Stateless (CONTRACT §5): each S1 invocation is fresh. The only state between
attempts is recovery_directive (input) + RetryHistory (S2 internal).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

# NOTE on import style: `src/` is the sys.path root (no __init__.py), so the
# sub-packages are imported via absolute paths rooted at src/ (e.g.
# `runtime.types`, `s2.types`). This matches how the rest of src/ is wired and
# is required for `cd src && python -c "from orchestrator import ..."`.
from runtime.types import (
    S1Input, S1Output, Verdict, Budget, RecoveryDirective, FailureObservation,
)
from runtime.dispatcher import S1Dispatcher
from s2.types import RetryHistory, AttemptRecord


@dataclass
class OrchestratorConfig:
    """Configuration for recovery cycle orchestrator."""
    max_retries: int = 3
    taxonomy_path: str = ""           # path to failure_taxonomy.yaml
    # S3* provider constraint (VSM-005): s1_provider ≠ s3star_provider
    s1_provider: str = ""             # documented for cross-provider audit
    s3star_provider: str = ""         # must differ from s1_provider


@dataclass
class RecoveryCycleResult:
    """Final result of the recovery cycle (aggregated across attempts)."""
    final_output: S1Output            # last S1Output
    total_attempts: int               # number of S1 invocations
    classifications: list[dict] = field(default_factory=list)  # S3 results per attempt
    audit_results: list[dict] = field(default_factory=list)    # S3* results per attempt
    recovery_results: list[dict] = field(default_factory=list)  # recovery executor results
    s2_authorizations: list[dict] = field(default_factory=list) # S2 authorize results
    terminated_by: str = ""           # task_resolved | budget_exhausted | max_retries | algedonic | not_authorized | no_observations
    history: RetryHistory | None = None


def run_recovery_cycle(
    input: S1Input,
    dispatcher: S1Dispatcher,
    classifier: Any,                  # FailureClassifier
    auditor: Any,                     # S3StarAuditor
    s2: Any,                          # S2Coordinator
    config: OrchestratorConfig | None = None,
) -> RecoveryCycleResult:
    """Run the full recovery cycle (CONTRACT.md §4).

    Args:
        input: initial S1Input (recovery_directive should be None for first attempt).
        dispatcher: S1Dispatcher (mono/multi/harness mode set internally).
        classifier: FailureClassifier (loaded with taxonomy).
        auditor: S3StarAuditor (independent, cross-provider).
        s2: S2Coordinator (authorize_retry).
        config: OrchestratorConfig (max_retries, taxonomy_path, providers).

    Returns:
        RecoveryCycleResult with final output + full audit trail.
    """
    cfg = config or OrchestratorConfig()
    task_id = f"task-{hash(input.task_prompt) % 100000}"

    history = RetryHistory(task_id=task_id)
    result = RecoveryCycleResult(
        final_output=S1Output(),
        total_attempts=0,
        history=history,
    )

    # Track cumulative budget consumption
    remaining_time = input.budget.time_seconds
    remaining_tokens = input.budget.tokens
    remaining_actions = input.budget.actions

    # Recovery directive for next attempt (None for first)
    current_directive: RecoveryDirective | None = None
    # Track policy_attempt per (failure_class, policy) for anti-repeat
    policy_attempt_counts: dict[str, int] = {}

    for attempt_num in range(cfg.max_retries + 1):
        result.total_attempts = attempt_num + 1

        # ── Build S1Input with current budget + directive ──
        attempt_input = S1Input(
            task_prompt=input.task_prompt,
            task_spec=input.task_spec,
            tools_transport=input.tools_transport,
            tools_config_ref=input.tools_config_ref,
            workspace=input.workspace,
            shell=input.shell,
            git_available=input.git_available,
            budget=Budget(
                time_seconds=max(1, remaining_time),
                tokens=max(1, remaining_tokens),
                actions=max(1, remaining_actions),
            ),
            recovery_directive=current_directive,
        )

        # ── Step 1: S1 invoke ──
        output = dispatcher.invoke(attempt_input)

        # Track budget consumption
        cost = output.cost
        remaining_time -= int(cost.get("time_used", 0))
        remaining_tokens -= int(cost.get("tokens_used", 0))
        remaining_actions -= int(cost.get("actions_taken", 0))

        # ── Step 2: Check termination conditions ──
        if output.verdict == Verdict.TASK_RESOLVED:
            result.final_output = output
            result.terminated_by = "task_resolved"
            history.add(AttemptRecord(
                attempt_num=attempt_num,
                failure_class="none",
                policy_applied="none",
                verdict="task_resolved",
            ))
            return result

        if output.verdict == Verdict.BUDGET_EXHAUSTED or remaining_time <= 0 or remaining_actions <= 0:
            output.verdict = Verdict.BUDGET_EXHAUSTED
            result.final_output = output
            result.terminated_by = "budget_exhausted"
            return result

        # ── Step 3: Check if there are failure_observations to classify ──
        obs_dicts = [_failure_obs_to_dict(o) for o in output.failure_observations]
        if not obs_dicts:
            # No observations — can't classify, can't recover
            result.final_output = output
            result.terminated_by = "no_observations"
            history.add(AttemptRecord(
                attempt_num=attempt_num,
                failure_class="none",
                policy_applied="none",
                verdict=output.verdict.value if hasattr(output.verdict, 'value') else str(output.verdict),
            ))
            return result

        # ── Step 4: S3 classify ──
        classification = classifier.classify(obs_dicts)
        cls_dict = _classification_to_dict(classification)
        result.classifications.append(cls_dict)

        # ── Step 5: S3* audit ──
        taxonomy_classes = [_taxonomy_class_to_dict(c) for c in classifier.classes]
        audit_result = auditor.audit_classification(cls_dict, obs_dicts, taxonomy_classes)
        audit_dict = _audit_result_to_dict(audit_result)
        result.audit_results.append(audit_dict)

        # ── Step 6: Check algedonic ──
        if audit_result.algedonic:
            result.final_output = output
            result.terminated_by = "algedonic"
            history.add(AttemptRecord(
                attempt_num=attempt_num,
                failure_class=classification.failure_class,
                policy_applied=classification.recovery_policy,
                verdict=output.verdict.value if hasattr(output.verdict, 'value') else str(output.verdict),
            ))
            return result

        # ── Step 7: Recovery executor ──
        policy_id = classification.recovery_policy
        # Track policy_attempt for anti-repeat
        attempt_key = f"{classification.failure_class}:{policy_id}"
        policy_attempt = policy_attempt_counts.get(attempt_key, 0)

        from recovery_policies.base import RecoveryContext, run_executor
        recovery_ctx = RecoveryContext(
            policy_id=policy_id,
            failure_class=classification.failure_class,
            workspace=input.workspace,
            failure_observations=obs_dicts,
            policy_attempt=policy_attempt,
        )
        recovery_result = run_executor(recovery_ctx)
        recovery_dict = _recovery_result_to_dict(recovery_result)
        result.recovery_results.append(recovery_dict)

        # Increment policy_attempt for next time
        policy_attempt_counts[attempt_key] = policy_attempt + 1

        # ── Check if recovery was blocked ──
        if recovery_result.blocked or not recovery_result.applied:
            result.final_output = output
            result.terminated_by = f"recovery_blocked:{recovery_result.blocked or 'not_applied'}"
            history.add(AttemptRecord(
                attempt_num=attempt_num,
                failure_class=classification.failure_class,
                policy_applied=policy_id,
                verdict=output.verdict.value if hasattr(output.verdict, 'value') else str(output.verdict),
            ))
            return result

        # ── Step 8: S2 authorize retry ──
        # Build directive for S2 to check
        auth_result = s2.authorize_retry(
            failure_class=classification.failure_class,
            policy_applied=policy_id,
            policy_attempt=policy_attempt,
            history=history,
        )
        auth_dict = {
            "authorized": auth_result.authorized,
            "blocked_by": auth_result.blocked_by,
            "reason": auth_result.reason,
        }
        result.s2_authorizations.append(auth_dict)

        # Record attempt in history (for next iteration's oscillation check)
        history.add(AttemptRecord(
            attempt_num=attempt_num,
            failure_class=classification.failure_class,
            policy_applied=policy_id,
            verdict=output.verdict.value if hasattr(output.verdict, 'value') else str(output.verdict),
            env_changes=recovery_result.env_changes,
        ))

        # ── Step 9: Check authorization ──
        if not auth_result.authorized:
            result.final_output = output
            result.terminated_by = f"not_authorized:{auth_result.blocked_by}"
            return result

        # ── Step 10: Prepare retry directive ──
        current_directive = RecoveryDirective(
            failure_class=classification.failure_class,
            policy_applied=policy_id,
            env_changes=recovery_result.env_changes,
            policy_attempt=policy_attempt + 1,
        )

    # ── Max retries reached ──
    result.final_output.verdict = Verdict.TASK_FAILED
    result.terminated_by = "max_retries"
    return result


# ── Dict serializers (for audit trail) ──

def _failure_obs_to_dict(obs: FailureObservation) -> dict:
    return {
        "kind": obs.kind,
        "value": obs.value,
        "source": obs.source,
        "command": obs.command,
        "action": obs.action,
        "deadline_seconds": obs.deadline_seconds,
        "at_action": obs.at_action,
    }


def _classification_to_dict(cls: Any) -> dict:
    # `evidence` is required by S3* audit_classification (consistency check):
    # auditor reads classification.get("evidence", []) and expects each item to
    # be a dict with a "signal" key. Serialize Evidence dataclass accordingly.
    evidence = getattr(cls, "evidence", []) or []
    return {
        "failure_class": cls.failure_class,
        "recovery_policy": cls.recovery_policy,
        "confidence": cls.confidence,
        "evidence": [
            {
                "signal": ev.signal,
                "observation_value": ev.observation_value,
                "observation_kind": ev.observation_kind,
                "at_action": ev.at_action,
            }
            for ev in evidence
        ],
        "matched_signals": cls.matched_signals,
        "ambiguous": cls.ambiguous,
        "alternative_classes": cls.alternative_classes,
        "reason": cls.reason,
    }


def _taxonomy_class_to_dict(c: Any) -> dict:
    return {
        "id": c.id,
        "category": c.category,
        "signals": c.signals,
        "recovery_policy": c.recovery_policy,
    }


def _audit_result_to_dict(audit: Any) -> dict:
    return {
        "passed": audit.passed,
        "algedonic": audit.algedonic,
        "critical_count": audit.critical_count,
        "warn_count": audit.warn_count,
        "findings": [
            {
                "type": f.finding_type.value if hasattr(f.finding_type, 'value') else str(f.finding_type),
                "severity": f.severity.value if hasattr(f.severity, 'value') else str(f.severity),
                "message": f.message,
            }
            for f in audit.findings
        ],
    }


def _recovery_result_to_dict(r: Any) -> dict:
    return {
        "applied": r.applied,
        "env_changes": r.env_changes,
        "blocked": r.blocked,
        "error": r.error,
    }

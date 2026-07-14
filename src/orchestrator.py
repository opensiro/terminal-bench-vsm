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
    # VSM-013: agent-runtime mode. False (default) = direct Python calls
    # (backward-compatible; capability_report uses this). True = coordinate
    # S1/S3/S3*/S2 via AgentProtocol (goose-agents + state-bus). The recovery
    # executor stays Python in both modes (deterministic infra, not a role).
    use_agents: bool = False
    # VSM-015: parallel S3||S3* in agent-mode. False (default) = sequential
    # (S3 classify → S3* audits S3's result). True = both independently classify
    # the same observations in parallel, then divergence is compared. Faster
    # (~50% on classify+audit step) AND a stronger audit (no anchoring bias).
    # Only applies when use_agents=True.
    parallel_s3_s3star: bool = False


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

    Routing: if config.use_agents=True, delegates to run_recovery_cycle_agents
    (VSM-013 agent-runtime mode). Otherwise runs the original Python path.
    """
    cfg = config or OrchestratorConfig()

    # VSM-013: agent-runtime mode — S1/S3/S3*/S2 as goose-agents via protocol.
    if cfg.use_agents:
        from agent_runtime.protocol import AgentProtocol, ProtocolConfig
        proto_cfg = ProtocolConfig(
            s1_provider=cfg.s1_provider or "zai",
            s3star_provider=cfg.s3star_provider or "anthropic",
        )
        protocol = AgentProtocol(proto_cfg)
        return run_recovery_cycle_agents(input, protocol, cfg)

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


def run_recovery_cycle_agents(
    input: S1Input,
    protocol: Any,                    # AgentProtocol (agent_runtime.protocol)
    config: OrchestratorConfig | None = None,
) -> RecoveryCycleResult:
    """Agent-mode recovery cycle (VSM-013): S1/S3/S3*/S2 invoked as goose-agents.

    Same lifecycle + return type as run_recovery_cycle, but each reasoning step
    (S1 solve, S3 classify, S3* audit, S2 authorize) runs as a goose-agent
    subprocess coordinated via the state-bus. The recovery executor stays Python
    (deterministic infra). Activated by OrchestratorConfig.use_agents=True.
    """
    cfg = config or OrchestratorConfig()
    import hashlib
    task_id = f"task-{hash(input.task_prompt) % 100000}"

    history = RetryHistory(task_id=task_id)
    result = RecoveryCycleResult(
        final_output=S1Output(),
        total_attempts=0,
        history=history,
    )

    remaining_time = input.budget.time_seconds
    remaining_tokens = input.budget.tokens
    remaining_actions = input.budget.actions
    current_directive: RecoveryDirective | None = None
    policy_attempt_counts: dict[str, int] = {}

    protocol.open_task(task_id, {
        "task_prompt": input.task_prompt,
        "workspace": str(input.workspace),
        "budget": {"time_seconds": remaining_time, "tokens": remaining_tokens,
                   "actions": remaining_actions},
    })

    try:
        for attempt_num in range(cfg.max_retries + 1):
            result.total_attempts = attempt_num + 1

            # ── Step 1: S1 agent ──
            s1_in = {
                "task_prompt": input.task_prompt,
                "workspace": str(input.workspace),
                "budget": {"time_seconds": max(1, remaining_time),
                           "tokens": max(1, remaining_tokens),
                           "actions": max(1, remaining_actions)},
                "recovery_directive": (current_directive.__dict__ if current_directive else None),
            }
            s1_res = protocol.invoke_s1(task_id, s1_in)
            s1_out = (s1_res.parsed or {}) if s1_res.parsed else {}

            # Map agent output → S1Output (best-effort; agent returns structured JSON)
            verdict_str = s1_out.get("verdict", "unknown")
            try:
                verdict = Verdict(verdict_str)
            except ValueError:
                verdict = Verdict.UNKNOWN
            cost = s1_out.get("cost", {})
            remaining_time -= int(cost.get("time_used", 0))
            remaining_tokens -= int(cost.get("tokens_used", 0))
            remaining_actions -= int(cost.get("actions_taken", 0))
            obs_dicts = s1_out.get("failure_observations", [])

            output = S1Output(verdict=verdict, cost=cost)
            output.failure_observations = [_obs_from_agent(o) for o in obs_dicts]

            # ── Step 2: termination check ──
            if verdict == Verdict.TASK_RESOLVED:
                result.final_output = output
                result.terminated_by = "task_resolved"
                history.add(AttemptRecord(attempt_num=attempt_num, failure_class="none",
                                          policy_applied="none", verdict="task_resolved"))
                return result
            if verdict == Verdict.BUDGET_EXHAUSTED or remaining_time <= 0 or remaining_actions <= 0:
                output.verdict = Verdict.BUDGET_EXHAUSTED
                result.final_output = output
                result.terminated_by = "budget_exhausted"
                return result
            if not obs_dicts:
                result.final_output = output
                result.terminated_by = "no_observations"
                return result

            # ── Steps 3+4: S3 classify + S3* audit ──
            # VSM-015: parallel mode — both independently classify the same
            # observations, divergence is the audit signal (no anchoring bias).
            # Sequential mode (default) — S3 classifies, S3* audits S3's result.
            if cfg.parallel_s3_s3star:
                s3_res, s3star_res, divergence = protocol.invoke_s3_parallel(task_id, obs_dicts)
                classification = (s3_res.parsed or {}) if s3_res.parsed else {}
                audit = divergence  # structured divergence = the audit result
            else:
                # ── Step 3: S3 agent (classify) ──
                s3_res = protocol.invoke_s3(task_id, obs_dicts)
                classification = (s3_res.parsed or {}) if s3_res.parsed else {}
                # ── Step 4: S3* agent (audit, cross-provider) ──
                s3star_res = protocol.invoke_s3star(task_id, classification, obs_dicts)
                audit = (s3star_res.parsed or {}) if s3star_res.parsed else {}
            result.classifications.append(classification)
            result.audit_results.append(audit)
            failure_class = classification.get("failure_class", "Unknown")
            policy_id = classification.get("recovery_policy", "DiagnoseAndPatch")

            if audit.get("algedonic"):
                result.final_output = output
                result.terminated_by = "algedonic"
                return result

            # ── Step 5: recovery executor (Python infra, not an agent) ──
            attempt_key = f"{failure_class}:{policy_id}"
            policy_attempt = policy_attempt_counts.get(attempt_key, 0)
            recovery_dict = protocol.apply_recovery(
                task_id, policy_id, failure_class, str(input.workspace),
                obs_dicts, policy_attempt, dry_run=True,
            )
            result.recovery_results.append(recovery_dict)
            policy_attempt_counts[attempt_key] = policy_attempt + 1

            if recovery_dict.get("blocked") or not recovery_dict.get("applied"):
                result.final_output = output
                result.terminated_by = f"recovery_blocked:{recovery_dict.get('blocked') or 'not_applied'}"
                return result

            # ── Step 6: S2 agent (authorize retry) ──
            s2_res = protocol.invoke_s2(task_id, failure_class, policy_id, policy_attempt)
            auth = (s2_res.parsed or {}) if s2_res.parsed else {}
            result.s2_authorizations.append(auth)
            history.add(AttemptRecord(
                attempt_num=attempt_num, failure_class=failure_class,
                policy_applied=policy_id,
                verdict=verdict_str,
                env_changes=recovery_dict.get("env_changes", []),
            ))

            if not auth.get("authorized"):
                result.final_output = output
                result.terminated_by = f"not_authorized:{auth.get('blocked_by')}"
                return result

            # ── Step 7: prepare retry directive ──
            current_directive = RecoveryDirective(
                failure_class=failure_class,
                policy_applied=policy_id,
                env_changes=recovery_dict.get("env_changes", []),
                policy_attempt=policy_attempt + 1,
            )

        result.final_output.verdict = Verdict.TASK_FAILED
        result.terminated_by = "max_retries"
        return result
    finally:
        protocol.close_task(task_id)


# ── Agent-output helpers (VSM-013 agent-mode: goose JSON → dataclasses) ──

# Valid fields for FailureObservation (from runtime/types.py). Goose-agents may
# emit extra/missing fields; we keep only valid ones with defaults.
_FAILURE_OBS_FIELDS = {"kind", "value", "source", "command", "action",
                       "deadline_seconds", "at_action"}


def _obs_from_agent(o: Any) -> FailureObservation:
    """Tolerantly map an agent-produced observation dict → FailureObservation.

    Goose-agents emit free-form JSON; only valid dataclass fields are kept,
    defaults filled for missing ones. Non-dict values become error_string obs.
    """
    if not isinstance(o, dict):
        return FailureObservation(kind="error_string", value=str(o))
    # Keep only valid fields, coerce types best-effort
    clean = {k: v for k, v in o.items() if k in _FAILURE_OBS_FIELDS}
    # Ensure required 'kind' has a value
    clean.setdefault("kind", "error_string")
    return FailureObservation(**clean)


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

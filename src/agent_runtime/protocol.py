"""protocol — coordination API for the agent runtime (VSM-013).

Replaces direct Python method calls in orchestrator.py with agent invocations.
Each recovery-cycle step = state-bus write (input) → goose-runner (agent) →
state-bus read (output). The orchestrator becomes a protocol driver.

Each invoke_* function:
  1. Writes structured input to the task's state-bus (key = step input).
  2. Runs the corresponding goose-agent via GooseRunner.
  3. Reads/parses the agent's structured output.
  4. Writes the output back to the state-bus (key = step output, for next agent).
  5. Returns the parsed output dict.

The orchestrator (VSM-013 Step 4) calls these instead of the old
dispatcher.invoke / classifier.classify / auditor.audit / s2.authorize_retry.

Per-role configs are defined in ROLE_CONFIGS below — the tool surface + provider
for each system. S3* gets a different provider (VSM-001 cross-provider).

Stateless (CONTRACT §5): each invoke_* is a fresh agent subprocess. Per-task
state lives only in the state-bus (cleaned up on close).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .goose_runner import AgentConfig, AgentResult, GooseRunner
from .state_bus import StateBus


# ── Per-role agent configs ──

# Default systems dir: vsm/systems/ (sibling of src/ in the monorepo).
# Override via ProtocolConfig for non-default layouts.
_DEFAULT_SYSTEMS_DIR = Path(__file__).resolve().parent.parent.parent / "vsm" / "systems"

ROLE_CONFIGS: dict[str, dict[str, Any]] = {
    "s1-dispatcher": {
        "tools": ["fs", "shell", "git"],
        "provider": "zai",
        "max_turns": 20,
    },
    "s2-coordinator": {
        "tools": ["state_bus_read", "state_bus_write", "conflict_check", "retry_authorize"],
        "provider": "zai",
        "max_turns": 10,
    },
    "s3-optimizer": {
        "tools": ["taxonomy_read", "signal_match", "policy_select"],
        "provider": "zai",
        "max_turns": 10,
    },
    "s3-star-auditor": {
        "tools": ["state_bus_read", "audit_check"],
        "provider": "anthropic",   # VSM-001: MUST differ from s1
        "max_turns": 10,
    },
    "s4-scout": {
        "tools": ["browser", "taxonomy_read", "intel_write", "fs"],
        "provider": "zai",
        "max_turns": 15,
    },
    "s5-guardian": {
        "tools": ["identity_read", "osm_apply", "issue_resolve", "algedonic_log", "fs"],
        "provider": "zai",
        "max_turns": 15,
    },
    # ── S1 triad sub-agents (VSM-021). Internal S1 roles, NOT standalone VSM
    # systems. Same provider as s1-dispatcher (zai) — they are part of S1, so
    # the cross-provider constraint (s1↔s3*) is unaffected. Workspace is bound
    # to the task workspace (set at runtime by the triad callables), not vsm/.
    "s1-planner": {
        "tools": ["fs", "shell"],
        "provider": "zai",
        "max_turns": 12,
    },
    "s1-test-controller": {
        "tools": ["fs", "shell", "git"],
        "provider": "zai",
        "max_turns": 15,
    },
    "s1-verifier": {
        "tools": ["fs", "shell"],
        "provider": "zai",
        "max_turns": 10,
    },
}


@dataclass
class ProtocolConfig:
    """Configuration for the agent coordination protocol.

    Args:
        systems_dir: path to vsm/systems/ (SOUL/SKILL/TASK per role).
        state_bus_root: root dir for StateBus (default: temp).
        s1_provider: LLM provider for S1 (documented for cross-provider constraint).
        s3star_provider: MUST differ from s1_provider (VSM-001).
        agent_timeout_sec: per-agent wall-clock cap.
    """

    systems_dir: Path = _DEFAULT_SYSTEMS_DIR
    state_bus_root: str | None = None
    s1_provider: str = "zai"
    s3star_provider: str = "anthropic"
    agent_timeout_sec: int = 300

    def _agent_config(self, role: str) -> AgentConfig:
        """Build AgentConfig for a role, applying provider overrides."""
        cfg = dict(ROLE_CONFIGS.get(role, {}))
        # Apply cross-provider constraint. S1 sub-agents (VSM-021 triad) are part
        # of S1 → use s1_provider, same as s1-dispatcher.
        if role in ("s1-dispatcher", "s1-planner", "s1-test-controller", "s1-verifier"):
            cfg["provider"] = self.s1_provider
        elif role == "s3-star-auditor":
            cfg["provider"] = self.s3star_provider
        return AgentConfig(
            system_name=role,
            systems_dir=self.systems_dir,
            provider=cfg.get("provider", "zai"),
            tools=cfg.get("tools", []),
            max_turns=cfg.get("max_turns", 15),
        )

    def _s3star_classify_config(self) -> AgentConfig:
        """S3* config for parallel-mode: classify (not audit) + classify contract.

        VSM-015: in parallel mode, S3* independently classifies the observations
        (same output shape as S3), instead of auditing S3's result. The contract
        override tells the agent to return a classification, not an audit.
        """
        base = self._agent_config("s3-star-auditor")
        base.contract_override = (
            "── Output contract (S3* parallel classify) ──\n"
            "You are classifying INDEPENDENTLY (do not see S3's result — different provider).\n"
            "End your response with a JSON block enclosed in ```json ... ```:\n"
            "```\n"
            '{"failure_class": <string>, "recovery_policy": <string>,\n'
            ' "confidence": "high|medium|low", "ambiguous": <bool>,\n'
            ' "alternative_classes": [<string>], "reason": <string>}\n'
            "```\n"
            "Use the signal_match / taxonomy_read tools to ground your classification."
        )
        # S3* in classify-mode needs taxonomy tools (like S3), not audit tools
        base.tools = ["taxonomy_read", "signal_match", "policy_select", "state_bus_read"]
        return base


class AgentProtocol:
    """Coordinates VSM system agents via the state-bus + goose-runner.

    The orchestrator holds one instance and calls invoke_s1/s3/s3star/s2 in the
    recovery-cycle sequence. Each call is one agent invocation (fresh subprocess).
    """

    def __init__(self, config: ProtocolConfig | None = None):
        self.config = config or ProtocolConfig()
        self.bus = StateBus(root=self.config.state_bus_root)
        self.runner = GooseRunner()

    # ── Task lifecycle ──

    def open_task(self, task_id: str, task_input: dict) -> None:
        """Create a task in the state-bus + write the initial task_input."""
        try:
            self.bus.create(task_id, agents=list(ROLE_CONFIGS.keys()))
        except ValueError:
            # Task already exists (retry) — close + recreate cleanly.
            self.bus.close(task_id)
            self.bus.create(task_id, agents=list(ROLE_CONFIGS.keys()))
        self.bus.update(task_id, "task_input", task_input)

    def close_task(self, task_id: str) -> None:
        """Clean up a task after the recovery cycle ends."""
        self.bus.close(task_id)

    # ── Per-role invocations ──

    def _invoke(self, task_id: str, role: str, input_key: str, input_value: Any,
                output_key: str) -> AgentResult:
        """Generic pattern: write input → run agent → read output → write output."""
        self.bus.update(task_id, input_key, input_value)

        # Build the text input the agent sees (current relevant state slice)
        task_input_text = json.dumps(
            {input_key: input_value, "task_id": task_id},
            ensure_ascii=False, indent=2,
        )
        agent_cfg = self.config._agent_config(role)
        result = self.runner.run(agent_cfg, task_input_text, self.config.agent_timeout_sec)

        if result.parsed is not None:
            self.bus.update(task_id, output_key, result.parsed)
        return result

    def invoke_s1(self, task_id: str, task_input: dict) -> AgentResult:
        """S1 solver agent: receives task, produces verdict + trace + failure_obs."""
        return self._invoke(task_id, "s1-dispatcher", "task_input", task_input, "s1_output")

    def invoke_s3(self, task_id: str, observations: list[dict]) -> AgentResult:
        """S3 classifier agent: receives failure_observations, produces classification."""
        return self._invoke(task_id, "s3-optimizer", "s1_failure_observations", observations,
                            "s3_classification")

    def invoke_s3star(self, task_id: str, classification: dict, observations: list[dict]) -> AgentResult:
        """S3* audit agent (cross-provider): audits a classification, produces findings."""
        # S3* needs both the classification and the observations to audit
        audit_input = {"classification": classification, "observations": observations}
        return self._invoke(task_id, "s3-star-auditor", "s3star_audit_input", audit_input,
                            "s3star_audit")

    def invoke_s3_parallel(self, task_id: str,
                           observations: list[dict]) -> tuple[AgentResult, AgentResult, dict]:
        """Run S3 + S3* IN PARALLEL: both independently classify the same observations.

        VSM-015 parallelization. Instead of S3 classify → S3* audit-sequentially,
        both agents receive the SAME observations and classify INDEPENDENTLY:
          - S3 (primary classifier, provider P1) → classification_s3
          - S3* (independent classifier, provider P2 ≠ P1) → classification_s3star
        Then their results are compared (divergence check).

        This is both FASTER (~50% on the classify+audit step) and a STRONGER audit:
        S3* does not see S3's classification → no anchoring bias. Divergence between
        two independent classifications on different providers is a richer audit
        signal than checking S3's self-consistency.

        Returns: (s3_result, s3star_result, divergence)
          divergence: {classes_match, policies_match, confidence_match, findings, algedonic}
        """
        from concurrent.futures import ThreadPoolExecutor

        # S3 input: observations (classify)
        s3_input = observations
        # S3* input: SAME observations (classify independently, NOT S3's result)
        # This is the key change — S3* classifies from scratch, no anchoring.
        s3star_input = {
            "observations": observations,
            "instruction": "Independently classify these observations. Do NOT assume "
                           "any prior classification — derive your own from the taxonomy.",
        }

        # Run both agents in parallel threads (goose subprocesses release the GIL
        # during subprocess.run wait, so this gives real parallelism).
        # S3* uses the classify-config (taxonomy tools + classify contract), NOT
        # its default audit-config — see _s3star_classify_config().
        s3star_cfg = self.config._s3star_classify_config()

        def _run_s3():
            return self._invoke(task_id, "s3-optimizer",
                                "s1_failure_observations", s3_input, "s3_classification")

        def _run_s3star():
            # Custom invoke: S3* config + classify contract, different input/output keys
            self.bus.update(task_id, "s3star_classify_input", s3star_input)
            task_text = json.dumps({"s3star_classify_input": s3star_input, "task_id": task_id},
                                   ensure_ascii=False, indent=2)
            res = self.runner.run(s3star_cfg, task_text, self.config.agent_timeout_sec)
            if res.parsed is not None:
                self.bus.update(task_id, "s3star_classification", res.parsed)
            return res

        with ThreadPoolExecutor(max_workers=2) as pool:
            future_s3 = pool.submit(_run_s3)
            future_s3star = pool.submit(_run_s3star)
            s3_res = future_s3.result()
            s3star_res = future_s3star.result()

        # Compare the two independent classifications
        cls_s3 = (s3_res.parsed or {}) if s3_res.parsed else {}
        cls_s3star = (s3star_res.parsed or {}) if s3star_res.parsed else {}
        divergence = self._classify_divergence(cls_s3, cls_s3star, observations)

        # Write divergence to state-bus (for orchestrator + observability)
        self.bus.update(task_id, "s3star_audit", divergence)
        # Keep s3star_res.parsed as the independent classification (not the audit)
        return s3_res, s3star_res, divergence

    def _classify_divergence(self, cls_s3: dict, cls_s3star: dict,
                             observations: list[dict]) -> dict:
        """Compare two independent classifications → structured audit findings.

        Divergence in failure_class is the critical signal (potential
        misclassification). Divergence in policy is less critical (multiple
        valid policies may exist for one class). Confidence mismatch flags
        uncertainty. Severe divergence (different class AND low confidence) →
        algedonic (escalate to S5).
        """
        findings = []
        classes_match = cls_s3.get("failure_class") == cls_s3star.get("failure_class")
        policies_match = cls_s3.get("recovery_policy") == cls_s3star.get("recovery_policy")
        conf_s3 = cls_s3.get("confidence", "low")
        conf_s3star = cls_s3star.get("confidence", "low")
        confidence_match = conf_s3 == conf_s3star

        if not classes_match:
            sev = "CRITICAL" if (conf_s3 == "high" and conf_s3star == "high") else "WARN"
            findings.append({
                "severity": sev,
                "type": "class_divergence",
                "message": (
                    f"S3 classified '{cls_s3.get('failure_class')}' but S3* "
                    f"independently classified '{cls_s3star.get('failure_class')}' "
                    f"— possible misclassification or taxonomy ambiguity"
                ),
            })
        if not policies_match and classes_match:
            findings.append({
                "severity": "WARN",
                "type": "policy_divergence",
                "message": (
                    f"same class but different policy: S3='{cls_s3.get('recovery_policy')}' "
                    f"vs S3*='{cls_s3star.get('recovery_policy')}'"
                ),
            })
        if not confidence_match:
            findings.append({
                "severity": "INFO",
                "type": "confidence_divergence",
                "message": f"confidence mismatch: S3={conf_s3} vs S3*={conf_s3star}",
            })

        # Algedonic if class divergence AND at least one high-confidence →
        # two independent agents strongly disagree = structural concern.
        algedonic = (not classes_match and
                     (conf_s3 == "high" or conf_s3star == "high"))

        return {
            "passed": classes_match and not algedonic,
            "classes_match": classes_match,
            "policies_match": policies_match,
            "confidence_match": confidence_match,
            "s3_classification": cls_s3,
            "s3star_classification": cls_s3star,
            "findings": findings,
            "algedonic": algedonic,
        }

    def invoke_s2(self, task_id: str, failure_class: str, policy_applied: str,
                  policy_attempt: int) -> AgentResult:
        """S2 coordinator agent: 4-check retry authorization."""
        s2_input = {
            "failure_class": failure_class,
            "policy_applied": policy_applied,
            "policy_attempt": policy_attempt,
        }
        return self._invoke(task_id, "s2-coordinator", "s2_authorize_input", s2_input,
                            "s2_authorization")

    # ── S4: on-demand intelligence (NOT part of recovery cycle) ──

    def scan_on_demand(self, trigger: dict) -> AgentResult:
        """S4 scout agent: on-demand environment scan (VSM-016).

        S4 is NOT part of the recovery cycle (S1→S3||S3*→S2). It is an on-demand
        intelligence role triggered by:
          - weak signals (taxonomy gaps, recovery_rate_drift, retry_burn_anomaly)
          - heartbeat (vsm.yaml: s4_scout every 1d)
          - explicit request (S5 / human)

        S4 uses browser tools (search/fetch) to scan for general-purpose coding
        patterns and recovery-policy candidates, then writes signals to
        state/intel.json. Strategic shifts → VSM-NNN → S5.

        Unlike invoke_s1/s2/s3, this does NOT use a per-task state-bus namespace
        (S4 is cross-task intelligence, not per-task recovery). It uses a fresh
        ephemeral task_id and writes results to the product's state/intel.json
        via the intel_write tool.

        Args:
            trigger: {type: "weak_signal|heartbeat|request", detail: "...",
                      context: {...}}  — what prompted the scan.

        Returns:
            AgentResult with parsed = {signals: [...], strategic_shifts: [...],
                                       patterns_discovered: [...]}.
        """
        import hashlib
        trigger_id = f"s4-scan-{hashlib.sha1(str(trigger).encode()).hexdigest()[:8]}"
        self.open_task(trigger_id, {"trigger": trigger})
        try:
            scan_input = {
                "trigger": trigger,
                "instruction": (
                    "Scan for general-purpose coding patterns and recovery-policy "
                    "candidates relevant to the trigger. Use browser.search for "
                    "web discovery, taxonomy_read to check current coverage. Write "
                    "findings to intel.json via intel_write. Flag strategic shifts "
                    "(e.g. uncovered failure class) — these require a VSM-NNN (basta)."
                ),
            }
            result = self._invoke(trigger_id, "s4-scout", "scan_input", scan_input,
                                  "scan_result")
            return result
        finally:
            # S4 scan results persist in state/intel.json (written by the agent
            # via intel_write tool); the ephemeral state-bus entry is cleaned up.
            self.close_task(trigger_id)

    # ── S5: autonomous architect (algedonic + triage, VSM-006/017) ──

    def handle_algedonic(self, signal: dict) -> AgentResult:
        """S5 guardian agent: handle an algedonic signal (VSM-017).

        S5 is the autonomous architect (VSM-006). When S3*/S4 raise an algedonic
        signal (severity S0/S1 — structural concern), S5 does NOT escalate to
        human. Instead it acts as architect:
          - analyze the signal (structural defect, viability breach, etc.)
          - decide: operational fix, or structural OSM primitive (Split/Merge/
            Reconfigure), or blocked (identity change requires parent)
          - execute via osm_apply / issue_resolve tools
          - log the intervention (observable by parent VSM-005 metric)

        S5 does NOT touch identity/values/never_do (the single autonomy limit —
        identity change requires a parent decision via VSM-NNN).

        Args:
            signal: {source: "S3*|S4|S3", severity: "S0|S1", type: <string>,
                     detail: <string>, context: {...}}

        Returns:
            AgentResult with parsed = {action: "osm_primitive|operational|blocked",
                                       primitive: <string|null>, issue_id: <string>,
                                       intervention_logged: <bool>}.
        """
        import hashlib
        sig_id = f"s5-algedonic-{hashlib.sha1(str(signal).encode()).hexdigest()[:8]}"
        self.open_task(sig_id, {"algedonic_signal": signal})
        try:
            algedonic_input = {
                "signal": signal,
                "instruction": (
                    "This is an ALGEDONIC signal (S0/S1 — structural concern). "
                    "As autonomous architect (VSM-006), decide and ACT (do not "
                    "escalate to human): apply an OSM primitive (Split/Merge/"
                    "Reconfigure) via osm_apply if structural, or resolve "
                    "operationally via issue_resolve. Identity/values/never_do "
                    "changes are BLOCKED (require parent). Log every intervention."
                ),
            }
            result = self._invoke(sig_id, "s5-guardian", "algedonic_input",
                                  algedonic_input, "s5_decision")
            return result
        finally:
            self.close_task(sig_id)

    def triage_issues(self, pending_issues: list[dict]) -> AgentResult:
        """S5 guardian agent: triage + resolve pending issues (VSM-017).

        The autonomous architect's routine duty: process issues with
        status=triage. For each, S5 decides (not prepares for human):
          - operational → decision + execution
          - structural → OSM primitive
          - identity change → blocked (标记 requires_parent)

        Args:
            pending_issues: list of issue dicts (id, title, severity, signal_type).

        Returns:
            AgentResult with parsed = {resolutions: [{issue_id, action, ...}]}.
        """
        import hashlib
        triage_id = f"s5-triage-{hashlib.sha1(str(pending_issues).encode()).hexdigest()[:8]}"
        self.open_task(triage_id, {"pending_issues": pending_issues})
        try:
            triage_input = {
                "issues": pending_issues,
                "instruction": (
                    "Triage and RESOLVE each issue (VSM-006 autonomous architect — "
                    "do not escalate to human). For each: decide operational fix, "
                    "structural OSM primitive, or blocked (identity change). "
                    "Record decisions via issue_resolve."
                ),
            }
            result = self._invoke(triage_id, "s5-guardian", "triage_input",
                                  triage_input, "s5_resolutions")
            return result
        finally:
            self.close_task(triage_id)

    # ── Recovery executor (not an agent — deterministic, stays Python) ──
    # The recovery executor applies env changes (pip install, venv, git reset).
    # It is deterministic infrastructure, NOT a reasoning role — stays Python.
    # VSM-012 agents = S1-S5 reasoning roles; recovery execution = infra.

    def apply_recovery(self, task_id: str, policy_id: str, failure_class: str,
                       workspace: str, failure_observations: list[dict],
                       policy_attempt: int, dry_run: bool = True) -> dict:
        """Apply a recovery policy to the environment (deterministic infra).

        Wraps recovery_policies.base.run_executor. Writes result to state-bus.
        NOT an agent — this is infrastructure (pip install / git reset / etc.).
        """
        from recovery_policies.base import RecoveryContext, run_executor
        ctx = RecoveryContext(
            policy_id=policy_id,
            failure_class=failure_class,
            workspace=Path(workspace),
            failure_observations=failure_observations,
            policy_attempt=policy_attempt,
            extra={"dry_run": dry_run},
        )
        result = run_executor(ctx)
        recovery_dict = {
            "applied": result.applied,
            "env_changes": result.env_changes,
            "blocked": result.blocked,
        }
        self.bus.update(task_id, "recovery_result", recovery_dict)
        return recovery_dict

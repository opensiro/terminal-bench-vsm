"""verify — S1 self-verification: pre-flight check + capability report.

E2E verification = internal S1 capability (recursive viability).
S1 contains its own verification functions, not external audit.

Two components:
  1. preflight_check: fast (~1s) self-check before each invoke.
     MCP alive, workspace OK, solver instantiates. Diagnostic output
     in S1Output.failure_observations (not escalation up).
  2. capability_report: on-demand full e2e. Runs solver → MCP → trace →
     recovery cycle. Structured report for phase transitions / config
     changes / S5 requests.

Triggered by:
  - Every invoke (preflight only — fast).
  - On-demand: phase transition (vsmlite /vsmlite-mature), config change,
    S5 request.
"""
from __future__ import annotations
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .types import S1Input, S1Output, Verdict, Budget, FailureObservation


@dataclass
class CheckResult:
    """Single check result in preflight or capability report."""
    name: str
    passed: bool
    detail: str = ""
    duration_ms: float = 0.0


@dataclass
class PreflightResult:
    """Result of preflight_check (fast, before each invoke)."""
    ok: bool
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def failed_checks(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed]


@dataclass
class SystemStatus:
    """Status of one system in capability report."""
    name: str               # S1, S2, S3, S3_star, orchestrator
    passed: bool
    checks: list[CheckResult] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)  # structured evidence

    @property
    def detail(self) -> str:
        lines = [f"{'PASS' if self.passed else 'FAIL'} {self.name}"]
        for c in self.checks:
            mark = "✓" if c.passed else "✗"
            lines.append(f"  {mark} {c.name}: {c.detail}")
        return "\n".join(lines)


@dataclass
class CapabilityReport:
    """Full capability report (on-demand e2e)."""
    systems: dict[str, SystemStatus] = field(default_factory=dict)
    overall: str = "unknown"  # all_passed | partial | failed
    generated_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))

    @property
    def all_passed(self) -> bool:
        return all(s.passed for s in self.systems.values())

    @property
    def passed_systems(self) -> list[str]:
        return [name for name, s in self.systems.items() if s.passed]

    @property
    def failed_systems(self) -> list[str]:
        return [name for name, s in self.systems.items() if not s.passed]

    def to_dict(self) -> dict:
        return {
            "overall": self.overall,
            "all_passed": self.all_passed,
            "generated_at": self.generated_at,
            "passed_systems": self.passed_systems,
            "failed_systems": self.failed_systems,
            "systems": {
                name: {
                    "passed": s.passed,
                    "checks": [{"name": c.name, "passed": c.passed, "detail": c.detail} for c in s.checks],
                    "evidence": s.evidence,
                }
                for name, s in self.systems.items()
            },
        }


# ── Preflight check (fast, every invoke) ──

def preflight_check(input: S1Input, mcp_server: Any) -> PreflightResult:
    """Fast self-check before invoke (~1s).

    Checks:
      1. MCP server responds to tools/list
      2. Workspace exists and is writable
      3. Budget > 0

    Returns PreflightResult. If not ok, caller should return diagnostic S1Output.
    """
    checks = []

    # Check 1: MCP alive
    t0 = time.time()
    try:
        tools = mcp_server.list_tools()
        tool_count = len(tools) if isinstance(tools, list) else 0
        checks.append(CheckResult(
            name="mcp_responds",
            passed=tool_count > 0,
            detail=f"{tool_count} tools registered",
            duration_ms=(time.time() - t0) * 1000,
        ))
    except Exception as exc:
        checks.append(CheckResult(
            name="mcp_responds",
            passed=False,
            detail=f"error: {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        ))

    # Check 2: workspace
    t0 = time.time()
    ws = Path(input.workspace)
    ws_exists = ws.exists()
    ws_writable = ws_exists and os.access(ws, os.W_OK)
    checks.append(CheckResult(
        name="workspace_accessible",
        passed=ws_exists and ws_writable,
        detail=f"exists={ws_exists}, writable={ws_writable}, path={ws}",
        duration_ms=(time.time() - t0) * 1000,
    ))

    # Check 3: budget > 0
    t0 = time.time()
    budget_ok = (
        input.budget.time_seconds > 0
        and input.budget.tokens > 0
        and input.budget.actions > 0
    )
    checks.append(CheckResult(
        name="budget_positive",
        passed=budget_ok,
        detail=f"time={input.budget.time_seconds}s tokens={input.budget.tokens} actions={input.budget.actions}",
        duration_ms=(time.time() - t0) * 1000,
    ))

    ok = all(c.passed for c in checks)
    return PreflightResult(ok=ok, checks=checks)


def preflight_diagnostic_output(result: PreflightResult) -> S1Output:
    """Build diagnostic S1Output for failed preflight (CONTRACT §3 format).

    Verdict = UNKNOWN. failure_observations contain preflight failures.
    Not an escalation up — normal diagnostic output.
    """
    observations = []
    for check in result.failed_checks:
        observations.append(FailureObservation(
            kind="error_string",
            value=f"preflight/{check.name}: {check.detail}",
            source="internal",
            at_action=0,
        ))
    return S1Output(
        verdict=Verdict.UNKNOWN,
        failure_observations=observations,
        cost={"time_used": 0.0, "tokens_used": 0, "actions_taken": 0},
    )


# ── Capability report (on-demand, full e2e) ──

@dataclass
class VerifyConfig:
    """Configuration for capability report."""
    taxonomy_path: str = ""
    workspace: str = ""          # if empty, creates temp workspace
    s1_provider: str = "zai"     # documented for S3* cross-provider constraint
    s3star_provider: str = "anthropic"  # must differ from s1_provider
    dry_run: bool = True         # dry_run recovery (no real pip install)


def capability_report(config: VerifyConfig | None = None) -> CapabilityReport:
    """Run full e2e capability report.

    Tests each system (S1, S2, S3, S3*, orchestrator) with real components.
    Returns structured CapabilityReport.
    """
    cfg = config or VerifyConfig()
    report = CapabilityReport()

    # Resolve taxonomy path
    src_dir = Path(__file__).resolve().parent.parent
    taxonomy_path = cfg.taxonomy_path or str(src_dir / "failure_taxonomy.yaml")

    # Create temp workspace if not provided
    if cfg.workspace:
        workspace = Path(cfg.workspace)
    else:
        workspace = Path(tempfile.mkdtemp(prefix="s1-verify-"))
        # Create a minimal Python file for solver to find
        (workspace / "test_file.py").write_text("def test_ok():\n    assert True\n")

    # ── S1 verify ──
    report.systems["S1"] = _verify_s1(workspace, cfg)

    # ── S2 verify ──
    report.systems["S2"] = _verify_s2(taxonomy_path)

    # ── S3 verify ──
    report.systems["S3"] = _verify_s3(taxonomy_path)

    # ── S3* verify ──
    report.systems["S3_star"] = _verify_s3_star(cfg.s1_provider, cfg.s3star_provider, taxonomy_path)

    # ── Orchestrator verify ──
    report.systems["orchestrator"] = _verify_orchestrator(workspace, taxonomy_path, cfg)

    # ── Agent runtime verify (VSM-013 foundation) ──
    report.systems["agent_runtime"] = _verify_agent_runtime()

    # ── S4 scout verify (VSM-016) ──
    report.systems["s4_scout"] = _verify_s4_scout()

    # Overall
    if report.all_passed:
        report.overall = "all_passed"
    elif len(report.passed_systems) > 0:
        report.overall = "partial"
    else:
        report.overall = "failed"

    return report


def _verify_agent_runtime() -> SystemStatus:
    """Verify agent_runtime foundation (VSM-013): state-bus + protocol API.

    Checks the foundation WITHOUT launching goose (keeps verify fast & offline).
    Goose-runner + full agent invocations are exercised in eval/integration tests.
    """
    checks = []
    evidence = {}

    # Check 1: state_bus inter-process read/write
    import tempfile
    t0 = time.time()
    try:
        from agent_runtime.state_bus import StateBus
        with tempfile.TemporaryDirectory() as td:
            bus = StateBus(root=td)
            bus.create("verify-task", agents=["s1", "s3"])
            bus.update("verify-task", "s1_output", {"verdict": "task_failed"})
            val = bus.read("verify-task", "s1_output")
            assert val == {"verdict": "task_failed"}
            bus.close("verify-task")
        checks.append(CheckResult(
            name="state_bus_read_write",
            passed=True,
            detail="create/update/read/close OK (file-based, atomic)",
            duration_ms=(time.time() - t0) * 1000,
        ))
        evidence["state_bus"] = "OK"
    except Exception as exc:
        checks.append(CheckResult(
            name="state_bus_read_write",
            passed=False,
            detail=f"error: {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        ))

    # Check 2: goose_runner prompt assembly + result parsing
    t0 = time.time()
    try:
        from agent_runtime.goose_runner import AgentConfig, build_prompt, parse_result
        from pathlib import Path
        systems_dir = Path(__file__).resolve().parent.parent.parent / "vsm" / "systems"
        cfg = AgentConfig(system_name="s2-coordinator", systems_dir=systems_dir)
        prompt = build_prompt(cfg, '{"test": true}')
        assert "S2" in prompt and "coordinator" in prompt
        parsed = parse_result('text\n```json\n{"x": 1}\n```\n')
        assert parsed == {"x": 1}
        checks.append(CheckResult(
            name="goose_runner_prompt_parse",
            passed=True,
            detail=f"prompt={len(prompt)} chars, parse_result extracts JSON",
            duration_ms=(time.time() - t0) * 1000,
        ))
        evidence["goose_runner"] = "OK"
    except Exception as exc:
        checks.append(CheckResult(
            name="goose_runner_prompt_parse",
            passed=False,
            detail=f"error: {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        ))

    # Check 3: protocol API + role configs
    t0 = time.time()
    try:
        from agent_runtime.protocol import ProtocolConfig, ROLE_CONFIGS
        pcfg = ProtocolConfig()
        # Cross-provider constraint: S3* provider must differ from S1
        s1_cfg = pcfg._agent_config("s1-dispatcher")
        s3star_cfg = pcfg._agent_config("s3-star-auditor")
        assert s1_cfg.provider != s3star_cfg.provider, \
            f"cross-provider violated: s1={s1_cfg.provider}, s3*={s3star_cfg.provider}"
        # Each role has a tool surface
        for role in ("s1-dispatcher", "s2-coordinator", "s3-optimizer", "s3-star-auditor"):
            assert ROLE_CONFIGS[role]["tools"], f"{role} has no tools"
        checks.append(CheckResult(
            name="protocol_role_configs",
            passed=True,
            detail=f"4 roles configured; s1={s1_cfg.provider}, s3*={s3star_cfg.provider} (differs)",
            duration_ms=(time.time() - t0) * 1000,
        ))
        evidence["protocol"] = {"s1_provider": s1_cfg.provider,
                                "s3star_provider": s3star_cfg.provider}
    except Exception as exc:
        checks.append(CheckResult(
            name="protocol_role_configs",
            passed=False,
            detail=f"error: {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        ))

    return SystemStatus(
        name="agent_runtime",
        passed=all(c.passed for c in checks),
        checks=checks,
        evidence=evidence,
    )


def _verify_s1(workspace: Path, cfg: VerifyConfig) -> SystemStatus:
    """Verify S1: solver runs, MCP tools work, produces trace."""
    checks = []
    evidence = {}

    # Check 1: mono-agent solver (RuleBasedSolver)
    t0 = time.time()
    try:
        from .dispatcher import S1Dispatcher
        from .types import S1Input, Budget

        dispatcher = S1Dispatcher(solver_mode="mono")
        input = S1Input(
            task_prompt="verify: run tests",
            workspace=workspace,
            budget=Budget(time_seconds=60, tokens=10000, actions=20),
        )
        output = dispatcher.invoke(input)
        passed = output.verdict in (Verdict.TASK_RESOLVED, Verdict.TASK_FAILED, Verdict.UNKNOWN)
        checks.append(CheckResult(
            name="mono_solver_invoke",
            passed=passed,
            detail=f"verdict={output.verdict.value}, trace={len(output.trace)} entries",
            duration_ms=(time.time() - t0) * 1000,
        ))
        evidence["mono"] = {"verdict": output.verdict.value, "trace_len": len(output.trace)}
    except Exception as exc:
        checks.append(CheckResult(
            name="mono_solver_invoke",
            passed=False,
            detail=f"error: {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        ))

    # Check 2: multi-agent solver (MultiAgentSolver via session sync)
    t0 = time.time()
    try:
        from .dispatcher import S1Dispatcher
        dispatcher = S1Dispatcher(solver_mode="multi")
        input = S1Input(
            task_prompt="verify: run tests (multi)",
            workspace=workspace,
            budget=Budget(time_seconds=60, tokens=10000, actions=20),
        )
        output = dispatcher.invoke(input)
        passed = output.verdict in (Verdict.TASK_RESOLVED, Verdict.TASK_FAILED, Verdict.UNKNOWN)
        checks.append(CheckResult(
            name="multi_solver_invoke",
            passed=passed,
            detail=f"verdict={output.verdict.value}, trace={len(output.trace)} entries",
            duration_ms=(time.time() - t0) * 1000,
        ))
        evidence["multi"] = {"verdict": output.verdict.value, "trace_len": len(output.trace)}
    except Exception as exc:
        checks.append(CheckResult(
            name="multi_solver_invoke",
            passed=False,
            detail=f"error: {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        ))

    # Check 3: preflight_check works
    t0 = time.time()
    try:
        from mcp_server.server import create_server
        mcp = create_server(str(workspace))
        from .types import S1Input, Budget
        input = S1Input(
            task_prompt="preflight test",
            workspace=workspace,
            budget=Budget(time_seconds=60, tokens=10000, actions=20),
        )
        result = preflight_check(input, mcp)
        checks.append(CheckResult(
            name="preflight_check",
            passed=result.ok,
            detail=f"ok={result.ok}, {len(result.checks)} checks",
            duration_ms=(time.time() - t0) * 1000,
        ))
        evidence["preflight"] = {"ok": result.ok}
    except Exception as exc:
        checks.append(CheckResult(
            name="preflight_check",
            passed=False,
            detail=f"error: {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        ))

    return SystemStatus(
        name="S1",
        passed=all(c.passed for c in checks),
        checks=checks,
        evidence=evidence,
    )


def _verify_s2(taxonomy_path: str) -> SystemStatus:
    """Verify S2: coordinator authorize_retry, anti-repeat, oscillation, conflict."""
    checks = []
    evidence = {}

    # Check 1: authorize_retry with valid attempt
    t0 = time.time()
    try:
        from s2.coordinator import S2Coordinator
        from s2.types import RetryHistory
        from classifier.classifier import FailureClassifier

        classifier = FailureClassifier(taxonomy_path)
        s2 = S2Coordinator(get_anti_repeat_limit=classifier.get_anti_repeat_limit)
        history = RetryHistory(task_id="s2-verify")
        auth = s2.authorize_retry(
            failure_class="ImportError",
            policy_applied="InstallDependency",
            policy_attempt=0,
            history=history,
        )
        checks.append(CheckResult(
            name="authorize_retry_valid",
            passed=auth.authorized,
            detail=f"authorized={auth.authorized}",
            duration_ms=(time.time() - t0) * 1000,
        ))
        evidence["authorize_valid"] = auth.authorized
    except Exception as exc:
        checks.append(CheckResult(
            name="authorize_retry_valid",
            passed=False,
            detail=f"error: {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        ))

    # Check 2: anti-repeat blocking
    t0 = time.time()
    try:
        from s2.coordinator import S2Coordinator
        from s2.types import RetryHistory
        from classifier.classifier import FailureClassifier

        classifier = FailureClassifier(taxonomy_path)
        s2 = S2Coordinator(get_anti_repeat_limit=classifier.get_anti_repeat_limit)
        history = RetryHistory(task_id="s2-verify-anti-repeat")
        auth = s2.authorize_retry(
            failure_class="ImportError",
            policy_applied="InstallDependency",
            policy_attempt=99,  # exceeds any limit
            history=history,
        )
        blocked = auth.blocked_by == "anti_repeat"
        checks.append(CheckResult(
            name="anti_repeat_blocking",
            passed=blocked,
            detail=f"blocked_by={auth.blocked_by}",
            duration_ms=(time.time() - t0) * 1000,
        ))
        evidence["anti_repeat_blocked"] = blocked
    except Exception as exc:
        checks.append(CheckResult(
            name="anti_repeat_blocking",
            passed=False,
            detail=f"error: {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        ))

    # Check 3: resource overlap detection
    t0 = time.time()
    try:
        from s2.conflict import ConflictDetector
        from s2.types import ResourceClaim

        detector = ConflictDetector()
        claim_a = ResourceClaim(task_id="task-a", workspace="/tmp/ws1", git_ref="main")
        claim_b = ResourceClaim(task_id="task-b", workspace="/tmp/ws1", git_ref="main")
        overlap = detector.detect_resource_overlap(claim_a, claim_b)
        no_overlap = not detector.detect_resource_overlap(
            ResourceClaim(task_id="task-a", workspace="/tmp/ws1"),
            ResourceClaim(task_id="task-b", workspace="/tmp/ws2"),
        )
        checks.append(CheckResult(
            name="resource_overlap_detection",
            passed=overlap and no_overlap,
            detail=f"overlap_detected={overlap}, distinct_ok={no_overlap}",
            duration_ms=(time.time() - t0) * 1000,
        ))
        evidence["resource_overlap"] = overlap and no_overlap
    except Exception as exc:
        checks.append(CheckResult(
            name="resource_overlap_detection",
            passed=False,
            detail=f"error: {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        ))

    return SystemStatus(
        name="S2",
        passed=all(c.passed for c in checks),
        checks=checks,
        evidence=evidence,
    )


def _verify_s3(taxonomy_path: str) -> SystemStatus:
    """Verify S3: classifier classify, policy selection, recovery executors."""
    checks = []
    evidence = {}

    # Check 1: classifier loads taxonomy
    t0 = time.time()
    try:
        from classifier.classifier import FailureClassifier
        classifier = FailureClassifier(taxonomy_path)
        class_count = len(classifier.classes)
        checks.append(CheckResult(
            name="taxonomy_loaded",
            passed=class_count > 0,
            detail=f"{class_count} classes loaded",
            duration_ms=(time.time() - t0) * 1000,
        ))
        evidence["class_count"] = class_count
    except Exception as exc:
        checks.append(CheckResult(
            name="taxonomy_loaded",
            passed=False,
            detail=f"error: {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        ))

    # Check 2: classify ImportError
    t0 = time.time()
    try:
        from classifier.classifier import FailureClassifier
        classifier = FailureClassifier(taxonomy_path)
        obs = [{"kind": "error_string", "value": "ModuleNotFoundError: No module named 'pytest'", "source": "stderr", "at_action": 1}]
        result = classifier.classify(obs)
        checks.append(CheckResult(
            name="classify_import_error",
            passed=result.failure_class == "ImportError",
            detail=f"class={result.failure_class}, policy={result.recovery_policy}, confidence={result.confidence}",
            duration_ms=(time.time() - t0) * 1000,
        ))
        evidence["classify_import"] = {
            "class": result.failure_class,
            "policy": result.recovery_policy,
        }
    except Exception as exc:
        checks.append(CheckResult(
            name="classify_import_error",
            passed=False,
            detail=f"error: {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        ))

    # Check 3: recovery executor (dry_run)
    t0 = time.time()
    try:
        from recovery_policies.base import RecoveryContext, run_executor
        ctx = RecoveryContext(
            policy_id="InstallDependency",
            failure_class="ImportError",
            workspace=Path(tempfile.mkdtemp()),
            failure_observations=[],
            policy_attempt=0,
            extra={"dry_run": True},
        )
        result = run_executor(ctx)
        checks.append(CheckResult(
            name="recovery_executor_dry_run",
            passed=result.applied,
            detail=f"applied={result.applied}, env_changes={result.env_changes}",
            duration_ms=(time.time() - t0) * 1000,
        ))
        evidence["recovery_dry_run"] = result.applied
    except Exception as exc:
        checks.append(CheckResult(
            name="recovery_executor_dry_run",
            passed=False,
            detail=f"error: {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        ))

    return SystemStatus(
        name="S3",
        passed=all(c.passed for c in checks),
        checks=checks,
        evidence=evidence,
    )


def _verify_s3_star(s1_provider: str, s3star_provider: str, taxonomy_path: str) -> SystemStatus:
    """Verify S3*: auditor audit_classification, cross-provider constraint."""
    checks = []
    evidence = {}

    # Check 1: cross-provider constraint validation
    t0 = time.time()
    try:
        from audit.config import AuditConfig
        config = AuditConfig(s1_provider=s1_provider, s3star_provider=s3star_provider)
        error = config.validate_provider_constraint()
        checks.append(CheckResult(
            name="cross_provider_constraint",
            passed=error is None,
            detail=f"s1={s1_provider}, s3*={s3star_provider}, error={error}",
            duration_ms=(time.time() - t0) * 1000,
        ))
        evidence["providers"] = {"s1": s1_provider, "s3star": s3star_provider, "ok": error is None}
    except Exception as exc:
        checks.append(CheckResult(
            name="cross_provider_constraint",
            passed=False,
            detail=f"error: {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        ))

    # Check 2: audit_classification runs
    t0 = time.time()
    try:
        from audit.auditor import S3StarAuditor
        from audit.config import AuditConfig
        config = AuditConfig(s1_provider=s1_provider, s3star_provider=s3star_provider)
        auditor = S3StarAuditor(config)
        classification = {
            "failure_class": "ImportError",
            "recovery_policy": "InstallDependency",
            "confidence": "high",
            "evidence": [{"signal": "No module named", "observation_value": "...", "observation_kind": "error_string", "at_action": 1}],
            "ambiguous": False,
            "alternative_classes": [],
            "reason": "test",
        }
        observations = [{"kind": "error_string", "value": "ModuleNotFoundError: No module named 'pytest'", "at_action": 1}]
        result = auditor.audit_classification(classification, observations)
        checks.append(CheckResult(
            name="audit_classification",
            passed=True,  # audit runs without crash
            detail=f"findings={len(result.findings)}, passed={result.passed}, algedonic={result.algedonic}",
            duration_ms=(time.time() - t0) * 1000,
        ))
        evidence["audit"] = {
            "findings": len(result.findings),
            "passed": result.passed,
        }
    except Exception as exc:
        checks.append(CheckResult(
            name="audit_classification",
            passed=False,
            detail=f"error: {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        ))

    return SystemStatus(
        name="S3_star",
        passed=all(c.passed for c in checks),
        checks=checks,
        evidence=evidence,
    )


def _verify_orchestrator(workspace: Path, taxonomy_path: str, cfg: VerifyConfig) -> SystemStatus:
    """Verify orchestrator: run_recovery_cycle end-to-end (dry_run recovery)."""
    checks = []
    evidence = {}

    # Patch run_executor for dry_run BEFORE the cycle runs. The orchestrator
    # imports run_executor inside the loop (from recovery_policies.base import
    # run_executor), so the patched attribute is picked up on each iteration.
    import recovery_policies.base as base
    original_run_executor = base.run_executor

    def dry_run_wrapper(ctx):
        ctx.extra["dry_run"] = True
        return original_run_executor(ctx)

    base.run_executor = dry_run_wrapper

    t0 = time.time()
    try:
        from orchestrator import run_recovery_cycle, OrchestratorConfig
        from runtime.dispatcher import S1Dispatcher
        from runtime.types import S1Input, Budget
        from classifier.classifier import FailureClassifier
        from audit.auditor import S3StarAuditor
        from audit.config import AuditConfig
        from s2.coordinator import S2Coordinator

        classifier = FailureClassifier(taxonomy_path)
        auditor = S3StarAuditor(AuditConfig(
            s1_provider=cfg.s1_provider,
            s3star_provider=cfg.s3star_provider,
        ))
        s2 = S2Coordinator(get_anti_repeat_limit=classifier.get_anti_repeat_limit)
        dispatcher = S1Dispatcher(solver_mode="mono")

        input = S1Input(
            task_prompt="verify: orchestrator cycle",
            workspace=workspace,
            budget=Budget(time_seconds=120, tokens=50000, actions=30),
        )
        result = run_recovery_cycle(
            input=input,
            dispatcher=dispatcher,
            classifier=classifier,
            auditor=auditor,
            s2=s2,
            config=OrchestratorConfig(
                max_retries=2,
                taxonomy_path=taxonomy_path,
                s1_provider=cfg.s1_provider,
                s3star_provider=cfg.s3star_provider,
            ),
        )

        checks.append(CheckResult(
            name="recovery_cycle_runs",
            passed=result.total_attempts > 0,
            detail=f"attempts={result.total_attempts}, terminated_by={result.terminated_by}",
            duration_ms=(time.time() - t0) * 1000,
        ))
        evidence["orchestrator"] = {
            "attempts": result.total_attempts,
            "terminated_by": result.terminated_by,
        }
    except Exception as exc:
        checks.append(CheckResult(
            name="recovery_cycle_runs",
            passed=False,
            detail=f"error: {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        ))
    finally:
        # Always restore — never leak the dry_run patch into other callers.
        try:
            base.run_executor = original_run_executor
        except Exception:
            pass

    return SystemStatus(
        name="orchestrator",
        passed=all(c.passed for c in checks),
        checks=checks,
        evidence=evidence,
    )


def _verify_s4_scout() -> SystemStatus:
    """Verify S4 scout agent (VSM-016): on-demand intelligence.

    Checks the S4 tool surface (browser + intel_write/read + taxonomy) and the
    scan_on_demand protocol entry, WITHOUT launching goose (keeps verify offline).
    """
    checks = []
    evidence = {}
    import tempfile
    from pathlib import Path

    # Check 1: S4 tool surface registers correctly
    t0 = time.time()
    try:
        from agent_runtime.mcp_server import create_server
        with tempfile.TemporaryDirectory() as ws:
            Path(ws, "state").mkdir()
            server = create_server(ws, None,
                ["browser", "intel_write", "intel_read", "taxonomy_read", "fs"])
            tool_names = [t["name"] for t in server.list_tools()]
            required = ["browser.fetch", "browser.search", "intel_write", "intel_read"]
            missing = [t for t in required if t not in tool_names]
            checks.append(CheckResult(
                name="s4_tool_surface",
                passed=not missing,
                detail=f"{len(required)} tools; missing={missing or 'none'}",
                duration_ms=(time.time() - t0) * 1000,
            ))
            evidence["tool_count"] = len(tool_names)
    except Exception as exc:
        checks.append(CheckResult(
            name="s4_tool_surface", passed=False,
            detail=f"error: {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        ))

    # Check 2: intel_write/read round-trip
    t0 = time.time()
    try:
        from agent_runtime.mcp_server import create_server
        with tempfile.TemporaryDirectory() as ws:
            Path(ws, "state").mkdir()
            server = create_server(ws, None, ["intel_write", "intel_read"])
            w = server.handlers["intel_write"](signals=[
                {"type": "gap", "severity": "warn", "summary": "test signal"}])
            r = server.handlers["intel_read"]()
            assert w["exit_code"] == 0 and r["total"] == 1
            checks.append(CheckResult(
                name="intel_write_read",
                passed=True,
                detail=f"write={w['written']}, read total={r['total']}",
                duration_ms=(time.time() - t0) * 1000,
            ))
            evidence["intel"] = "OK"
    except Exception as exc:
        checks.append(CheckResult(
            name="intel_write_read", passed=False,
            detail=f"error: {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        ))

    # Check 3: scan_on_demand protocol entry + S4 role config
    t0 = time.time()
    try:
        from agent_runtime.protocol import AgentProtocol, ProtocolConfig, ROLE_CONFIGS
        assert "s4-scout" in ROLE_CONFIGS
        s4_tools = ROLE_CONFIGS["s4-scout"]["tools"]
        assert "browser" in s4_tools and "intel_write" in s4_tools
        proto = AgentProtocol(ProtocolConfig())
        assert hasattr(proto, "scan_on_demand")
        checks.append(CheckResult(
            name="scan_on_demand_protocol",
            passed=True,
            detail=f"S4 tools={s4_tools}, scan_on_demand present",
            duration_ms=(time.time() - t0) * 1000,
        ))
        evidence["s4_tools"] = s4_tools
    except Exception as exc:
        checks.append(CheckResult(
            name="scan_on_demand_protocol", passed=False,
            detail=f"error: {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        ))

    return SystemStatus(
        name="s4_scout",
        passed=all(c.passed for c in checks),
        checks=checks,
        evidence=evidence,
    )


# ── CLI entry point ──

def _main():
    """CLI: python3 -m runtime.verify [--report] [--json]"""
    import argparse
    parser = argparse.ArgumentParser(description="S1 self-verification")
    parser.add_argument("--report", action="store_true", help="run full capability report")
    parser.add_argument("--json", action="store_true", help="output as JSON")
    parser.add_argument("--workspace", default="", help="workspace path (default: temp)")
    args = parser.parse_args()

    if args.report:
        config = VerifyConfig(workspace=args.workspace)
        report = capability_report(config)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            print(f"═══ S1 Capability Report ({report.generated_at}) ═══")
            print(f"Overall: {report.overall}")
            print(f"Passed: {report.passed_systems}")
            if report.failed_systems:
                print(f"Failed: {report.failed_systems}")
            print()
            for name, status in report.systems.items():
                print(status.detail)
                print()
        sys.exit(0 if report.all_passed else 1)
    else:
        print("Use --report for full capability report")
        sys.exit(0)


if __name__ == "__main__":
    _main()

"""test_orchestrator — smoke tests for recovery cycle (VSM-007).

Deterministic tests using FakeDispatcher + dry_run recovery.
No Goose, no real API calls, no real pip install.

Run:
    cd ../src && python3 tests/test_orchestrator.py
    # or, if pytest is installed:
    cd ../src && python3 -m pytest tests/test_orchestrator.py -v

Test matrix:
    A — ImportError → classify → InstallDependency → recovery (dry_run) → retry → resolved
    B — unknown failure → Unknown → no retry (EscalateToS3 has no executor → recovery_blocked)
    C — anti-repeat exceeded (same policy >limit) → blocked
    D — oscillation A→B→A→B → blocked (or output_contradiction — also valid)
    E — multi-agent (planner+executor+verifier) via session sync → resolved
    F — resource overlap detection (direct ConflictDetector test)
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Add src/ to path so `runtime.types`, `orchestrator`, etc. resolve whether
# the file is invoked as `python3 tests/test_orchestrator.py` or via pytest.
_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from runtime.types import (
    S1Input, S1Output, Verdict, Budget, RecoveryDirective, FailureObservation,
)
from classifier.classifier import FailureClassifier
from audit.auditor import S3StarAuditor
from audit.config import AuditConfig
from s2.coordinator import S2Coordinator
from s2.conflict import ConflictDetector
from s2.types import RetryHistory, AttemptRecord, ResourceClaim
from orchestrator import run_recovery_cycle, OrchestratorConfig

# Path to taxonomy (relative to src/).
_TAXONOMY = str(_SRC / "failure_taxonomy.yaml")


# ───────────────────────── FakeDispatcher ─────────────────────────

class FakeDispatcher:
    """Stub dispatcher for deterministic orchestrator tests.

    Returns pre-configured S1Output per attempt, in order. Once the
    pre-configured list is exhausted, returns TASK_FAILED (safe fallback so
    the orchestrator's max-retries bound terminates the cycle deterministically
    even if a test under-provisions outputs).
    """

    def __init__(self, outputs: list[S1Output]):
        self._outputs = outputs
        self._idx = 0

    def invoke(self, input: S1Input) -> S1Output:
        if self._idx >= len(self._outputs):
            return S1Output(verdict=Verdict.TASK_FAILED)
        out = self._outputs[self._idx]
        self._idx += 1
        return out


# ───────────────────────── helpers ─────────────────────────

def _make_obs(kind: str = "error_string", value: str = "", **kw) -> FailureObservation:
    return FailureObservation(kind=kind, value=value, **kw)


def _make_output(verdict: Verdict, observations: list[FailureObservation] | None = None) -> S1Output:
    return S1Output(
        verdict=verdict,
        failure_observations=observations or [],
        # Keep cost tiny so budget exhaustion never interferes with the test.
        cost={"time_used": 1.0, "tokens_used": 5, "actions_taken": 1},
    )


def _make_input() -> S1Input:
    return S1Input(
        task_prompt="test task",
        workspace=Path(tempfile.mkdtemp()),
        budget=Budget(time_seconds=300, tokens=100000, actions=500),
    )


def _make_orchestrator_config() -> OrchestratorConfig:
    # Use distinct providers so the S3* cross-provider invariant holds.
    return OrchestratorConfig(
        max_retries=5,
        taxonomy_path=_TAXONOMY,
        s1_provider="zai",
        s3star_provider="anthropic",
    )


def _setup_components():
    """Create real classifier, auditor, s2 coordinator (no mocking)."""
    classifier = FailureClassifier(_TAXONOMY)
    auditor = S3StarAuditor(AuditConfig(s1_provider="zai", s3star_provider="anthropic"))
    s2 = S2Coordinator(
        get_anti_repeat_limit=classifier.get_anti_repeat_limit,
    )
    return classifier, auditor, s2


# ── dry_run patching ──────────────────────────────────────────────
#
# The orchestrator imports run_executor via a LOCAL `from recovery_policies.base
# import RecoveryContext, run_executor` inside the loop body. That local import
# re-binds `run_executor` from the `recovery_policies.base` module on every
# call, so patching `recovery_policies.base.run_executor` is sufficient — the
# orchestrator picks up the patched version automatically. (There is no
# module-level `orchestrator.run_executor` attribute to patch.)
#
# The wrapper sets ctx.extra["dry_run"]=True before delegating to the real
# (now dry-run-aware) implementation. The real implementation then returns a
# mock RecoveryResult without any side effects (no real pip install / git reset).

def _patch_dry_run():
    """Install a dry_run wrapper on recovery_policies.base.run_executor.

    Returns a callable that restores the original.
    """
    import recovery_policies.base as base

    original = base.run_executor

    def dry_run_wrapper(ctx):
        ctx.extra["dry_run"] = True
        return original(ctx)

    base.run_executor = dry_run_wrapper

    def restore():
        base.run_executor = original

    return restore


# ───────────────────────── Test A ─────────────────────────

def test_a_importerror_to_resolved():
    """A: ImportError → classify → InstallDependency → recovery (dry_run)
    → retry → resolved.

    Attempt 0: ImportError failure → classify → InstallDependency
    Attempt 1: task_resolved (after dry-run recovery)
    """
    restore = _patch_dry_run()
    try:
        classifier, auditor, s2 = _setup_components()
        outputs = [
            _make_output(
                Verdict.TASK_FAILED,
                observations=[
                    _make_obs(value="ModuleNotFoundError: No module named 'pytest'"),
                ],
            ),
            _make_output(Verdict.TASK_RESOLVED),
        ]
        dispatcher = FakeDispatcher(outputs)
        result = run_recovery_cycle(
            _make_input(), dispatcher, classifier, auditor, s2,
            _make_orchestrator_config(),
        )

        assert result.terminated_by == "task_resolved", \
            f"expected task_resolved, got {result.terminated_by!r}"
        assert result.total_attempts == 2, \
            f"expected 2 attempts, got {result.total_attempts}"
        assert result.classifications[0]["failure_class"] == "ImportError", \
            f"class[0]={result.classifications[0]['failure_class']!r}"
        assert result.classifications[0]["recovery_policy"] == "InstallDependency", \
            f"policy[0]={result.classifications[0]['recovery_policy']!r}"
        assert result.recovery_results[0]["applied"] is True, \
            f"recovery[0] not applied: {result.recovery_results[0]}"
        assert result.recovery_results[0]["blocked"] is None, \
            f"recovery[0] blocked: {result.recovery_results[0]}"
        # dry_run env_change marker present
        assert any("dry_run" in c for c in result.recovery_results[0]["env_changes"]), \
            f"no dry_run marker: {result.recovery_results[0]['env_changes']}"
    finally:
        restore()


# ───────────────────────── Test B ─────────────────────────

def test_b_unknown_to_recovery_blocked():
    """B: unknown failure → Unknown → EscalateToS3 has no executor → blocked.

    EscalateToS3 is deliberately absent from the executor registry (it's an
    escalation, not a real recovery). So run_executor returns
    blocked="unknown_policy: EscalateToS3" → recovery_blocked.

    NOTE: dry_run is NOT patched here — we want the real executor lookup to
    fail for EscalateToS3. No subprocess is spawned (the executor lookup
    short-circuits before any pip install / git reset).
    """
    classifier, auditor, s2 = _setup_components()
    outputs = [
        _make_output(
            Verdict.TASK_FAILED,
            observations=[
                # An error string that matches no taxonomy signal → Unknown.
                _make_obs(value="qzxvbn_mystery_fault:: unrecoverable gibberish"),
            ],
        ),
    ]
    dispatcher = FakeDispatcher(outputs)
    result = run_recovery_cycle(
        _make_input(), dispatcher, classifier, auditor, s2,
        _make_orchestrator_config(),
    )

    assert result.classifications[0]["failure_class"] == "Unknown", \
        f"expected Unknown, got {result.classifications[0]['failure_class']!r}"
    assert result.classifications[0]["recovery_policy"] == "EscalateToS3", \
        f"expected EscalateToS3, got {result.classifications[0]['recovery_policy']!r}"
    assert "recovery_blocked" in result.terminated_by, \
        f"expected recovery_blocked, got {result.terminated_by!r}"
    # The recovery result should be blocked on unknown_policy (no executor).
    assert result.recovery_results[0]["applied"] is False, \
        f"recovery should not apply for EscalateToS3: {result.recovery_results[0]}"
    assert result.recovery_results[0]["blocked"] is not None, \
        f"recovery should be blocked: {result.recovery_results[0]}"
    assert "EscalateToS3" in result.recovery_results[0]["blocked"], \
        f"blocked reason should mention EscalateToS3: {result.recovery_results[0]['blocked']}"


# ───────────────────────── Test C ─────────────────────────

def test_c_anti_repeat_exceeded():
    """C: same ImportError → InstallDependency repeated → anti-repeat blocks.

    InstallDependency anti-repeat limit = 1 (DEFAULT_POLICY_LIMITS and
    taxonomy s2_anti_repeat ">1 раз"). The orchestrator tracks
    policy_attempt per (failure_class, policy). So:
      attempt 0: policy_attempt=0 (< limit) → dry_run applied → retry authorized
      attempt 1: policy_attempt=1 (>= limit) → recovery blocked by anti-repeat
                  (the anti-repeat check inside run_executor fires first)

    terminated_by contains "anti_repeat".
    """
    restore = _patch_dry_run()
    try:
        classifier, auditor, s2 = _setup_components()
        outputs = [
            _make_output(
                Verdict.TASK_FAILED,
                observations=[
                    _make_obs(value="ImportError: No module named 'requests'"),
                ],
            )
            for _ in range(4)
        ]
        dispatcher = FakeDispatcher(outputs)
        result = run_recovery_cycle(
            _make_input(), dispatcher, classifier, auditor, s2,
            _make_orchestrator_config(),
        )

        # Either run_executor's anti-repeat check (recovery_blocked:anti_repeat)
        # or S2's anti-repeat (not_authorized:anti_repeat) can fire. Both are
        # valid signals that anti-repeat is enforced.
        assert "anti_repeat" in result.terminated_by, \
            f"expected anti_repeat somewhere, got {result.terminated_by!r}"
        # The cycle must not have resolved (no real recovery happened).
        assert result.terminated_by != "task_resolved", \
            "anti-repeat should prevent resolution"
        # Confirm the failure was classified as ImportError at least once.
        assert any(
            c["failure_class"] == "ImportError" for c in result.classifications
        ), f"no ImportError classification: {result.classifications}"
    finally:
        restore()


# ───────────────────────── Test D ─────────────────────────

def test_d_oscillation_blocked():
    """D: oscillation SyntaxError → TestFailure → SyntaxError → TestFailure
    → blocked.

    Uses two classes whose anti-repeat limits are both 2 (FixSyntax and
    DiagnoseAndPatch), so the cycle can survive long enough to reach an
    oscillation-class block. (With a limit-1 class like InstallDependency,
    the second occurrence would be blocked by anti-repeat before any S2
    flip-flop guard could fire.)

    S2's conflict pipeline has TWO guards that can fire on this pattern:
      1. output_contradiction (fires earlier, at attempt_count>=2, when two
         consecutive attempts differ in class/policy/verdict)
      2. oscillation (fires at attempt_count>=4, A→B→A→B flip-flop)

    Either is a valid reason to block the cycle. So this test accepts BOTH.
    To assert oscillation detection specifically (independent of the
    orchestrator's earlier output_contradiction guard), we also call
    S2Coordinator._detect_oscillation directly on a clean 4-attempt flip-flop.
    """
    restore = _patch_dry_run()
    try:
        classifier, auditor, s2 = _setup_components()
        outputs = [
            _make_output(
                Verdict.TASK_FAILED,
                observations=[_make_obs(value="SyntaxError: invalid syntax")],
            ),
            _make_output(
                Verdict.TASK_FAILED,
                observations=[_make_obs(value="AssertionError: expected 5 but got 3")],
            ),
            _make_output(
                Verdict.TASK_FAILED,
                observations=[_make_obs(value="SyntaxError: invalid syntax")],
            ),
            _make_output(
                Verdict.TASK_FAILED,
                observations=[_make_obs(value="AssertionError: expected 5 but got 3")],
            ),
            _make_output(
                Verdict.TASK_FAILED,
                observations=[_make_obs(value="SyntaxError: invalid syntax")],
            ),
        ]
        dispatcher = FakeDispatcher(outputs)
        result = run_recovery_cycle(
            _make_input(), dispatcher, classifier, auditor, s2,
            _make_orchestrator_config(),
        )

        # Accept output_contradiction OR oscillation — both are valid S2 blocks
        # for the flip-flop pattern. anti_repeat alone would indicate the test
        # chose too-low-limit classes (a test bug, not an orchestrator signal).
        assert (
            "output_contradiction" in result.terminated_by
            or "oscillation" in result.terminated_by
        ), f"expected output_contradiction or oscillation, got {result.terminated_by!r}"
    finally:
        restore()

    # Direct oscillation-detection check: S2 must flag A→B→A→B in history.
    # This pins the oscillation guard itself, independent of which S2 guard
    # fires first inside the orchestrator.
    _classifier, _auditor, s2_direct = _setup_components()
    history = RetryHistory(task_id="osc-direct")
    for cls, verdict in [
        ("SyntaxError", "task_failed"),
        ("TestFailure", "task_failed"),
        ("SyntaxError", "task_failed"),
        ("TestFailure", "task_failed"),
    ]:
        history.add(AttemptRecord(
            attempt_num=len(history.attempts),
            failure_class=cls,
            policy_applied="dry",
            verdict=verdict,
        ))
    osc_reason = s2_direct._detect_oscillation(history)
    assert osc_reason is not None and "oscillation" in osc_reason.lower(), \
        f"_detect_oscillation should flag A→B→A→B, got {osc_reason!r}"


# ───────────────────────── Test E ─────────────────────────

def test_e_multiagent_resolved():
    """E: multi-agent (planner + executor + verifier) via session sync → resolved.

    Uses the REAL S1Dispatcher(solver_mode="multi") with the in-process MCP
    server and the rule-based planner/verifier stubs. A simple file is placed
    in the workspace so fs.list / shell.exec have something to operate on.
    dry_run is patched so any recovery attempt (none expected here, but
    defensively) doesn't shell out.

    The verifier stub passes when no error keywords appear in the observation,
    so the expected verdict is task_resolved. The only hard assertion is that
    the dispatcher runs without crashing and produces a verdict.
    """
    from runtime.dispatcher import S1Dispatcher

    restore = _patch_dry_run()
    try:
        classifier, auditor, s2 = _setup_components()
        ws = Path(tempfile.mkdtemp())
        (ws / "hello.py").write_text('print("hello")\n')

        dispatcher = S1Dispatcher(solver_mode="multi")
        inp = S1Input(
            task_prompt="run the test suite for hello.py",
            workspace=ws,
            budget=Budget(time_seconds=120, tokens=5000, actions=50),
        )
        result = run_recovery_cycle(
            inp, dispatcher, classifier, auditor, s2,
            _make_orchestrator_config(),
        )

        # The cycle must terminate cleanly (not crash) and ideally resolve.
        # task_resolved is the happy path; budget_exhausted / max_retries are
        # acceptable non-crash outcomes in a constrained sandbox.
        assert result.terminated_by in (
            "task_resolved", "budget_exhausted", "max_retries",
        ), f"unexpected termination: {result.terminated_by!r}"
        assert result.total_attempts >= 1, "must have run at least one attempt"
    finally:
        restore()


# ───────────────────────── Test F ─────────────────────────

def test_f_resource_overlap_detection():
    """F: two ResourceClaim with the same workspace → overlap detected.

    Direct test of ConflictDetector.detect_resource_overlap (not via the
    orchestrator). Covers the multi-agent isolation primitive: two tasks
    competing for the same workspace/git_ref/port must be flagged so S2
    queues rather than runs them in parallel.
    """
    detector = ConflictDetector()

    # Same workspace, different task_ids → overlap.
    claim_a = ResourceClaim(task_id="task-A", workspace="/workspace/shared")
    claim_b = ResourceClaim(task_id="task-B", workspace="/workspace/shared")
    assert detector.detect_resource_overlap(claim_a, claim_b) is True, \
        "same workspace must overlap"

    # Different workspaces, different tasks → no overlap.
    claim_c = ResourceClaim(task_id="task-C", workspace="/workspace/c")
    claim_d = ResourceClaim(task_id="task-D", workspace="/workspace/d")
    assert detector.detect_resource_overlap(claim_c, claim_d) is False, \
        "disjoint workspaces must not overlap"

    # Same task_id (same task holding its own resource) → not a conflict.
    claim_e1 = ResourceClaim(task_id="task-E", workspace="/workspace/e")
    claim_e2 = ResourceClaim(task_id="task-E", workspace="/workspace/e")
    assert detector.detect_resource_overlap(claim_e1, claim_e2) is False, \
        "same task_id must not overlap with itself"

    # Overlapping git_ref → overlap.
    claim_g1 = ResourceClaim(task_id="task-G1", workspace="/w1", git_ref="refs/heads/main")
    claim_g2 = ResourceClaim(task_id="task-G2", workspace="/w2", git_ref="refs/heads/main")
    assert detector.detect_resource_overlap(claim_g1, claim_g2) is True, \
        "same git_ref must overlap"

    # Shared port → overlap.
    claim_p1 = ResourceClaim(task_id="task-P1", workspace="/w1", ports=[8080, 9000])
    claim_p2 = ResourceClaim(task_id="task-P2", workspace="/w2", ports=[9000, 7000])
    assert detector.detect_resource_overlap(claim_p1, claim_p2) is True, \
        "shared port must overlap"

    # Disjoint ports → no overlap.
    claim_p3 = ResourceClaim(task_id="task-P3", workspace="/w3", ports=[8080])
    claim_p4 = ResourceClaim(task_id="task-P4", workspace="/w4", ports=[9000])
    assert detector.detect_resource_overlap(claim_p3, claim_p4) is False, \
        "disjoint ports must not overlap"


# ───────────────────────── runner ─────────────────────────

_TESTS = [
    ("A: ImportError → InstallDependency → resolved", test_a_importerror_to_resolved),
    ("B: Unknown → EscalateToS3 → recovery_blocked", test_b_unknown_to_recovery_blocked),
    ("C: anti-repeat exceeded → blocked", test_c_anti_repeat_exceeded),
    ("D: oscillation A→B→A→B → blocked", test_d_oscillation_blocked),
    ("E: multi-agent (planner+executor+verifier) → resolved", test_e_multiagent_resolved),
    ("F: resource overlap detection", test_f_resource_overlap_detection),
]


def _run_all() -> int:
    passed = 0
    failed = 0
    for name, fn in _TESTS:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as exc:
            print(f"  FAIL  {name}\n        AssertionError: {exc}")
            failed += 1
        except Exception as exc:
            print(f"  ERROR {name}\n        {type(exc).__name__}: {exc}")
            failed += 1
    print(f"\n{passed}/{passed + failed} passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())

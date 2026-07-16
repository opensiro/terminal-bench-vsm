"""triad_solver — S1 triad: solve → control-by-tests → verify (VSM-020).

Evolution of MultiAgentSolver (VSM-007). Adds a CONTROL phase between
execute and verify: run tests, and on failure revert to the last checkpoint
(CONTRACT §5.1, VSM-019) and re-solve — a bounded "solve → test → revert"
loop *inside one invocation* (operational axis, not memory axis).

State machine:
    SOLVING → CONTROLLING → { REVERT→SOLVING | VERIFYING } → DONE

  - SOLVING:    planner emits a plan; executor emits tool calls per plan step.
               A checkpoint is captured before SOLVING starts (and re-captured
               on each re-solve after a revert).
  - CONTROLLING: the test-controller sub-agent evaluates the last test run.
               PASS → VERIFYING. FAIL + reverts left → revert + SOLVING.
               FAIL + no reverts left → VERIFYING (final verify decides).
  - VERIFYING: the verifier sub-agent checks the full trace → __done__.

Sub-agent seams (callable injection points; rule-based stubs by default in
WS2, GooseRunner-backed in WS3):
  planner_fn:          (task_prompt, tools, directive) -> list[dict] plan
  test_controller_fn:  (plan, trace, checkpoint, revert_count, max_reverts) -> ControlResult
  verifier_fn:         (plan, trace, artifacts) -> VerifyResult

Stateless (CONTRACT §5): instance is fresh per AgentLoop.run(); checkpoint
state is in-invocation only and discarded on return.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from .types import (
    ControlResult, ControlVerdict, TraceEntry, VerifyResult,
)
from .checkpoint import Checkpoint, CheckpointManager


class _TriadPhase(str, Enum):
    SOLVING = "solving"
    CONTROLLING = "controlling"
    VERIFYING = "verify"
    DONE = "done"


@dataclass
class TriadSolver:
    """S1 triad solver: solve → control-by-tests → verify, with in-invocation
    checkpoint/revert (VSM-020). Implements SolverProtocol (structurally),
    driven by AgentLoop.

    Args:
        session_store: SessionStore for shared state (optional; for external
            observers / future sub-agent coordination). If None, created lazily.
        task_id: unique task identifier for the session.
        workspace: task-scoped workspace path (for CheckpointManager).
        checkpoint_mgr: CheckpointManager (created lazily from workspace if None).
        planner_fn: callable returning a plan (list of step dicts). Default:
            _default_planner (rule-based).
        test_controller_fn: callable returning a ControlResult. Default:
            _default_test_controller (rule-based).
        verifier_fn: callable returning a VerifyResult. Default:
            _default_verifier (rule-based).
        max_reverts: anti-oscillation cap on revert→re-solve cycles (CONTRACT §5.1).
    """

    session_store: Any = None
    task_id: str = "default-task"
    workspace: Path = Path(".")
    checkpoint_mgr: CheckpointManager | None = None
    planner_fn: Callable[..., list[dict]] | None = None
    test_controller_fn: Callable[..., ControlResult] | None = None
    verifier_fn: Callable[..., VerifyResult] | None = None
    max_reverts: int = 2

    # ── internal state (per-instance, fresh per AgentLoop.run — CONTRACT §5) ──
    _phase: _TriadPhase = field(default=_TriadPhase.SOLVING, init=False)
    _plan: list[dict] = field(default_factory=list, init=False)
    _step_idx: int = field(default=0, init=False)
    _skips: int = field(default=0, init=False)
    _executed: list[int] = field(default_factory=list, init=False)
    _checkpoint: Checkpoint | None = field(default=None, init=False)
    _revert_count: int = field(default=0, init=False)
    _control_results: list[ControlResult] = field(default_factory=list, init=False)
    # Trace cursor: control only inspects trace entries produced since the last
    # SOLVING start (so a revert + re-solve doesn't re-read the stale failed run).
    _trace_cursor: int = field(default=0, init=False)
    _session_created: bool = field(default=False, init=False)

    # ── SolverProtocol ──

    def decide_next_action(
        self,
        task_prompt: str,
        trace: list[TraceEntry],
        available_tools: list[str],
        recovery_directive: dict | None,
        budget_remaining: dict[str, float],
    ) -> dict[str, Any]:
        """State machine: SOLVING → CONTROLLING → {REVERT→SOLVING | VERIFYING} → DONE."""
        if not self._session_created:
            self._init_session()

        # ── SOLVING ──
        if self._phase == _TriadPhase.SOLVING:
            # On (re-)entering SOLVING: capture a checkpoint (CONTRACT §5.1) and
            # (re-)build the plan if we don't have one yet. Reset the trace cursor
            # so the control phase only inspects trace entries from this solve
            # pass (a reverted failure must not be re-read on the next pass).
            if not self._plan:
                self._trace_cursor = len(trace)
            if self._checkpoint is None:
                self._capture_checkpoint("pre-solve")

            if not self._plan:
                planner = self.planner_fn or _default_planner
                self._plan = planner(task_prompt, available_tools, recovery_directive)
                self._safe_update("plan", self._plan)
                self._step_idx = 0
                if not self._plan:
                    self._phase = _TriadPhase.DONE
                    self._close_session()
                    return {
                        "tool": "__done__", "verdict": "task_failed",
                        "thought": "triad: planner produced empty plan",
                    }

            # Emit the next plan step as a tool call.
            # step_idx is relative to the current SOLVING pass: how many steps
            # of THIS plan have already been emitted = (trace growth since the
            # pass started) + skips. This keeps the cursor correct after a
            # revert resets the plan but the trace retains prior entries.
            steps_emitted = (len(trace) - self._trace_cursor) + self._skips
            self._step_idx = steps_emitted
            if self._step_idx < len(self._plan):
                return self._emit_plan_step(available_tools)

            # Plan exhausted → run the control gate.
            self._phase = _TriadPhase.CONTROLLING

        # ── CONTROLLING ──
        if self._phase == _TriadPhase.CONTROLLING:
            return self._run_control(trace)

        # ── VERIFYING ──
        if self._phase == _TriadPhase.VERIFYING:
            return self._run_verify(trace)

        # ── DONE (shouldn't reach) ──
        return {"tool": "__done__", "verdict": "unknown",
                "thought": "triad: reached DONE unexpectedly"}

    # ── phase helpers ──

    def _emit_plan_step(self, available_tools: list[str]) -> dict[str, Any]:
        """Emit the current plan step as a tool call; skip if tool unavailable."""
        step = self._plan[self._step_idx]
        tool = step.get("tool", "")
        args = step.get("args", {})

        if tool not in available_tools:
            self._skips += 1
            return {
                "tool": "__skip__", "args": {},
                "thought": f"triad: step {self._step_idx} tool '{tool}' unavailable, skipping",
            }

        self._executed.append(self._step_idx)
        return {
            "tool": tool, "args": args,
            "thought": f"triad executor: step {self._step_idx + 1}/{len(self._plan)}",
        }

    def _run_control(self, trace: list[TraceEntry]) -> dict[str, Any]:
        """Test-control gate: evaluate the last test run, decide revert vs verify.

        On FAIL with reverts remaining: revert via CheckpointManager, reset plan,
        and transition back to SOLVING (the next decide_next_action re-emits steps).
        We return a __done__ with the control thought ONLY if we proceed to verify;
        re-solve is signaled by transitioning phase (next call resumes SOLVING).
        """
        controller = self.test_controller_fn or _default_test_controller
        # Only inspect the trace slice produced since the last SOLVING start, so
        # a reverted failure is not re-read on the next solve pass.
        recent_trace = trace[self._trace_cursor:]
        result = controller(
            plan=self._plan,
            trace=recent_trace,
            checkpoint=self._checkpoint,
            revert_count=self._revert_count,
            max_reverts=self.max_reverts,
        )
        self._control_results.append(result)
        self._safe_update("control_history", _serialize_control(result))
        self._safe_update("verifier_feedback", {
            "last_control": result.verdict.value, "reason": result.reason,
        })

        # PASS → verify.
        if result.verdict == ControlVerdict.PASS:
            self._phase = _TriadPhase.VERIFYING
            # Fall through to verify on the next call.
            return {
                "tool": "__skip__", "args": {},
                "thought": f"triad control: PASS ({result.reason}) → verify",
            }

        # FAIL but no reverts left → let the verifier make the final call.
        if result.verdict == ControlVerdict.FAIL_REVERT_LIMIT or \
           self._revert_count >= self.max_reverts:
            self._phase = _TriadPhase.VERIFYING
            return {
                "tool": "__skip__", "args": {},
                "thought": f"triad control: revert limit hit ({self._revert_count}) → verify",
            }

        # FAIL_NO_CHECKPOINT → cannot revert; verify as-is.
        if result.verdict == ControlVerdict.FAIL_NO_CHECKPOINT:
            self._phase = _TriadPhase.VERIFYING
            return {
                "tool": "__skip__", "args": {},
                "thought": "triad control: fail, no checkpoint to revert → verify",
            }

        # FAIL_REVERTED → revert and re-solve.
        reverted = self._revert_to_checkpoint()
        if reverted:
            self._revert_count += 1
            self._reset_plan_for_resolve()
            self._phase = _TriadPhase.SOLVING
            return {
                "tool": "__skip__", "args": {},
                "thought": f"triad control: reverted ({self._revert_count}/{self.max_reverts}) → re-solve",
            }
        # Revert failed (non-git workspace) → verify as-is.
        self._phase = _TriadPhase.VERIFYING
        return {
            "tool": "__skip__", "args": {},
            "thought": "triad control: revert failed → verify",
        }

    def _run_verify(self, trace: list[TraceEntry]) -> dict[str, Any]:
        """Final verify: run the verifier sub-agent and emit __done__.

        The verifier inspects only the trace slice since the last SOLVING start
        (post-revert), so a reverted failed attempt is not held against the
        final verdict. The full trace remains in S1Output for audit (S3* sees
        everything); verify judges only the latest solve pass.
        """
        verifier = self.verifier_fn or _default_verifier
        recent_trace = trace[self._trace_cursor:]
        artifacts = []
        if self.checkpoint_mgr and self._checkpoint:
            artifacts = self.checkpoint_mgr.diff_since(self._checkpoint)
        result = verifier(plan=self._plan, trace=recent_trace, artifacts=artifacts)
        self._safe_update("verify_result", {"passed": result.passed, "reason": result.reason})

        self._phase = _TriadPhase.DONE
        self._close_session()

        verdict = "task_resolved" if result.passed else "task_failed"
        return {
            "tool": "__done__", "verdict": verdict,
            "thought": f"triad verify: {'passed' if result.passed else 'failed'} — {result.reason}",
        }

    # ── checkpoint / plan-reset helpers ──

    def _capture_checkpoint(self, label: str) -> None:
        if self.checkpoint_mgr is None:
            self.checkpoint_mgr = CheckpointManager(self.workspace)
        self._checkpoint = self.checkpoint_mgr.create(label)

    def _revert_to_checkpoint(self) -> bool:
        if self.checkpoint_mgr is None or self._checkpoint is None:
            return False
        return self.checkpoint_mgr.revert(self._checkpoint)

    def _reset_plan_for_resolve(self) -> None:
        """Clear the executed plan so SOLVING re-plans (planner sees the revert
        context and produces a different plan via the directive / its own logic)."""
        self._plan = []
        self._step_idx = 0
        self._skips = 0
        self._executed = []
        # Keep the checkpoint as the revert target; a new checkpoint is captured
        # only if _checkpoint is None (it isn't here).

    # ── session lifecycle (mirrors MultiAgentSolver) ──

    def _init_session(self) -> None:
        if self.session_store is None:
            try:
                from session_sync import SessionStore  # type: ignore
                self.session_store = SessionStore()
            except Exception:
                self.session_store = None
        if self.session_store is not None:
            try:
                self.session_store.create(
                    self.task_id,
                    agents=["planner", "test-controller", "verifier"],
                )
            except ValueError:
                try:
                    self.session_store.close(self.task_id)
                    self.session_store.create(
                        self.task_id,
                        agents=["planner", "test-controller", "verifier"],
                    )
                except Exception:
                    pass
        self._session_created = True

    def _close_session(self) -> None:
        if self.session_store and self._session_created:
            try:
                self.session_store.close(self.task_id)
            except Exception:
                pass
            self._session_created = False

    def _safe_update(self, key: str, value: Any) -> None:
        if self.session_store is None:
            return
        try:
            self.session_store.update(self.task_id, key, value)
        except Exception:
            pass

    # ── public accessors (for S1Output enrichment by the dispatcher) ──

    def get_control_results(self) -> list[ControlResult]:
        return list(self._control_results)

    def get_verify_result(self, trace: list[TraceEntry]) -> VerifyResult | None:
        """Return the last verify result, or None if verify hasn't run.

        Note: the verifier runs inside decide_next_action, so this is only
        populated after the solver has emitted __done__. The dispatcher reads
        control_results via get_control_results(); verify_result is reconstructed
        from the final verdict in practice.
        """
        return None


def _serialize_control(result: ControlResult) -> dict:
    cp = result.checkpoint
    return {
        "verdict": result.verdict.value,
        "test_output": result.test_output[:500],
        "reason": result.reason,
        "revert_count": result.revert_count,
        "checkpoint_ref": cp.ref if cp else None,
        "checkpoint_label": cp.label if cp else None,
    }


# ── Default sub-agent implementations (rule-based stubs, for testing) ──


def _default_planner(
    task_prompt: str,
    available_tools: list[str],
    recovery_directive: dict | None,
) -> list[dict]:
    """Rule-based planner stub (reused from MultiAgentSolver semantics).

    Produces: list workspace → run tests. On a recovery/revert cycle the plan
    is the same — a real planner (WS3) would diverge based on the revert signal.
    """
    steps: list[dict] = []
    if "fs.list" in available_tools:
        steps.append({"tool": "fs.list", "args": {"path": "."}, "desc": "list workspace"})
    if "shell.exec" in available_tools:
        steps.append({
            "tool": "shell.exec",
            "args": {"command": "python3 -m pytest --tb=short 2>&1 || true", "timeout": 30},
            "desc": "run tests (control gate)",
        })
    if recovery_directive and recovery_directive.get("policy_applied") == "InstallDependency":
        env_changes = recovery_directive.get("env_changes") or [""]
        module = env_changes[0] if env_changes else ""
        if module and "shell.exec" in available_tools:
            steps.append({
                "tool": "shell.exec",
                "args": {"command": f"pip3 install {module} 2>&1 || true", "timeout": 60},
                "desc": f"recovery: install {module}",
            })
    return steps


def _default_test_controller(
    plan: list[dict],
    trace: list[TraceEntry],
    checkpoint: Checkpoint | None,
    revert_count: int,
    max_reverts: int,
) -> ControlResult:
    """Rule-based test-controller stub.

    Scans the trace for a pytest run and decides PASS/FAIL. On FAIL, if a
    checkpoint exists and reverts remain → FAIL_REVERTED; else FAIL_NO_CHECKPOINT
    or FAIL_REVERT_LIMIT.
    """
    # Find the most recent test run in the trace.
    test_obs = ""
    for entry in reversed(trace):
        action = entry.action or {}
        cmd = (action.get("args") or {}).get("command", "") or ""
        tool = action.get("tool", "")
        if "pytest" in cmd or "test" in cmd.lower() or tool == "shell.exec" and cmd:
            test_obs = entry.observation or ""
            break
    if not test_obs and trace:
        test_obs = trace[-1].observation or ""

    obs_lower = test_obs.lower()
    failed = any(kw in obs_lower for kw in [
        "error", "traceback", "failed", "exception", "module not found",
        # VSM-034 SECONDARY-2: "collected 0 items" / "no tests ran" is NOT a pass —
        # it means the solver produced nothing testable. Without these markers an
        # empty workspace passes the controller and masks a surrender (game-of-stones,
        # git-repo-forensics: verdict=pass but TB reward=0). These specific phrases
        # cannot match a real passing run ("1 item"/"2 items" don't contain "0 ").
        "collected 0", "no tests ran", "no tests collected", "0 selected",
        "0 items", "0 errors", "cannot collect",
    ])

    if not failed:
        return ControlResult(
            verdict=ControlVerdict.PASS, test_output=test_obs,
            checkpoint=checkpoint, revert_count=revert_count,
            reason="no error keywords and non-empty test collection in output",
        )

    # Failed — decide revert.
    if revert_count >= max_reverts:
        return ControlResult(
            verdict=ControlVerdict.FAIL_REVERT_LIMIT, test_output=test_obs,
            checkpoint=checkpoint, revert_count=revert_count,
            reason=f"tests failed but revert limit reached ({revert_count}/{max_reverts})",
        )
    if checkpoint is None or checkpoint.ref == "none":
        return ControlResult(
            verdict=ControlVerdict.FAIL_NO_CHECKPOINT, test_output=test_obs,
            checkpoint=checkpoint, revert_count=revert_count,
            reason="tests failed, no checkpoint to revert to",
        )
    return ControlResult(
        verdict=ControlVerdict.FAIL_REVERTED, test_output=test_obs,
        checkpoint=checkpoint, revert_count=revert_count,
        reason="tests failed — will revert to checkpoint and re-solve",
    )


def _default_verifier(
    plan: list[dict],
    trace: list[TraceEntry],
    artifacts: list[Any],
) -> VerifyResult:
    """Rule-based verifier stub (reused from MultiAgentSolver semantics).

    Passes if no error keywords appear in any trace observation; else fails.
    """
    error_keywords = ["error", "traceback", "failed", "exception", "module not found"]
    failed_checks: list[dict] = []
    for k, entry in enumerate(trace):
        obs = (entry.observation or "").lower()
        for kw in error_keywords:
            if kw in obs:
                failed_checks.append({
                    "trace_idx": k, "keyword": kw,
                    "detail": (entry.observation or "")[:200],
                })
                break
    if failed_checks:
        return VerifyResult(
            passed=False,
            reason=f"{len(failed_checks)} trace entries contain error keywords",
            checks=failed_checks,
        )
    return VerifyResult(
        passed=True, reason="no error keywords in any trace observation",
        checks=[{"name": "trace-scan", "passed": True}],
    )


# ── GooseRunner-backed sub-agent factories (VSM-021 agentization) ──
#
# These produce the same callable signatures the TriadSolver expects
# (planner_fn / test_controller_fn / verifier_fn), but each invocation spawns a
# goose subprocess running the corresponding vsm/systems/s1-<role>/ agent,
# bound to the TASK workspace (not vsm/). Lazy import of agent_runtime keeps
# runtime/ decoupled at import time (only the agentized path pulls it in).
#
# On any goose failure (binary missing, parse error, timeout) the factories
# FALL BACK to the rule-based stubs — so the triad degrades gracefully when
# goose is unavailable (tests, CI without goose, non-production setups).


def make_goose_planner(
    systems_dir,
    workspace,
    provider: str = "zai",
    timeout_sec: int = 120,
):
    """Return a planner_fn backed by the s1-planner goose agent.

    Falls back to _default_planner if goose is unavailable or parsing fails.
    The planner gets read-only tools (fs/shell) so it can inspect the workspace
    structure before producing a plan — its plan steps are then executed by the
    in-process AgentLoop via the full MCP server.
    """
    def _planner(task_prompt, available_tools, recovery_directive):
        task_input = _json_dump({
            "task_prompt": task_prompt,
            "available_tools": available_tools,
            "recovery_directive": recovery_directive,
        })
        parsed = _run_goose_subagent(
            role="s1-planner", systems_dir=systems_dir, workspace=workspace,
            provider=provider, task_input=task_input, timeout_sec=timeout_sec,
            tools=["fs", "shell"],
        )
        # VSM-034 A': record planner source for observability (log-only).
        import os
        import json
        import time as _time
        _diag_dir = os.environ.get("VSM_DIAG_DIR", "")
        def _src(source, **extra):
            if not _diag_dir:
                return
            try:
                rec = {"role": "planner_source", "ts": _time.time(),
                       "source": source, **extra}
                with open(os.path.join(_diag_dir, f"planner-source-{int(_time.time()*1000)}.json"), "w") as f:
                    json.dump(rec, f, default=str, indent=2)
            except Exception:
                pass
        if parsed is None:
            _src("default_fallback_none")
            return _default_planner(task_prompt, available_tools, recovery_directive)
        steps = parsed.get("steps") or []
        # Minimal validation: each step must have a tool.
        clean = [s for s in steps if isinstance(s, dict) and s.get("tool")]
        if not clean:
            _src("default_fallback_empty", raw_steps_count=len(steps))
            return _default_planner(task_prompt, available_tools, recovery_directive)
        _src("goose", steps_count=len(clean))
        return clean

    return _planner


def make_goose_test_controller(
    systems_dir,
    workspace,
    checkpoint_mgr: "CheckpointManager | None" = None,
    provider: str = "zai",
    timeout_sec: int = 150,
):
    """Return a test_controller_fn backed by the s1-test-controller goose agent.

    The agent decides verdict (pass / fail_reverted / ...). If it reports
    fail_reverted, the closure performs the actual git revert via checkpoint_mgr
    (the agent's git.reset_hard call is captured in its trace; the closure
    re-applies to keep CheckpointManager state consistent).

    Falls back to _default_test_controller on goose failure.
    """
    def _test_controller(plan, trace, checkpoint, revert_count, max_reverts):
        task_input = _json_dump({
            "plan_size": len(plan),
            "trace_tail": [(e.action.get("tool") if e.action else None,
                            (e.observation or "")[:300]) for e in trace[-5:]],
            "checkpoint_ref": checkpoint.ref if checkpoint else None,
            "checkpoint_label": checkpoint.label if checkpoint else None,
            "revert_count": revert_count,
            "max_reverts": max_reverts,
        })
        parsed = _run_goose_subagent(
            role="s1-test-controller", systems_dir=systems_dir, workspace=workspace,
            provider=provider, task_input=task_input, timeout_sec=timeout_sec,
            tools=["fs", "shell", "git"],
        )
        if parsed is None:
            return _default_test_controller(
                plan, trace, checkpoint, revert_count, max_reverts,
            )
        verdict_str = parsed.get("verdict", "pass")
        try:
            verdict = ControlVerdict(verdict_str)
        except ValueError:
            verdict = ControlVerdict.PASS
        revert_performed = bool(parsed.get("revert_performed"))
        # If the agent claims revert but didn't actually reset (or to keep
        # CheckpointManager consistent), perform it here too.
        if verdict == ControlVerdict.FAIL_REVERTED and checkpoint_mgr and checkpoint and revert_performed:
            checkpoint_mgr.revert(checkpoint)
        return ControlResult(
            verdict=verdict,
            test_output=str(parsed.get("test_output", ""))[:500],
            checkpoint=checkpoint, revert_count=revert_count,
            reason=str(parsed.get("reason", "")),
        )

    return _test_controller


def make_goose_verifier(
    systems_dir,
    workspace,
    provider: str = "zai",
    timeout_sec: int = 120,
):
    """Return a verifier_fn backed by the s1-verifier goose agent.

    Falls back to _default_verifier on goose failure.
    """
    def _verifier(plan, trace, artifacts):
        task_input = _json_dump({
            "plan_size": len(plan),
            "trace_tail": [(e.action.get("tool") if e.action else None,
                            (e.observation or "")[:300]) for e in trace[-5:]],
            "artifacts": [{"path": a.path, "op": a.op} for a in artifacts[:20]],
        })
        parsed = _run_goose_subagent(
            role="s1-verifier", systems_dir=systems_dir, workspace=workspace,
            provider=provider, task_input=task_input, timeout_sec=timeout_sec,
            tools=["fs", "shell"],
        )
        if parsed is None:
            return _default_verifier(plan, trace, artifacts)
        return VerifyResult(
            passed=bool(parsed.get("passed", False)),
            reason=str(parsed.get("reason", "")),
            checks=list(parsed.get("checks", [])),
        )

    return _verifier


def _is_network_failure(result) -> bool:
    """VSM-034: detect goose failures caused by flaky network (retryable).

    Two signatures observed in diagnostic data:
      (1) TCP-connect-hang → goose subprocess.TimeoutExpired (exit_code=124,
          timed_out=True, empty stdout). VPN-TUN connect stalls until the
          subprocess timeout kills goose.
      (2) Explicit 'Network error: Could not connect to api.z.ai' in stdout
          (exit_code=0, goose started its banner, API call failed).
    Both are transient (host network works moments later); retry recovers them.
    """
    if result is None:
        return False
    if getattr(result, "timed_out", False):
        return True
    stdout = (getattr(result, "stdout", "") or "").lower()
    stderr = (getattr(result, "stderr", "") or "").lower()
    network_markers = (
        "network error",
        "could not connect to",
        "connection reset",
        "connection refused",
        "temporary failure in name resolution",
        "tls handshake",
    )
    return any(m in stdout or m in stderr for m in network_markers)


def _diag_goose(role, status, **extra):
    """VSM-034 A': permanent diagnostic for goose sub-agent outcomes.

    Writes a small JSON record per goose invocation into $VSM_DIAG_DIR (default
    /tmp/vsm-diag, overridden by eval/harbor_adapter.py to a bind-mounted path
    so records survive the container). Log-only — never changes behavior.
    Records: role, status (ok | network_retry | parse_none), attempt number,
    exit_code, timed_out, duration, stdout/stderr heads. This makes the
    goose-vs-fallback decision observable in product-trace without ad-hoc
    instrumentation every time a regression like VSM-034 appears.
    """
    import os
    import json
    import time as _time
    _diag_dir = os.environ.get("VSM_DIAG_DIR", "/tmp/vsm-diag")
    try:
        os.makedirs(_diag_dir, exist_ok=True)
    except Exception:
        return
    try:
        rec = {"role": role, "ts": _time.time(), "status": status, **extra}
        with open(os.path.join(_diag_dir, f"goose-{role}-{int(_time.time()*1000)}.json"), "w") as f:
            json.dump(rec, f, default=str, indent=2)
    except Exception:
        pass


def _run_goose_subagent(
    role: str,
    systems_dir,
    workspace,
    provider: str,
    task_input: str,
    timeout_sec: int,
    tools: list[str] | None = None,
):
    """Run one goose sub-agent; return parsed dict or None on any failure.

    None return signals the caller to fall back to the rule-based stub. This
    keeps the triad usable without goose (tests, CI).

    VSM-034: retries on transient network failure (flaky VPN-TUN to z.ai).
    Diagnostic data showed 77% of planner fallbacks were network errors
    (TCP-connect-hang timeout OR explicit 'Network error'); a single retry
    recovered most of them. Retry budget = 2 attempts (initial + 1 retry)
    with 4s backoff. Non-network failures (parse error, real goose crash)
    are NOT retried — only network-classified ones.

    tools: per-role MCP tool modules to attach (e.g. ["fs", "shell"]). When
    non-empty, GooseRunner builds a --with-extension wrapper so goose can
    actually call the tools (read/write/exec). Without this, goose runs blind
    — it sees tool NAMES in the prompt text but cannot invoke them, so the
    planner/verifier output is unconstrained by what's actually executable.
    """
    try:
        from agent_runtime.goose_runner import AgentConfig, GooseRunner  # type: ignore
    except Exception:
        return None
    import shutil
    if not shutil.which("goose"):
        return None
    cfg = AgentConfig(
        system_name=role,
        systems_dir=systems_dir,
        provider=provider,
        workspace=str(workspace),
        tools=tools or [],
    )

    # VSM-034: network-retry loop. GooseRunner.run() does not raise on
    # subprocess timeout / network errors — it returns an AgentResult with
    # timed_out / exit_code set. We classify and retry transient network flaps.
    import time as _time
    max_attempts = 2  # initial + 1 retry
    backoff_sec = 4.0
    for attempt in range(1, max_attempts + 1):
        try:
            result = GooseRunner().run(cfg, task_input, timeout_sec=timeout_sec)
        except Exception:
            # Unexpected crash (not a GooseRunner-handled network/timeout).
            # Not retryable — bail out.
            return None
        if result.parsed is not None:
            _diag_goose(role, "ok", attempt=attempt, exit_code=result.exit_code,
                        duration_sec=round(result.duration_sec, 2),
                        parsed_keys=list(result.parsed.keys())
                        if isinstance(result.parsed, dict) else None)
            return result.parsed
        # parsed is None — decide whether to retry.
        if attempt < max_attempts and _is_network_failure(result):
            _diag_goose(role, "network_retry", attempt=attempt,
                        exit_code=result.exit_code,
                        timed_out=result.timed_out,
                        duration_sec=round(result.duration_sec, 2),
                        stdout_head=(result.stdout or "")[:500],
                        stderr_head=(result.stderr or "")[:500])
            _time.sleep(backoff_sec)
            continue
        # Non-network failure, or retry budget exhausted: log and fall back.
        _diag_goose(role, "parse_none", attempt=attempt,
                    exit_code=result.exit_code,
                    timed_out=result.timed_out,
                    duration_sec=round(result.duration_sec, 2),
                    stdout_len=len(result.stdout or ""),
                    stdout_head=(result.stdout or "")[:2000],
                    stderr_head=(result.stderr or "")[:2000],
                    has_json_block=("```json" in (result.stdout or "")),
                    network=_is_network_failure(result))
        return None
    return None


def _json_dump(obj) -> str:
    import json
    try:
        return json.dumps(obj, default=str)
    except Exception:
        return str(obj)


def make_triad_with_goose(
    systems_dir,
    workspace,
    checkpoint_mgr: "CheckpointManager | None" = None,
    provider: str = "zai",
    max_reverts: int = 2,
    task_id: str = "goose-triad",
):
    """Convenience: build a TriadSolver with all three sub-agents goose-backed.

    Used by the dispatcher when goose is available (solver_mode="triad" + goose
    detected). Each sub-agent falls back to its rule-based stub individually if
    goose fails — so partial goose availability still works.
    """
    return TriadSolver(
        task_id=task_id,
        workspace=workspace,
        checkpoint_mgr=checkpoint_mgr,
        planner_fn=make_goose_planner(systems_dir, workspace, provider),
        test_controller_fn=make_goose_test_controller(
            systems_dir, workspace, checkpoint_mgr, provider,
        ),
        verifier_fn=make_goose_verifier(systems_dir, workspace, provider),
        max_reverts=max_reverts,
    )

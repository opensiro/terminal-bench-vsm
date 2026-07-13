"""multi_agent — MultiAgentSolver: OSM Split S1 (VSM-007).

S1 split into three recursively-viable sub-agents:
  - planner: decomposes task_prompt into ordered steps (plan)
  - executor: executes steps via MCP tools, writes intermediate_results
  - verifier: checks each step result, writes verifier_feedback

Coordination via SessionStore (per-task shared state). Session lifecycle:
create at first decide_next_action, close when done.

Implements SolverProtocol — AgentLoop drives it the same way as
RuleBasedSolver. Internal state machine transitions:
  PLANNING -> EXECUTING -> VERIFYING -> (EXECUTING | DONE)

Stateless (CONTRACT §5): no state between invocations. Session is per-task
(TTL-based cleanup). MultiAgentSolver instance is fresh per AgentLoop.run().
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from .types import TraceEntry


class _Phase(str, Enum):
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    DONE = "done"


@dataclass
class MultiAgentSolver:
    """Multi-agent S1 solver: planner + executor + verifier (VSM-007 Split).

    Implements SolverProtocol (structurally). Driven by AgentLoop (same as
    RuleBasedSolver). Uses SessionStore for inter-agent shared state.

    Args:
        session_store: SessionStore for shared state (created externally and
            shared across sub-agents). If None, creates internally per task.
        task_id: unique task identifier for the session.
        planner_fn: callable(task_prompt, available_tools, recovery_directive)
            -> list[dict]. Returns a plan (list of steps). If None, uses
            _default_planner (rule-based stub for testing).
        verifier_fn: callable(step, observation) -> dict. Returns
            {"pass": bool, "reason": str}. If None, uses _default_verifier
            (rule-based: checks for error keywords).
    """

    session_store: Any = None  # SessionStore (injected or created)
    task_id: str = "default-task"
    planner_fn: Callable[..., list[dict]] | None = None
    verifier_fn: Callable[[dict, str], dict] | None = None

    # Internal state (per-instance, fresh per AgentLoop.run — CONTRACT §5).
    # step_idx is tracked off len(trace) in decide_next_action; kept here as a
    # cache of how many executor steps have already been emitted this run.
    _phase: _Phase = field(default=_Phase.PLANNING, init=False)
    _plan: list[dict] = field(default_factory=list, init=False)
    _step_idx: int = field(default=0, init=False)
    # Number of planner steps skipped because their tool was unavailable.
    # AgentLoop does NOT append a TraceEntry for __skip__, so the executor
    # cursor = len(trace) + _skips (skips advance the cursor without growing
    # the trace).
    _skips: int = field(default=0, init=False)
    # Plan-step indices that were actually executed (not skipped). Built up as
    # the executor emits real tool calls. Verifier pairs
    # _executed[k] <-> trace[k] so steps skipped in the middle of the plan do
    # not desync trace-vs-plan alignment.
    _executed: list[int] = field(default_factory=list, init=False)
    _session_created: bool = field(default=False, init=False)

    def decide_next_action(
        self,
        task_prompt: str,
        trace: list[TraceEntry],
        available_tools: list[str],
        recovery_directive: dict | None,
        budget_remaining: dict[str, float],
    ) -> dict[str, Any]:
        """State machine: PLANNING -> EXECUTING -> VERIFYING -> DONE.

        AgentLoop calls this once per iteration. Each call returns either:
          - {"tool": <name>, "args": {...}, "thought": ...}  (executor step)
          - {"tool": "__skip__", ...}  (planner step unavailable; AgentLoop
            re-calls without consuming budget / polluting trace)
          - {"tool": "__done__", "verdict": "task_resolved"|"task_failed",
             "thought": ...}
        """
        # Initialize session on first call
        if not self._session_created:
            self._init_session()

        # ── PLANNING phase ──
        if self._phase == _Phase.PLANNING:
            planner = self.planner_fn or _default_planner
            self._plan = planner(task_prompt, available_tools, recovery_directive)
            # Write plan to session
            self._safe_update("plan", self._plan)
            self._phase = _Phase.EXECUTING
            self._step_idx = 0

            # Empty plan -> nothing to do
            if not self._plan:
                self._close_session()
                return {
                    "tool": "__done__",
                    "verdict": "task_failed",
                    "thought": "planner produced empty plan",
                }

        # ── EXECUTING phase ──
        if self._phase == _Phase.EXECUTING:
            # Re-sync step_idx with the actual trace length: every completed
            # executor step produced exactly one TraceEntry (AgentLoop appends
            # one entry per executed tool call). Skipped steps (__skip__) do
            # NOT grow the trace, so add _skips to keep the cursor correct.
            self._step_idx = len(trace) + self._skips

            if self._step_idx >= len(self._plan):
                # All steps executed -> verify
                self._phase = _Phase.VERIFYING
            else:
                step = self._plan[self._step_idx]
                tool = step.get("tool", "")
                args = step.get("args", {})

                # Tool unavailable -> ask AgentLoop to skip (no trace entry).
                # Advance the skip counter so the next call moves past this
                # step rather than re-emitting __skip__ forever.
                if tool not in available_tools:
                    self._skips += 1
                    return {
                        "tool": "__skip__",
                        "args": {},
                        "thought": (
                            f"planner step {self._step_idx}: tool '{tool}' "
                            "not available, skipping"
                        ),
                    }

                # Record that this plan-step will be executed, so the verifier
                # can pair it with the upcoming trace entry.
                self._executed.append(self._step_idx)

                return {
                    "tool": tool,
                    "args": args,
                    "thought": (
                        f"executor: step {self._step_idx + 1}/{len(self._plan)}"
                    ),
                }

        # ── VERIFYING phase ──
        if self._phase == _Phase.VERIFYING:
            verifier = self.verifier_fn or _default_verifier

            # Pair each executed plan-step with its trace entry by position:
            # _executed[k] (plan index) <-> trace[k] (observation). This stays
            # correct even when steps were skipped mid-plan. If the trace has
            # not yet caught up to the steps we claimed to execute (e.g. solver
            # forced into VERIFYING early), those extra steps are unverifiable.
            all_passed = True
            n_verifiable = min(len(self._executed), len(trace))
            for k in range(n_verifiable):
                plan_idx = self._executed[k]
                step = self._plan[plan_idx]
                obs = trace[k].observation
                result = verifier(step, obs)
                self._safe_update_verifier_feedback(plan_idx, result)
                if not result.get("pass", False):
                    all_passed = False
            # Claimed executions not yet reflected in trace -> unverifiable
            if len(self._executed) > len(trace):
                all_passed = False

            self._phase = _Phase.DONE
            self._close_session()

            if all_passed:
                return {
                    "tool": "__done__",
                    "verdict": "task_resolved",
                    "thought": "verifier: all steps passed",
                }
            return {
                "tool": "__done__",
                "verdict": "task_failed",
                "thought": "verifier: one or more steps failed verification",
            }

        # ── DONE (shouldn't reach here) ──
        return {
            "tool": "__done__",
            "verdict": "unknown",
            "thought": "state machine reached DONE unexpectedly",
        }

    def record_step_result(self, step_idx: int, observation: str) -> None:
        """Write an intermediate_result to the session.

        Optional hook: AgentLoop may call this after executing a step. The
        solver does not depend on it (it derives step_idx from len(trace)),
        but it keeps session_sync intermediate_results in sync for external
        observers / verifier sub-agent.
        """
        self._safe_update_intermediate(step_idx, observation)

    # ── session lifecycle helpers ──

    def _init_session(self) -> None:
        """Create session in SessionStore (re-create if it already exists)."""
        if self.session_store is None:
            # Lazy import: session_sync is a sibling package of runtime, so it
            # resolves when src/ is on sys.path (the standard run config).
            from session_sync import SessionStore  # type: ignore

            self.session_store = SessionStore()
        try:
            self.session_store.create(
                self.task_id,
                agents=["planner", "executor", "verifier"],
            )
        except ValueError:
            # Session exists (reuse path) — close and recreate cleanly.
            self.session_store.close(self.task_id)
            self.session_store.create(
                self.task_id,
                agents=["planner", "executor", "verifier"],
            )
        self._session_created = True

    def _close_session(self) -> None:
        """Close session after completion."""
        if self.session_store and self._session_created:
            self.session_store.close(self.task_id)
            self._session_created = False

    def _safe_update(self, key: str, value: Any) -> None:
        try:
            self.session_store.update(self.task_id, key, value)
        except Exception:
            # session may be closed/missing/expired — non-fatal for the solver
            pass

    def _safe_update_intermediate(self, step_idx: int, observation: str) -> None:
        try:
            results = self.session_store.read(self.task_id, "intermediate_results")
            results[step_idx] = observation
            self.session_store.update(self.task_id, "intermediate_results", results)
        except Exception:
            pass

    def _safe_update_verifier_feedback(self, step_idx: int, result: dict) -> None:
        try:
            feedback = self.session_store.read(self.task_id, "verifier_feedback")
            feedback[step_idx] = result
            self.session_store.update(self.task_id, "verifier_feedback", feedback)
        except Exception:
            pass


# ── Default sub-agent implementations (rule-based, for testing) ──


def _default_planner(
    task_prompt: str,
    available_tools: list[str],
    recovery_directive: dict | None,
) -> list[dict]:
    """Rule-based planner stub: simple decomposition for testing.

    A real planner would use an LLM (HarnessRunner/Goose) to decompose
    task_prompt. This stub: list workspace -> run tests, plus a recovery
    remediation step if a recovery directive is present.
    """
    steps: list[dict] = []

    # Step 1: list workspace
    if "fs.list" in available_tools:
        steps.append(
            {"tool": "fs.list", "args": {"path": "."}, "desc": "list workspace"}
        )

    # Step 2: run tests
    if "shell.exec" in available_tools:
        steps.append(
            {
                "tool": "shell.exec",
                "args": {
                    "command": "python3 -m pytest --tb=short 2>&1 || true",
                    "timeout": 30,
                },
                "desc": "run tests",
            }
        )

    # Recovery directive -> remediation step
    if recovery_directive and recovery_directive.get("policy_applied"):
        policy = recovery_directive["policy_applied"]
        if policy == "InstallDependency" and "shell.exec" in available_tools:
            env_changes = recovery_directive.get("env_changes") or [""]
            module = env_changes[0] if env_changes else ""
            steps.append(
                {
                    "tool": "shell.exec",
                    "args": {
                        "command": f"pip3 install {module} 2>&1 || true",
                        "timeout": 60,
                    },
                    "desc": f"recovery: install {module}",
                }
            )

    return steps


def _default_verifier(step: dict, observation: str) -> dict:
    """Rule-based verifier stub: checks observation for error keywords.

    A real verifier would use an LLM to check whether the step achieved its
    goal. This stub: passes if no error keywords are found in the observation.
    """
    obs_lower = (observation or "").lower()
    error_keywords = ["error", "traceback", "failed", "exception", "module not found"]
    for kw in error_keywords:
        if kw in obs_lower:
            return {"pass": False, "reason": f"found error keyword: {kw}"}
    return {"pass": True, "reason": "no error keywords found"}

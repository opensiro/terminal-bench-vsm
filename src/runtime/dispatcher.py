"""dispatcher — s1-dispatcher runtime (T2 CONTRACT §4 lifecycle).

Stateless (CONTRACT §5): fresh-per-invocation. No state between runs.

Four execution modes:
  1. AgentLoop + RuleBasedSolver (mono, default, for testing): deterministic
     stub drives MCP tools in-process.
  2. AgentLoop + MultiAgentSolver (multi, VSM-007 Split): planner + executor +
     verifier sub-agents, coordinated via SessionStore. Set via solver_mode="multi".
  3. AgentLoop + TriadSolver (triad, VSM-020): solve → control-by-tests → verify
     with in-invocation checkpoint/revert (CONTRACT §5.1). Set via solver_mode="triad".
  4. HarnessRunner (production): external harness (Claude Code / Goose) drives
     MCP server as subprocess. Harness = brain, MCP = hands (VSM-005 membrane).
"""
from __future__ import annotations

from pathlib import Path
from .types import S1Input, S1Output, Verdict
from .budget import BudgetTracker
from .artifacts import snapshot, diff


def _systems_dir() -> Path:
    """Resolve vsm/systems/ relative to src/ (sibling of src/runtime/).

    Used by the agentized triad (VSM-021) to locate s1-planner /
    s1-test-controller / s1-verifier SOUL/SKILL/TASK. Mirrors the
    _DEFAULT_SYSTEMS_DIR resolution in agent_runtime/protocol.py.
    """
    return Path(__file__).resolve().parent.parent.parent / "vsm" / "systems"


class S1Dispatcher:
    """S1 dispatcher: launch → isolate → trace → collect output.

    Stateless: each invoke() is independent. No state between invocations.

    Four execution modes:
      1. AgentLoop + RuleBasedSolver (mono, default, for testing): deterministic
         stub drives MCP tools in-process.
      2. AgentLoop + MultiAgentSolver (multi, VSM-007 Split): planner + executor
         + verifier sub-agents coordinated via SessionStore.
      3. AgentLoop + TriadSolver (triad, VSM-020): solve → control-by-tests → verify
         with in-invocation checkpoint/revert (CONTRACT §5.1, VSM-019).
      4. HarnessRunner (production): external harness (Claude Code / Goose)
         drives MCP server as subprocess.

    Args:
        mcp_server: in-process MCP server (for AgentLoop modes). If None + no
            harness, creates one automatically.
        harness: HarnessRunner for production mode. If set, uses external harness
            instead of in-process AgentLoop (takes precedence over solver_mode).
        solver_mode: "mono" (default) → RuleBasedSolver; "multi" →
            MultiAgentSolver (VSM-007 Split); "triad" → TriadSolver (VSM-020).
            Ignored when harness is set.
    """

    def __init__(self, mcp_server=None, harness=None, solver_mode: str = "mono"):
        if solver_mode not in ("mono", "multi", "triad"):
            raise ValueError(
                f"invalid solver_mode: {solver_mode!r} (expected 'mono', 'multi' or 'triad')"
            )
        self._mcp_server = mcp_server
        self._harness = harness
        self._solver_mode = solver_mode

    def invoke(self, input: S1Input) -> S1Output:
        """One invocation of S1 solver (CONTRACT §4 lifecycle).

        1. Snapshot filesystem (for artifacts diff).
        2. Launch solver (AgentLoop or HarnessRunner), under budget.
        3. Solver works until verdict OR budget exhaustion.
        4. Collect trace + artifacts diff + failure_observations.
        """
        # Harness mode: external harness + MCP subprocess (takes precedence)
        if self._harness is not None:
            return self._harness.invoke(input)

        # AgentLoop mode: in-process solver + MCP (mono or multi)
        return self._invoke_agent_loop(input)

    def _invoke_agent_loop(self, input: S1Input) -> S1Output:
        """In-process AgentLoop mode (mono or multi, for testing)."""
        from .solver import solve, solve_with_solver

        # 1. Snapshot
        fs_before = snapshot(input.workspace)

        # 2. Budget tracker
        budget = BudgetTracker(
            time_seconds=input.budget.time_seconds,
            tokens=input.budget.tokens,
            actions=input.budget.actions,
        )

        # 3. Get MCP server
        if self._mcp_server is None:
            from mcp_server.server import create_server
            self._mcp_server = create_server(str(input.workspace))

        # 3.1 S1 preflight self-check (CONTRACT: S1 contains its own verification).
        # Lazy import avoids circular imports (verify imports dispatcher at runtime).
        from .verify import preflight_check, preflight_diagnostic_output
        preflight = preflight_check(input, self._mcp_server)
        if not preflight.ok:
            return preflight_diagnostic_output(preflight)

        # 4. Run solver (mono → RuleBasedSolver, multi → MultiAgentSolver,
        #    triad → TriadSolver with checkpoint/revert)
        if self._solver_mode in ("multi", "triad"):
            import hashlib
            # Derive a deterministic task_id for the per-task session. S1Input has
            # no explicit id, so hash the task prompt + workspace for isolation
            # between tasks while remaining stable across retries of the same task.
            task_id = hashlib.sha1(
                f"{input.task_prompt}|{input.workspace}".encode("utf-8")
            ).hexdigest()[:12]

            if self._solver_mode == "triad":
                from .checkpoint import CheckpointManager
                checkpoint_mgr = CheckpointManager(input.workspace)
                # VSM-021: use goose-backed sub-agents when goose is available;
                # otherwise fall back to in-process stubs (tests, CI).
                import shutil
                if shutil.which("goose"):
                    from .triad_solver import make_triad_with_goose
                    solver = make_triad_with_goose(
                        systems_dir=_systems_dir(),
                        workspace=input.workspace,
                        checkpoint_mgr=checkpoint_mgr,
                        task_id=task_id,
                    )
                else:
                    from .triad_solver import TriadSolver
                    solver = TriadSolver(
                        task_id=task_id,
                        workspace=input.workspace,
                        checkpoint_mgr=checkpoint_mgr,
                    )
            else:  # multi
                from .multi_agent import MultiAgentSolver
                solver = MultiAgentSolver(task_id=task_id)
            output = solve_with_solver(input, self._mcp_server, budget, solver)

            # Enrich S1Output with triad control_results (auditability, VSM-020).
            if self._solver_mode == "triad":
                output.control_results = solver.get_control_results()
                output.verify_result = solver.get_verify_result()
        else:
            output = solve(input, self._mcp_server, budget)

        # 5. Artifacts diff
        fs_after = snapshot(input.workspace)
        output.artifacts = diff(fs_before, fs_after, input.workspace)

        # 6. Budget check
        if budget.exhausted and output.verdict != Verdict.TASK_RESOLVED:
            output.verdict = Verdict.BUDGET_EXHAUSTED

        output.cost = budget.summary()
        return output

    def capability_report(self, workspace: str = ""):
        """Run full e2e capability report (S1 self-verification).

        On-demand e2e: solver → MCP → trace → recovery cycle. Used for phase
        transitions, config changes, S5 requests. Lazy import to avoid circular
        imports (verify imports dispatcher at runtime).
        """
        from .verify import capability_report, VerifyConfig
        return capability_report(VerifyConfig(workspace=workspace))


def invoke(
    input: S1Input,
    mcp_server=None,
    harness=None,
    solver_mode: str = "mono",
) -> S1Output:
    """Convenience function: create dispatcher and invoke.

    If harness is provided, uses HarnessRunner (production mode).
    Otherwise uses AgentLoop: solver_mode="mono" → RuleBasedSolver (testing),
    solver_mode="multi" → MultiAgentSolver (VSM-007 Split),
    solver_mode="triad" → TriadSolver with checkpoint/revert (VSM-020).
    """
    dispatcher = S1Dispatcher(
        mcp_server=mcp_server, harness=harness, solver_mode=solver_mode
    )
    return dispatcher.invoke(input)

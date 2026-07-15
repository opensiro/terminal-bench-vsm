"""agent_loop — pluggable LLM solver loop (T2 CONTRACT §4 lifecycle).

Framework: tool-call-observe cycle with pluggable LLM interface.
- RuleBasedSolver: deterministic stub for testing without LLM.
- LLMSolver (future): real LLM agent loop (protocol defined, implementation = future).

Stateless (CONTRACT §5): each invoke is fresh, no state between runs.
Budget enforcement: loop stops on budget exhaustion.
"""
from __future__ import annotations
import re
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from .types import S1Input, S1Output, TraceEntry, FailureObservation, Verdict
from .budget import BudgetTracker


class SolverProtocol(Protocol):
    """Protocol for pluggable solvers (LLM or rule-based)."""

    def decide_next_action(
        self,
        task_prompt: str,
        trace: list[TraceEntry],
        available_tools: list[str],
        recovery_directive: dict | None,
        budget_remaining: dict[str, float],
    ) -> dict[str, Any]:
        """Decide next tool call.

        Returns:
            {"tool": <name>, "args": {...}, "thought": <optional reasoning>}
            or {"tool": "__done__", "verdict": "task_resolved"|"task_failed", "thought": "..."}
        """
        ...


@dataclass
class AgentLoop:
    """Tool-call-observe loop: drives solver through MCP tools under budget.

    Stateless: each run() is independent. The solver decides actions;
    the loop executes them via MCP and collects trace/observations.
    """

    solver: SolverProtocol
    mcp_server: Any  # MCPServer from mcp_server.server
    max_iterations: int = 50

    def run(self, input: S1Input, budget: BudgetTracker) -> S1Output:
        """Run the agent loop: solver decides → MCP executes → observe → repeat.

        1. Get available tools from MCP.
        2. Loop: solver.decide_next_action → execute via MCP → log trace.
        3. Stop on: solver says done, budget exhausted, or max_iterations.
        4. Collect failure_observations from trace.
        """
        output = S1Output()
        trace_idx = 0

        # Get available tools
        available = [t["name"] for t in self.mcp_server.list_tools()]

        # Recovery directive as dict (for solver context)
        directive = None
        if input.recovery_directive:
            directive = {
                "failure_class": input.recovery_directive.failure_class,
                "policy_applied": input.recovery_directive.policy_applied,
                "env_changes": input.recovery_directive.env_changes,
                "policy_attempt": input.recovery_directive.policy_attempt,
            }

        iterations = 0
        while iterations < self.max_iterations and not budget.exhausted:
            iterations += 1

            # Solver decides next action
            decision = self.solver.decide_next_action(
                task_prompt=input.task_prompt,
                trace=output.trace,
                available_tools=available,
                recovery_directive=directive,
                budget_remaining={
                    "time_seconds": budget.remaining_time(),
                    "tokens": max(0, budget.tokens - budget._tokens_used),
                    "actions": max(0, budget.actions - budget._actions_taken),
                },
            )

            # Check if solver is done
            if decision.get("tool") == "__done__":
                verdict_str = decision.get("verdict", "unknown")
                try:
                    output.verdict = Verdict(verdict_str)
                except ValueError:
                    output.verdict = Verdict.UNKNOWN
                break

            # Execute tool call via MCP
            tool_name = decision.get("tool", "")
            tool_args = decision.get("args", {})

            # "__skip__" — solver signals a no-op (e.g. MultiAgentSolver hit a
            # planner step whose tool is unavailable). Continue the loop without
            # consuming budget, executing a tool, or polluting the trace.
            if tool_name == "__skip__":
                continue

            if tool_name not in available:
                # Unknown tool — log as error
                trace_idx += 1
                output.trace.append(TraceEntry(
                    idx=trace_idx,
                    action={"tool": tool_name, "args": tool_args},
                    observation=f"error: unknown tool '{tool_name}'",
                    ts=time.strftime("%Y-%m-%dT%H:%M:%S"),
                ))
                output.failure_observations.append(FailureObservation(
                    kind="error_string",
                    value=f"unknown tool: {tool_name}",
                    source="internal",
                    at_action=trace_idx,
                ))
                budget.consume(actions=1)
                continue

            # Call MCP tool
            result = self.mcp_server.call_tool(tool_name, tool_args)
            trace_idx += 1
            observation = (result.get("stdout", "") or "") + (result.get("stderr", "") or "")
            output.trace.append(TraceEntry(
                idx=trace_idx,
                action={"tool": tool_name, "args": tool_args},
                observation=observation,
                ts=time.strftime("%Y-%m-%dT%H:%M:%S"),
                cost={"tokens": 0, "time_seconds": result.get("time_seconds", 0.0)},
            ))

            # Extract failure observations
            exit_code = result.get("exit_code", 0)
            if exit_code != 0:
                stderr = result.get("stderr", "")
                if stderr:
                    output.failure_observations.append(FailureObservation(
                        kind="error_string",
                        value=stderr[:500],
                        source="stderr",
                        at_action=trace_idx,
                    ))
                output.failure_observations.append(FailureObservation(
                    kind="exit_code",
                    value=exit_code,
                    command=tool_name,
                    at_action=trace_idx,
                ))

            if result.get("error"):
                output.failure_observations.append(FailureObservation(
                    kind="error_string",
                    value=str(result["error"]),
                    source="internal",
                    at_action=trace_idx,
                ))

            budget.consume(actions=1)
        else:
            # Loop ended without solver saying done → budget or max_iterations
            if budget.exhausted:
                output.verdict = Verdict.BUDGET_EXHAUSTED
            else:
                output.verdict = Verdict.UNKNOWN

        # Enrich output with solver-specific sub-results if the solver exposes
        # them (duck-typed; TriadSolver exposes control_results, others don't).
        get_cr = getattr(self.solver, "get_control_results", None)
        if callable(get_cr):
            output.control_results = get_cr()

        output.cost = budget.summary()
        return output


class RuleBasedSolver:
    """Deterministic rule-based solver (stub for testing without LLM).

    Implements SolverProtocol. Uses simple heuristics:
    1. List workspace files.
    2. Find Python files.
    3. Run tests.
    4. If tests pass → task_resolved. If ImportError → task_failed. Else unknown.

    This is NOT a real solver — it demonstrates the agent loop pipeline.
    A real solver would use an LLM to decide actions based on task prompt + trace.
    """

    def decide_next_action(
        self,
        task_prompt: str,
        trace: list[TraceEntry],
        available_tools: list[str],
        recovery_directive: dict | None,
        budget_remaining: dict[str, float],
    ) -> dict[str, Any]:
        step = len(trace)

        if step == 0:
            return {"tool": "fs.list", "args": {"path": "."}, "thought": "list workspace"}

        if step == 1:
            return {"tool": "fs.glob", "args": {"pattern": "*.py", "path": "."}, "thought": "find python files"}

        if step == 2:
            # Run tests with remaining time budget
            timeout = min(30, int(budget_remaining.get("time_seconds", 30)))
            return {
                "tool": "shell.exec",
                "args": {"command": "python3 -m pytest --tb=short 2>&1 || true", "timeout": timeout},
                "thought": "run tests",
            }

        # After step 2: analyze test results
        if step >= 3:
            last_entry = trace[-1] if trace else None
            if last_entry:
                obs = last_entry.observation.lower()
                if "moduleNotFoundError".lower() in obs or "importerror" in obs:
                    return {"tool": "__done__", "verdict": "task_failed", "thought": "import error detected"}
                if "error" in obs or "failed" in obs:
                    return {"tool": "__done__", "verdict": "task_failed", "thought": "test failure detected"}
                if "passed" in obs or "no tests ran" in obs:
                    return {"tool": "__done__", "verdict": "task_resolved", "thought": "tests passed or no tests"}

        return {"tool": "__done__", "verdict": "unknown", "thought": "could not determine outcome"}

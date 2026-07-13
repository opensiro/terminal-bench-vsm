"""solver — minimal S1 solver that uses MCP tools to solve coding tasks.

This is a placeholder solver: it reads the task prompt, attempts basic actions
via MCP tools (shell.exec, fs.read), and returns a verdict. A real solver would
use an LLM agent loop; this stub demonstrates the trace/observation pipeline.

Stateless (CONTRACT §5): no state between invocations.
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from .types import S1Input, S1Output, TraceEntry, FailureObservation, Verdict
from .budget import BudgetTracker


def solve(input: S1Input, mcp_server, budget: BudgetTracker) -> S1Output:
    """Run solver on task. Uses MCP tools. Returns S1Output with trace + verdict.

    This is a minimal stub: real implementation would use an LLM agent loop.
    """
    output = S1Output()
    trace_idx = 0

    def log_tool(tool: str, args: dict, result: dict):
        nonlocal trace_idx
        trace_idx += 1
        output.trace.append(TraceEntry(
            idx=trace_idx,
            action={"tool": tool, "args": args},
            observation=result.get("stdout", "") + result.get("stderr", ""),
            ts=time.strftime("%Y-%m-%dT%H:%M:%S"),
            cost={"tokens": 0, "time_seconds": result.get("time_seconds", 0.0)},
        ))
        # Extract failure observations
        if result.get("exit_code", 0) != 0:
            stderr = result.get("stderr", "")
            if stderr:
                output.failure_observations.append(FailureObservation(
                    kind="error_string", value=stderr[:500], source="stderr", at_action=trace_idx,
                ))
            output.failure_observations.append(FailureObservation(
                kind="exit_code", value=result["exit_code"], command=tool, at_action=trace_idx,
            ))
        budget.consume(actions=1)

    # Step 1: list workspace
    if budget.exhausted:
        output.verdict = Verdict.BUDGET_EXHAUSTED
        return output
    result = mcp_server.call_tool("fs.list", {"path": "."})
    log_tool("fs.list", {"path": "."}, result)

    # Step 2: try to find and read task-related files
    if budget.exhausted:
        output.verdict = Verdict.BUDGET_EXHAUSTED
        return output
    result = mcp_server.call_tool("fs.glob", {"pattern": "*.py", "path": "."})
    log_tool("fs.glob", {"pattern": "*.py"}, result)

    # Step 3: run tests if present
    if budget.exhausted:
        output.verdict = Verdict.BUDGET_EXHAUSTED
        return output
    result = mcp_server.call_tool("shell.exec", {"command": "python3 -m pytest --tb=short 2>&1 || true", "timeout": min(30, int(budget.remaining_time()))})
    log_tool("shell.exec", {"command": "pytest"}, result)

    # Determine verdict based on observations
    if not output.failure_observations:
        output.verdict = Verdict.TASK_RESOLVED
    elif any("ModuleNotFoundError" in str(o.value) or "ImportError" in str(o.value)
             for o in output.failure_observations):
        output.verdict = Verdict.TASK_FAILED
    elif any(o.kind == "exit_code" and o.value != 0 for o in output.failure_observations):
        output.verdict = Verdict.TASK_FAILED
    else:
        output.verdict = Verdict.UNKNOWN

    output.cost = budget.summary()
    return output

# `src/runtime/` — s1-dispatcher runtime (T2 CONTRACT implementation)

> S1 stateless runtime: launch → isolate → trace → collect output.
> Budget enforcement (time/tokens/actions). Trace collection. Failure observations.
> Artifacts diff. General-purpose (не привязан к конкретному оценочному набору).

## Modules

- `types.py` — S1 input/output contracts (CONTRACT §2, §3). Verdict, Budget,
  RecoveryDirective, TraceEntry, FailureObservation, Artifact.
- `budget.py` — BudgetTracker: time/tokens/actions enforcement.
- `artifacts.py` — filesystem snapshot + diff (CONTRACT §3 artifacts).
- `solver.py` — minimal S1 solver (stub: uses MCP tools, LLM agent loop = future).
- `dispatcher.py` — S1Dispatcher.invoke(): one invocation lifecycle (CONTRACT §4).

## Usage

```python
import sys; sys.path.insert(0, 'src')
from runtime.types import S1Input, Budget
from runtime.dispatcher import invoke

input = S1Input(
    task_prompt="Fix the failing test in utils.py",
    workspace=Path("/path/to/workspace"),
    budget=Budget(time_seconds=300, tokens=100000, actions=50),
)
output = invoke(input)
print(output.verdict)          # task_resolved | task_failed | budget_exhausted | unknown
print(len(output.trace))       # number of tool calls
print(output.failure_observations)  # for S3-classifier
```

## Stateless (CONTRACT §5)

Each invoke() is independent. No state stored between invocations. The only
channel for retry info is `recovery_directive` in input (which class to expect,
what env changed). S1 does not receive trace/artifacts from previous attempts.

## Dependencies

- `mcp_server` (T4) — tool surface. S1 calls tools via MCP.
- `recovery_policies` (T3) — recovery executor applies policy to env before retry.
- `failure_taxonomy` (T1) — S3-classifier matches observations to classes.

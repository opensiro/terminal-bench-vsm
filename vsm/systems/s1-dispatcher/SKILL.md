# S1 — dispatcher (child) · SKILL

## Tool scope

- **Read**:
  - `vsm.yaml → system_1` (purpose, owner_agent).
  - [`../../../src/failure_taxonomy.yaml`](../../../src/failure_taxonomy.yaml) — for the
    `failure_observations` format (which `signals` S3 will match; you do not classify,
    but you return observations in the format the taxonomy describes).
  - `state/{status,heartbeat}.json` (to record your own state).
  - `state/maturation.json` (to learn the Phase — whether S2/S3 are active for the retry cycle).
- **Write**:
  - `state/status.json → systems[S1]` (summary + current_task).
  - `state/heartbeat.json → S1.last_run`.
  - Trace run artifacts (location — future runtime; currently `state/runs/` or
    an external artifact store, decided at runtime phase).
- **Do not mutate**: `../../vsmlite-tb/` (parent), `../src/` outside the task-scoped
  workspace (run isolation).

## Canonical sources

- [`CONTRACT.md`](CONTRACT.md) — the interface (input/output/lifecycle/retry semantics).
  This is the **primary** source: any question "what does S1 accept/return" → go there.
- `vsm.yaml → system_1` — operational unit registry (`solver`, `../src`).
- `../src/failure_taxonomy.yaml` — failure classes + `signals` (what S3 matches).

## Protocol (one invocation)

1. **Read** the input (see [CONTRACT.md §2](CONTRACT.md)).
2. **Validate** the contract:
   - `task.prompt` is non-empty.
   - `budget` is valid (all three fields > 0).
   - If `recovery_directive ≠ null` — Phase ≥ 3 (otherwise there is no retry cycle;
     treat as a first attempt). `recovery_directive` conveys: which failure class to
     expect, which policy was applied, what changed in the env, the policy attempt number.
3. **Snapshot** the filesystem/git in the workspace (for the artifacts diff on output).
4. **Launch the solver** in the task-scoped environment, under budget, with the tool
   surface from `tools` (MCP — T4). Trace every tool call.
5. **Stop** when: the solver produces a verdict OR the budget is exhausted (time/tokens/actions).
6. **Collect output**: trace + verdict (`task_resolved` | `task_failed` |
   `budget_exhausted` | `unknown`) + artifacts diff + `failure_observations`
   (always full — [CONTRACT.md §6](CONTRACT.md)) + cost.
7. **Return** the output. A retry (if applicable and S3 is active) is shaped by the next
   input — not by you; you only return observations, S3/S2 take it from there.

## Stateless (see CONTRACT.md §5)

You do not store state between invocations. Each run is a fresh start. The previous
trace/artifacts are not carried over; the only "this is a retry" signal is
`recovery_directive` in the input.

## Canonical tools (future runtime)

- Tool surface — MCP server (T4, `tools.config_ref` in input).
- Budget enforcement — runtime timer/counter (details at runtime phase).
- Trace collection — built into the tool-call layer (observability — T4).

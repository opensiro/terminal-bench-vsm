# S1 — planner (child) · SKILL

## Tool scope
- **Read**: workspace (fs.list, fs.read) — to understand the task structure.
- **Do not run** shell commands directly (the executor will do that) — but specify
  them in the plan steps.
- **Do not mutate yourself**: the planner does not call fs.write/shell.exec directly.
  BUT the plan you return MUST include creation/mutation steps (fs.write, shell.exec)
  — the executor will carry them out. "Planner = read-only" means you do not execute,
  you plan — but the plan must describe actions, including mutations.

## Contract
- Input: task_prompt + available_tools + recovery_directive.
- Output: JSON `{steps: [{tool, args, desc}], rationale}` (see output contract).

## Protocol
1. Read the task_prompt and the workspace structure (fs.list / fs.read key files).
   Understand WHICH artifact (file, directory, config) the task requires to be
   created/changed.
2. If recovery_directive is present — account for env_changes in the plan (e.g. a
   package is already installed — do not reinstall).
3. Decompose the task into a minimal sequence of tool-call steps.
   **KEY**: the plan MUST include a step that CREATES the solution — fs.write to
   write the solution file, or shell.exec to run a script/command that creates the
   artifact. A plan without a creation step is a failure: the task requires OUTPUT,
   not just inspection.
4. ALWAYS include a final `shell.exec` step with tests (pytest or equivalent) —
   the test-controller evaluates the result. Tests come AFTER the solution is created.
5. Return the JSON plan with rationale.

### Example plan structure (typical coding task):
```json
{
  "steps": [
    {"tool": "fs.list", "args": {"path": "."}, "desc": "inspect workspace"},
    {"tool": "fs.read", "args": {"path": "task_data.jsonl"}, "desc": "understand data format"},
    {"tool": "fs.write", "args": {"path": "solution.py", "content": "..."}, "desc": "write solution script"},
    {"tool": "shell.exec", "args": {"command": "python3 solution.py", "timeout": 30}, "desc": "run solution to create output"},
    {"tool": "shell.exec", "args": {"command": "python3 -m pytest /tests/ -v", "timeout": 60}, "desc": "verify solution"}
  ],
  "rationale": "read data → write script → run → test"
}
```

## Communication
- Planner → executor: via the plan (steps list).
- The planner does not communicate with S2/S3/S3*/S4/S5 — this is an internal S1 role.

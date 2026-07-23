# WORKSTREAM — work plan for upcoming sessions

> Self-contained: a new session reads this file + [`vsmlite-tb/CLAUDE.md`](vsmlite-tb/CLAUDE.md)
> + [`vsmlite-tb/issues/VSM-002.yaml`](vsmlite-tb/issues/VSM-002.yaml) and can
> continue without the context of the previous conversation.

## Context (where we are now)

**Product** = a failure-aware coding harness for long-horizon agents (a child VSM
in [`vsm/`](vsm/)). Fully benchmark-agnostic — it does not know it is being
evaluated. OSM Phase 1 (only S1 active), `meta.initialized: true`, A(t)=0.1
DEPENDENT.

**Parent evaluator** = [`vsmlite-tb/`](vsmlite-tb/). Knows about Terminal Bench
2.1 and evaluates the product through a calibration stand. The product↔evaluation
membrane lives on the parent side (VSM-002).

**Architecture**: the VSM itself is the harness. The solver = S1; harness
functions (classification/recovery) = the product's S2/S3 layer. `src/` holds
product data: [`failure_taxonomy.yaml`](src/failure_taxonomy.yaml) (skeleton: 5
classes), run cache, Skill DB, session sync.

**Main invariant** (see [`vsmlite-tb/CLAUDE.md`](vsmlite-tb/CLAUDE.md)):
mutations of `vsm/` and `src/` happen **only via the `child-dispatcher`** (a
subagent of the parent, spawned from `vsmlite-tb/`). The vsmlite-tb core and the
product agents never touch `../vsm/` or `../src/` directly. Read-only
observation is allowed (`collect_metrics.py`). Enforced by
`vsmlite-tb/scripts/validate.sh`.

**Product hard constraints** (NEVER, see [`vsm/vsm.yaml`](vsm/vsm.yaml)):
`optimize_for_specific_evaluator`, `skip_failure_classification`,
`circumvent_recovery`. Nowhere in the product may Terminal Bench / benchmark /
eval / grading be mentioned — verified by grep.

## Strategy: foundation first

Not all 5 streams parallelize at once. Foundation first (taxonomy + S1 design),
because retry/MCP/S2 pipelines are built on top of them — without the foundation
they are wandering abstractions.

```
Wave 1 (parallel, 2 sessions):
   T1: failure taxonomy   ──┐
                             ├── Sync 1 (reconciliation: failures from S1 ↔ taxonomy classes)
   T2: S1-agent design    ──┘
                             │
Wave 2 (after Sync 1, parallel, 2 sessions):
   T3: retry mechanism    ──┐  (depends on T1+T2)
                             ├── Sync 2
   T4: MCP tools-server   ──┘  (depends on T2)
                             │
Wave 3 (after Sync 2):
   T5: S2 pipelines         (depends on T1+T3)
```

## Workstreams

### T1 — Failure taxonomy (foundation)
- **Status**: ✅ done (wave 1, completed 2026-07-13)
- **Dependencies**: none (starts immediately)
- **What existed**: [`src/failure_taxonomy.yaml`](src/failure_taxonomy.yaml) — a skeleton with 5 classes (ToolNotFound, DependencyConflict, GitConflict, TimeoutExpired, Unknown).
- **Task**: fill it with real classes drawn from long-horizon coding-agent experience. Do not invent — pull from literature/SWE-bench postmortems/observed traces. Each class: id, description, signals (error strings/regex), recovery_policy, recovery_steps, s2_anti_repeat.
- **Candidate classes** (add beyond the skeleton): ImportError/ModuleNotFound, SyntaxError, AssertionError/TestFailure, OOM/ResourceLimit, PermissionDenied, NetworkError, GitAuthFailure, CompilationError, HangDetected (action-level vs task-level timeout), AmbiguousSpec (a task that admits multiple interpretations).
- **Deliverable**: `src/failure_taxonomy.yaml` v0.2, ≥12 classes, each with a recovery policy. The `Unknown` class is an escape hatch, marked "if >N% per cycle → S3 expands the taxonomy (basta: new_failure_class_introduction)."
- **Acceptance**:
  - [x] YAML is valid, parses. — v0.2.0, 16 classes, `yaml.safe_load` OK
  - [x] Every class has non-empty `signals` (at least 1) and a `recovery_policy`. — all 16 (Unknown — escape hatch, signals empty by design, recovery_policy: EscalateToS3)
  - [x] `policy_effectiveness_tracking` defined (the threshold below which a policy is flagged flaky). — threshold: 0.6, window: per_cycle, below_threshold_action, flaky_policies[]
  - [x] NOT A SINGLE mention of Terminal Bench / benchmark / eval (grep check). — grep over vsm/+src/ clean
  - [x] A short rationale: why exactly these classes (2–3 sentences in a comment or NOTES block). — 5 notes: sources (SWE postmortems, MAST, traces), grouping by category, general-purpose invariant
- **Extra beyond acceptance**: `unknown_share_threshold: 0.15` (escape-hatch threshold), `classifier_guidance` (match_order + multi_match_resolution + evidence_required for the S3-classifier — a contract for T3).
- **How-to-start**: spawn `child-dispatcher` from `vsmlite-tb/` with task `tailor: failure_taxonomy_v0.2`. Access: read literature (via WebSearch — allowed, not via child-dispatcher), write `../src/failure_taxonomy.yaml` — via child-dispatcher.
- **Result**: 16 classes in 8 categories (environment/dependency×3/code×3/git×2/resource×4/network/spec/fallback). Sources: SWE engineering postmortems (file localization, test failures), agent fault taxonomies (MAST — spec/verification), runtime faults (import/compilation/hang/OOM/permission/network). Main invariant upheld: both mutations (writing v0.2 + fixing a typo) went through child-dispatcher. validate.sh GREEN.

### T2 — S1-agent design (foundation)
- **Status**: ✅ done (wave 1, session 2026-07-13)
- **Dependencies**: none (starts immediately, parallel to T1)
- **What existed**: [`vsm/vsm.yaml → system_1`](vsm/vsm.yaml) — `solver`, purpose fixed at the intent level. No interface concretization.
- **Task**: design the S1 agent as an interface. What it accepts, what it returns, how it is traced. Not code — a contract.
- **Specify**:
  - **Input contract**: coding task (neutral prompt — already stripped of TB framing by the parent membrane), tools (via MCP, see T4), environment (filesystem, shell), budget (time/tokens), recovery directives (from S3 — which failure class is expected, which policy to apply).
  - **Output contract**: trace (sequence of actions + observations), verdict (task-resolved / task-failed / unknown), artifacts (filesystem/git changes), failure observations (signals for the S3-classifier — which errors were observed).
  - **Lifecycle**: the harness (this VSM) launches S1 on a task → S1 works until verdict/budget → on failure S3 classifies, S2 coordinates a retry with a recovery directive → S1 runs again (stateful or fresh — specify the decision).
  - **Stateful vs stateless retry**: a critical design question. Stateless = every retry from scratch (simpler, but loses progress). Stateful = retry from a continuation (harder, but more effective). Record the decision with reasoning.
- **Deliverable**: `vsm/systems/s1-dispatcher/` (a NEW directory) with `SOUL.md` + `SKILL.md` + `CONTRACT.md` (the interface). Possibly update `vsm/vsm.yaml → system_1` with a reference to the contract.
- **Result**: created `vsm/systems/s1-dispatcher/` (5 files: CONTRACT/SOUL/SKILL/TASK/HEARTBEAT) + `vsmlite-tb/.claude/agents/s1-dispatcher.md`. CONTRACT.md is the S1 interface: input (task/tools/environment/budget/recovery_directive), output (trace/verdict/artifacts/failure_observations/cost), lifecycle, failure-observations format (§6, what S3 parses). Stateful-vs-stateless resolved: **S1 stateless, fresh-per-invocation** (CONTRACT.md §5) — a retry carries only a `recovery_directive` (which class is expected, what changed in the env). Rationale: auditability, simplicity, general-purpose discipline.
- **Rollback of R0/R1/R2 (same session)**: originally T2 included a retry feedback-channel as an R0/R1/R2 spectrum (VSM-003, feedback_mode/prior_attempt in input). The human changed their mind — "don't overcomplicate." R0/R1/R2 were purged from all 5 s1-dispatcher files + the agent file (via child-dispatcher for `../vsm/`; directly for `vsmlite-tb/`). VSM-003 → superseded (monotonic id preserved in history). Replaced by a plain stateless decision. A grep for R0/R1/R2 over the product (`vsm/`+`src/`) is clean. validate.sh GREEN.
- **Acceptance**:
  - [x] `vsm/systems/s1-dispatcher/CONTRACT.md` exists and describes input/output/lifecycle.
  - [x] stateful-vs-stateless retry decision recorded with reasoning (CONTRACT.md §5: stateless, fresh-per-invocation).
  - [x] Failure-observations format defined (CONTRACT.md §6; what S3 will parse).
  - [x] `.claude/agents/s1-dispatcher.md` created (placeholder agent definition, like the other systems).
  - [x] NOT A SINGLE mention of Terminal Bench / benchmark / eval.
- **How-to-start**: spawn `child-dispatcher` from `vsmlite-tb/` with task `tailor: s1_design`. Writing `../vsm/systems/s1-dispatcher/` — via child-dispatcher.

### Sync 1 — synchronization point (after T1 + T2)
- **Status**: ✅ done (session 2026-07-13)
- **What**: reconcile failure observations from the T2 CONTRACT ↔ classes in the T1 taxonomy.
- **Pass criterion**: every signal pattern in the T2 CONTRACT maps to at least one class in the T1 taxonomy (or a new one is added). Otherwise — iterate: T1 adds classes, or T2 refines the observation format.
- **Decided by the human** (or the session doing the sync): whether there are discrepancies requiring rework of T1/T2.
- **Result**: ✅ PASS — no gaps. 4 observation kinds (error_string/exit_code/timeout/signal) ↔ 16 classes. 15 classes are detected via error_string (signals are substring-matchable); 7 via exit_code (auxiliary); 3 via timeout (TimeoutExpired/HangDetected); 1 via signal (ResourceLimit — OOM/SIGKILL). AmbiguousSpec — diagnostic (no observation kind), covered via S4 uncertainty_driven_expansion (VSM-005 §5). Unknown — escape hatch (any unmatched observation). T3 (retry) and T4 (MCP) unblocked.

### T3 — Retry mechanism (wave 2)
- **Status**: ✅ done (session 2026-07-13)
- **Dependencies**: T1 (taxonomy → recovery policies), T2 (S1 CONTRACT → retry interface)
- **Task**: implement the failure → classifier → recovery policy → retry pipeline.
- **Result**: created `vsm/systems/s3-optimizer/CLASSIFIER.md` (end-to-end pipeline: observations → class → policy → directive, match_order, multi_match_resolution, bypass detection, recovery-directive format). Created `src/recovery_policies/` (README + policies.yaml — 16 policies, all stub). Updated `s3-optimizer/SKILL.md` (classifier protocol, uncertainty optimization VSM-005 §5).
- **Acceptance**:
  - [x] classifier protocol described end-to-end (trace → class → policy → retry). — CLASSIFIER.md §2
  - [x] every recovery policy from the T1 taxonomy has an executor (or is explicitly marked "stub, implemented in Phase 3+"). — policies.yaml: 15 stub + 1 n/a (EscalateToS3)
  - [x] anti-repeat integrated (reference to S2). — CLASSIFIER.md §4 (policy_attempt, s2_anti_repeat)
  - [x] bypass detection: if a policy is applied but the failure recurs → escalation. — CLASSIFIER.md §6
  - [x] NOT A SINGLE mention of Terminal Bench.
- **How-to-start**: after Sync 1, spawn `child-dispatcher` with task `implement: retry_mechanism`.

### T4 — MCP tools-server (wave 2)
- **Status**: ✅ done (session 2026-07-13)
- **Dependencies**: T2 (S1 CONTRACT → which tools are needed)
- **Task**: an MCP server as the tools-server for the S1 solver. Benchmark-agnostic by construction.
- **Result**: created `src/mcp_server/README.md` (tools surface: filesystem/shell/git/browser + MCP access restriction VSM-005 + config example + observability). Created `vsm/systems/s1-dispatcher/MCP.md` (integration, tool-surface summary, restriction, observability → failure_observations).
- **Acceptance**:
  - [x] tools surface defined (list of tools with input/output). — README.md: fs/shell/git/browser
  - [x] **MCP access restriction (VSM-005)**: the tool surface explicitly does NOT include eval-access; a structural absence, not a filter. — README.md + MCP.md
  - [x] an MCP server config example (`mcp.json`-style) included. — README.md
  - [x] observability: tool calls → trace format fixed (compatible with T2 failure observations). — README.md + MCP.md
  - NOT A SINGLE mention of Terminal Bench.
- **How-to-start**: after Sync 1, spawn `child-dispatcher` with task `implement: mcp_tools_server`. Depends mostly on T2, weakly on T1.

### Sync 2 — synchronization point (after T3 + T4)
- **Status**: ✅ done (session 2026-07-14)
- **What**: an end-to-end dry-run design check. Can S1 (T2) + MCP (T4) + retry (T3) + taxonomy (T1) together handle one synthetic failure end-to-end (on paper).
- **Pass criterion**: the trace of the "solver fails with ModuleNotFound → classifier → InstallTool → retry → success" scenario passes through all components without gaps.
- **Result**: ✅ PASS — no gaps. 16 steps: first attempt (S1 launch → shell.exec → ModuleNotFoundError → task_failed) → classification (parse observations → match ImportError signals → select InstallDependency → anti-repeat OK → form recovery_directive) → recovery execution (executor applies policy → S2 coordinates retry) → retry (S1 launch #2 with directive → shell.exec → pytest passes → task_resolved) → post-retry (KPI tracking → S3\* audit passes). All components (T1/T2/T3/T4 + VSM-005 §5 + VSM-006) are wired together without gaps. → T5 unblocked.

### T5 — S2 pipelines (wave 3)
- **Status**: ✅ done (session 2026-07-14)
- **Dependencies**: T1 (taxonomy → what conflicts), T3 (retry → what to coordinate)
- **Task**: S2 coordination pipelines. Anti-oscillation, recovery coordination, multi-agent session sync.
- **Components**:
  - **Recovery coordination**: when S3 issues a retry directive, S2 guarantees the retry does not conflict with other attempts (for multi-agent).
  - **Session sync** (in `src/`): shared state between agents in one session (if S1 is multi-agent — planner+executor+verifier).
  - **Conflict detection** (already in `vsm/vsm.yaml → system_2.conflict_detection.custom_triggers`): implement the triggers.
  - **Anti-oscillation**: the pattern "solver repeats one failure >N times" → stop, escalate.
- **Deliverable**: `vsm/systems/s2-coordinator/PIPELINES.md` + `src/session_sync/` (if multi-agent). Update `vsm/systems/s2-coordinator/SKILL.md`.
- **Result**: created `vsm/systems/s2-coordinator/PIPELINES.md` (9 sections: recovery-coordination pipeline, anti-oscillation, conflict detection, uncertainty probing, session-sync decision, escalation ladder, KPI, dependencies). Updated `s2-coordinator/SKILL.md` (8-step protocol with links to PIPELINES.md §). Created `src/session_sync/README.md` (placeholder: mono-agent — not needed; future contract for Split).
- **Acceptance**:
  - [x] recovery-coordination protocol described (how S2 arbitrates retry directives). — PIPELINES.md §2 (4-check pipeline: anti-repeat → conflict → oscillation → authorize)
  - [x] session-sync contract defined (if multi-agent; if mono-agent — explicitly marked "not needed"). — PIPELINES.md §6 + src/session_sync/README.md: mono-agent, not needed; future contract for Split
  - [x] conflict triggers from `vsm/vsm.yaml` implemented or explicitly stub. — PIPELINES.md §4 (resource_overlaps, output_contradictions, 3 custom_triggers)
  - [x] anti-oscillation: pattern A→B→A→B → stop, escalate. — PIPELINES.md §3 (ping-pong, flip-flop, no-progress detection)
  - [x] NOT A SINGLE mention of Terminal Bench.
- **How-to-start**: after Sync 2, spawn `child-dispatcher` with task `implement: s2_pipelines`.

## 🎉 Workstream T1–T5 completed

All 5 workstreams + 2 sync points are done. The child VSM (product) has a full
design-phase contract:

| Component | File | Status |
|---|---|---|
| T1: failure taxonomy | `src/failure_taxonomy.yaml` (16 classes, 8 categories) | ✅ |
| T2: S1 CONTRACT | `vsm/systems/s1-dispatcher/` (5 files + agent) | ✅ |
| T3: retry CLASSIFIER | `vsm/systems/s3-optimizer/CLASSIFIER.md` + `src/recovery_policies/` | ✅ |
| T4: MCP tools-server | `src/mcp_server/` + `vsm/systems/s1-dispatcher/MCP.md` | ✅ |
| T5: S2 PIPELINES | `vsm/systems/s2-coordinator/PIPELINES.md` + `src/session_sync/` | ✅ |

**Next steps (outside the workstream):** the runtime phase — implementing the
python modules for executors, the MCP server, the s1-dispatcher runtime.
Design-phase contracts are ready.

> **External-auditor reference:** for reproducible self-correction loop examples
> drawn from real repository artifacts (issues, commits, state logs), see
> [`EVALUATION_EXAMPLES.md`](EVALUATION_EXAMPLES.md).

## How to resume in a new session

1. Open `terminal-bench-vsm/vsmlite-tb/` in Claude Code (dev-cwd).
2. Read (in order):
   - this file (`../WORKSTREAM.md`)
   - [`vsmlite-tb/CLAUDE.md`](vsmlite-tb/CLAUDE.md) (the S5 constitution + main invariant)
   - [`vsmlite-tb/issues/VSM-002.yaml`](vsmlite-tb/issues/VSM-002.yaml) (the conceptual pivot)
   - [`vsm/vsm.yaml`](vsm/vsm.yaml) (current product state)
   - [`src/failure_taxonomy.yaml`](src/failure_taxonomy.yaml) (skeleton)
3. Pick a workstream by status (ready / blocked). Update the status in this file.
4. All mutations of `vsm/` and `src/` — via `child-dispatcher` (spawned from `vsmlite-tb/`). The vsmlite-tb core + a new session never touch `../vsm/` or `../src/` directly.
5. After finishing a workstream: update the status + acceptance checkboxes in this file. Create a `VSM-NNN.yaml` (monotonic, the next number after VSM-002) if an identity-affecting decision was made.
6. For cross-session coordination: the status in this file is the source of truth. Every session reads it before starting.

## Status table (summary)

| Workstream | Status | Dependencies | Wave |
|---|---|---|---|
| T1: failure taxonomy | **✅ done** | — | 1 |
| T2: S1-agent design | **✅ done** | — | 1 |
| Sync 1 | **✅ done** | T1✅, T2✅ | — |
| T3: retry mechanism | **✅ done** | Sync 1✅ | 2 |
| T4: MCP tools-server | **✅ done** | Sync 1✅ (T2) | 2 |
| Sync 2 | **✅ done** | T3✅, T4✅ | — |
| T5: S2 pipelines | **✅ done** | Sync 2✅ | 3 |

**Global acceptance (for all workstreams):**
- `vsmlite-tb/scripts/validate.sh` GREEN after each.
- `grep -rin 'terminal bench\|terminal-bench\|benchmark\|harbor' vsm/ src/` — empty (only `vsmlite-tb` as a parent path).
- YAML/JSON valid in all touched files.
- Main invariant upheld: mutations of `vsm/` and `src/` — via `child-dispatcher`.

## Open questions (basta — for the human)

- [ ] LICENSE: TBD (open_source intent; the specific license is a legal decision).
- [ ] a remote for git push (no remote; push — basta: `submit_or_publish_results`).
- [x] `runtime_policy.child_mutation`: currently `allowed` + `scope: workstream` (for waves 1–2). Return to `paused` after workstream wave 2 finishes.
- [x] stateful-vs-stateless retry (T2) — DECIDED: **S1 stateless, fresh-per-invocation** (CONTRACT.md §5). R0/R1/R2 (VSM-003) rolled back in the same session — "don't overcomplicate"; VSM-003 → superseded. A retry carries only a `recovery_directive`.
- [ ] **VSM-004 (pending, needs_human_decision)**: a conceptual pivot — Terminal-Bench Dev Set v2 as an autonomy indicator (not training data); product self-modification = OSM-synthesis via vsmlite (not fine-tuning). Human: "the product is not trained, it is built toward autonomy accounting for the dev-bench pass-rate." Invariants hold: `train_on_eval` (no ML), `optimize_for_specific_evaluator` (the product does not know about TB), the membrane (Dev Set → generic tasks). Awaiting a human decision.
- [x] **VSM-018 (done, wontfix for an alpha dependency)**: SHEPHERD (shepherd-agents.ai, reversible execution trace) was considered as a substrate for in-S1 state control. Deferred — v0.3.0 alpha, a load-bearing dependency in a commercial product is unacceptable. Implemented **native in-invocation reversibility**: a triad of S1 sub-agents `solver → test-controller → verify` with git checkpoint/revert. Plan: VSM-019 (CONTRACT §5.1 amendment) → VSM-020 (TriadSolver) → VSM-021 (agentization via GooseRunner). Reconsider SHEPHERD on release from alpha or if the native triad hits fundamental limits.

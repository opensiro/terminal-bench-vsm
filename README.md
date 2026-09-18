# terminal-bench-vsm

> **Product = a failure-aware coding harness.** This monorepo contains the
> product (`vsm/` + `src/`) and its calibration stand / evaluation layer
> (`vsmlite-tb/`). The product is benchmark-agnostic: it does not know it is
> being evaluated. The calibration stand is currently Terminal Bench 2.1, but is
> interchangeable (it could be SWE-bench, or a real ticket stream).

## Working on OpenSiro?

Repository-local work stays here.

For contributor roles, authority, escalation, cross-repository coordination, or organizational evolution across public OpenSiro projects, start at [`opensiro/vsm-oss-organization/CONTRIBUTOR_START.md`](https://github.com/opensiro/vsm-oss-organization/blob/main/CONTRIBUTOR_START.md).

Following that route does not make this experimental repository part of the bounded VSM Harness S1 plane. Also note that this repository is publicly readable but its license is currently TBD; public availability must not be confused with an open-source license.

## Architecture: product ↔ evaluator

```
┌──────────────────────────────────────────────────────────────────┐
│  vsmlite-tb/  — PARENT = evaluation/growing layer                │  ← KNOWS about TB
│  mission: grow the product and evaluate it via Terminal Bench      │     (this is the "stand")
│  S3: pass_rate / coverage per TB category                          │
│  S4: TB evolution (when the version changes — basta)               │
│  S5: evaluator identity + membrane (transduction at the boundary)  │
│  hard constraints: train_on_eval, use_harbor_tb2,                  │
│    leak_evaluation_context_to_product                              │
└──────────────────────┬───────────────────────────────────────────┘
                       │ product↔evaluation membrane (VSM-002)
                       │ TB task → generic coding task (TB framing is stripped)
┌──────────────────────▼───────────────────────────────────────────┐
│  vsm/  — PRODUCT (child VSM = failure-aware coding harness)      │  ← DOES NOT know about TB
│  mission: a viable coding harness for long-horizon agents           │     (at all)
│  S1: solver (launched by the harness = this VSM)                    │
│  S2: recovery coordination (anti-repetition of identical failures)  │
│  S3: failure classifier → recovery policy → retry                   │
│  S3*: independent recovery audit                                    │
│  S4: coding patterns / recovery-policy expansions (internet)        │
│  S5: product identity (general-purpose, not optimized for a         │
│      specific evaluation set)                                       │
│  KPI: failure_recovery_rate, retry_efficiency,                      │
│       policy_effectiveness, classifier_precision                    │
└──────────────────────┬───────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────────┐
│  src/  — product data and infrastructure                           │  ← DOES NOT know about TB
│  - failure_taxonomy.yaml — primary ontology (failure classes →     │
│    recovery policies: InstallTool / CreateFreshVenv /              │
│    ResetAndReplay / RetryWithSmallerScope / EscalateToS3)          │
│  - run cache: traces + verdicts (verdict — from the product)       │
│  - Skill DB: general-purpose coding patterns (populated by S4)     │
│  - session sync: coordination space for multi-agent runs           │
└──────────────────────────────────────────────────────────────────┘
```

**Evaluation principle (blinded).** The product (`vsm/` + `src/`) is fully
agnostic — it does not know about Terminal Bench in design-time, runtime, or
S5. Even the fact that it is being evaluated is hidden. This keeps the quality
measure honest: the product cannot optimize for the evaluation set. Knowledge
of TB lives only in `vsmlite-tb/` (the parent evaluator) and in this root
README.

## Two working-directory (cwd) modes

The structure is **portable**: no absolute-path hardcoding, only relative paths.

| Mode | cwd | Who works | What is visible |
|---|---|---|---|
| **dev** | `vsmlite-tb/` | human + Claude Code (product development/evaluation) | the whole monorepo structure; `/vsmlite-*` commands |
| **prod** | the evaluation stand's cwd (container) | the product (`vsm/`) as a harness for the solver | **only** the coding task + tools + environment; the TB structure is physically invisible (the membrane is reinforced by container isolation) |

In prod the product itself comes up as a harness for the solver (architecture:
VSM = harness, solver = S1). The evaluation stand feeds TB tasks through the
membrane; the product receives a generic coding task.

## Hard constraints (NEVER)

**In the product (`vsm/` + `src/`)** — product-level, unaware of TB:
- `optimize_for_specific_evaluator` — stay a general-purpose coding harness.
- `skip_failure_classification` — always failure → classifier → policy → retry (blind retry is forbidden).
- `circumvent_recovery` — do not repeat the same failure more than N times.

**In the evaluator (`vsmlite-tb/`)** — evaluation-stand constraints:
- `train_on_eval` — training on TB eval labels is forbidden by the benchmark rules.
- `use_harbor_tb2` — `github.com/harbor-framework/terminal-bench-2` is not used
  in any form (explicit requirement).
- `leak_evaluation_context_to_product` — do not leak knowledge of TB into the product.

## Basta (only the human decides)

- publishing / submitting results;
- changing the target TB version;
- deleting runs / data / logs;
- changing identity / values / never-do (of the product or the evaluator);
- adding a new failure class to the product's failure taxonomy.

## Quick start

```bash
# dev mode: open vsmlite-tb/ in Claude Code
cd vsmlite-tb/
# parent VSM (evaluator) commands:
#   /vsmlite-cycle    (full S2→S3→S3*→S4→S5 with a digest)
#   /vsmlite-check    (viability-check + invariant-grep)

# monitor (static HTML, no backend):
cd vsmlite-tb/monitor && python3 -m http.server 8765
#   → http://localhost:8765/            (product maturation / 4 signs of A(t))
#   → http://localhost:8765/issues.html  (VSM-NNN, incl. VSM-002 — the conceptual pivot)
```

## Evaluation artifacts

- **[EVALUATION_EXAMPLES.md](EVALUATION_EXAMPLES.md)** — three reproducible
  self-correction loops (VSM-037, VSM-039, VSM-034 TERTIARY-2) for an external
  auditor: each is backed by a real issue file, fix/merge commits, and a
  state-log entry. Shows how the system (GLM model + deterministic scripts)
  detects its own error, localizes the root cause, fixes it, and validates.

## License

**TBD.** Intent — open source. The specific license is a basta-decision of the
human (legal), not yet chosen. Until chosen: default — all rights reserved.

## History

`vsmlite-tb/` was originally a standalone git repository (a template, 5 commits);
the history is preserved in a git bundle. The conceptual evolution of the
product is visible in the commits: init → TB-bound → `refactor(product)`
(VSM-002) → a benchmark-agnostic failure-aware coding harness.

# Proof-of-Concept Logs

This file is **evidence for an external auditor**: a chronological record of what
the vsmlite-tb machinery has actually *done*, captured straight from runtime
state. Its purpose is to demonstrate that the maturation loop, the eval
pipeline, and the S1–S5/S3\* systems are wired together and functional — i.e.
that the template is a working proof of concept, not a static document.

> **Scope warning — read first.** The runs recorded here are **probe / smoke
> runs on 1–2 tasks per batch**, not full Terminal-Bench 2.1 leaderboard
> submissions (89 tasks). Pass-rates below are a *pipeline health signal*, not
> a frontier benchmark claim. For external baseline anchors, see
> [`public-report/`](public-report/). See [Caveats](#caveats).

All numbers below are derived from tracked files under `state/` and are
reproducible from them.

---

## What this proves — and what it does not

| ✅ Proves (pipeline integrity) | ❌ Does not claim (benchmark performance) |
|---|---|
| The maturation cycle runs end-to-end (REPL → digest → decision → execution → telemetry) | SOTA / frontier pass-rate on TB-2.1 |
| The eval pipeline executes TB tasks, scores them, and records structured metrics | Statistically meaningful pass-rate (n = 1–2 per batch) |
| S1–S5/S3\* systems emit events and issues autonomously | Full autonomy (A(t) is at 0.475 / 1.0 — `SEMI-AUTONOMOUS`) |
| Trend detection and regression/escalation paths fire correctly | Production-grade stability |

---

## Maturation cycle progression

15 maturation cycles were executed over **2026-07-16 → 2026-07-17**. Source:
[`state/cycle_history.json`](state/cycle_history.json).

| Cycle | Timestamp | Pass-rate | Autonomy A(t) | Verdict | Decision |
|------:|-----------|----------:|--------------:|---------|----------|
| 1  | 2026-07-16 00:06 | 0.333 | 0.475 | SEMI-AUTONOMOUS | ok_with_concerns (1 warning) |
| 2  | 2026-07-16 00:09 | 0.333 | 0.475 | SEMI-AUTONOMOUS | ok_with_concerns (1 warning) |
| 3  | 2026-07-16 00:43 | 0.000 | 0.175 | DEPENDENT | **needs_human_decision: regression** |
| 4–14 | 2026-07-16 01:16 → 2026-07-17 00:48 | 0.000 | 0.175 | DEPENDENT | ok_with_concerns (1–2 warnings) |
| 15 | 2026-07-17 01:08 | **1.000** | **0.475** | **SEMI-AUTONOMOUS** | **ok_no_action** |

**Notable:** cycle 3 correctly detected a **regression** (0.333 → 0.000) and
escalated to `needs_human_decision` — the algedonic (pain) channel works.
Autonomy tracks the four OSM signs (S5/S4/S3/S1 activity + eval) and recovered
to 0.475 once the eval sign met threshold in cycle 15.

---

## Eval runs

Two profiles were exercised. Sources: [`state/dev_metrics.json`](state/dev_metrics.json),
[`state/eval_test_metrics.json`](state/eval_test_metrics.json).

### `train` profile — TB Dev Set v2 (`open-thoughts/OpenThoughts-TB-dev-v2`)

| Field | Value |
|---|---|
| Harness | claude-code (`eval/`) |
| Tasks evaluated | 1 (geometry / medium) |
| Pass-rate | 0 / 1 (0%) |
| Agent duration | 453.9 s |
| Timed out | no |
| Generated | 2026-07-17 |

### `eval-test` profile — TB-2.1 verified (`zai-org/terminal-bench-2-verified`)

| Field | Value |
|---|---|
| Harness | claude-code (`eval/`) |
| Tasks evaluated | 1 (software-engineering / hard) |
| Pass-rate | 0 / 1 (0%) |
| Agent duration | 175.7 s |
| Timed out | no |
| Generated | 2026-07-15 |

---

## Batch progression (train profile)

Five training batches were run over **2026-07-16 21:25 → 2026-07-17 00:53**.
Source: [`state/batch_summaries/`](state/batch_summaries/).

| Batch (timestamp) | Tasks | Passed | Pass-rate | Trend | Wall-clock |
|---|---:|---:|---:|---|---:|
| train__20260716-212553 | 1 | 0 | 0% | none | 1058.4 s |
| train__20260716-221048 | 1 | 0 | 0% | none | — |
| train__20260716-235943 | 1 | 0 | 0% | none | — |
| train__20260717-004002 | 1 | 0 | 0% | none | — |
| train__20260717-005347 | 1 | 1 | **100%** | **up (+100%)** | 905.6 s |

**Notable:** the final batch flipped from 0% to 100% and the trend detector
emitted an `improvement` observation (`pass_rate 0.0% → 100.0%, delta +100.0%`).
The same detector emitted `zero_pass` warnings on the earlier batches — the
observation/diagnosis path is functioning in both directions.

---

## System activity (S1–S5 / S3\*)

The systems produced **32 structured events** over 2026-07-15 → 2026-07-17.
Source: [`state/events.json`](state/events.json).

| Event type | Count |
|---|---:|
| `cycle.completed` | 15 |
| `issue.changed` | 10 |
| `eval.run` | 3 |
| `autonomy.changed` | 2 |
| `autonomy.verdict` | 2 |

The issue (algedonic) channel grew to **39 records** (`VSM-001` … `VSM-039`)
over the same window — see [`issues/`](issues/).

Current system health snapshot (from [`state/status.json`](state/status.json),
2026-07-17 01:08):

| System | Health | Current task |
|---|---|---|
| S1 synthesis-operator | active | A(t)=0.475 (SEMI-AUTONOMOUS) |
| S2 s2-coordinator | healthy | no conflicts detected |
| S3 s3-optimizer | healthy | op signs: 1/4 meet |
| S3\* s3-star-auditor | healthy | idle (no findings) |
| S4 s4-scout | idle | scanning |
| S5 s5-guardian | healthy | prepare_only (basta) |

---

## Caveats

1. **Sample size.** Each batch above evaluates 1–2 tasks (`tasks_total`), not
   the full 89-task TB-2.1 set. Per-task durations and the single 100% batch
   reflect pipeline behavior, not model capability. Do not cite these as
   benchmark results.
2. **`task_id` aliasing.** Several probe runs record `task_id: "task"` rather
   than a distinct TB identifier — an artifact of the smoke harness used during
   bring-up. It does not affect reward computation but limits per-task
   traceability until the full-dataset runner lands.
3. **Concurrency.** All runs used `workers: 1`. Wall-clock figures are
   sequential and not optimized.
4. **A(t) is a maturation index, not a pass-rate.** Autonomy 0.475 means
   "SEMI-AUTONOMOUS" under the OSM sign calculus (2 of 5 signs met), and is
   decoupled from the TB pass-rate. See [`public-report/vsm-baseline-0.0.1.md`](public-report/vsm-baseline-0.0.1.md)
   for the distinction.
5. **Full-dataset pass-rate is TBD.** The infra runner for the complete 89-task
   evaluation is tracked separately; the snapshot at
   [`public-report/vsm-baseline-0.0.1.md`](public-report/vsm-baseline-0.0.1.md)
   marks it as `verified-in-this-repo (structural snapshot)`.

---

## Reproducing

The raw evidence lives entirely in tracked `state/` files:

```
state/cycle_history.json        # 15-cycle progression table above
state/dev_metrics.json          # train-profile eval run
state/eval_test_metrics.json    # eval-test-profile eval run
state/batch_summaries/*.json    # 5 train batches
state/events.json               # 32 structured events
state/status.json               # system health snapshot
state/maturation.json           # OSM phase + A(t) signs
```

To regenerate a fresh run (requires local eval deps; datasets are public):

```bash
python3 -m eval.harbor_run --task <task_id>   # single task
# or via the slash command in a Claude Code session:
/vsmlite-eval
```

See [`eval/README.md`](eval/README.md) for the full eval pipeline reference.

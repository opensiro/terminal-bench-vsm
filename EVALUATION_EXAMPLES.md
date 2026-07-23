# Evaluation Examples — Self-Correction Loops

> **Purpose of this document.** Three reproducible self-correction loop examples
> from the `vsmlite-tb` system, drawn **exclusively from real repository
> artifacts** — git commits, issue files `issues/VSM-*.yaml`, and state logs
> `state/*.json`. There are no retouched chat transcripts below: every claim is
> backed by a clickable link to a file or commit.
>
> Goal: show an external auditor **exactly how** the system (the GLM model acting
> as the S1 synthesis-operator, plus infrastructure scripts) detects its own
> error, localizes the root cause, fixes it, and validates the fix.

---

## 0. How to read these examples

In the `vsmlite-tb` project, "the model" is not a single request to GLM. It is a
set of roles (VSM — Viable System Model). To keep the auditor oriented on who
does what:

| Role | Role in the loop | Who physically |
|------|------------------|----------------|
| **Human (S5 — architect)** | Sets the task, prepares the decision (`prepare_only`), never decides for the system | Repository operator |
| **S1 / synthesis-operator** | Analyzes diagnostics, formulates the root cause, writes the fix | **The GLM-5.2 model** |
| **S3\* — auditor** | Independent cross-provider integrity audit of the evaluation | A different model provider |
| **Infra scripts** (`scripts/true_verifier.py`, harbor tooling, TB `test.sh`) | Give **deterministic** feedback — reward, false-positive signature, `recovery_blocked` | Code without an LLM |

Key project principle (see `vsmlite-tb/CLAUDE.md`, invariant
`basta_constraint: prepare_only`): **the human prepares, the model executes.**
In the examples below it is explicitly marked where the feedback came from a
script (deterministic) and where from the model itself (a behavioral diagnosis).

The skeleton of the loop is the same in all three cases:

```
 task → model writes code/behavior
       → a script OR the model detects an anomaly
       → model localizes the root cause
       → model writes the fix (commit fix(eval): VSM-NNN)
       → model validates (acceptance criteria, live batch)
       → merge (commit merge: VSM-NNN)
```

---

## Example 1. VSM-039 — workspace probe breaks the artifact path

**Feedback type:** deterministic (the runner script emits `recovery_blocked`).
**Blast radius:** ~48% of train tasks (WORKDIR ≠ `/app`).

### Task (S5 → S1)
The model must run the product in the container's correct working directory, so
that artifacts the product creates via `fs.write` land where the plan's
`shell.exec` will later look for them.

### What the model produced before the fix (product behavior)
The product (goose-planner) correctly reads the task WORKDIR from the Dockerfile
and plans `fs.write path="/workdir/solution.py"`. But the overlay-executor runs
in workspace=`/app` due to a regression in `workspace_probe`:

```
fs.write /workdir/solution.py   → remapped to /app/solution.py   (file created — OK)
shell.exec "python3 /workdir/solution.py" → No such file
recovery_blocked: pattern 'solution.py' not found in /app
```

### How the error was detected
Not by a human. The trace landed in `product-trace.json` as
`terminated_by = no_observations`, and the recovery-runner printed an explicit
diagnostic: `recovery_blocked: pattern 'solution.py' not found in /app`. This
is precisely "the script gives the model feedback": the instrumentation itself
showed **where** the search failed to find the expected artifact (`/app`
instead of `/workdir`).

The model (S1) correlated this with two facts from the repository:

- `vsmlite-tb/eval/harbor_adapter.py:128-132` — `workspace_probe` iterates
  candidates in the order `[/app, /workdir, /workspace, /root]` and takes the
  **first one that exists**;
- the overlay Dockerfile runs `mkdir /app` **always** → `/app` always exists →
  always wins the probe, even when the task WORKDIR is `/workdir`.

### Root cause (verbatim from `vsmlite-tb/issues/VSM-039.yaml`)

> VSM-036 workspace_probe (harbor_adapter.py:128-132) checks /app first.
> VSM-036 overlay Dockerfile (harbor_run.py) runs `mkdir /app` always — so /app
> always exists and always wins the probe, even when the task
> WORKDIR=/workdir or /workspace.

### Fix (the model chose option P1 out of three)
`harbor_run._prepare_overlay_task` parses the last `WORKDIR` (after the final
`FROM`) from the task Dockerfile → `ENV TASK_WORKDIR=<path>` in the final-stage
overlay. `workspace_probe` checks `$TASK_WORKDIR` **first** (if set and exists),
falling back to the old list `[/app,/workdir,/workspace,/root]`.

### Validation (verbatim from `vsmlite-tb/issues/VSM-039.yaml`, `decision:` field)

> bracket-sequence-restoration (WORKDIR=/workdir) — PASS reward=1.0 (previously
> recovery_blocked: pattern not found in /app). broken-python (WORKDIR=/app) —
> PASS reward=1.0 (no regression).

### Artifacts to verify
- Issue: [`vsmlite-tb/issues/VSM-039.yaml`](vsmlite-tb/issues/VSM-039.yaml)
- Commits: `8581075` (docs) → `c515a3b` (fix) → `b65fcd0` (merge, 01:09:53 → 01:09:55, a 2-second gap)
- Chosen option: **P1** (Dockerfile WORKDIR parse); alternatives P2/P3 rejected with reasoning in the `proposal:` field

---

## Example 2. VSM-037 — false-positive PASS detected by a script across 251 trials

**Feedback type:** deterministic metric (post-trial attribution).
**Blast radius:** pass-rate inflated by **3.2 pp** (8.8% raw → 5.6% strict).

### Task (S1 → self)
Understand how honest the product's `pass-rate` metric is when the overlay layer
installs dependencies (pip, goose, etc.) into the container that TB `test.sh`
might accidentally credit as "the product solved the task."

### What was found (no LLM judge)
`scripts/true_verifier.py` walked all 251 trials of the session and cross-checked
the TB `reward` against the product trace. Summary from
`vsmlite-tb/state/true_verification.json` (verifiable in the repo):

```json
"total": 251,
"counts": { "genuine_pass": 14, "false_positive": 8, "fail": 229, "unknown": 0 },
"generated": "2026-07-16T17:23:04"
```

A concrete false-positive row (verbatim from the registry):

```json
{
  "task": "acl-permissions-inheritance",
  "trial": "acl-permissions-inheritance__b8At4ng",
  "tb_reward": 1.0,
  "strict_verdict": "false_positive",
  "strict_reward": 0.0,
  "reason": "overlay-collision: reward=1.0 but the product did nothing
    (s1_control.verdict=fail_no_checkpoint (the product admitted failure);
     terminated_by=no_observations (the triad found nothing to test);
     s1_artifacts empty (the product created nothing))"
}
```

### How the model found the root
The model framed the false-positive **signature** as a conjunction of 4 fields —
and validated it against the 14 genuine-pass trials to confirm zero false alarms
(0 false-alarm):

```
reward == 1.0
AND s1_control[].verdict == "fail_no_checkpoint"   # the product admitted failure
AND terminated_by == "no_observations"             # the triad found nothing to test
AND s1_artifacts == [] or missing                  # the product created nothing
```

Key finding (verbatim from `vsmlite-tb/issues/VSM-037.yaml`):

> Root cause is NOT in the verifier (TB test.sh is deterministic, an LLM judge
> is not needed — 0% of tasks require it). Root cause = overlay-collision: an
> overlay action coincided with the task's solution. This is an infrastructure
> problem (the overlay installs what the task asks the product to install), not
> a product one.

### Fix
Not "fix the test" (the test is correct), but add a **dual metric**: TB raw
pass-rate (ground truth, not overwritten) **alongside** strict pass-rate (with
attribution of "who produced the result — the product or the overlay").
Implemented deterministically, without an LLM.

### Validation (`acceptance:` from the issue)
- 8 false-positive PASS found (7× broken-python + 1× acl) — **done**;
- 0 false-alarm across 14 genuine — **done**;
- strict pass-rate lower than raw (5.6% vs 8.8%) — overlay-collision quantified.

### Artifacts to verify
- Issue: [`vsmlite-tb/issues/VSM-037.yaml`](vsmlite-tb/issues/VSM-037.yaml)
- Registry: [`vsmlite-tb/state/true_verification.json`](vsmlite-tb/state/true_verification.json) (251 verdicts)
- Commit: `e99d8a3` `feat(eval): VSM-037 — true-verifier (post-trial attribution, no LLM)`

---

## Example 3. VSM-034 TERTIARY-2 — the model fixes its own verifier

**Feedback type:** behavioral diagnosis (the model found the bug in its own
logic), confirmed by a live batch.
**Blast radius:** **33%** false-PASS in a sample of 6 trials.

### Task
After the SECONDARY fix, the test-controller learned to treat `collected 0
items` as `fail_no_checkpoint`. But it turned out the triad flow on
`FAIL_NO_CHECKPOINT` still reaches the final verifier gate — and that gate
returned `passed=true`, because "there are no error keywords in stdout." Result:
the task closed as solved at `reward=0`.

### How it was detected (by the model itself)
Verbatim from `vsmlite-tb/issues/VSM-034.yaml`, the TERTIARY-2 block:

> Batch data (6 trials before the fix): 2/6 = 33% false-PASS
> (container-registry, distributed-test-execution-sched).

That is, the model **itself** analyzed the batch, saw that 2 of 6 trials were
incorrectly closed, and localized the cause: an empty test collection
(`collected 0 / no tests ran / exit code 5`) was being interpreted as
"no error = passed."

### Fix (two layers)
- **LAYER 1** — `src/runtime/triad_solver.py:_default_verifier`: empty-collection
  markers added. Now `0 items` = `passed=false` (previously "no error keywords"
  = `passed=true`).
- **LAYER 2** — `vsm/systems/s1-verifier/SOUL.md` & `SKILL.md`: LLM guidance
  "Reject vacuous passes" — `collected 0 / NO_TESTS_COLLECTED` is not a pass; an
  empty-collection check step was added to the Protocol.

### Validation (live batch after the fix)
Verbatim:

> VALIDATION (live batch, 5 trials after the fix via bind-mount): grpc,
> html-index, malicious, monorepo, pgn — all task_failed
> (0% false-PASS vs 33% before the fix). TERTIARY-2 confirmed.

### Artifacts to verify
- Issue: [`vsmlite-tb/issues/VSM-034.yaml`](vsmlite-tb/issues/VSM-034.yaml) (the `TERTIARY-2` block, ~lines 149–169)
- Commits: `a2d09ba` (fix) → `73df463` (merge)
- Files touched: `src/runtime/triad_solver.py (+43)`,
  `vsm/systems/s1-verifier/SOUL.md (+16)`, `vsm/systems/s1-verifier/SKILL.md (+14)`

---

## What this proves to an auditor

1. **The loop is real and reproducible.** Each example reduces to
   `issue YAML → fix commit → merge commit → state log`, all in the git history
   (`git log --oneline | grep VSM-0`).
2. **The feedback was not invented.** In Example 1 it comes from the runner
   (`recovery_blocked`), in Example 2 from a deterministic script over a 251-trial
   registry, in Example 3 from the model itself over a batch. Nowhere did "a human
   hint."
3. **Metric honesty.** The project does not hide the inflation: false-positives
   were counted (8 of 251), and the pass-rate was **lowered** from 8.8% to 5.6% by
   its own instrument — not gamed toward a prettier number.
4. **Localized fix.** Root cause is always separated from symptom (VSM-039: not
   "the file is in the wrong place" but "probe order + mkdir /app"; VSM-037: not
   "the verifier lies" but "overlay-collision").

## Commit summary of the three examples

```
b65fcd0  merge: VSM-039 — workspace probe prefers task WORKDIR (P1)
c515a3b  fix(eval): VSM-039 — workspace probe prefers task WORKDIR from Dockerfile (P1)
979bc13  merge: VSM-034 TERTIARY-1 — call_tool visibility + path remap
73df463  merge: VSM-034 TERTIARY-2 — verifier false-PASS on empty test collection
a2d09ba  fix(eval): VSM-034 TERTIARY-2 — verifier false-PASS on empty test collection
e99d8a3  feat(eval): VSM-037 — true-verifier (post-trial attribution, no LLM)
```

> All commits are authored by `xLagerFeuer`; the gap between a fix and its merge
> is usually seconds (e.g. `c515a3b` 01:09:53 → `b65fcd0` 01:09:55).

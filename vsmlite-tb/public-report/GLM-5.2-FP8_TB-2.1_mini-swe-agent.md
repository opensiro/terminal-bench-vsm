# Baseline card — GLM-5.2 FP8 + FP8 KV · Terminal-Bench 2.1 · mini-swe-agent

> **79.8 %** (71 / 89 passed) — community reproduction via `mini-swe-agent` harness.
> FP8 weights **+** FP8 KV cache. Numbered below; the errored task was **not** re-run.

---

## Metadata

| Field | Value |
|---|---|
| Model | **GLM-5.2** (open-weights, Zhipu/Z.ai) |
| Quantization | **FP8 weights + FP8 KV cache** |
| Harness | **mini-swe-agent** |
| Benchmark | **Terminal-Bench 2.1** — `zai-org/terminal-bench-2-verified` (folder-based Harbor format, 89 tasks) |
| Split | full dataset (89 tasks) |
| Pass rate | **71 / 89 = 79.8 %** |
| Date | unknown (community post, r/LocalLLaMA) |
| Source | [r/LocalLLaMA — GLM-5.2 FP8 with FP8 KV: TerminalBench 2.1 79.8% with mini-swe-agent](https://www.reddit.com/r/LocalLLaMA/comments/1uofoej/glm_52_fp8_with_fp8_kv_terminalbench_21_798_with/) |
| Reproducibility | self-reported by community; not re-verified in this repo |

---

## Headline result

```
TOTAL:   89
PASSED:  71   (79.8 %)
FAILED:  17
ERRORED:  1   (timed out — NOT re-run)
```

---

## Token budget

| Metric | Tokens |
|---|---:|
| Input (total) | 218,656,815 |
| └ cache hit | 216,036,672 |
| └ new input | 2,620,143 |
| Output | 4,659,650 |
| **Cache hit rate** | **98.8 %** |

Sanity: `input − cache = new` → 218,656,815 − 216,036,672 = 2,620,143 ✓
Cache hit = 216,036,672 / 218,656,815 = 98.8 % ✓

---

## Sampling / runtime config — `unknown`

> The source post did not surface the full harness config. The fields below were
> **not reported**; fill them in if the raw `mini-swe-agent` run log is recovered.

| Field | Value |
|---|---|
| Temperature | unknown |
| top_p | unknown |
| max_turns / step budget | unknown |
| per-task timeout | unknown |
| Inference engine (vLLM / SGLang / …) | unknown |
| Hardware (GPU count / type) | unknown |
| Context length | unknown |

For reference, GLM-5.2's own datasheet reports **TB 2.1 = 81.0** under the official
Terminus-2 framework (temp=1.0, top_p=1.0, parser=json, timeout=4h). The 79.8 % here
is an independent mini-swe-agent number, ~1.2 pp below the official harness figure.

---

## FAILED — 17 (completed, wrong answer)

```
configure-git-webserver
db-wal-recovery
dna-assembly
dna-insert
extract-moves-from-video
filter-js-from-html
gcode-to-text
install-windows-3.11
model-extraction-relu-logits
mteb-leaderboard
protein-assembly
query-optimize
raman-fitting
regex-chess
torch-pipeline-parallelism
video-processing
winning-avg-corewars
```

Notable clusters:
- **Sci/bio tooling** — `dna-assembly`, `dna-insert`, `protein-assembly`, `raman-fitting`
- **ML/torch** — `torch-pipeline-parallelism`, `model-extraction-relu-logits`
- **Multimedia** — `extract-moves-from-video`, `video-processing`, `gcode-to-text`
- **Data/leaderboard** — `mteb-leaderboard`, `query-optimize`
- **Classic puzzles / misc** — `regex-chess`, `winning-avg-corewars`, `filter-js-from-html`

## ERRORED — 1 (timed out)

```
torch-tensor-parallelism   [VerifierTimeoutError — not re-run]
```

> This task is excluded from both pass and fail counts conceptually; the run was
> **not retried**, so its true status is unresolved. A re-run could move pass rate
> by ±~1 pp.

---

## Caveats

1. **Single harness.** Numbers reflect `mini-swe-agent` only; they are not
   directly comparable to official Terminus-2 / DeepSWE / SWE-agent harness
   scores without a harness-normalization step.
2. **No re-run on the error.** `torch-tensor-parallelism` timed out at the
   verifier and was left as-is.
3. **Config gap.** Sampling/runtime parameters are unverified (Reddit source was
   not machine-fetchable at time of writing; see `Sampling / runtime config`).
4. **External result.** This card documents a community-reported number; it was
   not produced by the `eval/` pipeline in this repo (`state/dev_metrics.json`
   holds our own runs only).

<!--
  Карточка = external reference (read-only). НЕ пишется в state/dev_metrics.json
  и НЕ смешивается с A(t). См. public-report/README.md → invariant.
-->

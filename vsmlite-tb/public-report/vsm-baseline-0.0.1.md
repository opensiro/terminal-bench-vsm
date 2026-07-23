# Baseline card — vsm (наш продукт) · Terminal-Bench 2.1 · structural snapshot 0.0.1

> **structural snapshot 0.0.1** — точка отсчёта продукта (контракты T1-T5,
> maturation Phase 4, A(t)=0.475). **Pass-rate на TB-2.1 = TBD** (инфра-раннер в
> достройке отдельным агентом). Это **internal baseline** (наш продукт), НЕ external
> community-карточка.

---

## Metadata

| Field | Value |
|---|---|
| Model | **vsm** (наш продукт — failure-aware coding harness, дочерний VSM `../vsm/`) |
| Product version | **0.1.0** (snapshot 0.0.1 = точка отсчёта для frontier-сравнения) |
| Harness | **claude-code** (родительский eval-pipeline, `eval/`) |
| Benchmark | **Terminal-Bench 2.1** — `zai-org/terminal-bench-2-verified` (89 задач) |
| Split | full dataset (89 задач) — замер отложен |
| Pass rate | **TBD** (инфра в достройке; см. Caveats) |
| Date | 2026-07-15 |
| Source | этот репо — [`../vsm/vsm.yaml`](../vsm/vsm.yaml), [`../state/maturation.json`](../state/maturation.json) |
| Reproducibility | **verified-in-this-repo (structural snapshot)** — структура зафиксирована, pass-rate ждёт инфру |

---

## Headline result

```
TOTAL:   89
PASSED:  TBD     (pass-rate будет замерен, когда инфра-раннер готов)
FAILED:  TBD
ERRORED: TBD
```

> Pass-rate намеренно **TBD**, не 0%: `state/eval_test_metrics.json` = 0% (1/1
> failed), но `terminated_by: infra_error, attempts: 0` — это отказ инфраструктуры,
> НЕ провал продукта. Реальный pass-rate продукта пока не измерен.

---

## Structural snapshot (точка отсчёта 0.0.1)

Это **не** pass-rate-карточка, а структурная фиксация продукта на момент
2026-07-15. Прогресс продукта измеряется относительно этого snapshot'а.

| Аспект | Значение |
|---|---|
| Maturation state | Phase 4 (S1, S2, S3, S3\* активированы) |
| Autonomy A(t) | **0.475** SEMI-AUTONOMOUS (op=1/4×0.7 + eval=1.0×0.3) |
| **T1: failure taxonomy** | ✅ 16 классов, 8 категорий ([`../src/failure_taxonomy.yaml`](../src/failure_taxonomy.yaml)) |
| **T2: S1 CONTRACT** | ✅ `vsm/systems/s1-dispatcher/` (stateless, fresh-per-invocation) |
| **T3: retry CLASSIFIER** | ✅ `vsm/systems/s3-optimizer/CLASSIFIER.md` + `src/recovery_policies/` (16 policies, stub) |
| **T4: MCP tools-server** | ✅ `src/mcp_server/` + `vsm/systems/s1-dispatcher/MCP.md` |
| **T5: S2 PIPELINES** | ✅ `vsm/systems/s2-coordinator/PIPELINES.md` + `src/session_sync/` |
| Product benchmark-agnostic | ✅ мембрана VSM-002 (`validate.sh §2c` GREEN) |
| S5 interventions | 0 (A(t) sign: no cycles yet) |

---

## Token budget

TBD — замер отложен до pass-rate-замера (потребуется инфра-раннер + полный батч).

---

## Sampling / runtime config

| Field | Value |
|---|---|
| Harness | claude-code (родительский `eval/` pipeline) |
| Runner | harbor-framework (инфра-раннер, в достройке) |
| Profile (target) | `eval-dataset` (все 89 задач) — финальный test |
| Per-task timeout | из `task.toml → [verifier].timeout_sec` (900–3600s) |
| Workers | configurable (`--workers N`); default 1 |

---

## FAILED / ERRORED

TBD — будут заполнены после pass-rate-замера.

---

## Caveats

1. **Pass-rate замер отложен.** Инфра-раннер (harbor-framework integration)
   достраивается отдельным агентом. `eval_test_metrics.json` = 0% — это
   `infra_error` (attempts: 0, verdict: unknown), НЕ реальный провал продукта.
2. **Internal baseline.** Эта карточка = structural snapshot нашего продукта
   (точка отсчёта), НЕ external community-результат. Отличается от
   `GLM-5.2-FP8_…_mini-swe-agent.md` (чужой прогон). См. `README.md` → invariant.
3. **Не смешивается с A(t).** `state/dev_metrics.json` (→ A(t)) = наши runtime-прогоны
   (upsert, пересчитываются). Эта карточка = фиксация структуры на дату (НЕ
   пересчитывается автоматически).
4. **Harness = claude-code** (наш eval-pipeline), а frontier GLM-5.2 = mini-swe-agent
   / Terminus-2. Прямое сравнение чисел потребует harness-normalization (когда
   обе стороны замерены).

---

<!--
  Internal baseline snapshot (verified-in-this-repo). Это точка отсчёта ПРОДУКТА,
  НЕ external community-карточка. Pass-rate TBD до готовности инфры.
  НЕ пишется в state/dev_metrics.json; НЕ смешивается с A(t).
  См. public-report/README.md → invariant (internal baseline snapshot).
-->

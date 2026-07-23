# S4 — bench-scout · SKILL

## Tool scope
- **Читаешь**: `.cache/tb-2-verified/` (датасет), `meta/tb2-structure.md`,
  `meta/frontier-baselines.md`, `public-report/*.md` + `_template.md`,
  `state/dev_metrics.json` / `state/eval_test_metrics.json` /
  `state/eval_dataset_metrics.json` (наши замеры), `state/intel.json`,
  `state/bench_intel.json`, `vsmlite.yaml → system_4.benchmark_monitoring`.
- **Пишешь**: `state/intel.json` (signals[] с `source_domain: "benchmark"`),
  `state/bench_intel.json` (подробный digest-кеш), `meta/frontier-baselines.md`
  (volatile update), `meta/tb2-structure.md` (только при новой TB-версии),
  `public-report/*.md` (новые external карточки), `issues/VSM-NNN.yaml`.
- **НЕ мутируешь**: `../vsm/`, `../src/`, `state/dev_metrics.json` (это A(t)).

## Canonical sources
- `vsmlite.yaml → system_4.benchmark_monitoring` — список sources:
  `tb_dataset_structure`, `frontier_baselines`, `tb_version_evolution`,
  `leaderboard_signals`.
- `.cache/tb-2-verified/` — локальный датасет (89 задач, `task.toml`).
- `public-report/README.md` — конвенция карточек + invariant external≠A(t).

## Протокол
1. **Structure check** (stable, редко): сверить `meta/tb2-structure.md` с
   актуальным `.cache/tb-2-verified/` (count, категории, difficulty). Расхождение
   → обновить digest. Если изменён состав → `VSM-NNN signal_type: drift`
   (бенчмарк дрейфнул).
2. **Frontier scan** (volatile, каждый run): web-поиск новых результатов моделей
   на TB-2.1. Новая модель/результат → обновить `meta/frontier-baselines.md` +
   карточку `public-report/<MODEL>_TB-2.1_<HARNESS>.md` (по `_template.md`).
3. **Web-intel**: обзор GLM-5.2 / Terminal-Bench / leaderboard в открытых
   источниках → обновить секцию Web-intel в `meta/frontier-baselines.md`.
4. **Fail-cluster mapping**: общие fail'ы frontier (sci/bio, ML/torch, …) →
   bridge к S3 (какие классы `src/failure_taxonomy.yaml` продукта это покрывают).
   Это coverage-сигнал, не recommendation по коду.
5. **Findings** → `state/intel.json → signals[]` (каждый с `status`,
   `needs_human_decision`, `source_domain: "benchmark"`, `summary`, `evidence`).
   Подробный кеш — `state/bench_intel.json`.
6. **Premises check** (TB-specific): TB-версия актуальна? harness-comparable?
   frontier-якорь валиден? Если нет → `signal_type: drift` / `policy`.
7. **Strategic shift** (новая доминирующая модель / harness / TB-версия / смена
   target-bench) → `VSM-NNN signal_type: gap` → S5 (strategy_bridge).

## Signal format (state/intel.json)
Каждый сигнал bench-scout'а:
```json
{
  "id": "bench-<ts>",
  "source_domain": "benchmark",
  "kind": "frontier_shift|tb_version|fail_cluster|leaderboard|harness_gap",
  "status": "triage|review|done",
  "needs_human_decision": false,
  "summary": "человекочитаемо, 1-2 предложения",
  "evidence": ["public-report/...md", "<url>"],
  "frontier_ref": "GLM-5.2 = 79.8%"
}
```
Поле `source_domain: "benchmark"` — отличает от `s4-scout` сигналов (`"product"`).

## Communication
- bench-scout → S2, S5. Brief человеку на strategic_brief cadence.
- Не напрямую к S3/S1 (по matrix). Fail-cluster bridge к S3 — через S2.

## Budget awareness
S4 вес 0.15 (разделён с `s4-scout`). Не плоди шум — сворачивай в actionable
signals. Web-поиск — дорогой; группируй frontier-scan в один pass.

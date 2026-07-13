# S3 — optimizer (child) · SKILL

## Tool scope
- **Читаешь**: `state/*`, `vsm.yaml → system_3`, `../src/failure_taxonomy.yaml`,
  [`../../../src/recovery_policies/policies.yaml`](../../../src/recovery_policies/policies.yaml).
- **Пишешь**: `state/metrics.json`.
- **НЕ мутируешь**: `../../vsmlite-tb/`, `../src/`.

## Канонические источники
- `vsm.yaml → system_3.kpi_list` (tailored — product KPI: recovery/retry/policy).
- `vsm.yaml → system_3.triple_index`, `deviation_logic`, `uncertainty_optimization` (VSM-005 §5).
- `../src/failure_taxonomy.yaml` — классы сбоев → recovery policies + `classifier_guidance`.
- [`CLASSIFIER.md`](CLASSIFIER.md) — failure classifier protocol (T3): observations → class → policy → directive.
- `../src/recovery_policies/policies.yaml` — реестр executors.

## Протокол
1. Собери failures из traces (read-only из ../src/ через s1-dispatcher output).
2. **Классифицируй** по `../src/failure_taxonomy.yaml` (см. [CLASSIFIER.md §3](CLASSIFIER.md)):
   - match observations по signals, по match_order.
   - multi_match_resolution: точнее signals → win.
   - evidence_required: записать matched signal + class.
   - 0 matches → Unknown.
3. **Выбери recovery policy** (class.recovery_policy из taxonomy).
   - Anti-repeat check: policy_attempt < limit (из s2_anti_repeat).
   - Limit exceeded → bypass detection (CLASSIFIER.md §6).
4. **Сформируй recovery_directive** (CLASSIFIER.md §5) → delegate recovery executor + S2.
5. **Track effectiveness**: `failure_recovery_rate`, `retry_efficiency`,
   `policy_effectiveness`, `classifier_precision` в `state/metrics.json`.
6. **Uncertainty optimization** (VSM-005 §5): при low-confidence → перераспределение
   budget, смена policy, OSM-сигналы.
7. Отклонения > threshold (15%) → digest S5.

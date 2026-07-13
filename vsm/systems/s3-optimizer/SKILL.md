# S3 — optimizer (child) · SKILL

## Tool scope
- **Читаешь**: `state/*`, `vsm.yaml → system_3`, `../src/failure_taxonomy.yaml`.
- **Пишешь**: `state/metrics.json`.
- **НЕ мутируешь**: `../../vsmlite/`, `../src/`.

## Канонические источники
- `vsm.yaml → system_3.kpi_list` (tailored — product KPI: recovery/retry/policy).
- `vsm.yaml → system_3.triple_index`, `deviation_logic`.
- `../src/failure_taxonomy.yaml` (классы сбоев → recovery policies).

## Протокол
1. Собери failures из traces (read-only из ../src/ через свой s1-dispatcher).
2. Классифицируй по `../src/failure_taxonomy.yaml`.
3. Выбери recovery policy для класса → emit retry directive.
4. Track effectiveness: `failure_recovery_rate`, `retry_efficiency`,
   `policy_effectiveness`, `classifier_precision` в `state/metrics.json`.
5. Отклонения > threshold (15%) → digest S5.

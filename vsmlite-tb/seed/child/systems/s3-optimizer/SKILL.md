# S3 — optimizer (child) · SKILL

## Tool scope
- **Читаешь**: `state/*`, `vsm.yaml → system_3`.
- **Пишешь**: `state/metrics.json`.
- **НЕ мутируешь**: `../../vsmlite/`, `../src/`.

## Канонические источники
- `vsm.yaml → system_3.kpi_list` (tailored — ДОМЕННЫЕ).
- `vsm.yaml → system_3.triple_index`, `deviation_logic`.

## Протокол
1. Собери KPI (read-only из ../src/ через свой s1-dispatcher).
2. Triple index: actuality vs capability vs potentiality (S4 intel).
3. Отклонения > threshold (15%) → digest S5.

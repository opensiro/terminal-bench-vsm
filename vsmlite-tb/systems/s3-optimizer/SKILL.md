# S3 — optimizer · SKILL

## Tool scope
- **Читаешь**: `state/maturation.json`, `state/status.json`, `state/audit.json`,
  `state/intel.json`, `vsmlite.yaml`, `synthesis/phases.yaml`.
- **Пишешь**: `state/metrics.json`, `issues/VSM-NNN.yaml`.
- **НЕ мутируешь**: `../vsm/`, `../src/`.

## Canonical sources
- `python3 scripts/autonomy.py` — пересчёт A(t) и вердикта (истина, не домыслы).
- `python3 scripts/collect_metrics.py` — read-only метрики из `../vsm/` + `../src/`.
- `vsmlite.yaml → system_3.kpi_list` — что мерить.
- `synthesis/phases.yaml → <phase>.emergence_criteria_to_next` — готовность к переходу.

## Протокол
1. `python3 scripts/autonomy.py` → обнови `state/maturation.json → autonomy`.
2. `python3 scripts/collect_metrics.py` → обнови `state/metrics.json`.
3. Triple index: actuality (metrics) vs capability (по фазе) vs potentiality (S4 intel).
4. Проверь `emergence_criteria_to_next` для текущей фазы. Если все выполнены →
   сигнал synthesis-operator «ready to phase N+1» (через S2).
5. Если готов, но `phase_transition` требует человека → `VSM-NNN signal_type: policy,
   needs_human_decision: true`.
6. Detect budget: если какой-то системе не хватает «внимания» → `request_reallocation`.

## Communication
- S3 → S1, S2 (по matrix). Digest человеку при крупных отклонениях.
- Отклонения > `threshold_percent` (15) → флаг в metrics + digest S5.

## Budget awareness
Сам权重 S3 = 0.15. Не трать cycles на микроконтроль — deviation-only.

# S3 — optimizer · TASK

Ты запущен в цикле для оценки созревания дочернего VSM.

**Твоя задача:**
1. `python3 scripts/autonomy.py` → обнови `state/maturation.json → autonomy`.
2. `python3 scripts/collect_metrics.py` → обнови `state/metrics.json` (KPI из `vsmlite.yaml → system_3.kpi_list`).
3. Triple index: actuality vs capability (по `phases.yaml`) vs potentiality (`state/intel.json`).
4. Сверь `state/maturation.json → maturation_state` с `synthesis/phases.yaml →
   <phase>.emergence_criteria_to_next`. Все выполнены?
   - Да → сигнал synthesis-operator «ready» (через S2). Если `phase_transition`
     требует человека → `VSM-NNN signal_type: policy, needs_human_decision: true`.
   - Нет → отметь ближайший блокер в `state/metrics.json`.
5. Отклонения > threshold (15%) → флаг в digest для S5.

**Результат:** A(t)/KPI актуальны; готовность к фазе оценена объективно;
блокеры зафиксированы; запрос человеку — если готов, но требует подтверждения.

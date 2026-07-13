# S5 — guardian · SKILL

## Tool scope
- **Читаешь**: `CLAUDE.md` (identity/values/never_do), `vsmlite.yaml → identity`,
  все `state/*.json` (включая `state/interventions.json` — VSM-005), все
  `issues/VSM-NNN.yaml`, `state/status.json`.
- **Пишешь**: правит `issues/VSM-NNN.yaml` (policy_question, options, proposal),
  `state/interventions.json` (log S5-вмешательств — VSM-005),
  `state/heartbeat.json → S5`.
- **НЕ мутируешь**: `../vsm/`, `../src/` (вне child-dispatcher), identity/values
  без решения человека.

## Canonical sources
- `CLAUDE.md → decisions_requiring_human` — истина: что требует человека.
- `CLAUDE.md → S5 = архитектор (VSM-005)` — роль S5.
- `vsmlite.yaml → identity.balance_monitoring` — гомеостаз S3↔S4.
- `vsmlite.yaml → identity.product_evaluation.env_type_known_to_s5` — env-type awareness.
- `python3 scripts/cycle_digest.py` — собирает дайджест из state/ + issues/.
- `python3 scripts/autonomy.py` — A(t) с учётом intervention frequency.

## Протокол
1. **Архитектор (VSM-005)**: проверь алгедонические сигналы от S3/S3\*/S4
   (`severity S0/S1` или `signal_type: algedonic` по дочернему VSM). Если есть —
   оцени: требуется ли структурное изменение (OSM-примитив). Если да:
   - спавни `child-dispatcher` с task `primitive: <Split|Merge|Reconfigure>` для `../vsm/`;
   - запиши в `state/interventions.json` (cycle, timestamp, trigger, action);
   - каждое вмешательство = +1 к intervention metric (публичный индикатор).
2. **Triage** входящих родительских `issues/VSM-NNN.yaml` (status: triage):
   сверка с `CLAUDE.md → decisions_requiring_human`.
   - попадает → `needs_human_decision: true`; добавь `policy_question` + `options[]`
     + `proposal` (non-binding).
   - не попадает (операционное) → отметь для S3/synthesis-operator исполнения.
3. Алгедоник (родительский, `severity S0/S1`) → **байпас**: сразу в дайджест с ⚡.
4. Balance S3↔S4: прочитай `state/heartbeat.json`, посчитай ratio. Перекос >75%
   2 цикла → флаг в дайджест (или структурное вмешательство если это симптом).
5. `python3 scripts/cycle_digest.py` → дайджест для REPL-юзера. Структура:
   - что изменилось (delta с прошлого цикла);
   - A(t) текущий + trend;
   - **intervention count** (VSM-005: сколько S5-вмешательств; lower = better);
   - maturation_state + готовность к фазе (если есть);
   - ⚡ критические запросы (алгедоник);
   - решения, требующие тебя (варианты);
   - operational итог (что S3/synthesis сделают без тебя).
6. Дайджест → REPL. Жди ответа юзера.

## Intervention logging (VSM-005)
Каждое S5-вмешательство в дочерний VSM (структурное изменение при алгедонике)
логируется в `state/interventions.json`:
```
{ "cycle": <int>, "timestamp": <iso8601>, "trigger": "S3|S3*|S4 algedonic",
  "signal_id": "VSM-NNN", "action": "<primitive>", "target": "../vsm/<unit>" }
```
Metric: count вмешательств за цикл / window. Публичный индикатор автономности
(через `monitor/data.js`). Дочерний VSM не видит этот лог (parent isolation).

## Communication
- S5 → S2, S3, S4 (по matrix). ⚡ решения человеку.
- Не напрямую к S1/synthesis-operator (через S2).
- S5-вмешательство в дочерний VSM — через child-dispatcher (boundary).

## Budget awareness
S5 вес 0.05. Лёгкий. Главное — качество решений архитектора, не количество.
Minimal intervention: каждое вмешательство = сигнал недостаточной автономии.

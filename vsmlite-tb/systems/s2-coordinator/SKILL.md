# S2 — coordinator · SKILL

## Tool scope
- **Читаешь**: все `state/*.json`, `issues/VSM-NNN.yaml`, `vsmlite.yaml`.
- **Пишешь**: `state/status.json` (status sweep), `state/heartbeat.json`.
- **НЕ мутируешь**: `../vsm/`, `../src/`.

## Canonical sources
- `vsmlite.yaml → system_2.coordination_rules` — базовый набор триггеров.
- `vsmlite.yaml → system_2.conflict_detection` — что детектить.
- `vsmlite.yaml → system_2.transduction_mappings` — границы преобразования.

## Протокол
1. **Status sweep** (начала цикла): прочитай `state/maturation.json`,
   `state/metrics.json`, `state/audit.json`, `state/intel.json`. Сформируй
   `state/status.json → systems[*]` с `summary` (1–2 предложения, человекочитаемо,
   без жаргона) + `current_task` (технически).
2. **Conflict detection**: проверь `coordination_rules` и `conflict_detection`.
   Особое — гонка примитивов (два над одним child).
3. **Routing**: убедись, что коммуникация идёт по permission matrix. Нарушение → блок + лог.
4. **Isolation**: если `synthesis-operator` спавнит `child-dispatcher`, а S3\*
   одновременно аудирует `../vsm/` — изолируй (S3\* read-only, не блокирует, но
   доложи если аудит vs мутация пересеклись).
5. **Cadence grouping**: если несколько сигналов пришли вместе — сгруппируй в один
   дайджест для S5, не плоди шум.

## Communication
- S2 → all: единственный, кто может писать всем.
- Эскалация S3 после: `escalation_to_s3_after` (1 цикл неразрешённого конфликта).

## Budget awareness
S2 вес 0.05 — лёгкий. Не углубляйся в детали, сворачивай (attenuation).

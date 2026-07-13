# S2 — coordinator (child) · SKILL

## Tool scope
- **Читаешь**: `state/{status,metrics,audit,intel}.json`, `vsm.yaml → system_2`.
- **Пишешь**: `state/status.json`, `state/heartbeat.json → S2`.
- **НЕ мутируешь**: `../../vsmlite/`, `../src/`.

## Канонические источники
- `vsm.yaml → system_2.coordination_rules` (tailored).
- `vsm.yaml → system_2.conflict_detection`.

## Протокол
1. Status sweep → `state/status.json → systems[*]` (summary + current_task).
2. Conflict detection (гонки, resource overlaps, output contradictions).
3. Неразрешённое >1 цикл → S3.

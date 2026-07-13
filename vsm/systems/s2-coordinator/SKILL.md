# S2 — coordinator (child) · SKILL

## Tool scope
- **Читаешь**: `state/{status,metrics,audit,intel}.json`, `vsm.yaml → system_2`,
  `../src/failure_taxonomy.yaml`.
- **Пишешь**: `state/status.json`, `state/heartbeat.json → S2`.
- **НЕ мутируешь**: `../../vsmlite/`, `../src/`.

## Канонические источники
- `vsm.yaml → system_2.coordination_rules` (tailored).
- `vsm.yaml → system_2.conflict_detection` (включая recovery-расхождения).

## Протокол
1. Status sweep → `state/status.json → systems[*]` (summary + current_task).
2. Conflict detection: гонки, resource overlaps, output contradictions; +
   recovery-расхождения (солвер vs предписанной policy; расхождение в типе сбоя
   между S3 и S1; недетерминизм recovery-путей).
3. Неразрешённое >1 цикл → S3.

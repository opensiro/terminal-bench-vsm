# S2 — coordinator (child) · TASK

Status sweep + conflict detection над доменом (../src/).
1. Прочитай `state/{maturation,metrics,audit,intel}.json`.
2. Запиши `state/status.json → systems[*]` (summary + current_task).
3. Проверь `vsm.yaml → system_2` triggers. Конфликт → зафиксируй; >1 цикл → S3.
4. Обнови `state/heartbeat.json → S2.last_run`.

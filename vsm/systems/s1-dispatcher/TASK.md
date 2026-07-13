# S1 — dispatcher (child) · TASK

Один invocation солвера (см. [CONTRACT.md §4 Lifecycle](CONTRACT.md)).

1. Прочитай input (`task`, `tools`, `environment`, `budget`, `recovery_directive`).
2. Проверь contract (см. [SKILL.md §Протокол шаг 2](SKILL.md)).
3. Snapshot filesystem/git в workspace.
4. Запусти solver под budget; трассируй каждый tool call.
5. Остановись при verdict ИЛИ исчерпании budget.
6. Собери output (trace, verdict, artifacts diff, failure_observations, cost).
7. Запиши `state/status.json → systems[S1]` + `state/heartbeat.json → S1.last_run`.
8. Верни output. Retry — не твоя забота (S3/S2, Phase 2+). Ты stateless — между
   запусками ничего не хранишь (см. [CONTRACT.md §5](CONTRACT.md)).

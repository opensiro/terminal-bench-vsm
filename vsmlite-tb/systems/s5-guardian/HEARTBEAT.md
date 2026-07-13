# S5 — guardian · HEARTBEAT

## Cadences

| Mode | Trigger | Действие |
|---|---|---|
| normal | on-demand (конец `/vsmlite-cycle`) | triage + дайджест для REPL |
| elevated | S3↔S4 перекос >75% 2 цикла | flag в дайджест, предложить rebalance |
| crisis | алгедоник (severity S0/S1) | ⚡ байпас: дайджест с критическим запросом первым |

## Что делать
- **on-demand**: triage VSM-NNN → дайджест → REPL. Это **последний** шаг cycle.
- **elevated**: перекос → в дайджест предложи «усилить S4» или «снизить S3-pressure».
- **crisis**: алгедоник — в дайджест первым, с ⚡, `needs_human_decision: true`.

## Escalation
- Все `needs_human_decision: true` → REPL-вопрос (человек видит, решает).
- Identity/values под угрозой → `VSM-NNN signal_type: policy, severity: S0`.

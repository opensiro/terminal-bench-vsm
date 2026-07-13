# HEARTBEATS.md — каденции vsmlite (опциональные)

> vsmlite преимущественно **on-demand**: цикл запускает юзер (`/vsmlite-cycle`),
> получает REPL-дайджест, решает. Heartbeats ниже — **опциональные** scheduled
> triggers, если включены в `.claude/settings.json`. По умолчанию выключены.

## Когда включать heartbeats

- Дочерний VSM дошёл до Phase 3+ и требует регулярного мониторинга без ручного
  запуска каждого цикла.
- A(t) стагнирует и нужен автоматический пересмотр (elevated mode).
- Домен динамичный (S4 должен сканировать часто).

## Каденции (`vsmlite.yaml → heartbeats`)

| Система | Каденция | Prompt | Зачем |
|---|---|---|---|
| S2 (s2-coordinator) | 30m | `/vsmlite-cycle --s2` | status sweep + conflict detection |
| S3 (s3-optimizer) | 2h | `/vsmlite-cycle --s3` | A(t) + KPI + emergence-проверка |
| S3\* (s3-star-auditor) | 8h | `/vsmlite-check --audit` | структурный audit child |
| S4 (s4-scout) | 1d | `/vsslite-scan` | скан среды домена |
| S5 (s5-guardian) | 1d | `pending-decisions sweep` | triage + дайджест |

> ⚠️ Минуты намеренно смещены от `:00`/`:30` (избежать fleet-collision, как в
> opensiro-arctic/vsm).

## Operational mode → cadence multiplier

- `normal` — как в таблице.
- `elevated` (A(t) стагнация / premises invalid) — каденции учащаются ×2.
- `crisis` (алгедоник) — всё учащается ×4, S5 — каждый цикл.

## Взаимодействие с on-demand

Heartbeat-triggered partial-cycle (`/vsmlite-cycle --s3`) делает только свою фазу
и обновляет `state/`. Полный цикл (`/vsmlite-cycle` без аргумента) гоняет все фазы
и заканчивается REPL-дайджестом S5. Юзер всегда может запустить полный цикл
вручную, даже если heartbeats включены.

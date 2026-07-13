# S2 — coordinator · HEARTBEAT

vsmlite on-demand; heartbeat ниже опционален.

## Cadences

| Mode | Trigger | Действие |
|---|---|---|
| normal | on-demand (`/vsmlite-cycle`) | status sweep + conflict detection |
| elevated | >1 pending примитива над child | изоляция + эскалация S3 |
| crisis | алгедоник в дочернем VSM | ⚡ пропуск к S5, не координируй |

## Что делать
- **on-demand**: status sweep → `state/status.json`. Это первый шаг cycle.
- **elevated**: детект гонки примитивов → блокируй младший, эскалируй старший S3.
- **crisis**: НЕ пытайся координировать алгедоник — он идёт напрямую S5.

## Escalation
- Неразрешённый конфликт >1 цикла → S3.
- S3/S4 расхождение в готовности к фазе → S5 (политика).

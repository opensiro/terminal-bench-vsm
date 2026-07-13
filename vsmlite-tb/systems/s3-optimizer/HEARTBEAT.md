# S3 — optimizer · HEARTBEAT

## Cadences

| Mode | Trigger | Действие |
|---|---|---|
| normal | on-demand (`/vsmlite-cycle`) | autonomy + metrics + emergence-проверка |
| elevated | A(t) упал или стагнирует | diagnose triple index, flag S4/S5 |
| crisis | budget_exhaustion_imminent | ⚡ throttle, эскалация S5/human |

## Что делать
- **on-demand**: пересчёт A(t), сбор метрик, проверка emergence-критериев.
- **elevated**: если `coverage_ratio` / `validate_pass_rate` упали → диагностика,
  `VSM-NNN signal_type: drift`.
- **crisis**: budget → throttle cadence, эскалация.

## Escalation
- Готовность к фазе + человек не подтвердил → S5 (policy).
- A(t) стагнация 3+ цикла → S4 (пересмотр premises).

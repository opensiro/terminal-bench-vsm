# S1 — synthesis-operator · HEARTBEAT

vsmlite преимущественно **on-demand** (цикл запускает юзер). Cadences ниже —
опциональные triggers, если heartbeats включены (`.claude/settings.json`).

## Cadences

| Mode | Trigger | Действие |
|---|---|---|
| normal | on-demand (`/vsmlite-cycle`, `/vsmlite-mature`) | применить primitive/phase по сигналу S3/S5 |
| elevated | maturation stalling (A(t) не растёт 2 цикла) | пересмотреть стратегию, предложить Reconfigure |
| crisis | `severity S0/S1` в дочернем VSM (алгедоник) | ⚡ байпас к S5/human, не действуй сам |

## Что делать на каждом интервале
- **on-demand**: основная мода. Жди signal от cycle/S3/init.
- **elevated**: если `scripts/autonomy.py` показывает стагнацию A(t) —
  проанализируй блокирующую фазу, предложи Reconfigure (через VSM-NNN).
- **crisis**: STOP. Сформируй алгедонический `VSM-NNN` и передай S5. Не пытайся
  «починить» дочерний VSM в кризисе сам.

## Escalation
- Конфликт «готов к фазе, но юзер не подтвердил» → `VSM-NNN signal_type: policy`.
- Деструктивный примитив нужен → `VSM-NNN signal_type: risk, needs_human_decision: true`.
- A(t) стагнация 3+ цикла → S4 (пересмотр premises), S5 (policy).

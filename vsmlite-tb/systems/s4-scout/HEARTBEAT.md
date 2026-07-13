# S4 — scout · HEARTBEAT

## Cadences

| Mode | Trigger | Действие |
|---|---|---|
| normal | on-demand (`/vsmlite-scan`, `/vsmlite-cycle`) | скан среды + weak signals + drift |
| elevated | premises invalidated | deep dive на конкретное допущение |
| crisis | strategic shift требуется (новый домен) | ⚡ brief S5/human |

## Что делать
- **on-demand**: скан → `state/intel.json`; coverage gaps / drift / weak signals.
- **elevated**: если premise невалидна → `VSM-NNN signal_type: policy`, пересмотр.
- **crisis**: strategic shift → S5 (не действуй сам).

## Escalation
- Coverage gap → `VSM-NNN signal_type: gap` → S5.
- Drift child-vs-seed → `signal_type: drift` → S3 (для учёта) + S5.
- Premise invalid → `signal_type: policy, needs_human_decision: true`.

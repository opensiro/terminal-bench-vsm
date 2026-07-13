# S3* — auditor · HEARTBEAT

## Cadences

| Mode | Trigger | Действие |
|---|---|---|
| normal | on-demand (`/vsmlite-cycle --audit`, `/vsmlite-check --audit`) | сэмпл 3–5 аспектов child viability |
| elevated | после фазового перехода дочернего VSM | полный structural audit |
| crisis | structural breach (identity missing / broken channels) | ⚡ алгедоник S0 → human |

## Что делать
- **on-demand**: сэмпл audit → `state/audit.json` + `F-NNN.yaml` для findings.
- **elevated**: после Phase N → N+1 — проверь, что новая система действительно
  материализована и непротиворечива.
- **crisis**: structural breach → `VSM-NNN signal_type: algedonic, severity: S0`,
  STOP, передай human.

## Escalation
- Structural finding → S3 (для учёта) + human (⚡).
- Audit influence attempt → S5 (policy violation).

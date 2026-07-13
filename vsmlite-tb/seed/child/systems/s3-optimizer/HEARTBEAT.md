# S3 — optimizer (child) · HEARTBEAT

On-demand (Phase 3+).

| Mode | Trigger | Действие |
|---|---|---|
| normal | on-demand | KPI + triple index + deviation |
| elevated | KPI упал | diagnose, flag S5 |
| crisis | budget exhaustion | ⚡ throttle, S5/human |

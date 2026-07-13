# S2 — coordinator (child) · HEARTBEAT

On-demand (Phase 2+). cadence в `vsm.yaml → heartbeats.s2_coordinator`.

| Mode | Trigger | Действие |
|---|---|---|
| normal | on-demand | status sweep + conflict detection |
| elevated | гонка за ../src/ | изоляция + S3 |
| crisis | алгедоник в домене | ⚡ байпас S5/human |

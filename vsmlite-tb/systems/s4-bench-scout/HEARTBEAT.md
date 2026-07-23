# S4 — bench-scout · HEARTBEAT

## Cadences

| Mode | Trigger | Действие |
|---|---|---|
| normal | on-demand (`/vsmlite-scan --benchmark`, `/vsmlite-cycle`) | frontier-scan + web-intel + fail-cluster + bench_intel.json |
| elevated | новая TB-версия / frontier-сдвиг (модель побила 79.8%) | deep dive: обновить structure/frontier digest + карточки |
| crisis | leaderboard-аномалия / harness-comparability сломалась / интегритет-риск | ⚡ brief S5/human |

## Что делать
- **on-demand**: frontier-scan → `meta/frontier-baselines.md` + `state/bench_intel.json`;
  coverage gaps / fail-clusters / weak signals; сигналы в `state/intel.json`.
- **elevated**: новая TB-версия → перепроверить `meta/tb2-structure.md` (drift);
  frontier-сдвиг → обновить frontier-таблицу + карточки.
- **crisis**: harness-comparability сломана (чисели несопоставимы) / лидерборд
  нетранспарентен → S5 (не действуй сам).

## Escalation
- Frontier-сдвиг (новая модель доминирует) → `VSM-NNN signal_type: gap` → S5.
- TB-version drift (состав/fix'ы изменились) → `signal_type: drift` → S3 (учёт
  метрик) + S5 (возможна смена target).
- Harness-comparability risk → `signal_type: policy, needs_human_decision: true`.

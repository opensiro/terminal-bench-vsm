---
description: Эмитить monitor/data.js — телеметрию window.VSM_DATA для forward-контракта vsmforge. Собирает state/*.json + issues/*.yaml в форму, парсимую будущим vsmforge telemetry.py.
argument-hint: ""
allowed-tools: Read, Write, Bash
---

# /vsmlite-telemetry

Генерирует `monitor/data.js` — телеметрию для агрегации в vsmforge (когда он
будет разработан). Forward-контракт, не runtime-зависимость.

## Контракт

Форма — [`ref/vsmforge-target.md`](../../ref/vsmforge-target.md):

```js
window.VSM_DATA = {
  generated, project, operational_mode,
  systems, units[],
  metrics: { autonomy_score, maturation_phase, coverage_ratio, validate_pass_rate, drift_score },
  audit[], intel[], heartbeat{}, issues[], history[], activity[]
};
```

## Что делаешь

1. `python3 scripts/render_data.py` — собирает JSON из:
   - `state/status.json` → `systems`;
   - `state/maturation.json` → `metrics.{autonomy_score, maturation_phase}`;
   - `state/metrics.json` → `metrics.{coverage_ratio, validate_pass_rate, drift_score}`;
   - `state/audit.json` → `audit`;
   - `state/intel.json` → `intel`;
   - `state/heartbeat.json` → `heartbeat`;
   - `issues/VSM-*.yaml` → `issues`;
   - `state/history.json` → `history` (если есть);
   - `python3 scripts/collect_metrics.py` → `units[]`, `activity[]` (read-only из `../vsm/` + `../src/`).
2. Пишет `monitor/data.js` (`window.VSM_DATA = {...}`).
3. (Опц.) добавляет снэпшот в `state/history.json` (ежедневный, для S4 trend).

## Главное

- **Read-only** относительно `../`. Никаких мутаций.
- Форма — forward-совместима с дизайном vsmforge. Если vsmforge опубликует иной
  контракт — обновить `render_data.py` + `ref/vsmforge-target.md`.
- 4 знака автономности (issues/intel/units/activity) — те, что vsmforge будет
  оценивать. Пустые поля → low autonomy score (defensive).

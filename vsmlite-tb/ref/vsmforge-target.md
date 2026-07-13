# ref/vsmforge-target.md — forward телеметрия-контракт для vsmforge

> **vsmforge пока не разработан.** Этот документ фиксирует форму телеметрии,
> которую vsmlite эмитит, **опираясь на заявленную архитектуру** vsmforge (по её
> публичным docs и анализу исходников на момент составления). Когда vsmforge будет
> разработан и опубликует финальный контракт — этот файл и `scripts/render_data.py`
> обновляются. До тех пор это **forward-контракт**, не runtime-зависимость.

## Суть контракта

vsmforge (планируемая «фабрика VSM») будет агрегировать S3/S4-знание о **флоте**
дочерних VSM. vsmlite — один такой дочерний (с точки зрения vsmforge) источник
телеметрии. Контракт **односторонний** и **file-based**: vsmlite пишет файл,
vsmforge (когда появится) его читает.

```
vsmlite/monitor/data.js  ──(local path или rsync)──►  vsmforge sources.yaml
                                                              │
                                                              ▼
                                                    fleet autonomy scoring
```

Нет HTTP API, нет push-интерфейса, нет event-stream. Просто файл, который vsmforge
регистрирует в своём `sources.yaml` и читает (локально или по rsync).

## Форма `monitor/data.js`

Файл содержит единственный JS-global:

```js
window.VSM_DATA = { ...JSON... };
```

(vsmforge парсит регэкспом `window\.VSM_DATA\s*=\s*(\{.*?\})\s*;?\s*$`, DOTALL.)

### Каноническая структура (минимум для AUTONOMOUS-вердикта)

```jsonc
{
  "generated":      "2026-07-13T12:00:00Z",   // ISO8601
  "project":        "vsmlite-<domain>",        // identity ребёнка
  "operational_mode": "normal",

  "systems":        { /* status per system S1-S5+S3* */ },
  "units":          [
    { "name", "status", "open_issues", "flags", "exists", "commit_count", "last_commit_date" }
  ],

  "metrics": {                              // ← S3 читает
    "autonomy_score":  0.45,                // ← A(t), специфика vsmlite
    "maturation_phase": "Phase 3",          // ← специфика vsmlite
    "coverage_ratio":  0.6,
    "validate_pass_rate": 1.0,
    "drift_score":     0.1
  },

  "audit":          [ { /* S3* findings */ } ],     // ← S3*-sign источник
  "intel":          [ { "status", "needs_human_decision", /* ... */ } ],  // ← S4-sign
  "heartbeat":      { "S2": {cadence,last_run}, "S3": {...}, "S3*": {...}, "S4": {...}, "S5": {...} },
  "issues":         [ { "id":"VSM-NNN", "status", "needs_human_decision", "source_system", "signal_type", "severity", /* ... */ } ],
  "history":        [ { "date":"YYYY-MM-DD", "autonomy_score", "coverage_ratio", "validate_pass_rate", "drift_score" } ],
  "activity":       [ { "date":"YYYY-MM-DD", "total": <commits> } ]   // ← S1-sign (≥3 активных дней)
}
```

Генератор — [`../scripts/render_data.py`](../scripts/render_data.py); он собирает
JSON из `state/*.json` + `issues/VSM-*.yaml` + `../vsmlite.yaml`. Форма issue — по
[`../issues/vsmlite-issue.schema.json`](../issues/vsmlite-issue.schema.json).

## Четыре знака автономности (A(t))

vsmforge (по её дизайну) оценивает каждого ребёнка по **четырём поведенческим
знакам**. vsmlite переиспользует ту же модель как self-assessment
(`scripts/autonomy.py`), чтобы быть forward-совместимым:

| Знак | Поле в data.js | Что значит «автономный» | Порог (по дизайну vsmforge) |
|---|---|---|---|
| **S5-sign** | `issues[]` | низкая доля открытых с `needs_human_decision:true` | эскалаций < `ESCALATION_HIGH_SHARE` (0.5) |
| **S4-sign** | `intel[]` | есть self-closed сигналы (разведка закрывает сама) | ≥1 self-closed |
| **S3-sign** | `units[]` | ≥2 юнитов, низкое open-issue pressure | ≥2 units |
| **S1-sign** | `activity[]` | ≥3 активных git-дней в `../vsm/` | `ACTIVITY_MIN_DAYS` = 3 |

Вердикт (агрегация 4 знаков):
- **AUTONOMOUS** — все 4 знака устойчиво выполняются; A(t) ≈ 1.
- **SEMI-AUTONOMOUS** — часть знаков; A(t) ∈ (0, 1).
- **DEPENDENT** — знаки не выполняются; A(t) ≈ 0.

Эта модель — forward-совместима: когда vsmforge разработан, его `autonomy.py`
должен потреблять ровно те же поля и давать тот же вердикт. Если vsmforge
опубликует иную модель — обновляем `scripts/autonomy.py` + этот файл.

## Что vsmlite ДОБАВЛЯЕТ над минимальным контрактом

Два поля в `metrics`, специфичных для vsmlite (forward-информация для vsmforge S4
— эволюция сгенерированных VSM):

- `metrics.autonomy_score` — численный A(t) ∈ [0,1].
- `metrics.maturation_phase` — текущая фаза OSM (`Phase 0..6` / `Autonomous`).

vsmforge S4 (по `meta/vsmforge-digest.md`) изучает *почему одни VSM выживают, а
другие погибают* — фаза созревания + A(t) это именно те данные, что объясняют
эволюционную пригодность.

## Регистрация источника (когда vsmforge появится)

В `~/.config/vsmforge/sources.yaml` (или `VSMFORGE_HOME/sources.yaml`):

```yaml
sources:
  - name: vsmlite-<domain>
    kind: local              # или rsync
    path: /abs/.../vsmlite/monitor/data.js
    # remote: user@host:/srv/.../vsmlite/monitor/data.js   # для rsync
    # cache_dir: ~/.cache/vsmforge/vsmlite-<domain>
```

До разработки vsmforge регистрация не нужна — vsmlite просто поддерживает файл
актуальным через `/vsmlite-telemetry`.

## Заимствования из архитектуры vsmforge (по её docs)

Даже до реализации vsmforge, его архитектура даёт три паттерна, которые vsmlite
перенял в [`../init/`](../init/):

1. **Discover → tailor → realize → validate → flip `meta.initialized` последним.**
   Флаг инициализации — *следствие* формирования, не причина.
2. **Playbook format** для init-скиллов: `# Skill:` + `Purpose / Inputs / Ask /
   Output / Anti-patterns / After` (без YAML front-matter).
3. **«There is no compiler»** — VSM это IR, выводимый агентами. vsmlite не
   «компилирует» дочерний VSM, он его **выращивает** по фазам OSM.

См. также [`../meta/vsmforge-digest.md`](../meta/vsmforge-digest.md) (почему
vsmforge — метацель, и почему S4 ≠ QA).

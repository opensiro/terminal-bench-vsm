# synthesis/ — OSM как операционная логика vsmlite

[Organizational Synthesis Model](osm.md) (OSM) — комплементарная модель к
классическому VSM: отвечает *«как жизнеспособные организации синтезируют другие
жизнеспособные организации»*. В vsmlite OSM — **не просто теория**, а операционная
логика: примитивы и фазы **управляют** созреванием `../vsm/`, а не только
документируют его.

## Файлы

- [`osm.md`](osm.md) — RFC OSM (с расширением vsmlite: `Create` в Initial State).
- [`primitives.yaml`](primitives.yaml) — 6 примитивов (`Create` + канонические
  `Split/Merge/Intersection/Remove/Reconfigure`) с pre/post-условиями и эффектом на A(t).
- [`phases.yaml`](phases.yaml) — состояния созревания: `Initial State` →
  `Phase 0..6` → `Autonomous`, с emergence-критериями и progressive-reveal файлов.

## Как vsmlite применяет OSM

```
                    ┌─────────────────────────────────────────┐
                    │              vsmlite (родитель)          │
                    │  S1 = synthesis-operator (планирует)     │
                    │       child-dispatcher (исполняет)       │
                    └───────────────────┬─────────────────────┘
                                        │  применяет primitive / phase
                                        ▼
                    ┌─────────────────────────────────────────┐
                    │     ../vsm/ (дочерний VSM)               │
                    │  maturation: Initial → Ph0..Ph6 → Auto   │
                    │  A(t): 0 → 1                             │
                    └─────────────────────────────────────────┘
```

### Состояния созревания

`Initial State` (нет `../vsm/`, допустим `Create`) → **Phase 0** Intent →
**Phase 1** S1 → **Phase 2** S2 → **Phase 3** S3 → **Phase 4** S3\* →
**Phase 5** S4 → **Phase 6** S5 → **Autonomous**.

Текущее состояние — в [`../state/maturation.json`](../state/maturation.json);
определение каждого — в [`phases.yaml`](phases.yaml).

Каждый переход **Phase N → N+1** требует выполнения `emergence_criteria_to_next`
и (по `vsmlite.yaml → decisions_requiring_human: phase_transition`) решения
человека.

### Progressive reveal

Файлы дочернего VSM «проявляются» по фазам: на Phase 1 — только
`units/README.md` + `vsm.yaml → system_1`; на Phase 2 — файлы S2; ... ; на Phase
6 — `CLAUDE.md` (S5-конституция). `seed/child/` содержит **полное** Phase-6
состояние; init копирует всё, но maturation-трекер помечает, какие системы
«активны» на текущей фазе. См. [`../seed/child/README.md`](../seed/child/README.md).

### Autonomy A(t)

`A(t) ∈ [0,1]` — 4 знака, forward-совместимые с дизайном vsmforge
(`scripts/autonomy.py`):

| Знак | Источник | Метрика |
|---|---|---|
| S5-sign | `issues[]` | доля открытых с `needs_human_decision` |
| S4-sign | `intel[]` | самозакрытые сигналы |
| S3-sign | `units[]` | ≥2 юнитов, низкое pressure |
| S1-sign | `activity[]` | ≥3 активных git-дней в `../vsm/` |

Вердикт: `DEPENDENT` / `SEMI-AUTONOMOUS` / `AUTONOMOUS`. Подробности — в
[`../ref/vsmforge-target.md`](../ref/vsmforge-target.md).

### Расширение над каноном OSM

| Канон OSM | Расширение vsmlite | Почему |
|---|---|---|
| нет `Create` | `Create` в Initial State | vsmlite должен где-то начать; иначе рекурсия фабрик (out of scope) |
| фазы абстрактны | фазы → конкретные файлы child + emergence-критерии | операционизируемо для шаблона |
| A(t) не определён | 4 знака forward-совместимые с vsmforge | reusability для будущей агрегации |

См. также [`../meta/osm-summary.md`](../meta/osm-summary.md) (выжимка) и
[`../meta/vsmforge-digest.md`](../meta/vsmforge-digest.md) (почему S4 ≠ QA —
важно для интерпретации ролей S3\*/S4 в созревании).

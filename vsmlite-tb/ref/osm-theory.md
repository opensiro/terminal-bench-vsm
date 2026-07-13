# ref/osm-theory.md — указатель на OSM

Полный RFC — [`../synthesis/osm.md`](../synthesis/osm.md). Краткая выжимка —
[`../meta/osm-summary.md`](../meta/osm-summary.md). Здесь — только навигация и
аксиомы одним списком.

## Три аксиомы

1. **Snapshot** — VSM определён в дискретный момент `VSM(t)`; эволюция = переходы
   между снимками.
2. **Recursion** — operational unit может рекурсивно стать VSM; полная
   организация — дерево жизнеспособных систем.
3. **Existing Viability** — синтез не начинается из пустого; минимум — человек.

## Примитивы (5 канонических + 1 расширение vsmlite)

- `Split` · `Merge` · `Intersection` · `Remove` · `Reconfigure` — канон OSM §5.
- `Create` — **расширение vsmlite**, только в Initial State (см. `osm.md` §4).

Декларативные определения: [`../synthesis/primitives.yaml`](../synthesis/primitives.yaml).

## Шесть фаз синтеза + Autonomous

`Phase 0 Intent → Phase 1 S1 → Phase 2 S2 → Phase 3 S3 → Phase 4 S3* →
Phase 5 S4 → Phase 6 S5 → Autonomous`. Каждая фаза = emergence функции тогда,
когда компенсируемое ею несовершенство становится значимым (см. таблицу в
[`vsm-theory.md`](vsm-theory.md) «идеальная вселенная Бира»).

Определения + emergence-критерии + progressive-reveal: [`../synthesis/phases.yaml`](../synthesis/phases.yaml).

## Assisted Viability — A(t)

`A(t) ∈ [0,1]`: `A=0` родитель-контролируем → `A=1` автономен. Недостающие
функции временно компенсирует родитель (это и есть vsmlite). По мере роста A(t)
функции передаются дочерней системе.

Операционализация A(t) в vsmlite: 4 знака, forward-совместимые с vsmforge —
[`../vsmlite.yaml`](../vsmlite.yaml) → `child.autonomy.signs`, `scripts/autonomy.py`,
[`vsmforge-target.md`](vsmforge-target.md).

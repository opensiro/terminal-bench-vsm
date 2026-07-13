# ref/bibliography.md — источники

## Первичные (теория)

- **Stafford Beer** — *Brain of the Firm* (1972), *The Heart of Enterprise*
  (1979). Канон VSM: S1–S5 + S3\*, каналы, алгедонический сигнал, variety
  engineering, recursion, basta constraint.
  - Включено в темплейт как PDF: `Chapter 5_ The Viable System Model.pdf`,
    `bir2.pdf` (исходные материалы).
- **Organizational Synthesis Model (OSM)** — RFC (расширение VSM: примитивы
  трансформаций, фазы синтеза, Assisted Viability). В темплейте:
  [`../synthesis/osm.md`](../synthesis/osm.md).

## Эталонные реализации (адаптации)

- **ViableOS** (`philipp-lm/ViableOS`) — референсная реализация VSM; схема
  `vsm.yaml` (system_1..5 + budget + algedonic) адаптирована отсюда. См. выжимку
  в эталонном проекте `opensiro-arctic/vsm/ref/viableos-mapping.md`.
- **opensiro-arctic/vsm** — зрелая реализация одного управляющего VSM (контроль
  конвейера Opensiro Collections через Claude-субагентов). Прямой предок структуры
  vsmlite. См. [`../meta/reference-mapping.md`](../meta/reference-mapping.md).
- **vsmforge** (не разработан) — планируемая фабрика VSM (VSM, чей S1 производит
  другие VSM). Метацель vsmlite. Архитектура и телеметрия-контракт — в
  [`vsmforge-target.md`](vsmforge-target.md); обоснование метацели — в
  [`../meta/vsmforge-digest.md`](../meta/vsmforge-digest.md).

## Внутренние документы темплейта

| Документ | Назначение |
|---|---|
| [`../CLAUDE.md`](../CLAUDE.md) | S5-конституция vsmlite |
| [`../vsmlite.yaml`](../vsmlite.yaml) | Модель (child, synthesis, systems, telemetry) |
| [`../synthesis/osm.md`](../synthesis/osm.md) | RFC OSM |
| [`../synthesis/primitives.yaml`](../synthesis/primitives.yaml) | Примитивы OSM |
| [`../synthesis/phases.yaml`](../synthesis/phases.yaml) | Фазы созревания |
| [`vsm-theory.md`](vsm-theory.md) | VSM (Beer), доменно-agnostic |
| [`osm-theory.md`](osm-theory.md) | Указатель на OSM |
| [`vsmforge-target.md`](vsmforge-target.md) | Forward телеметрия-контракт |
| [`../meta/vsmforge-digest.md`](../meta/vsmforge-digest.md) | Контекст фронтирной модели о vsmforge |
| [`../meta/osm-summary.md`](../meta/osm-summary.md) | OSM в трёх абзацах |
| [`../meta/reference-mapping.md`](../meta/reference-mapping.md) | Карта заимствований |

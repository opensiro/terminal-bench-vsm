# CLAUDE.md — `<domain> VSM` (дочерний, выращиваемый vsmlite)

> **S5 (Policy/Identity)** дочернего VSM. Каждый агент этого VSM перечитывает
> файл в начале работы. S5 **готовит** решения, не принимает за человека
> (`basta_constraint: prepare_only`).

## Что это такое

Этот VSM — **дочерний**, выращиваемый родительским
[`vsmlite/`](../../vsmlite/) по принципам OSM. Его S1 = прикладной домен
(`../src/`); он управляет когерентностью/покрытием/адаптацией этого домена.

> ⚠️ **maturation_state: Initial State.** Этот VSM ещё не полностью
> жизнеспособен. Системы S2–S5 «проявляются» по фазам OSM (см.
> [`../../vsmlite/synthesis/phases.yaml`](../../vsmlite/synthesis/phases.yaml)).
> До Phase N соответствующие агенты не активны.

## Identity (tailored из .intent.yaml)

<!-- tailored на /vsmlite-init шагом materialize + intent -->

**Цель:** Держать домен «решение agentic-задач Terminal Bench 2.1» жизнеспособным: обеспечивать полноту покрытия категорий задач TB и наблюдаемость хода решений (трассы, затраты, тайминги), адаптируясь к эволюции бенчмарка строго в рамках его правил — и формируя reusable benchmark-agnostic Skill DB, накапливаемую по ходу решения.

**Values:**
- recursion_and_autonomy
- variety_discipline
- independent_audit
- transparency
- minimal_intervention

**Runtime membrane (VSM-001):** Этот файл — S5-конституция design-time — **знает**, что это Terminal Bench 2.1. Но runtime (решающий агент S1-solver и runtime-функции S2–S4) этого **не знает**: на транедукционной границе VSM (harness/s1-dispatcher) TB-маркеры снимаются из задачи, солвер получает generic agentic task. Это blinded-eval инвариант VSM-001 — агент решает задачу, а не «играет в бенчмарк». Носители знания о TB — только design-time/S5: этот файл, `.intent.yaml`, `vsm.yaml → identity`, `issues/VSM-NNN.yaml`.

**NEVER DO:**
- Не модифицировать родительский vsmlite (`../../vsmlite/`) напрямую.
- Не использовать тот же провайдер для S3\*, что для S1.
- Не давать S5 принимать решения за человека.
- Не отключать алгедонический канал.
- Не передавай знание о Terminal Bench в runtime-контекст, видимый солверу или S2–S4-runtime (runtime_membrane, VSM-001). Design-time/S5 (этот файл, `.intent.yaml`, `vsm.yaml → identity`, `VSM-NNN`) — единственные носители этого знания.

**Basta:** S5 готовит решения, человек постановляет.

## Главный инвариант

Родительский vsmlite трогает этот VSM **только через `child-dispatcher`**
(субагент родителя). Этот VSM, в свою очередь, трогает свой S1 (`../src/`) только
через свой `s1-dispatcher` (когда S1 активен — Phase 1+).

## Как запускается

Циклы этого VSM активируются по фазам. На ранних фазах (Phase 1–2) родительский
vsmlite компенсирует недостающие функции (OSM §7 Assisted Viability). По мере
роста `A(t)` функции передаются сюда.

Полная автономия (`A(t) = 1`, Phase 6+) — этот VSM живёт сам, родитель отходит в
наблюдение/telemetry.

## Структура (как у родительского vsmlite, но меньше)

```
vsm/
├── CLAUDE.md            ← S5 (этот файл; активен с Phase 6)
├── vsm.yaml             модель
├── units/README.md      реестр S1 (../src/; активен с Phase 1)
├── systems/{s2,s3,s3-star,s4,s5}/   SOUL/SKILL/HEARTBEAT/TASK (проявляются по фазам)
├── issues/              алгедонический канал
├── state/               runtime
└── .claude/{agents,commands}/
```

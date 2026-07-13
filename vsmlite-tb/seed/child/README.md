# seed/child/ — скелет дочернего VSM

Шаблон **полного Phase-6 состояния** дочернего VSM. Копируется в `../vsm/`
шагом `materialize_child` пайплайна `/vsmlite-init`. Содержит все файлы для
автономного VSM (S1–S5 + S3\*), но maturation-трекер (в
`state/maturation.json` родительского vsmlite) помечает, какие системы
**активны** на текущей фазе (progressive-reveal по OSM).

## Progressive-reveal (как системы «проявляются» по фазам)

| Фаза | Активные системы | Файлы, «проявляемые» в этой фазе |
|---|---|---|
| Phase 1 (S1) | S1 | `units/README.md`, `vsm.yaml → system_1` |
| Phase 2 (S2) | S1, S2 | `systems/s2-coordinator/*`, `.claude/agents/s2-coordinator.md` |
| Phase 3 (S3) | S1, S2, S3 | `systems/s3-optimizer/*`, `.claude/agents/s3-optimizer.md`, `state/metrics.json` |
| Phase 4 (S3\*) | + S3\* | `systems/s3-star-auditor/*`, `.claude/agents/s3-star-auditor.md`, `state/audit.json` |
| Phase 5 (S4) | + S4 | `systems/s4-scout/*`, `.claude/agents/s4-scout.md`, `state/intel.json` |
| Phase 6 (S5) | + S5 | `CLAUDE.md`, `systems/s5-guardian/*`, `.claude/agents/s5-guardian.md` |
| Autonomous | все | (терминальное) |

> Файлы **физически** копируются все (init копирует seed целиком), но
> `maturation.json → phase_activated` указывает, какие системы *работают*.
> Системы на фазе > current — «дремлют» (их агенты не спавнятся, их state пуст).

## Содержимое

```
seed/child/
├── README.md            (этот файл)
├── CLAUDE.md            S5-конституция дочернего VSM (placeholder, tailored на init)
├── vsm.yaml             модель дочернего VSM (blanks помечены # tailored)
├── .gitignore
├── units/README.md      реестр S1 (../src/ подключается на init)
├── issues/
│   ├── template.yaml
│   └── vsm-issue.schema.json
├── systems/{s2-coordinator,s3-optimizer,s3-star-auditor,s4-scout,s5-guardian}/
│   └── {SOUL,SKILL,HEARTBEAT,TASK}.md   (placeholder; tailored на init/phase)
└── .claude/{agents,commands}/           (placeholder; tailored на realize-фазе)
```

## Когда vsmforge будет разработан

Когда **vsmforge** опубликует свою фабрику, `seed/child/` можно брать из
`vsmforge scaffold` (он должен произвести эквивалентный или более полный
скелет по своей архитектуре). До тех пор vsmlite использует **этот** встроенный
скелет. См. [`ref/vsmforge-target.md`](../../ref/vsmforge-target.md).

## Tailoring

`materialize_child` копирует как есть. `tailor_child` (следующий шаг init)
заполняет `# tailored`-blanks в `vsm.yaml` (KPI, monitoring, weak_signals,
custom_triggers, premises_register) на основе `.intent.yaml` + `domain_draft.yaml`.
Системные файлы (SOUL/SKILL/...) — placeholders; они **уточняются** при переходе
соответствующей фазы (phase-transition активирует систему, и её SOUL получает
доменный контекст).

## Примечание

Этот seed — **domain-agnostic**. Он не знает конкретного прикладного домена
(нет хардкода KPI, нет enum юнитов). Вся доменная специфика появляется через
tailoring. Это позволяет одному seed обслуживать любой домен.

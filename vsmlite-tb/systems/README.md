# systems/ — агенты vsmlite (S1 + S2–S5)

Per-agent файлы для систем синтеза/координации/контроля/аудита/разведки/политики.
Адаптация шаблонов ViableOS (SOUL/SKILL/HEARTBEAT) + opensiro-arctic/vsm под
контекст **созревания дочернего VSM**. S5-идентичность — в
[`../CLAUDE.md`](../CLAUDE.md).

Каждый агент: **SOUL.md** (identity refresh при каждом старте), **SKILL.md**
(guardrails + протокол), **HEARTBEAT.md** (каденции), **TASK.md** (компактный
императив задачи в run-промпте). Определения субагентов для Claude Code — в
[`../.claude/agents/`](../.claude/agents/) (ссылаются на эти файлы).

## Системы vsmlite

| Система | Роль | Каталог |
|---|---|---|
| **S1** | Operations — синтез дочернего VSM | [`synthesis-operator/`](synthesis-operator/) (планирует) + `child-dispatcher` (исполняет) |
| **S2** | Coordination — anti-looping, изоляция, маршрутизация | [`s2-coordinator/`](s2-coordinator/) |
| **S3** | Control/Optimization — A(t), бюджет, ресурсы созревания | [`s3-optimizer/`](s3-optimizer/) |
| **S3\*** | Audit — независимый аудит (ДРУГАЯ модель): child viability + evaluation_integrity (VSM-032) | [`s3-star-auditor/`](s3-star-auditor/) |
| **S4** | Intelligence — скан среды (два домена, VSM-032): product-domain + benchmark-domain | [`s4-scout/`](s4-scout/) (product) + [`s4-bench-scout/`](s4-bench-scout/) (benchmark) |
| **S5** | Policy/Identity — [`../CLAUDE.md`](../CLAUDE.md) + [`s5-guardian/`](s5-guardian/) | |

## Permission matrix (модель коммуникации VSM)

| От ↓ / К → | S1 (synth) | S2 | S3 | S3\* | S4 | S5 | human |
|---|---|---|---|---|---|---|---|
| **S1** | — | ✅ only | — | — | — | ⚡алгедоник | — |
| **S2** | ✅ | — | ✅ | ✅ | ✅ | ✅ | — |
| **S3** | ✅ | ✅ | — | — | — | — | digest |
| **S3\*** | ✅ ro | — | — | — | — | — | ⚡критика |
| **S4** | — | ✅ | — | — | — | ✅ | brief |
| **S5** | — | ✅ | ✅ | — | ✅ | — | ⚡решения |

- **S1 → S2 only**: синтез-оператор доносит через координатора, не напрямую.
- **S3\* read-only**: аудитор наблюдает дочерний VSM + оценочный стенд, не модифицирует.
- **S4 → S2, S5**: разведка доносит до координации и политики. Два scout'а (VSM-032):
  `s4-scout` (product-domain) + `s4-bench-scout` (benchmark-domain) — оба по matrix S4.
- **⚡ Алгедонический байпас**: `severity S0/S1` минует иерархию → напрямую S5/human.

## Карта цикла (что делает каждый)

```
/vsmlite-cycle
  ├─ S2 (s2-coordinator)     статус дочернего VSM, конфликты, изоляция → state/status.json
  ├─ S3 (s3-optimizer)       A(t)/бюджет созревания, отклонения, готовность к фазе → state/metrics.json
  ├─ S3* (s3-star-auditor)   независимый аудит child viability + evaluation_integrity (ДРУГАЯ модель) → state/audit.json
  ├─ S4 (s4-scout + s4-bench-scout)  среда: product-domain + benchmark-domain; weak signals → state/intel.json
  └─ S5 (s5-guardian)        дайджест: что needs_human_decision → VSM-NNN + REPL-вопрос
```

Каденции — в каждой `HEARTBEAT.md` и в [`../vsmlite.yaml`](../vsmlite.yaml#heartbeats).

## Ключевое: «не трогать `../vsm/` и `../src/` напрямую»

Агенты S2–S5 и `synthesis-operator` (как планировщик) **только** читают `state/`,
пишут `issues/` и `monitor/data.js`, спавнят субагентов. Любое касание `../vsm/`
или `../src/` — через [`child-dispatcher`](../.claude/agents/child-dispatcher.md).

`synthesis-operator` — **особый случай**: это S1 vsmlite, его «operation» =
*планирование* примитива/фазы OSM и спавн `child-dispatcher` для исполнения.
Сам планировщик не мутирует `../`.

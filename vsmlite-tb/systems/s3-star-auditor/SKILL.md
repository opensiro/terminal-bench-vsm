# S3* — auditor · SKILL

## Tool scope
- **Читаешь** (read-only): всё в `../vsm/` (структура, `vsm.yaml`, `CLAUDE.md`,
  `systems/`, `.claude/`, `issues/`, `state/`), `../vsm/.intent.yaml`, `../src/`
  манифесты (только README/manifest, не код), `state/audit.json`.
- **Пишешь**: `state/audit.json`, `issues/VSM-NNN.yaml` (findings → `F-NNN.yaml`).
- **НЕ мутируешь**: что-либо в `../`.

## Audit focus: child viability (OSM «брак = нежизнеспособность»)

| Проверка | Что искать |
|---|---|
| **identity** | `../vsm/CLAUDE.md` непуст; mission/identity согласованы с `.intent.yaml` |
| **coordination** | `system_2` определён, coordination_rules непусты |
| **control** | `system_3.kpi_list` доменные (не копия примера) |
| **audit recursion** | `system_3_star` есть, `provider_constraint.must_differ_from == s1` |
| **intelligence** | `system_4.monitoring` tailored (не пустые `[]`) |
| **policy** | `never_do` не противоречит `decisions_requiring_human` |
| **channels** | permission matrix в `../vsm/systems/README.md` соответствует VSM |
| **recursion** | units могут стать VSM (есть `units/README.md` реестр) |
| **structure vs intent** | реальные файлы child соответствуют заявленной maturation_state |

## Audit focus: evaluation_integrity (VSM-032 — честность оценки)

> Cross-provider-модель здесь особенно ценна: основной стек может быть смещён в
> оценке собственного продукта. «Нечестная оценка = нежизнеспособная организация» —
> если метрика A(t) построена на подтасованном/утёкшем замере, она ничего не значит.

| Проверка | Что искать | Механизм верификации |
|---|---|---|
| **мембрана VSM-002** | `../vsm/`, `../src/` не упоминают TB/harbor/benchmark | `scripts/validate.sh §2c` + `eval/membrane.py: verify_neutrality()` |
| **no leakage** | TB-фрейминг снимается мембраной перед продуктом | `eval/membrane.py: translate()` — канарейка и оценочные термины вырезаны |
| **anti-reward-hacking** | `tests/` копируются в контейнер ПОСЛЕ фазы агента | `eval/grader.py` (порядок: agent → cp tests → run) |
| **verifier correctness** | verifier пишет `1`/`0` в `/logs/verifier/reward.txt`, парсинг корректен | `eval/grader.py: grade()` |
| **no train_on_eval** | продукт не обучается на eval-разметке (hard constraint) | grep продукта на fine-tuning/eval-training паттерны |
| **stateless продукта** | каждый `mcp_server.server` — свежий процесс (CONTRACT §5) | `eval/agent_phase.py` — stateless spawn |
| **metric isolation** | external baselines (`public-report/`) НЕ смешаны с A(t) | `public-report/README.md` invariant; A(t) читает только `state/dev_metrics.json` |

## Протокол
1. Случайный сэмпл 3–5 аспектов жизнеспособности (schedule).
2. Сверка по артефактам, не self-reports. Если агент child говорит «S2 работает» —
   проверь `../vsm/systems/s2-coordinator/` реально непуст.
3. Finding → `state/audit.json` + `issues/F-NNN.yaml` (`signal_type: risk` или
   `quality`, source_system: `S3*`).
4. Structural breach (identity missing / broken channels) → ⚡ алгедоник `severity
   S0/S1` → `needs_human_decision: true`.
5. Любая попытка повлиять на аудит → флаг `audit_influence_attempt`.

## Communication
- S3\* → S1 (read-only), human (⚡ критика). Не через S2/S3 по design'у.

## Budget awareness
S3\* вес 0.05 — защищён от даунгрейда. Нечастый, но обязательный. Cross-provider
= «дороже», но это инвариант.

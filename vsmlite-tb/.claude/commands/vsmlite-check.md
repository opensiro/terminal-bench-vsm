---
description: Viability-проверка. /vsmlite-check — invariant-grep + структурные проверки vsmlite.yaml. --audit — независимый S3* structural audit дочернего VSM. --init-check — проверить init-состояние без flip.
argument-hint: "[--audit | --init-check]"
allowed-tools: Read, Bash, Agent
---

# /vsmlite-check

Структурная проверка vsmlite и (опц.) независимый аудит дочернего VSM.

## Режимы

### (без аргумента) — invariant + viability check

1. `scripts/validate.sh` — invariant-grep: core vsmlite не мутирует `../vsm/` и
   `../src/` напрямую (только `child-dispatcher` + read-only `collect_metrics.py`).
2. Проверь `vsmlite.yaml` консистентность:
   - `system_3_star.provider_constraint.must_differ_from == s1`;
   - `identity.never_do` не противоречит `decisions_requiring_human`;
   - `child.path` / `child.src_path` указывают на `../vsm` / `../src`;
   - `synthesis.phases` / `primitives` ссылаются на существующие файлы.
3. Вывод: `verdict: green|yellow|red` + findings.

### `--audit` — независимый S3* structural audit

Спавни `s3-star-auditor` (cross-provider!) для структурного аудита
жизнеспособности `../vsm/`. Это **не** init-check и **не** QA — поиск
нежизнеспособности (identity missing / broken channels / policy conflict / etc.).
Результат → `state/audit.json` + `issues/F-NNN.yaml` для findings.
Structural breach → ⚡ алгедоник.

### `--init-check` — проверить готовность к flip initialized

Прогон [`init/validate_init.md`](../../init/validate_init.md) checks БЕЗ flip
`meta.initialized`. Используется: (а) перед `/vsmlite-init` шагом 5, (б) после
ручных правок для самопроверки.

## Главное

- `--audit` всегда cross-provider (S3\* инвариант).
- Read-only проверки; ничего не мутируешь.
- red → STOP, доложи блокер.

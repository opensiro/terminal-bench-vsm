# Skill: validate_init

## Purpose

Структурный gate в конце `/vsmlite-init` (и переиспользуется в `/vsmlite-check`):
убедиться, что дочерний VSM зарождён корректно, `../src/` подключён, инварианты
соблюдены. **Только после green** — flip `meta.initialized: true` **последним**
(как в vsmforge: флаг это *следствие* формирования, не причина).

## Inputs

- `../vsm/` — материализованный дочерний VSM.
- `../vsm/.intent.yaml` — Phase 0 Intent.
- `../vsm/vsm.yaml` — модель дочернего VSM (с tailored blanks).
- `state/maturation.json` — состояние maturation (vsmlite).
- `scripts/validate.sh` — invariant-grep.

## Checks

1. **Intent записан.** `../vsm/.intent.yaml` существует и непуст; `mission.statement`
   ≠ пусто; `authority.basta_constraint` ≠ пусто.
2. **Child на диске.** `../vsm/` существует и содержит минимальный скелет
   (`vsm.yaml`, `units/README.md`, `CLAUDE.md` — даже если «неактивны» до Phase 6).
3. **`../src/` подключён.** `../vsm/vsm.yaml → system_1` ссылается на `../src/`;
   `../vsm/units/README.md` регистрирует ≥1 юнит.
4. **Tailored blanks заполнены.** В `../vsm/vsm.yaml` нет `# tailored`-полей с
   пустым значением (S3 kpi_list, S4 monitoring, S2 custom_triggers). Если есть —
   вернись к `tailor_child`.
5. **S3\* provider constraint.** В `../vsm/vsm.yaml → system_3_star.provider_constraint.must_differ_from == s1`.
   КРИТИЧНО для независимого аудита.
6. **Invariant-grep green.** `scripts/validate.sh` не находит прямого касания
   `../vsm/` или `../src/` из core vsmlite (только `child-dispatcher` +
   read-only `collect_metrics.py`).
7. **Maturation консистентен.** `state/maturation.json` → `maturation_state: Phase 1`,
   `phase_activated: [S1]`, `child_initialized: false` (станет true ниже).
8. **meta.initialized ещё false.** Должен flipнуться **только** здесь, последним.

## Output

```yaml
# verdict validate_init
verdict: green           # green | yellow | red
findings:
  - { check: "intent_recorded",       status: pass }
  - { check: "child_on_disk",         status: pass }
  - { check: "src_connected",         status: pass }
  - { check: "blanks_tailored",       status: pass }
  - { check: "s3star_provider_diff",  status: pass }
  - { check: "invariant_grep",        status: pass }
  - { check: "maturation_consistent", status: pass }
  - { check: "meta_initialized_last", status: pass }
next: flip_initialized
```

Если `verdict ≠ green` — **не flip'ай** `meta.initialized`. Вернись к
соответствующему playbook (`materialize_child` / `tailor_child`) или к юзеру.

## Flip (только при green)

Через `child-dispatcher`:

```yaml
# ../vsm/vsm.yaml → meta
meta:
  initialized: true       # ← FLIP последним
```

И в vsmlite:

```json
// state/maturation.json
{ "child_initialized": true, "updated": "2026-07-13" }
```

## Anti-patterns

- **Не flip'ай `meta.initialized` до green.** Это нарушает инвариант «флаг —
  следствие формирования». vsmforge `validate_runtime` явно проверяет, что флаг
  не был flipнут раньше.
- **Не игнорируй yellow/red.** Yellow = можно продолжить с пометкой; red = стоп,
  вернись к playbook. Никогда не flip при red.
- **Не мутируй `../vsm/` напрямую при починке.** Если found issue в `../vsm/vsm.yaml`
  — правит `child-dispatcher`, не ядро vsmlite.

## After

- Из init: `/vsmlite-init` завершён. Дочерний VSM в `Phase 1`, `initialized: true`.
  Дальше — `/vsmlite-cycle`.
- Из check (`/vsmlite-check`): отчёт. Если не-init контекст и `verdict: green` —
  ничего flip'ать не надо (уже true).

# `src/` — данные и инфраструктура coding harness продукта

> Этот каталог зарегистрирован как дочерний S1 родительского vsmlite (`../vsm/`)
> на шаге `materialize` пайплайна `/vsmlite-init`. Заполняется на следующих фазах
> созревания VSM, через `s1-dispatcher` дочернего VSM (когда Phase 1 активна).

## Назначение

Здесь живут данные и инфраструктура failure-aware coding harness. Роли каталога:

1. **Failure taxonomy — первичная онтология** (`failure_taxonomy.yaml`):
   классы сбоев → recovery policies. S3 (failure classifier) читает это; S2
   координирует применение; S4 ищет expansions.
2. **Кэш прогонов** — traces + verdicts. Verdict — от продукта: «задача
   решена / сбой / неизвестно» (не от внешнего грейдера; продукт не знает о
   внешней оценке).
3. **Skill DB** — general-purpose coding patterns, пополняется S4.
4. **Session sync** — coordination space для мультиагентных прогонов.

## Hard constraints (NEVER)

- **`optimize_for_specific_evaluator`** — не оптимизироваться под конкретный
  оценочный набор; оставаться general-purpose coding harness.
- **`skip_failure_classification`** — никогда не retry без классификации сбоя
  (blind retry запрещён); всегда failure → classifier → policy → retry.
- **`circumvent_recovery`** — не обходить recovery policies (напр. не повторять
  одну и ту же неудачу >N раз; это задача S2).
- **`modify_parent_directly`** — родительский `../vsmlite/` трогает этот домен
  только через `child-dispatcher` (главный инвариант VSM).

## Intent

- `license_intent: open_source` — coding patterns и recovery policies формируются
  как воспроизводимые и пригодные для опенсорс-сообщества.
- Полная формулировка intent, basta-границ и 4 знаков автономности — в
  `../vsm/.intent.yaml`.

## Доступ

Мутации в этом каталоге — только через `s1-dispatcher` дочернего VSM (Phase 1+).
Родительский vsmlite не трогает `../src/` напрямую (рекурсия VSM: его
`child-dispatcher` работает с дочерним VSM, а не с его S1 напрямую).

_Заполнение этого каталога реальным кодом runtime coding harness — будущие фазы
созревания дочернего VSM. Сейчас здесь skeleton (failure_taxonomy.yaml)._

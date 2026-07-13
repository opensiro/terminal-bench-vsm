# units/ — реестр S1 дочернего VSM

Дочерний S1 = прикладной домен (`../src/`). Регистрируется здесь шагом
`materialize_child` пайплайна `/vsmlite-init`.

## Реестр

`meta.layout: single` (см. `state/domain_draft.yaml`) → один operational unit.

| Юнит | Путь | Роль | Owner | Рекурсия |
|---|---|---|---|---|
| `terminal-bench-solver` | `../src` | агент-решатель + harness + обёртка грейдера Terminal Bench 2.1 | `s1-dispatcher` | может стать VSM при сложности (Split, basta) |

<!-- tailored на /vsmlite-init: если ../src/ содержит несколько подкаталогов
     (meta.layout: siblings), они регистрируются как отдельные юниты. -->

## Рекурсия (OSM §3)

Каждый юнит `../src/<subdir>`, если он достаточно сложен (имеет собственные
S1–S5-потребности), может быть рекурсивно представлен как VSM. Это решение
принимает родительский vsmlite через примитив `Split` (см.
[`../../vsmlite/synthesis/primitives.yaml`](../../vsmlite/synthesis/primitives.yaml))
и требует решения человека (`destructive_primitive`).

## Управление

Доступ к `../src/` — только через `s1-dispatcher` этого VSM (когда S1 активен —
Phase 1+). Родительский vsmlite не трогает `../src/` напрямую (его
`child-dispatcher` работает с этим VSM, а не с его S1 напрямую — рекурсия).

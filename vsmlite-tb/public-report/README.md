# `public-report/` — внешние baseline-карточки (frontier-якорь для A(t))

> **Read-only reference-слой.** Фиксирует ВНЕШНИЕ community/official результаты
> (не наши прогоны) — даёт A(t) frontier-якорь, относительно которого оценивать
> pass_rate продукта. Конвенция заведена в [VSM-028](../issues/VSM-028.yaml).

## Назначение

`vsmlite-tb` хранит собственные прогоны в `state/dev_metrics.json` → индикатор
автономности A(t) ([VSM-004/005](../eval/README.md)). Без внешних baseline-ов
A(t) — число в вакууме: нет точки отсчёта «SOTA / frontier / community-уровень».

`public-report/` закрывает этот gap: **машиночитаемые человекочитаемые карточки**
внешних результатов, которые можно вручную сопоставить с A(t).

## Инвариант: external ≠ A(t)

- Карточки здесь — **read-only reference**. Они **НЕ пишутся** в
  `state/dev_metrics.json` и **НЕ смешиваются** с A(t).
- `state/` = наши прогоны (могут пересчитываться, upsert, idempotent).
  `public-report/` = чужие результаты (фиксация «как сообщено», без пересчёта).
- Карточка явно помечает `Reproducibility` (community-reported / official /
  verified-in-this-repo), чтобы не спутать с A(t).

## Конвенция именования

```
<MODEL>_<BENCH>_<HARNESS>.md
```

- `<MODEL>` — модель + квантизация через `-`, без пробелов: `GLM-5.2-FP8`
- `<BENCH>` — бенчмарк: `TB-2.1`, `SWE-bench-Pro`, …
- `<HARNESS>` — harness прогона: `mini-swe-agent`, `Terminus-2`, …
- Подчёркивания как разделители групп; дефисы внутри группы.

Пример: `GLM-5.2-FP8_TB-2.1_mini-swe-agent.md`

## Формат: Markdown + `_template.md`

[VSM-028 option `md-template`](../issues/VSM-028.yaml): фиксированный набор
полей через шаблон. Нарратив сохраняется (кластеризация fail'ов, caveats),
сравнимость ручная — поля не «плавают» между карточками.

Новая карточка:
```bash
cp public-report/_template.md public-report/<MODEL>_<BENCH>_<HARNESS>.md
# заполнить поля в <угловых скобках>; unknown → явно пометить + caveats
```

Поля шаблона: **Metadata · Headline result · Token budget · Sampling/runtime
config · FAILED · ERRORED · Caveats**. Числа проверять на арифметическую
консистентность (token budget: `input − cache = new`).

## Отличие от соседних артефактов

| Артефакт | Что хранит | Чьё | Меняется |
|---|---|---|---|
| `state/dev_metrics.json` | наши прогоны → A(t) | продукт (наше) | да (upsert) |
| `public-report/*.md` (external) | внешние baseline-ы | community / official | нет (фиксация) |
| `public-report/*.md` (internal snapshot) | structural snapshot нашего продукта — точка отсчёта | продукт (наше) | нет (фиксация на дату) |
| `issues/VSM-*.yaml` | алгедонические сигналы | vsmlite-meta | lifecycle (triage→done) |

### Invariant: internal baseline snapshot

С VSM-032 в `public-report/` появляется **второй тип карточек** — internal
structural snapshot нашего продукта (`Reproducibility: verified-in-this-repo`).
Отличие от external community-карточек и от A(t):

- **internal snapshot** (напр. `vsm-baseline-0.0.1.md`) — фиксация структуры
  продукта на дату (контракты, фаза, A(t) на момент). Это **точка отсчёта**, относительно
  которой benchmark-intelligence (s4-bench-scout) меряет прогресс продукта vs frontier.
- **НЕ пересчитывается** автоматически (в отличие от `state/dev_metrics.json` → A(t),
  который upsert'ится каждым прогоном). Новый snapshot = новая карточка с новым
  version-суффиксом (`vsm-baseline-0.0.2.md`, …).
- **НЕ external**: помечается `Reproducibility: verified-in-this-repo`, чтобы не
  спутать с community-reported числами.
- Pass-rate в snapshot'е может быть **TBD** (если инфра-раннер ещё не готов) —
  это валидное состояние, не ошибка.

Invariant сохранён: external ≠ A(t), и теперь также internal-snapshot ≠ A(t)
(оба живут в `public-report/`, оба read-only-фиксации, не пересчитываются).

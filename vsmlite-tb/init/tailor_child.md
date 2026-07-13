# Skill: tailor_child

## Purpose

Заполнить доменно-специфичные blanks в `../vsm/vsm.yaml` на основе OSM Phase 0
Intent (`.intent.yaml`) и драфта домена (`domain_draft.yaml`). Шаблон
доставляется с пустыми списками и комментарием `# tailored by /vsmlite-init или
/vsmlite-cycle`; этот skill владеет именно их заполнением.

**Переиспользуется:** вызывается и из `/vsmlite-init`, и из `/vsmlite-cycle`
(когда домен меняется или S4 находит новые слабые сигналы).

## Inputs

- `../vsm/.intent.yaml` — Phase 0 Intent.
- `state/domain_draft.yaml` — наблюдённые capabilities/environment/units.
- `../vsm/vsm.yaml` — blanks, помеченные `# tailored`.
- (опц.) `state/intel.json` — если вызывается из cycle, S4 нашёл новое.

## Ask the developer

Короткое интервью, **только** для доменно-специфичных полей (всё остальное
шаблон даёт дефолтом). Если `confidence: high` в драфте — большая часть
заполняется из драфта без вопросов.

1. **KPI** (S3 дочернего): какие 3–5 метрик жизненно важны для этого домена?
   (Не «coverage_ratio» как в Opensiro — *доменные*. Напр. для e-commerce:
   conversion, latency p95, inventory drift.)
2. **Внешняя среда** (S4 дочернего): `competitors`, `technology`, `regulation` —
   что сканировать?
3. **Weak signals**: какие ранние признаки важны? (модель-дрейф, рост эскалаций,
   ...).
4. **Custom triggers конфликтов** (S2 дочернего): какие расхождения между юнитами
   критичны в этом домене?
5. **Premises register**: какие допущения надо перепроверять?

## Output

Правки в `../vsm/vsm.yaml` (через `child-dispatcher`):

```yaml
# ../vsm/vsm.yaml → system_3 (дочерний)
system_3:
  kpi_list:              # tailored — ДОМЕННЫЕ, не копия примера
    - <domain_kpi_1>
    - <domain_kpi_2>

# ../vsm/vsm.yaml → system_4 (дочерний)
system_4:
  monitoring:
    competitors: []      # tailored
    technology: []       # tailored
    regulation: []       # tailored
  weak_signals:
    sources: []          # tailored
  premises_register:     # tailored
    - premise: "..."
      check_frequency: monthly
      invalidation_signal: "..."
      consequence_if_invalid: "..."

# ../vsm/vsm.yaml → system_2 (дочерний)
system_2:
  conflict_detection:
    custom_triggers: []  # tailored — доменные расхождения
```

## Anti-patterns

- **Не копируй пример KPI дословно.** `coverage_ratio` / `validate_pass_rate` —
  это пример из Opensiro, **не** дефолт. Для чужого домена они бессмысленны.
  Шаблон помечен `# tailored` именно чтобы это не попало в прод.
- **Не вставляй фреймворки.** KPI — это *что* измеряем (conversion, drift), а НЕ
  *чем* (Prometheus, Grafana). Runtime — отдельная стадия (когда есть).
- **Не решай за человека доменные KPI.** Это его экспертиза; ты только
  структурируешь.
- **Не мутируй напрямую.** Правки в `../vsm/vsm.yaml` — через `child-dispatcher`.

## After

- Если из init → [`validate_init.md`](validate_init.md).
- Если из cycle → `/vsmlite-cycle` продолжается (S5 triage).

# Skill: scan_domain

## Purpose

Scan-first обзор целевой папки прикладного проекта, куда скопирован vsmlite.
Сформировать драфт-описание домена (миссия, возможности, окружение), который
уточняется на следующем шаге `discover_intent`. Это **расширение vsmlite над
vsmforge** (vsmforge намеренно не сканирует кодовую базу — discovery там
интервью-only). Lite-темплейт позволяет scan-first для скорости обнаружения.

## Inputs

- Рабочий каталог vsmlite (где запущен `/vsmlite-init`).
- `..` — родительский каталог (корень прикладного проекта). Содержит (возможно):
  - `src/` — прикладной домен (дочерний S1). Может существовать заранее.
  - `vsm/` — дочерний VSM. Ожидается, что НЕ существует (Init его создаст).
  - иные материалы: README, доки, заметки, код.
- `../vsmlite.yaml` — для чтения `child.path`, `child.src_path`.

## Scan

**Только read-only.** Никаких мутаций.

1. **Определи `meta.layout`** (где живут будущие юниты дочернего S1):
   - `siblings` — в `../src/` есть несколько подкаталогов-юнитов.
   - `mono` — `../src/` один проект (монолит).
   - `single` — `../src/` пуст или содержит один артефакт.
2. **Прочитай материалы домена** (если есть), не глубже 2 уровней:
   - `../README*`, `../src/README*`, любые `*.md` в `..` и `../src/`.
   - манифесты: `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`,
     `composer.json`, `*.cabal`, etc.
   - структура каталогов `../src/` (`ls`, без содержимого файлов глубже манифеста).
3. **Извлеки наблюдённое:**
   - миссия/назначение (из README/manifest description);
   - capabilities — что домен делает (runtime-independent существительные, НЕ
     фреймворки/языки — это runtime leakage, анти-паттерн);
   - environment — внешние интеграции, провайдеры, клиенты;
   - obvious units — кандидаты в S1-юниты дочернего VSM (по `meta.layout`).
4. **Если материал недостаточен** для драфта — НЕ додумывай. Запиши в `Output`
   `confidence: low` и сформулируй конкретные вопросы для `discover_intent`.

## Output

```yaml
# state/domain_draft.yaml — драфт описания домена (scan-first)
generated: 2026-07-13
scanner: scan_domain (vsmlite init)
meta:
  layout: siblings          # siblings | mono | single
  confidence: medium        # low | medium | high — насколько материал убедителен
observed:
  mission: |                # 1–3 предложения из материалов; "" если не найдено
    ...
  capabilities:             # runtime-independent nouns; НЕ фреймворки
    - { name: "...", tier: core|support, maturity: existing|planned }
  environment:
    providers: []           # { name, kind: llm|cloud|api|... }
    integrations: []
    customers: []
  candidate_units:          # по meta.layout
    - { name: "...", path: ../src/<...>, role: "..." }
  open_questions:           # для discover_intent, если confidence: low
    - "..."
```

## Anti-patterns

- **Не додумывай домен.** Если README пуст / отсутствует — `confidence: low` и
  вопросы в `open_questions`, а не выдуманная миссия.
- **Не выдавай runtime leakage.** Capabilities — это *что* домен делает
  («обрабатывает заявки», «обучает модели»), а НЕ *на чём* («FastAPI сервис с
  PostgreSQL»). Фреймворк/язык/agent-count/graph/transport — анти-паттерн.
- **Не мутируй.** `scan_domain` — read-only. Любой materialize — в
  `materialize_child` через `child-dispatcher`.
- **Не уходи глубже 2 уровней.** Цель — узнать домен, не провести аудит кода.

## After

→ [`discover_intent.md`](discover_intent.md): интервью на основе этого драфта.
Если `confidence: high`, интервью сводится к подтверждению; если `low` — к
дона\uC108ению пропусков.

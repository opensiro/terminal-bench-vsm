# issues/ — алгедонический канал vsmlite

Файловый журнал корректировок и сигналов (`VSM-NNN.yaml`). Это реализация
**алгедонического канала** VSM + общий журнал сигналов vsmlite. Любая система
может записать сигнал; s5-guardian triage'ит и выносит требующие человека в
REPL-дайджест.

## Формат

- **`VSM-NNN.yaml`** — запись сигнала (NNN monotonic, 3+ цифр, **никогда** не
  переиспользуется, даже после `wontfix`). Schema —
  [`vsmlite-issue.schema.json`](vsmlite-issue.schema.json) (JSON Schema 2020-12).
- **`F-NNN.yaml`** — finding независимого аудита (S3\*). Та же schema, `source_system: S3*`.
- **`template.yaml`** — заготовка для копирования.

## Поля (ключевые)

| Поле | Назначение |
|---|---|
| `id` | `VSM-NNN`, monotonic |
| `source_system` | кто поднял (S1/S2/S3/S3\*/S4/S5) |
| `signal_type` | `algedonic` (⚡ байпас) / `quality` / `gap` / `drift` / `budget` / `risk` / `policy` |
| `severity` | `S0` (viability breach) → `S3` (impact, не effort) |
| `target_unit` | `child` (дочерний VSM) / `meta` (сам vsmlite) / доменный юнит (свободная строка) |
| `needs_human_decision` | `true` → в REPL-дайджест как вопрос |
| `status` | `triage → accepted → in-progress → review → done` (или `blocked`/`wontfix`) |
| `decision` | **заполняет человек** (basta_constraint: prepare_only) |
| `primitive` / `phase_from` / `phase_to` | опц., если сигнал запрашивает OSM-операцию |

## Условные правила (enforced schema)

- `severity S0/S1` ⇒ `needs_human_decision: true` (алгедоник).
- `signal_type: algedonic` ⇒ `needs_human_decision: true`.
- `status: wontfix/blocked` ⇒ `decision` обязательна (minLength 3).

## Поток

```
1. Любая система пишет VSM-NNN.yaml (status: triage)
2. s5-guardian triage:
   ├─ needs_human_decision: true → policy_question + options → REPL-дайджест → человек
   └─ operational → маршрутизация S3 / synthesis-operator
3. Ответ человека → VSM-NNN.yaml (status, decision, selected_options)
4. accepted → synthesis-operator планирует → child-dispatcher исполняет
```

## Алгедонический байпас (экстренный)

`severity S0/S1` или `signal_type: algedonic`:
- **минует** очередь S3 (S1 → S5 напрямую);
- s5-guardian выносит в дайджест **первым** с ⚡-маркером;
- человек видит критический запрос немедленно.

## Отличие от opensiro-arctic/vsm

- `target_unit` — **свободная строка** + `'child'`/`'meta'` (не доменный enum):
  темплейт не знает конкретных юнитов будущего домена.
- Нет Gitea-интеграции (`gh`, `gh_url`, `issue-liaison`) — решения в REPL, не во
  внешнем трекере. При необходимости добавить — расширить schema + агент.
- Добавлены `primitive` / `phase_from` / `phase_to` — для OSM-сигналов
  (запрос примитива или перехода фазы).

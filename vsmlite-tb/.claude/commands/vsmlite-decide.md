---
description: Записать решение человека по VSM-NNN. Обновляет status/decision/selected_options в записи. После accept — сигнал synthesis-operator исполнить.
argument-hint: "VSM-NNN <accept|defer|reject|wontfix> [\"причина\"] [--opt <option-id>]"
allowed-tools: Read, Edit, Write, Agent
---

# /vsmlite-decide

Применяет решение человека к `issues/VSM-NNN.yaml`. Юзер отвечает в REPL на
вопросы из дайджеста S5; эта команда фиксирует ответ.

## Что делаешь

1. Прочитай `issues/<VSM-NNN>.yaml`.
2. Обнови поля:
   - `status`: `accept` → `accepted`; `defer` → `triage` (осталось); `reject`/`wontfix` → `wontfix`;
   - `decision`: «<глагол> — <причина>» (из аргумента; если `wontfix`/`blocked` — minLength 3 обязательно по schema);
   - `selected_options`: из `--opt` (если был multiselect);
   - `updated`: сегодня.
3. Если `accept` и в записи есть `primitive` / `phase_to` (OSM-сигнал):
   - Спавни `synthesis-operator` с уведомлением: «VSM-NNN accepted, исполни
     primitive=<...> phase_to=<...>». synthesis-operator сам проверит pre-условия
     и спавнит `child-dispatcher`.
4. `python3 scripts/render_data.py` (обновить `issues[]` в телеметрии).

## Главное

- **Только человек** принимает решение (basta). Эта команда — механическая запись
  его ответа; не интерпретируй, не «дополни».
- Если `decision` пустой при `wontfix`/`blocked` — STOP, schema требует minLength 3.
- Не flip'ай `meta.initialized` (это validate_init).
- Не мутируешь `../` (исполнение accepted — через synthesis-operator → child-dispatcher).

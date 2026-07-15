# S1 — verifier (child) · SKILL

## Tool scope
- **fs.read**: прочитать финальные артефакты, тест-вывод.
- **shell.exec**: при необходимости повторно запустить тесты для финальной проверки.
- **НЕ мутируешь**: ничего. Verifier = read-only final check.

## Контракт
- Вход: plan, trace (post-checkpoint), artifacts diff (с момента checkpoint).
- Выход: JSON `{passed, reason, checks}` (см. output contract).

## Протокол
1. Оцени trace **только с момента последнего checkpoint** (reverted attempts не считаются).
2. Проверки (checks):
   - tests_pass: последний pytest-запуск прошёл.
   - artifacts_coherent: artifacts diff осмыслен (созданы ожидаемые файлы).
   - no_error_keywords: нет error/traceback/failed в post-checkpoint trace.
3. Все checks passed → `{passed: true}`.
4. Любой check failed → `{passed: false}` с конкретной причиной.
5. Верни JSON: passed + reason + checks.

## Communication
- verifier → solver: через final verdict (passed → task_resolved).
- Не общается с S2/S3/S3*/S4/S5 — internal S1 role.

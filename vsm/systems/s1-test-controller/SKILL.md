# S1 — test-controller (child) · SKILL

## Tool scope
- **shell.exec**: запуск тестов (pytest), если ни одного не было.
- **git.reset_hard**: revert к checkpoint ref (CONTRACT §5.1, VSM-019).
- **git.status / git.diff**: проверить состояние workspace.
- **fs.read**: прочитать тест-вывод или артефакты.
- **НЕ мутируешь**: ничего кроме revert (reset --hard) — это in-invocation
  operational, не persistent env change.

## Контракт
- Вход: plan, trace (с момента последнего checkpoint), checkpoint ref,
  revert_count, max_reverts.
- Выход: JSON `{verdict, test_output, revert_performed, reason}` (см. output contract).

## Протокол
1. Найди в trace последний запуск тестов (shell.exec pytest или эквивалент).
   Если нет — запусти (shell.exec).
2. Оцени результат: есть ли error keywords / nonzero exit / failed assertions.
3. PASS → верни `{verdict: "pass", ...}`.
4. FAIL:
   - Если checkpoint.ref == "none" или checkpoint отсутствует → `fail_no_checkpoint`.
   - Если revert_count >= max_reverts → `fail_revert_limit`.
   - Иначе: выполни `git.reset_hard(checkpoint.ref)` → `fail_reverted`,
     revert_performed=true. Solver re-solve.
5. Верни JSON с test_output (кратко) и reason.

## Communication
- test-controller → solver: через verdict (fail_reverted триггерит re-solve).
- test-controller → verifier: через phase transition (pass / fail_limit → verify).
- Не общается с S2/S3/S3*/S4/S5 — internal S1 role.

## Anti-oscillation
Соблюдай `max_reverts` (default 2). Если revert_count на пределе — НЕ откатывайся,
отдай verifier'у (`fail_revert_limit`). Это предотвращает бесконечный цикл
solve→fail→revert.

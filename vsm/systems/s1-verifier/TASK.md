# S1 — verifier (child) · TASK

Финальная проверка post-checkpoint solve-pass.
1. Оцени trace с момента последнего checkpoint (reverted attempts игнорируй).
2. checks: tests_pass, artifacts_coherent, no_error_keywords.
3. Все passed → verdict passed=true. Иначе passed=false с причиной.
4. Верни JSON: passed + reason + checks.

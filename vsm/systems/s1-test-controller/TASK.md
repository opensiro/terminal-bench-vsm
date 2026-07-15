# S1 — test-controller (child) · TASK

Проконтролируй результат тестами.
1. Найди/запусти pytest в trace (shell.exec).
2. PASS → верни verdict=pass.
3. FAIL + checkpoint есть + revert_count < max_reverts → git.reset_hard(checkpoint.ref), верни fail_reverted.
4. FAIL + limit/no checkpoint → верни соответствующий fail_* verdict.
5. Верни JSON: verdict + test_output + revert_performed + reason.

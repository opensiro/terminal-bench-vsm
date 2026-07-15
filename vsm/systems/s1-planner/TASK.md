# S1 — planner (child) · TASK

Декомпозируй задачу в plan.
1. Прочитай task_prompt и workspace (fs.list, fs.read ключевых файлов).
2. Учти recovery_directive (если есть) — env_changes уже применены.
3. Построй минимальный план tool-call шагов.
4. Включи финальный шаг запуска тестов (shell.exec pytest).
5. Верни JSON: steps + rationale.

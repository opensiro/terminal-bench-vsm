"""membrane — TB instruction → нейтральный task_prompt (VSM-002).

Мембрана живёт на стороне родителя: перед тем как задача пересечёт границу в
продукт (../src/ — который benchmark-agnostic), TB-фрейминг снимается.

Что мембрана делает:
  1. Вырезает TB-канарейку (GUID 26b5c67b-...) из текста.
  2. Вырезает явные упоминания оценочных терминов: "terminal bench", "TB",
     "benchmark", "harbor", "t-bench".
  3. verify_neutrality() — assert что ничего не осталось; бросает ошибку иначе.

Продукт видит только нейтральный coding-prompt. Метаполя (difficulty/category)
НЕ пересекают границу — они нужны только родителю для агрегации метрик.
"""
from __future__ import annotations

import re

from .loader import TBTask

# TB-канарейка (Terminal-Bench convention —GUID во всех файлах задачи).
CANARY_PATTERN = re.compile(
    r"#\s*BENCHMARK DATA SHOULD NEVER APPEAR[^\n]*\n?"
    r"|terminal-bench-canary GUID [0-9a-f-]+[^\n]*\n?",
    re.IGNORECASE,
)

# Термины, раскрывающие оценочный фрейминг. Case-insensitive, со word boundaries.
# Порядок: длинные фразы → короткие, чтобы "terminal bench" не оставил "bench".
FORBIDDEN_TERMS = [
    r"terminal[\s-]*bench",
    r"t[\s-]*bench",
    r"benchmark",
    r"harbor[\s-]*framework",
    r"laude[\s-]*institute",
    r"\bharbor\b",
]

FORBIDDEN_RE = re.compile("|".join(FORBIDDEN_TERMS), re.IGNORECASE)


def translate(task: TBTask) -> str:
    """TB instruction.md → нейтральный task_prompt.

    Снимает канарейку + оценочные термины. Возвращает чистый prompt.
    """
    prompt = task.instruction

    # 1. Вырезать канарейку (целиком строки)
    prompt = CANARY_PATTERN.sub("", prompt)

    # 2. Вырезать оценочные термины (заменить на нейтральный контекст).
    #    "complete this terminal bench task" → "complete this task"
    #    "benchmark" → нейтрализуется по контексту.
    prompt = _neutralize_terms(prompt)

    # 3. Схлопнуть лишние пустые строки от вырезаний.
    prompt = re.sub(r"\n{3,}", "\n\n", prompt).strip()

    return prompt


def _neutralize_terms(text: str) -> str:
    """Заменить оценочные фразы на нейтральные формулировки.

    Порядок важен: фразы с контекстом — раньше изолированных терминов, чтобы
    "this Terminal-Bench task" → "this task", а не "this the terminal task".
    """
    replacements = [
        (re.compile(r"this\s+terminal[\s-]*bench\s+task", re.IGNORECASE), "this task"),
        (re.compile(r"the\s+terminal[\s-]*bench\s+task", re.IGNORECASE), "the task"),
        (re.compile(r"a\s+terminal[\s-]*bench\s+task", re.IGNORECASE), "a task"),
        (re.compile(r"terminal[\s-]*bench\s+task", re.IGNORECASE), "the task"),
        (re.compile(r"terminal[\s-]*bench", re.IGNORECASE), "the task"),
        (re.compile(r"t[\s-]*bench", re.IGNORECASE), "the task"),
        (re.compile(r"harbor[\s-]*framework", re.IGNORECASE), "the evaluation framework"),
        (re.compile(r"laude[\s-]*institute", re.IGNORECASE), "the evaluation team"),
        (re.compile(r"\bharbor\b", re.IGNORECASE), "the evaluator"),
        (re.compile(r"\bbenchmark\b", re.IGNORECASE), "evaluation"),
    ]
    for pattern, repl in replacements:
        text = pattern.sub(repl, text)
    return text


def verify_neutrality(prompt: str) -> None:
    """Assert что prompt не содержит оценочных терминов.

    Бросает ValueError с описанием найденных утечек, если что-то осталось.
    Вызывается перед передачей task_prompt в продукт.
    """
    leaks = FORBIDDEN_RE.findall(prompt)
    if leaks:
        found = ", ".join(sorted(set(m.strip() for m in leaks if m.strip())))
        raise ValueError(
            f"membrane leak: нейтральный prompt содержит оценочные термины: {found}"
        )

    # Проверка канарейки
    if CANARY_PATTERN.search(prompt):
        raise ValueError("membrane leak: нейтральный prompt содержит TB-канарейку")

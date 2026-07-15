"""metrics — запись/чтение state/dev_metrics.json (метрика автономности).

Решает открытый вопрос из VSM-004: «где физически живёт Dev Set pass-rate
метрика — vsmlite-tb/state/dev_metrics.json».

Формат (forward-совместим с телеметрией vsmforge):
  {
    "generated": "2026-07-14",
    "dataset": "open-thoughts/OpenThoughts-TB-dev-v2",
    "harness": "claude-code",
    "summary": {"total": 100, "passed": 42, "failed": 50, "error": 8, "pass_rate": 0.42},
    "by_category": {...},
    "by_difficulty": {...},
    "tasks": [{task_id, status, passed, category, difficulty, ...}]
  }

Идемпотентно: summary/by_* всегда пересчитываются из tasks[]. Запись task —
upsert по task_id (повторный прогон перезаписывает).
"""
from __future__ import annotations

import json
import os
import fcntl
import tempfile
import time
from collections import defaultdict
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

from .config import EvalConfig


def load(config: EvalConfig) -> dict:
    """Прочитать dev_metrics.json или вернуть пустой каркас."""
    path = config.dev_metrics_file
    if not path.exists():
        return _empty_skeleton(config)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if "tasks" not in data:
            data["tasks"] = []
        return data
    except (json.JSONDecodeError, OSError):
        return _empty_skeleton(config)


def _empty_skeleton(config: EvalConfig) -> dict:
    return {
        "generated": None,
        "profile": config.profile,        # VSM-026: режим (train/eval-test/eval-dataset)
        "dataset": config.dataset_repo,
        "harness": config.harness_type,
        "summary": {"total": 0, "passed": 0, "failed": 0, "error": 0, "pass_rate": 0.0},
        "by_category": {},
        "by_difficulty": {},
        "tasks": [],
    }


def record(config: EvalConfig, task_result: dict) -> dict:
    """Upssert результата одной задачи в dev_metrics.json.

    task_result: {task_id, status, passed, category, difficulty, agent_duration_sec,
                  trace_len, pytest_passed, pytest_failed, timestamp, error}
    Пересчитывает summary/by_*. Возвращает обновлённый data dict.

    VSM-031: read-modify-write под flock — параллельные trial'ы не теряют
    результаты (раньше last-writer-wins молча дропал чужой task). Атомарный
    _write (tempfile + os.replace) даёт lock-free читателям цельный файл.
    """
    with _locked(config):
        data = load(config)
        data["generated"] = date.today().isoformat()
        data["profile"] = config.profile      # VSM-026: режим
        data["dataset"] = config.dataset_repo
        data["harness"] = config.harness_type

        # Upsert по task_id
        tid = task_result["task_id"]
        tasks = [t for t in data["tasks"] if t.get("task_id") != tid]
        tasks.append(task_result)
        # Сортировка для стабильности (task_id — slug, лексикографически стабен)
        tasks.sort(key=lambda t: t.get("task_id", ""))
        data["tasks"] = tasks

        data["summary"] = _compute_summary(tasks)
        data["by_category"] = _compute_breakdown(tasks, "category")
        data["by_difficulty"] = _compute_breakdown(tasks, "difficulty")

        _write(config, data)
        return data


def record_run(config: EvalConfig) -> dict:
    """Зафиксировать снэпшот текущего прогона в state/eval_history.json (trend).

    Аналог history.json для metrics (render_data.py): один снэпшот в день с
    summary pass-rate + by_difficulty. Нужно для S4 trend extraction и ответа
    «выросла ли проходимость». Вызывается ОДИН РАЗ в конце батча (run_all), не
    на каждую задачу.
    """
    data = load(config)
    summary = data.get("summary", {})
    snapshot = {
        "date": date.today().isoformat(),
        "profile": config.profile,        # VSM-026: режим (trend не смешивается)
        "pass_rate": summary.get("pass_rate", 0.0),
        "total": summary.get("total", 0),
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "error": summary.get("error", 0),
        "harness": config.harness_type,
    }
    # by_difficulty в снэпшот (для trend по сложности)
    by_diff = data.get("by_difficulty", {})
    snapshot["by_difficulty"] = {
        diff: counts.get("pass_rate", 0.0) for diff, counts in by_diff.items()
    }

    history = load_history(config)
    # Заменить снапшот сегодняшнего дня (один в день), иначе добавить
    if history and history[-1].get("date") == snapshot["date"]:
        history[-1] = snapshot
    else:
        history.append(snapshot)
    # Храним последние 90 дней (как history.json в render_data.py)
    history = history[-90:]

    # VSM-031: flock + atomic write для eval_history.json (читается/пишется
    # per-batch; один батч в моменте, но блокировка страхует future-use).
    with _locked_path(_history_path(config)) as path:
        _atomic_write(path, history)
    return snapshot


def load_history(config: EvalConfig) -> list[dict]:
    """Прочитать eval_history.json (trend снэпшоты). Пустой список если нет."""
    path = _history_path(config)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def compute_trend(config: EvalConfig) -> dict:
    """Trend pass-rate: delta к прошлому прогону + направление.

    Возвращает {current, previous, delta, direction: up|down|flat|none}.
    Нужно autonomy.py (eval_sign meets-критерий) и дайджесту S5.
    """
    history = load_history(config)
    if not history:
        return {"current": 0.0, "previous": None, "delta": 0.0, "direction": "none"}
    current = history[-1].get("pass_rate", 0.0)
    if len(history) < 2:
        return {"current": current, "previous": None, "delta": 0.0, "direction": "none"}
    previous = history[-2].get("pass_rate", 0.0)
    delta = round(current - previous, 4)
    if delta > 0.005:
        direction = "up"
    elif delta < -0.005:
        direction = "down"
    else:
        direction = "flat"
    return {"current": current, "previous": previous, "delta": delta, "direction": direction}


def _history_path(config: EvalConfig) -> Path:
    """state/eval_history[_<profile>].json — trend per-режима (VSM-026).

    train → eval_history.json (backward-compat: существующее имя).
    eval-test / eval-dataset → eval_history_<profile>.json (изоляция trend'ов).
    """
    if config.profile == "train":
        return config.results_dir / "eval_history.json"
    return config.results_dir / f"eval_history_{config.profile}.json"


def _compute_summary(tasks: list[dict]) -> dict:
    total = len(tasks)
    passed = sum(1 for t in tasks if t.get("status") == "passed")
    failed = sum(1 for t in tasks if t.get("status") == "failed")
    error = sum(1 for t in tasks if t.get("status") == "error")
    pass_rate = round(passed / total, 4) if total else 0.0
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "error": error,
        "pass_rate": pass_rate,
    }


def _compute_breakdown(tasks: list[dict], key: str) -> dict:
    """Группировка по полю (category/difficulty) → {value: {total, passed, pass_rate}}."""
    groups: dict[str, dict] = defaultdict(lambda: {"total": 0, "passed": 0})
    for t in tasks:
        val = t.get(key) or "unknown"
        groups[val]["total"] += 1
        if t.get("status") == "passed":
            groups[val]["passed"] += 1
    out = {}
    for val, counts in sorted(groups.items()):
        pr = round(counts["passed"] / counts["total"], 4) if counts["total"] else 0.0
        out[val] = {**counts, "pass_rate": pr}
    return out


def _write(config: EvalConfig, data: dict) -> None:
    """Atomic write: tempfile в той же дир + os.replace (VSM-031).

    Читатели без лока видят либо старый, либо новый цельный файл — без torn
    reads. Вызывается уже под _locked() (см. record/record_run).
    """
    _atomic_write(config.dev_metrics_file, data)


@contextmanager
def _locked_path(path: Path, timeout: float = 30.0) -> Iterator[Path]:
    """flock на sidecar <path>.lock вокруг write-транзакции (VSM-031).

    Эталон — src/agent_runtime/state_bus.py:218-245 (flock+LOCK_NB+spin).
    Блокирует до timeout секунд; потом TimeoutError. Возвращает путь —
    чтобы caller писал именно в него. Lock освобождается в finally.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = Path(str(path) + ".lock")
    lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
    deadline = time.time() + timeout
    try:
        while True:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.time() > deadline:
                    raise TimeoutError(f"metrics lock timeout: {path}")
                time.sleep(0.05)
        yield path
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(lock_fd)


@contextmanager
def _locked(config: EvalConfig) -> Iterator[Path]:
    """flock на dev_metrics.json.lock вокруг read-modify-write (VSM-031)."""
    with _locked_path(config.dev_metrics_file) as path:
        yield path


def _atomic_write(path: Path, data) -> None:
    """tempfile в той же директории + os.replace → atomic publish (VSM-031)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp, path)
    except BaseException:
        # Не оставлять мусор (os.replace уже мог пройти — тогда tmp уже нет).
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ── Batch summaries (VSM-030 layer-1 seam, VSM-031 закладывает артефакт) ──
# После eval-батча пишется state/batch_summaries/<batch_id>.json — per-batch
# саммари с pass_rate/tasks/workers/wall_clock. observations/decision/
# issues_raised — светлые плейсхолдеры для VSM-030 layer-2 (S4-наблюдение) и
# layer-3 (S5-решение). VSM-031 только производит артефакт; UI (batches.html) —
# отдельный scope VSM-030.

def batch_summaries_dir(config: EvalConfig) -> Path:
    """state/batch_summaries/ — per-batch артефакты (VSM-030/VSM-031)."""
    return config.results_dir / "batch_summaries"


def record_batch(config: EvalConfig, batch: dict) -> Path:
    """Записать batch-саммари в state/batch_summaries/<batch_id>.json (VSM-031).

    batch: {batch_id, profile, workers, wall_clock_sec, started_at, finished_at,
            tasks[], summary{...}, trend_delta, ...}. Поля observations/decision/
    issues_raised — светлые плейсхолдеры для будущих layer-2/3 (VSM-030).

    Возвращает путь к записанному файлу. Atomic write (tempfile + os.replace);
    батчи не параллелятся между собой, flock страхует future-use.
    """
    out = batch_summaries_dir(config) / f"{batch['batch_id']}.json"
    with _locked_path(out):
        _atomic_write(out, batch)
    return out


def compute_pass_rate(config: EvalConfig) -> float:
    """Текущий pass-rate из dev_metrics.json (0.0 если пусто)."""
    return load(config).get("summary", {}).get("pass_rate", 0.0)


def print_summary(config: EvalConfig) -> None:
    """CLI: вывести человекочитаемый pass-rate + разбивку."""
    data = load(config)
    summary = data.get("summary", {})
    print(f"── {config.profile_meta.metrics_filename} (profile={config.profile}) ──")
    print(f"  dataset: {data.get('dataset', '?')}")
    print(f"  harness: {data.get('harness', '?')}")
    print(f"  generated: {data.get('generated', '—')}")
    print()
    print(f"  summary:")
    print(f"    total:     {summary.get('total', 0)}")
    print(f"    passed:    {summary.get('passed', 0)}")
    print(f"    failed:    {summary.get('failed', 0)}")
    print(f"    error:     {summary.get('error', 0)}")
    print(f"    pass_rate: {summary.get('pass_rate', 0.0):.1%}")
    print()

    by_diff = data.get("by_difficulty", {})
    if by_diff:
        print(f"  by difficulty:")
        for diff, counts in by_diff.items():
            print(f"    {diff:<12} {counts['passed']}/{counts['total']}  "
                  f"({counts['pass_rate']:.1%})")
        print()

    by_cat = data.get("by_category", {})
    if by_cat:
        print(f"  by category (top):")
        sorted_cats = sorted(by_cat.items(), key=lambda x: x[1]["total"], reverse=True)
        for cat, counts in sorted_cats[:10]:
            print(f"    {cat:<30} {counts['passed']}/{counts['total']}  "
                  f"({counts['pass_rate']:.1%})")

#!/usr/bin/env python3
"""collect_metrics.py — read-only сбор метрик из ../vsm/ и ../src/.

Единственное read-only исключение из инварианта «core не трогает ../».
Делает ТОЛЬКО: git log/show, ls, чтение манифестов/README. Никаких мутаций.

Пишет state/live_metrics.json:
  units[]   — юниты дочернего S1 (../src/ подкаталоги или сам ../src/)
  activity[]— {date, total} — коммиты по дням в ../vsm/ (для S1-sign A(t))

Usage:
  python3 scripts/collect_metrics.py
"""
from __future__ import annotations
import json
import subprocess
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
CHILD_VSM = (ROOT / "../vsm").resolve()
CHILD_SRC = (ROOT / "../src").resolve()


def _git(repo: Path, *args: str):
    try:
        out = subprocess.run(["git", "-C", str(repo), *args],
                             capture_output=True, text=True, timeout=10,
                             check=False)
        return out.stdout if out.returncode == 0 else ""
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def collect_units():
    """Сбор юнитов дочернего S1 (../src/)."""
    units = []
    if not CHILD_SRC.exists():
        return units
    # Если ../src/ содержит подкаталоги — они юниты (layout: siblings).
    subdirs = [d for d in CHILD_SRC.iterdir()
               if d.is_dir() and not d.name.startswith(".") and d.name != "node_modules"]
    if len(subdirs) > 1:
        for d in sorted(subdirs):
            commits = _git(d, "rev-list", "--count", "HEAD").strip()
            units.append({
                "name": d.name,
                "path": str(d.relative_to(ROOT.parent)) if d.is_relative_to(ROOT.parent) else str(d),
                "exists": True,
                "commit_count": int(commits) if commits.isdigit() else 0,
                "last_commit_date": _git(d, "log", "-1", "--format=%ci").strip()[:10] or None,
                "status": "active" if commits.isdigit() and int(commits) > 0 else "empty",
                "open_issues": 0,
                "flags": [],
            })
    else:
        # layout: mono | single — весь ../src/ один юнит.
        commits = _git(CHILD_SRC, "rev-list", "--count", "HEAD").strip()
        units.append({
            "name": CHILD_SRC.name,
            "path": str(CHILD_SRC.relative_to(ROOT.parent)) if CHILD_SRC.is_relative_to(ROOT.parent) else str(CHILD_SRC),
            "exists": True,
            "commit_count": int(commits) if commits.isdigit() else 0,
            "last_commit_date": _git(CHILD_SRC, "log", "-1", "--format=%ci").strip()[:10] or None,
            "status": "active" if commits.isdigit() and int(commits) > 0 else "empty",
            "open_issues": 0,
            "flags": [],
        })
    return units


def collect_activity():
    """Коммиты по дням в ../vsm/ — для S1-sign A(t)."""
    if not (CHILD_VSM / ".git").exists():
        return []
    log = _git(CHILD_VSM, "log", "--format=%ad", "--date=short", "--date=format:%Y-%m-%d")
    by_day = Counter(line.strip() for line in log.splitlines() if line.strip())
    return [{"date": d, "total": c} for d, c in sorted(by_day.items())]


def collect_child_vitals():
    """Базовые виталсы ../vsm/ для телеметрии."""
    if not CHILD_VSM.exists():
        return {"exists": False}
    has_vsm_yaml = (CHILD_VSM / "vsm.yaml").exists()
    has_intent = (CHILD_VSM / ".intent.yaml").exists()
    has_claude = (CHILD_VSM / "CLAUDE.md").exists()
    commits = _git(CHILD_VSM, "rev-list", "--count", "HEAD").strip()
    return {
        "exists": True,
        "path": str(CHILD_VSM.relative_to(ROOT.parent)) if CHILD_VSM.is_relative_to(ROOT.parent) else str(CHILD_VSM),
        "has_vsm_yaml": has_vsm_yaml,
        "has_intent": has_intent,
        "has_claude_md": has_claude,
        "commit_count": int(commits) if commits.isdigit() else 0,
    }


def main():
    out = {
        "_comment": "live_metrics.json — read-only метрики из ../vsm/ + ../src/. Пишет collect_metrics.py.",
        "generated": date.today().isoformat(),
        "child_vsm": collect_child_vitals(),
        "units": collect_units(),
        "activity": collect_activity(),
    }
    target = STATE / "live_metrics.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"── collect_metrics ──")
    print(f"  ../vsm/ exists: {out['child_vsm'].get('exists', False)}")
    print(f"  units: {len(out['units'])}")
    print(f"  activity days: {len(out['activity'])}")
    print(f"  → {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

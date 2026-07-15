#!/usr/bin/env python3
"""prebuild_images.py — построить patched overlay-образы для TB-задач (VSM-032).

КОРНЕВАЯ ПРОБЛЕМА (диагностирована при eval-test):
  Все 89 задач TB-2.1 имеют `docker_image = "xiangyangli/<task>:20260204"` в
  task.toml. Harbour видит это и использует prebuilt-образ НАПРЯМУЮ, ИГНОРИРУЯ
  наш overlay Dockerfile (should_use_prebuilt_docker_image → True). Вся overlay
  логика в harbor_run.py:_prepare_overlay_task работала вхолостую: создавала
  Dockerfile с goose+pyyaml+pytest, который harbour никогда не читал.
  Результат: ModuleNotFoundError: yaml → все trials infra_error.

РЕШЕНИЕ (вариант A — docker commit / derive):
  Для каждой задачи строим patched-образ:
    FROM xiangyangli/<task>:<tag>
    RUN <install product deps + goose + common task deps>
  Tag: vsm/<task>:patched
  Затем harbor_run.py патчит task.toml в overlay-copy: docker_image → наш tag.
  Harbour берёт patched-образ (с deps), продукт запускается корректно.

ЗАВИСИМОСТИ (по сканированию всех 89 задач):
  Product runtime: pyyaml (taxonomy_loader), pytest (test-controller)
  Goose: binary + pyyaml (recipe parsing)
  Common task deps: numpy, pandas, scipy, matplotlib, pillow, requests
  Heavy ML (опционально, по флагу): torch, transformers, datasets

БЕЗОПАСНОСТЬ:
  - НЕ мутирует ../vsm, ../src (главный инвариант validate.sh).
  - НЕ мутирует оригинальный датасет (.cache/tb-2-verified/) — патчит только
    overlay-копию в tmpdir (как _prepare_overlay_task).
  - Tag vsm/<task>:patched не collide с оригинальным xiangyangli/<task>.

Usage:
  # построить для 3 задач канарейки (default):
  python3 scripts/prebuild_images.py

  # все 89 задач:
  python3 scripts/prebuild_images.py --all

  # конкретные задачи:
  python3 scripts/prebuild_images.py build-cython-ext constraints-scheduling

  # с heavy ML deps (torch ~2GB, медленно):
  python3 scripts/prebuild_images.py --heavy

  # форсировать rebuild (игнорировать существующий vsm/<task>:patched):
  python3 scripts/prebuild_images.py --force
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / ".cache" / "tb-2-verified"

# Канарейка: 3 задачи разной сложности для первичной проверки.
CANARY_TASKS = ["build-cython-ext", "constraints-scheduling", "torch-pipeline-parallelism"]

# ── Dependency profiles (4 образа покрывают большинство задач) ────────────────
# Каждый профиль = набор pip-пакетов + goose + uv. Профиль auto-detect'ится по
# import-scan'у задачи. Профили кумулятивны (ml ⊃ sci ⊃ core; web ⊃ core).
#
# По сканированию всех 89 задач:
#   core (57 tasks): лёгкий — product runtime + base web utils
#   sci  (22 tasks): + numpy/scipy/pandas/matplotlib (научный стек)
#   ml   (9 tasks):  + torch/transformers (heavy, ~2GB)
#   web  (2 tasks):  + selenium/bs4 (scraping)
PROFILE_DEPS: dict[str, list[str]] = {
    "core": ["pyyaml", "pytest", "requests", "pillow"],
    "sci":  ["numpy", "scipy", "pandas", "matplotlib"],    # + core
    "ml":   ["torch", "transformers"],                      # + core + sci
    "web":  ["selenium", "beautifulsoup4"],                 # + core
}

# import → profile mapping (для auto-detect)
_IMPORT_TO_PROFILE: dict[str, str] = {
    "numpy": "sci", "scipy": "sci", "pandas": "sci", "matplotlib": "sci",
    "torch": "ml", "transformers": "ml", "datasets": "ml",
    "selenium": "web", "bs4": "web",
}

# Stdlib + internal modules to exclude from import scan
_STDLIB = frozenset({
    "os","sys","json","re","pathlib","datetime","time","math","random","collections",
    "itertools","functools","typing","subprocess","shutil","tempfile","argparse","io","csv",
    "base64","hashlib","urllib","logging","traceback","copy","enum","dataclasses","contextlib",
    "abc","unittest","string","textwrap","platform","glob","inspect","importlib","warnings",
    "signal","threading","asyncio","concurrent","queue","socket","struct","codecs","unicodedata",
    "fractions","decimal","statistics","operator","heapq","bisect","array","weakref","gc","ctypes",
    "pprint","uuid","secrets","configparser","sqlite3","xml","html","email","http","zipfile",
    "gzip","tarfile","platform","distutils","site","__future__","types","numbers","locale",
    "calendar","difflib","token","tokenize","ast","dis","compileall","fcntl","fnmatch","venv","stat",
})

_GOOSE_VERSION = "stable"


def _detect_profile(task_dir: Path) -> str:
    """Auto-detect dependency profile для задачи по import-scan.

    Возвращает один из: core, sci, ml, web. Профили кумулятивны:
    ml ⊃ sci ⊃ core; web ⊃ core. Если нужны и ml и web — ml (тяжелее, включает sci).
    """
    found: set[str] = set()
    for root, dirs, files in os.walk(task_dir):
        for f in files:
            if not (f.endswith(".py") or f.endswith(".md") or f.endswith(".sh")):
                continue
            try:
                txt = open(os.path.join(root, f), encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for m in re.finditer(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", txt, re.M):
                mod = (m.group(1) or m.group(2) or "").split(".")[0]
                if mod in _IMPORT_TO_PROFILE:
                    found.add(_IMPORT_TO_PROFILE[mod])
    # priority: ml > sci > web > core (ml includes sci via cumulative deps)
    if "ml" in found:
        return "ml"
    if "sci" in found:
        return "sci"
    if "web" in found:
        return "web"
    return "core"


def _deps_for_profile(profile: str) -> list[str]:
    """Кумулятивный список pip-пакетов для профиля (core всегда включён)."""
    deps = list(PROFILE_DEPS["core"])
    if profile == "sci":
        deps += PROFILE_DEPS["sci"]
    elif profile == "ml":
        deps += PROFILE_DEPS["sci"] + PROFILE_DEPS["ml"]
    elif profile == "web":
        deps += PROFILE_DEPS["web"]
    return deps


def _read_task_docker_image(task_dir: Path) -> str | None:
    """Извлечь docker_image из task.toml (или None если нет)."""
    toml = task_dir / "task.toml"
    if not toml.exists():
        return None
    text = toml.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^docker_image\s*=\s*"([^"]+)"', text, re.M)
    return m.group(1) if m else None


def _image_exists(tag: str) -> bool:
    """Проверить есть ли образ локально."""
    r = subprocess.run(
        ["docker", "image", "inspect", tag],
        capture_output=True, text=True,
    )
    return r.returncode == 0


def _dockerfile_for(base_image: str, profile: str) -> str:
    """Сгенерировать Dockerfile для patched-образа по профилю (core/sci/ml/web).

    Базируется на оригинальном task-образе, досыпает product + profile deps +
    goose binary. --break-system-packages для PEP 668 (python 3.12+).
    """
    all_deps = _deps_for_profile(profile)
    pip_pkgs = " ".join(all_deps)

    return f"""# Patched by scripts/prebuild_images.py (VSM-033) — profile: {profile}
# Adds VSM product runtime deps + goose binary on top of the original task image.
FROM {base_image}

# System deps + dev-tools (triad test-controller needs jq/make/file/tree).
RUN apt-get update -qq && \\
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \\
        python3 python3-pip curl bzip2 libxcb1 libgomp1 gettext \\
        jq make file tree > /dev/null 2>&1 && \\
    rm -rf /var/lib/apt/lists/*

# Python deps: product runtime (pyyaml, pytest) + common task deps.
# --break-system-packages for PEP 668 (externally-managed python 3.12+).
RUN python3 -m pip install --no-cache-dir --quiet --break-system-packages {pip_pkgs}

# uv: pre-install so TB verifier test.sh finds it on PATH (no network at verify).
# Retry wrapper: GitHub release-assets flaky (TLS errors). 5 attempts, backoff.
# If ALL fail, continue — verifier test.sh may fall back to pip; product still runs.
RUN for i in 1 2 3 4 5; do \\
      curl -LsSf https://astral.sh/uv/0.7.13/install.sh | sh && break || \\
      echo "uv attempt $i failed, retrying..." && sleep 10; \\
    done && \\
    ln -sf $HOME/.local/bin/uv /usr/local/bin/uv 2>/dev/null || true && \\
    (uv --version || echo "uv not installed (verifier test.sh will use pip fallback)")

# Goose binary (retry wrapper for flaky TLS; 286MB). 5 attempts.
RUN ARCH=$(uname -m) && \\
    for i in 1 2 3 4 5; do \\
      curl -fsSL https://github.com/aaif-goose/goose/releases/download/{_GOOSE_VERSION}/goose-$ARCH-unknown-linux-gnu.tar.bz2 -o /tmp/goose.tar.bz2 && break || \\
      echo "goose attempt $i failed, retrying..." && sleep 10; \\
    done && \\
    test -s /tmp/goose.tar.bz2 && \\
    tar -xjf /tmp/goose.tar.bz2 -C /tmp && \\
    mv /tmp/goose /usr/local/bin/goose && chmod +x /usr/local/bin/goose && \\
    rm /tmp/goose.tar.bz2 && \\
    goose --version
"""


def _patch_task_toml(task_dir: Path, patched_tag: str) -> None:
    """Заменить docker_image в overlay-копии task.toml на patched tag.

    Мутирует ТОЛЬКО overlay-copy (в tmpdir), не оригинал в .cache/. Это та же
    стратегия что _prepare_overlay_task (copytree → patch).
    """
    toml = task_dir / "task.toml"
    text = toml.read_text(encoding="utf-8")
    patched = re.sub(
        r'(^docker_image\s*=\s*")[^"]+(")',
        rf"\g<1>{patched_tag}\g<2>",
        text,
        count=1,
        flags=re.M,
    )
    toml.write_text(patched, encoding="utf-8")


def prebuild_task(task_id: str, *, force: bool,
                  profile_override: str | None = None) -> str | None:
    """Построить patched-образ для одной задачи.

    Профиль auto-detect'ится по import-scan (_detect_profile), если не задан
    profile_override. Возвращает tag (vsm/<task>:patched) или None если:
      - нет docker_image в task.toml (не prebuilt задача);
      - образ уже есть и не --force.
    """
    task_dir = DATASET / task_id
    if not task_dir.exists():
        print(f"  ✗ {task_id}: task dir not found ({task_dir})", file=sys.stderr)
        return None

    base_image = _read_task_docker_image(task_dir)
    if not base_image:
        print(f"  ⚠ {task_id}: no docker_image in task.toml (build-context task, skip)")
        return None

    patched_tag = f"vsm/{task_id}:patched"

    if _image_exists(patched_tag) and not force:
        print(f"  ✓ {task_id}: {patched_tag} exists (use --force to rebuild)")
        return patched_tag

    # Auto-detect dependency profile (core/sci/ml/web) или override.
    profile = profile_override or _detect_profile(task_dir)
    deps = _deps_for_profile(profile)
    print(f"  📋 {task_id}: profile={profile} deps={len(deps)} ({', '.join(deps[:6])}{'…' if len(deps)>6 else ''})")

    # Pull base image if not local (harbour needs it as FROM).
    if not _image_exists(base_image):
        print(f"  ⬇ {task_id}: pulling base {base_image}...", file=sys.stderr)
        subprocess.run(["docker", "pull", base_image], check=True)

    # Generate Dockerfile + build.
    dockerfile = _dockerfile_for(base_image, profile)
    with tempfile.TemporaryDirectory(prefix=f"vsm-prebuild-{task_id}-") as tmp:
        ctx = Path(tmp)
        (ctx / "Dockerfile").write_text(dockerfile, encoding="utf-8")
        print(f"  🔨 {task_id}: building {patched_tag} (FROM {base_image}, profile={profile})...")
        r = subprocess.run(
            ["docker", "build", "-t", patched_tag, str(ctx)],
            capture_output=False,
        )
        if r.returncode != 0:
            print(f"  ✗ {task_id}: build failed (exit {r.returncode})", file=sys.stderr)
            return None

    # Verify: core deps + goose present.
    print(f"  🔍 {task_id}: verifying deps...")
    checks = {
        "yaml": ["python3", "-c", "import yaml; print(yaml.__version__)"],
        "pytest": ["python3", "-c", "import pytest; print(pytest.__version__)"],
        "goose": ["goose", "--version"],
    }
    all_ok = True
    for name, cmd in checks.items():
        r = subprocess.run(
            ["docker", "run", "--rm", patched_tag] + cmd,
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            ver = r.stdout.strip().splitlines()[-1][:40] if r.stdout.strip() else "ok"
            print(f"     ✓ {name}: {ver}")
        else:
            print(f"     ✗ {name}: FAILED ({r.stderr.strip()[:80]})", file=sys.stderr)
            all_ok = False

    if all_ok:
        print(f"  ✅ {task_id}: {patched_tag} ready")
    else:
        print(f"  ⚠ {task_id}: {patched_tag} built but some checks failed", file=sys.stderr)
    return patched_tag


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="prebuild_images",
        description="Pre-build patched overlay images for TB tasks (VSM-033)",
    )
    parser.add_argument("tasks", nargs="*", help="task_ids (default: canary 3)")
    parser.add_argument("--all", action="store_true",
                        help="all 89 tasks in dataset (slow; builds individually)")
    parser.add_argument("--profile", choices=["core", "sci", "ml", "web"], default=None,
                        help="override auto-detected dependency profile (default: auto-detect)")
    parser.add_argument("--force", action="store_true",
                        help="rebuild even if vsm/<task>:patched exists")
    parser.add_argument("--list", action="store_true",
                        help="list all tasks with profile + docker_image + status")
    args = parser.parse_args()

    if args.list:
        print(f"{'task_id':40} {'profile':8} {'docker_image':50} status")
        print("-" * 110)
        for d in sorted(os.listdir(DATASET)):
            tp = DATASET / d
            if not tp.is_dir():
                continue
            img = _read_task_docker_image(tp) or "(build-context)"
            prof = _detect_profile(tp) if img != "(build-context)" else "—"
            patched = f"vsm/{d}:patched"
            status = "✓ patched" if _image_exists(patched) else "—"
            print(f"{d:40} {prof:8} {img:50} {status}")
        return 0

    if args.all:
        tasks = [d for d in sorted(os.listdir(DATASET))
                 if (DATASET / d).is_dir() and _read_task_docker_image(DATASET / d)]
    elif args.tasks:
        tasks = args.tasks
    else:
        tasks = CANARY_TASKS

    print(f"── prebuild_images: {len(tasks)} task(s) ──")
    if args.profile:
        print(f"  profile: {args.profile} (override; auto-detect skipped)")
    else:
        print(f"  profile: auto-detect per task (core/sci/ml/web)")
    print(f"  force: {args.force}")
    print()

    built = []
    failed = []
    for tid in tasks:
        tag = prebuild_task(tid, force=args.force, profile_override=args.profile)
        (built if tag else failed).append(tid)

    print()
    print(f"── summary ──")
    print(f"  built: {len(built)}/{len(tasks)}")
    if failed:
        print(f"  failed: {', '.join(failed)}")
    print()
    print("harbor_run.py auto-patches task.toml to use vsm/<task>:patched when present.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

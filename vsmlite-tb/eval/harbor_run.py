"""harbor_run — CLI wrapper: resolve paths, run a harbor trial, record the result.

VSM-024: entry point for harbor-based eval runs. The cwd contains a space
("Opensiro Collections") which harbor/docker bind-mounts handle poorly, so this
script generates a resolved config (absolute paths) in /tmp and invokes harbor
trial start with it. After the trial, harbor_bridge parses the output into
dev_metrics.json via the existing metrics.py.

Usage:
    python3 -m eval.harbor_run --task jsonl-aggregator
    python3 -m eval.harbor_run --task jsonl-aggregator --keep-config  # debug

This is the eval entry point for harbor-based runs. Phase 2: runs the real
triad (goose sub-agents) inside the container; API keys are propagated via --ae
from the host goose secrets.yaml so the container never needs the secrets file.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .config import EvalConfig
from .loader import load_tasks
from . import harbor_bridge
from . import metrics


def _resolve_repo_root() -> Path:
    """vsmlite-tb/.. = the monorepo root (parent of this package)."""
    return Path(__file__).resolve().parent.parent.parent


# Cache for API keys read from the host goose secrets.yaml (lazily populated).
_SECRETS: dict[str, str] = {}


def _read_goose_secrets() -> list[str]:
    """Read API keys from ~/.config/goose/secrets.yaml (host) into _SECRETS.

    Returns the list of key NAMES that were found (caller uses them to build
    --ae KEY=VALUE flags). Goose 1.42 stores keys under their provider-specific
    env-var name (ZHIPU_API_KEY for zai). We never print values — only names.
    Falls back to os.environ if the secrets file is absent or unreadable.
    """
    if _SECRETS:
        return list(_SECRETS.keys())

    # Try goose secrets.yaml first (canonical source on this host).
    secrets_path = Path.home() / ".config" / "goose" / "secrets.yaml"
    found: dict[str, str] = {}
    if secrets_path.exists():
        try:
            import re
            for line in secrets_path.read_text(encoding="utf-8").splitlines():
                m = re.match(r"^([A-Z][A-Z0-9_]*_API_KEY)\s*:\s*(.+)$", line.strip())
                if m:
                    found[m.group(1)] = m.group(2).strip().strip('"').strip("'")
        except OSError:
            pass

    # Fall back to env (covers CI / other hosts without a goose secrets file).
    for key in ("ZHIPU_API_KEY", "ANTHROPIC_API_KEY", "ZAI_API_KEY"):
        val = os.environ.get(key)
        if val and key not in found:
            found[key] = val

    _SECRETS.update(found)
    return list(_SECRETS.keys())


# ── Overlay task: extend the task's Dockerfile with goose + deps ──

# Goose version on the host — pin it so the overlay image is reproducible and
# the content-addressed hash stays stable across rebuilds.
_GOOSE_VERSION = "stable"


# ── VSM-033: dependency profiles (mirrors scripts/prebuild_images.py) ─────────
# 4 кумулятивных профиля: core ⊂ sci ⊂ ml; core ⊂ web. Auto-detect'ится по
# import-scan задачи. Применяется к build-context датасетам (TB Dev v2 / train);
# prebuilt (TB-2.1 verified) использует vsm/<task>:patched через _maybe_use_patched_image.
_PROFILE_DEPS: dict[str, list[str]] = {
    "core": ["requests", "pillow"],
    "sci":  ["numpy", "scipy", "pandas", "matplotlib"],
    "ml":   ["torch", "transformers"],
    "web":  ["selenium", "beautifulsoup4"],
}
_PROFILE_IMPORT_MAP: dict[str, str] = {
    "numpy": "sci", "scipy": "sci", "pandas": "sci", "matplotlib": "sci",
    "torch": "ml", "transformers": "ml", "datasets": "ml",
    "selenium": "web", "bs4": "web",
}
_STDLIB_MODULES = frozenset({
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


def _detect_dep_profile(task_dir: Path) -> str:
    """Auto-detect dependency profile (core/sci/ml/web) by import-scan of task.

    Mirror of scripts/prebuild_images.py:_detect_profile. Returns the highest-
    priority profile found: ml > sci > web > core. pyyaml+pytest всегда ставятся
    (product runtime) независимо от профиля.
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
                if mod in _PROFILE_IMPORT_MAP:
                    found.add(_PROFILE_IMPORT_MAP[mod])
    if "ml" in found:
        return "ml"
    if "sci" in found:
        return "sci"
    if "web" in found:
        return "web"
    return "core"


def _prepare_overlay_task(original_task_dir: Path, overlay_dir: Path) -> Path:
    """Copy a task dir and replace its Dockerfile with a goose-enabled overlay.

    Two strategies, chosen by whether vsm-tools:<profile> exists locally:

    VSM-035 OFFLINE (preferred): COPY --from=vsm-tools:<profile>. Tools image
      carries goose/uv/get-pip/wheels, built ONCE on host (where network works)
      by scripts/build_tools_images.py. Zero network RUNs in the overlay → no
      DNS/SSL failures. Host docker build is reliable; harbor-build network is
      not (WSL2+VPN-TUN). 11/15 train tasks died on harbor-build DNS before this.

    VSM-033 LEGACY (fallback): curl/pip RUN with retry-wrapper. Used when
      vsm-tools:<profile> is not built. Less reliable (network in build).

    VSM-033: dependency profile auto-detected per-task (core/sci/ml/web) by
    import scan. Prebuilt datasets (TB-2.1 verified) use vsm/<task>:patched via
    _maybe_use_patched_image instead of this overlay.
    """
    import shutil as _shutil

    profile = _detect_dep_profile(original_task_dir)
    profile_deps = _PROFILE_DEPS[profile]
    tools_tag = f"vsm-tools:{profile}"
    use_offline = _tools_image_exists(tools_tag)

    # Copy the entire task dir (task.toml, instruction.md, environment/, tests/,
    # solution/) — harbor needs the full structure to build + verify.
    _shutil.copytree(original_task_dir, overlay_dir)

    env_dir = overlay_dir / "environment"
    original_dockerfile = env_dir / "Dockerfile"
    if not original_dockerfile.exists():
        raise FileNotFoundError(f"task has no environment/Dockerfile: {original_task_dir}")

    original_content = original_dockerfile.read_text(encoding="utf-8")

    # The original Dockerfile may be multi-stage. We alias its FINAL FROM as
    # 'todo-task-base' so our stage 2 can reference the built task image. The
    # final FROM = the last stage docker builds (what harbor uses as task-image).
    # Aliasing the first FROM breaks multi-stage Dockerfiles (e.g. reverse-
    # engineer-stack-vm: FROM gcc AS builder / FROM debian — aliasing 'gcc'
    # lefts the 'debian' final stage unaliased → 'todo-task-base' unresolved).
    lines = original_content.splitlines()
    last_from_idx = -1
    for i, line in enumerate(lines):
        if line.strip().upper().startswith("FROM "):
            last_from_idx = i  # keep updating → ends on the LAST FROM
    if last_from_idx >= 0:
        line = lines[last_from_idx]
        parts = line.split(maxsplit=2)
        if len(parts) >= 2 and " AS " not in line.upper():
            lines[last_from_idx] = f"{parts[0]} {parts[1]} AS todo-task-base"
        # if it already has an AS alias, docker can still reference it by the
        # user's alias — but our stage-2 needs 'todo-task-base'. Append a comment
        # marker; the COPY-from-tools layer doesn't depend on the base name being
        # exactly 'todo-task-base' as long as the final stage is the default.
    patched_original = "\n".join(lines)

    # VSM-039: parse the task's effective WORKDIR = the LAST `WORKDIR <path>`
    # directive at or after the final FROM (this is the cwd docker sets for the
    # container's main process). Expose it as TASK_WORKDIR env so the product
    # adapter can prefer it over the /app-first probe (VSM-039 root cause: probe
    # finds /app first because overlay mkdir /app always creates it, masking the
    # real task WORKDIR like /workdir → artifact/exec path mismatch).
    task_workdir = ""
    search_lines = lines[last_from_idx:] if last_from_idx >= 0 else lines
    for line in search_lines:
        s = line.strip()
        if s.upper().startswith("WORKDIR "):
            wd = s.split(None, 1)[1].strip() if len(s.split(None, 1)) > 1 else ""
            # Strip inline comments and surrounding quotes.
            wd = wd.split("#")[0].strip().strip('"').strip("'")
            if wd:
                task_workdir = wd  # keep updating → ends on the LAST WORKDIR

    deps_str = " ".join(profile_deps)
    strategy_note = (
        "# VSM-035 OFFLINE strategy: COPY --from=vsm-tools:%s (zero network RUN).\n"
        "# Run scripts/build_tools_images.py to build tools images.\n" % profile
        if use_offline else
        "# VSM-033 LEGACY strategy: curl/pip RUN w/ retry (build vsm-tools:%s\n"
        "# via scripts/build_tools_images.py for offline reliability).\n" % profile
    )

    overlay_dockerfile = (
        "# ── Overlay Dockerfile (generated by eval/harbor_run.py) ──\n"
        "# Extends the task's original image with goose + deps for the VSM product.\n"
        + strategy_note +
        "# Harbor caches this image by build-context hash; deps install once at build.\n\n"
        f"{patched_original}\n\n"
    )
    # VSM-039: expose the task's parsed WORKDIR as TASK_WORKDIR env. Must be set
    # in the FINAL stage (after FROM todo-task-base) to survive into the running
    # container — ENV doesn't cross multi-stage FROM boundaries. Injected into
    # both branches below via workdir_env. Empty → adapter falls back to probe.
    workdir_env = f"ENV TASK_WORKDIR={task_workdir}\n" if task_workdir else ""

    if use_offline:
        # ── VSM-035 offline: COPY binaries+wheels from tools image, pip --no-index ──
        # VSM-036 fix: apt-get MUST install python3/python3-pip (ubuntu-base tasks
        # like acl-permissions have no python). Also mkdir /app — harbour defaults
        # cwd=/app but tasks without WORKDIR don't create it → OCI chdir fails.
        overlay_dockerfile += (
            f"# ── tools stage (offline binaries + wheels, profile={profile}) ──\n"
            f"FROM {tools_tag} AS tools\n\n"
            "# ── final: task image + tools layered via COPY (zero network) ──\n"
            "FROM todo-task-base\n"
            + workdir_env +
            "# python3 + pip: ubuntu-base tasks have NO python (acl, etc). curl/bzip2\n"
            "# for goose/uv extraction; libxcb1/libgomp1 for goose runtime deps.\n"
            "RUN apt-get update -qq && \\\n"
            "    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \\\n"
            "        python3 python3-pip curl bzip2 libxcb1 libgomp1 jq make file tree > /dev/null 2>&1 && \\\n"
            "    rm -rf /var/lib/apt/lists/*\n"
            "# VSM-036: ensure /app exists (harbour defaults cwd=/app; tasks without\n"
            "# WORKDIR don't create it → OCI exec 'chdir /app failed'). mkdir is idempotent\n"
            "# and harmless for tasks that already have /app or use /workdir.\n"
            "RUN mkdir -p /app\n"
            "# Binaries from tools image (goose, uv) + get-pip for broken-python intent.\n"
            "COPY --from=tools /opt/bin/goose /usr/local/bin/goose\n"
            "COPY --from=tools /opt/bin/uv    /usr/local/bin/uv\n"
            "COPY --from=tools /opt/get-pip.py /tmp/get-pip.py\n"
            "# Wheels for BOTH python 3.11 and 3.13 (task images vary). pip picks compatible.\n"
            "COPY --from=tools /opt/wheels /tmp/wheels\n"
            "# Bootstrap pip if missing (broken-python intent = python broken by design).\n"
            "RUN if ! python3 -m pip --version >/dev/null 2>&1; then \\\n"
            "      python3 /tmp/get-pip.py --break-system-packages >/dev/null 2>&1 || true; \\\n"
            "    fi\n"
            "# Install profile deps OFFLINE (--no-index --find-links = local wheels only).\n"
            f"RUN python3 -m pip install --no-cache-dir --quiet --break-system-packages \\\n"
            f"      --no-index --find-links=/tmp/wheels pyyaml pytest {deps_str} || \\\n"
            "    echo 'WARN: some deps not in offline wheels (product may fail)'\n"
            "RUN python3 -c \"import yaml, pytest; print('offline deps OK')\" 2>/dev/null \\\n"
            "    || echo 'WARN: yaml/pytest missing (product will infra_error)'\n"
        )
    else:
        # ── VSM-033 legacy: curl/pip RUN with retry (fallback when no tools image) ──
        overlay_dockerfile += (
            "# ── Stage 2: goose + python deps layered on top of the task image ──\n"
            "FROM todo-task-base\n"
            + workdir_env +
            "RUN apt-get update -qq && \\\n"
            "    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \\\n"
            "        python3 python3-pip curl bzip2 libxcb1 libgomp1 > /dev/null 2>&1 && \\\n"
            "    rm -rf /var/lib/apt/lists/*\n"
            # VSM-035 retry-wrapper (5 attempts) + get-pip bootstrap for broken-python.
            "RUN if ! python3 -m pip --version >/dev/null 2>&1; then \\\n"
            "      for i in 1 2 3 4 5; do curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py && break || \\\n"
            "        echo \"get-pip attempt $i failed, retrying...\" && sleep $((i*3)); done; \\\n"
            "      python3 /tmp/get-pip.py --break-system-packages >/dev/null 2>&1 || true; \\\n"
            "    fi\n"
            "RUN for i in 1 2 3 4 5; do python3 -m pip install --no-cache-dir --quiet --break-system-packages pyyaml pytest "
            f"{deps_str} && break || echo \"pip attempt $i failed, retrying...\" && sleep $((i*3)); done && \\\n"
            "    python3 -c \"import yaml, pytest; print('deps OK')\" || echo \"WARN: deps incomplete (product may fail)\"\n"
            "RUN apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \\\n"
            "    --no-install-recommends jq make file tree > /dev/null 2>&1 && \\\n"
            "    rm -rf /var/lib/apt/lists/*\n"
            "RUN for i in 1 2 3 4 5; do curl -LsSf https://astral.sh/uv/0.7.13/install.sh | sh && break || \\\n"
            "      echo \"uv attempt $i failed, retrying...\" && sleep $((i*5)); done; \\\n"
            "    ln -sf $HOME/.local/bin/uv /usr/local/bin/uv 2>/dev/null || true && \\\n"
            "    (uv --version || echo 'WARN: uv install failed (verifier test.sh will use pip fallback)')\n"
            "RUN ARCH=$(uname -m) && \\\n"
            "    for i in 1 2 3; do \\\n"
            f"      curl -fsSL https://github.com/aaif-goose/goose/releases/download/{_GOOSE_VERSION}/"
            "goose-$ARCH-unknown-linux-gnu.tar.bz2 -o /tmp/goose.tar.bz2 && break || \\\n"
            "      echo \"attempt $i failed, retrying...\" && sleep 5; \\\n"
            "    done && \\\n"
            "    test -s /tmp/goose.tar.bz2 && \\\n"
            "    tar -xjf /tmp/goose.tar.bz2 -C /tmp && \\\n"
            "    mv /tmp/goose /usr/local/bin/goose && chmod +x /usr/local/bin/goose && \\\n"
            "    rm /tmp/goose.tar.bz2 && \\\n"
            "    goose --version\n"
        )

    original_dockerfile.write_text(overlay_dockerfile, encoding="utf-8")
    return overlay_dir


# ── VSM-032: patched prebuilt images ─────────────────────────────────────────
# Все 89 TB-задач prebuilt (docker_image в task.toml). Harbour видит это и
# использует prebuilt-образ напрямую, ИГНОРИРУЯ наш overlay Dockerfile. Поэтому
# overlay (с goose+pyyaml) никогда не применялся → ModuleNotFoundError: yaml.
# Fix: scripts/prebuild_images.py строит vsm/<task>:patched (base image + deps).
# Здесь — патчим task.toml в overlay-copy: docker_image → vsm/<task>:patched.
# Harbour берёт patched-образ (с deps), продукт запускается корректно.

_PATCHED_TAG_RE = re.compile(r'^docker_image\s*=\s*"[^"]+"', re.M)


def _tools_image_exists(tools_tag: str) -> bool:
    """Проверить есть ли vsm-tools:<profile> образ локально (VSM-035 offline).

    Если есть — _prepare_overlay_task генерирует overlay с COPY --from (zero
    network). Если нет — fallback на legacy curl/pip RUN с retry-wrapper.
    Build tools: python3 scripts/build_tools_images.py
    """
    import subprocess as _sp
    r = _sp.run(["docker", "image", "inspect", tools_tag],
                capture_output=True, text=True)
    return r.returncode == 0


def _maybe_use_patched_image(overlay_dir: Path, task_id: str) -> bool:
    """Если vsm/<task>:patched существует — патчим task.toml на него.

    Возвращает True если patched-образ использован (overlay Dockerfile не нужен),
    False если нет (overlay Dockerfile работает как раньше для build-context задач).
    """
    import subprocess as _sp
    patched_tag = f"vsm/{task_id}:patched"
    # Быстрая проверка: есть ли образ локально?
    r = _sp.run(["docker", "image", "inspect", patched_tag],
                capture_output=True, text=True)
    if r.returncode != 0:
        return False  # нет patched-образа → оригинальный flow
    toml_path = overlay_dir / "task.toml"
    if not toml_path.exists():
        return False
    text = toml_path.read_text(encoding="utf-8")
    if not _PATCHED_TAG_RE.search(text):
        return False  # нет docker_image в task.toml (build-context задача)
    patched_text = _PATCHED_TAG_RE.sub(f'docker_image = "{patched_tag}"', text)
    toml_path.write_text(patched_text, encoding="utf-8")
    print(f"  patched: task.toml → {patched_tag}", file=sys.stderr)
    return True


def _generate_config(task_path: Path, trials_dir: Path, config_out: Path) -> Path:
    """Render the harbor trial config with absolute paths substituted.

    Copies the template and replaces <ABS_*> placeholders. Paths with spaces
    ("Opensiro Collections") are kept verbatim — harbor passes them to docker
    which accepts quoted bind-mount sources.
    """
    repo = _resolve_repo_root()
    template = Path(__file__).resolve().parent / "harbor_config_template.yaml"
    text = template.read_text(encoding="utf-8")
    replacements = {
        "<ABS_SRC>": str(repo / "src"),
        "<ABS_VSM>": str(repo / "vsm"),
        "<ABS_EVAL>": str(Path(__file__).resolve().parent),
        "<ABS_TASK>": str(task_path),
        "<ABS_TRIALS>": str(trials_dir),
    }
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
    config_out.write_text(text, encoding="utf-8")
    return config_out


def run_trial(task_id: str, config: EvalConfig, keep_config: bool = False) -> dict:
    """Run one harbor trial for task_id, parse it, record into dev_metrics.json.

    Returns the task_result dict that was recorded.
    """
    trials_dir = config.results_dir / "harbor-trials"
    trials_dir.mkdir(parents=True, exist_ok=True)

    # Resolve the task dir from the dataset cache (same loader the old eval used).
    tasks = load_tasks(config)
    task = next((t for t in tasks if t.task_id == task_id), None)
    if task is None:
        print(f"✗ task not found: {task_id}", file=sys.stderr)
        return {}

    task_path = task.task_dir

    with tempfile.TemporaryDirectory(prefix="harbor-cfg-") as tmpdir:
        tmpdir_path = Path(tmpdir)
        config_path = tmpdir_path / "harbor-config.yaml"
        _generate_config(task_path, trials_dir, config_path)

        # Build an overlay task dir: copy the task verbatim, then replace the
        # environment/Dockerfile with one that extends the original image and
        # bakes in goose + deps. Harbor content-addresses the image by build
        # context hash, so the overlay image is built ONCE and reused across
        # trials — no per-trial runtime install. Best-practice Docker layering.
        overlay_path = _prepare_overlay_task(task_path, tmpdir_path / "task")

        # VSM-032: если vsm/<task>:patched существует — патчим task.toml overlay-copy
        # на patched-образ. Harbour возьмёт его (с deps), overlay Dockerfile не нужен.
        # Если нет — overlay Dockerfile работает как раньше (build-context задачи).
        _maybe_use_patched_image(overlay_path, task_id)

        print(f"── harbor trial: {task_id} ──", file=sys.stderr)
        print(f"  task: {task_path}", file=sys.stderr)
        print(f"  overlay: {overlay_path}", file=sys.stderr)
        print(f"  config: {config_path}", file=sys.stderr)
        print(f"  trials: {trials_dir}", file=sys.stderr)

        cmd = [
            "harbor", "trial", "start",
            "--path", str(overlay_path),
            "--config", str(config_path),
            "--trials-dir", str(trials_dir),
        ]

        # Propagate LLM API keys into the container as env overlay (--ae). Goose
        # sub-agents (triad planner/test-controller/verifier) read these to call
        # the model. Keys are read from the host goose secrets.yaml (not env, which
        # is empty for these names), so the container doesn't need the file mounted.
        # ZHIPU_API_KEY → zai/glm-5.2 (S1/S2/S3/S4/S5); ANTHROPIC_API_KEY → S3* (opt).
        for key in _read_goose_secrets():
            cmd.extend(["--ae", f"{key}={_SECRETS[key]}"])
            print(f"  --ae {key}=<redacted>", file=sys.stderr)

        print(f"  $ {' '.join(cmd[:6])} ...", file=sys.stderr)

        # Harbor runs under its own python (uv tools); it imports our ProductAdapter
        # via import_path "eval.harbor_adapter:ProductAdapter". For that import to
        # resolve, our cwd (the vsmlite-tb/ root containing the eval/ package) must
        # be on PYTHONPATH. subprocess inherits env, so prepend cwd explicitly.
        env = os.environ.copy()
        cwd_abs = str(Path(__file__).resolve().parent.parent)
        env["PYTHONPATH"] = cwd_abs + os.pathsep + env.get("PYTHONPATH", "")

        proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if proc.stdout:
            print(proc.stdout, file=sys.stderr)
        if proc.returncode != 0:
            # Trial failed (timeout, infra error), but harbor still writes a trial
            # dir with partial result.json (exception_info, timing). Don't bail —
            # fall through to parse_trial so the failure is recorded in metrics
            # instead of silently dropped.
            print(f"⚠ harbor trial non-zero exit {proc.returncode} (parsing partial trial)", file=sys.stderr)
            print(proc.stderr, file=sys.stderr)

        if keep_config:
            kept = trials_dir / f"{task_id}-last-config.yaml"
            shutil.copy(config_path, kept)
            print(f"  config kept: {kept}", file=sys.stderr)

    # Parse the most recent trial for this task.
    trial_dir = harbor_bridge.find_latest_trial(trials_dir, task_id)
    if trial_dir is None:
        print(f"✗ no trial dir found for {task_id} in {trials_dir}", file=sys.stderr)
        return {}

    print(f"  parsing trial: {trial_dir.name}", file=sys.stderr)
    task_result = harbor_bridge.parse_trial(trial_dir)

    # Enrich with category/difficulty from task.toml (harbor doesn't carry TB metadata).
    task_result["category"] = task.meta.category
    task_result["difficulty"] = task.meta.difficulty

    # Record into dev_metrics.json via the existing writer (idempotent upsert).
    recorded = harbor_bridge.record_trial(config, task_result)
    summary = recorded.get("summary", {})
    print(f"  recorded: {task_result['status']} "
          f"(trace_len={task_result['trace_len']}, "
          f"duration={task_result['agent_duration_sec']}s)", file=sys.stderr)
    print(f"  dev_metrics: pass_rate={summary.get('pass_rate', 0.0):.1%} "
          f"({summary.get('passed', 0)}/{summary.get('total', 0)})", file=sys.stderr)
    return task_result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a harbor trial for one task.")
    parser.add_argument("--task", required=True, help="task_id to run")
    parser.add_argument("--keep-config", action="store_true",
                        help="keep the resolved harbor config for debugging")
    parser.add_argument("--dataset-dir", default=None,
                        help="override dataset cache dir (env EVAL_DATASET_DIR)")
    parser.add_argument("--finalize", action="store_true",
                        help="after the trial, write an eval_history snapshot "
                             "(metrics.record_run) — фиксирует точку T0/T1 для trend "
                             "при интервальных прогонах (одиночный harbor trial start "
                             "не вызывает record_run сам; только _run_batch делает)")
    args = parser.parse_args()

    config = EvalConfig()
    if args.dataset_dir:
        config.dataset_dir = Path(args.dataset_dir)

    result = run_trial(args.task, config, keep_config=args.keep_config)

    # VSM-031: --finalize — для интервальных прогонов (канарейка/полный датасет
    # по частям). Один harbor trial start не пишет eval_history snapshot; без него
    # trend T0→T1 не фиксируется. record_run пишет daily-snapshot (один в день).
    if args.finalize and result:
        snapshot = metrics.record_run(config)
        trend = metrics.compute_trend(config)
        print(f"── finalize ──", file=sys.stderr)
        print(f"  eval_history snapshot: pass_rate={snapshot.get('pass_rate', 0.0):.1%} "
              f"({snapshot.get('passed', 0)}/{snapshot.get('total', 0)})", file=sys.stderr)
        print(f"  trend: {trend['direction']} (delta={trend['delta']:+.1%})", file=sys.stderr)
        print(f"  → {metrics._history_path(config)}", file=sys.stderr)

    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())

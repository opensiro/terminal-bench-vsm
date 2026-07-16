#!/usr/bin/env python3
"""build_tools_images.py — построить vsm-tools:<profile> (VSM-035 offline-fix).

КОРНЕВАЯ ПРОБЛЕМА (Round 1+2 train-batches):
  Harbor-build network ненадёжна (WSL2+VPN-TUN): DNS timeout на
  pypi.org/ghcr.io/github.com, SSL_ERROR на release-assets. Retry-wrapper
  ловит часть, но base-pull на ghcr.io и goose-download всё равно падают —
  11/15 задач Round 2 упали на build-network, продукт не запускался.

КЛЮЧЕВОЕ НАБЛЮДЕНИЕ: host `docker build` РАБОТАЕТ (DNS 172.22.160.1, pip pyyaml
OK). Падал именно harbor-build (docker compose / иной network context). Значит
tools-образы строятся надёжно на host, а overlay получает их через COPY.

РЕШЕНИЕ (tools-слой по профилям, переиспользует категоризацию prebuild_images):
  Один раз строим vsm-tools:<profile> (core/sci/ml/web) через host docker build.
  Каждый содержит готовые бинарники (goose, uv, get-pip.py) + wheels своего
  профиля. Overlay затем COPY --from=vsm-tools:<profile> — НОЛЬ сетевых RUN,
  шарится между всеми задачами этого профиля.

  vsm-tools:<profile>  (host docker build, сеть работает)
    /opt/bin/goose, /opt/bin/uv, /opt/get-pip.py
    /opt/wheels/<profile-pkgs>.whl   (скачаны в builder-стадии)

  overlay Dockerfile (per task, zero network):
    FROM <task-base> AS todo-task-base
    FROM vsm-tools:<auto-detect profile> AS tools
    FROM todo-task-base
    COPY --from=tools /opt/bin/goose  /usr/local/bin/goose
    COPY --from=tools /opt/bin/uv     /usr/local/bin/uv
    COPY --from=tools /opt/wheels     /tmp/wheels
    COPY --from=tools /opt/get-pip.py /tmp/get-pip.py
    RUN (pip bootstrap если нет) + pip install --no-index --find-links=/tmp/wheels ...

PYTHON-ВЕРСИИ: task-образы на python 3.11 и 3.13. Wheels pyyaml/numpy
version-specific (cp311/cp313). Builder качает wheels для обеих версий в одну
директорию; pip install --no-index --find-links в task-образе выбирает
совместимый автоматически.

БЕЗОПАСНОСТЬ:
  - НЕ мутирует ../vsm, ../src (главный инвариант validate.sh).
  - Только host-side docker build образов vsm-tools:*.

Usage:
  python3 scripts/build_tools_images.py                # core+sci (быстро, покрывает большинство)
  python3 scripts/build_tools_images.py --all          # все 4: core/sci/ml/web (ml ~2GB)
  python3 scripts/build_tools_images.py core sci       # конкретные профили
  python3 scripts/build_tools_images.py --force        # rebuild даже если образ есть
  python3 scripts/build_tools_images.py --list         # статус образов
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import prebuild_images as _pb  # noqa: E402  (переиспользуем PROFILE_DEPS, _deps_for_profile)

# Все 4 профиля. ml/web тяжёлые; default = core+sci (покрывает ~79/89 задач).
ALL_PROFILES = ["core", "sci", "ml", "web"]
DEFAULT_PROFILES = ["core", "sci"]

_UV_VERSION = "0.7.13"
_GOOSE_VERSION = _pb._GOOSE_VERSION  # "stable"


def _image_exists(tag: str) -> bool:
    r = subprocess.run(["docker", "image", "inspect", tag],
                       capture_output=True, text=True)
    return r.returncode == 0


def _tools_dockerfile(profile: str) -> str:
    """Dockerfile для vsm-tools:<profile>.

    Multi-stage: builder качает wheels для python 3.11, 3.12, 3.13 (task-образы
    разные: python:3.x-slim, ubuntu-apt python3.12, ghcr python-3-13), final-stage
    minimal — кладёт binaries + wheels в /opt/.

    VSM-036 note: 3.12 added — ubuntu-base tasks (apt-get install python3) get
    system python 3.12.3, which had NO matching wheel (only 3.11/3.13 were
    built) → 'No module named yaml' infra_error. Now covered.
    """
    pkgs = _pb._deps_for_profile(profile)
    pkgs_str = " ".join(pkgs)

    return f"""# vsm-tools:{profile} — offline tools+deps layer (VSM-035).
# Built by scripts/build_tools_images.py via host `docker build` (network works
# on host; harbor-build network is unreliable — this image removes all network
# RUNs from the per-task overlay).

# ── Builder: download wheels for python 3.11, 3.12, 3.13 (task images vary) ──
FROM python:3.11-slim AS py311
RUN pip download --dest /wheels311 --only-binary=:all: {pkgs_str} || \\
    pip download --dest /wheels311 {pkgs_str}

FROM python:3.12-slim AS py312
RUN pip download --dest /wheels312 --only-binary=:all: {pkgs_str} || \\
    pip download --dest /wheels312 {pkgs_str}

FROM python:3.13-slim AS py313
RUN pip download --dest /wheels313 --only-binary=:all: {pkgs_str} || \\
    pip download --dest /wheels313 {pkgs_str}

# ── Final: binaries + merged wheels in /opt/ ──
FROM debian:bookworm-slim
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \\
        curl ca-certificates bzip2 xz-utils && \\
    rm -rf /var/lib/apt/lists/*

# goose binary (286MB). Retry wrapper: flaky TLS. Download ONCE here on host.
RUN ARCH=$(uname -m) && mkdir -p /opt/bin && \\
    for i in 1 2 3 4 5; do \\
      curl -fsSL https://github.com/aaif-goose/goose/releases/download/{_GOOSE_VERSION}/goose-$ARCH-unknown-linux-gnu.tar.bz2 \\
        -o /tmp/goose.tar.bz2 && break || \\
      echo "goose attempt $i failed, retrying..." && sleep $((i*5)); \\
    done && test -s /tmp/goose.tar.bz2 && \\
    tar -xjf /tmp/goose.tar.bz2 -C /tmp && mv /tmp/goose /opt/bin/goose && \\
    chmod +x /opt/bin/goose && rm /tmp/goose.tar.bz2 && /opt/bin/goose --version

# uv binary. Retry wrapper.
RUN mkdir -p /opt/bin && \\
    for i in 1 2 3 4 5; do \\
      curl -fsSL https://github.com/astral-sh/uv/releases/download/{_UV_VERSION}/uv-x86_64-unknown-linux-gnu.tar.gz \\
        -o /tmp/uv.tar.gz && break || \\
      echo "uv attempt $i failed, retrying..." && sleep $((i*5)); \\
    done && test -s /tmp/uv.tar.gz && \\
    tar -xzf /tmp/uv.tar.gz -C /tmp && cp /tmp/uv-*/uv /opt/bin/uv && \\
    chmod +x /opt/bin/uv && rm -rf /tmp/uv.tar.gz /tmp/uv-* && /opt/bin/uv --version

# get-pip.py (для intent-сломанных python образов, напр. broken-python).
RUN mkdir -p /opt && curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /opt/get-pip.py

# Merged wheels from all three python versions → /opt/wheels.
RUN mkdir -p /opt/wheels
COPY --from=py311 /wheels311/ /opt/wheels/
COPY --from=py312 /wheels312/ /opt/wheels/
COPY --from=py313 /wheels313/ /opt/wheels/
RUN ls /opt/wheels | wc -l && echo "wheels staged for profile {profile}"
"""


def build_profile(profile: str, *, force: bool) -> bool:
    """Построить vsm-tools:<profile> через host docker build."""
    tag = f"vsm-tools:{profile}"
    if _image_exists(tag) and not force:
        print(f"  ✓ {tag}: exists (use --force to rebuild)")
        return True

    pkgs = _pb._deps_for_profile(profile)
    print(f"\n── building {tag} (pkgs: {', '.join(pkgs)}) ──")
    dockerfile = _tools_dockerfile(profile)

    with tempfile.TemporaryDirectory(prefix=f"vsm-tools-{profile}-") as tmp:
        ctx = Path(tmp)
        (ctx / "Dockerfile").write_text(dockerfile, encoding="utf-8")
        r = subprocess.run(
            ["docker", "build", "-t", tag, str(ctx)],
            # capture stdout/stderr to our stderr (progress visible, not mixed).
        )
        if r.returncode != 0:
            print(f"  ✗ {tag}: build FAILED (exit {r.returncode})", file=sys.stderr)
            return False

    # Verify the image carries the key binaries + at least core wheels.
    print(f"  🔍 verifying {tag}...")
    checks = [
        ("goose", ["docker", "run", "--rm", "--entrypoint", "/opt/bin/goose", tag, "--version"]),
        ("uv", ["docker", "run", "--rm", "--entrypoint", "/opt/bin/uv", tag, "--version"]),
        ("get-pip", ["docker", "run", "--rm", "--entrypoint", "test", tag, "-s", "/opt/get-pip.py"]),
        ("wheels", ["docker", "run", "--rm", "--entrypoint", "sh", tag, "-c",
                    "ls /opt/wheels/*.whl 2>/dev/null | wc -l"]),
    ]
    ok = True
    for name, cmd in checks:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            out = r.stdout.strip().splitlines()[-1][:50] if r.stdout.strip() else "ok"
            print(f"     ✓ {name}: {out}")
        else:
            print(f"     ✗ {name}: FAILED ({r.stderr.strip()[:80]})", file=sys.stderr)
            ok = False
    if ok:
        print(f"  ✅ {tag}: ready")
    else:
        print(f"  ⚠ {tag}: built but some checks failed", file=sys.stderr)
    return ok


def cmd_list() -> int:
    print(f"── vsm-tools images status ──")
    for p in ALL_PROFILES:
        tag = f"vsm-tools:{p}"
        exists = _image_exists(tag)
        pkgs = _pb._deps_for_profile(p)
        mark = "✓" if exists else "—"
        size = ""
        if exists:
            r = subprocess.run(
                ["docker", "image", "inspect", tag,
                 "--format", "{{.Size}}"],
                capture_output=True, text=True,
            )
            if r.returncode == 0:
                try:
                    size = f" ({int(r.stdout.strip()) // (1024 * 1024)}MB)"
                except ValueError:
                    pass
        print(f"  {mark} {tag}{size}  pkgs: {', '.join(pkgs[:6])}{'…' if len(pkgs) > 6 else ''}")
    print()
    print("overlay Dockerfile uses COPY --from=vsm-tools:<profile> (zero network).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="build_tools_images",
        description="Build vsm-tools:<profile> images — offline tools+deps layer (VSM-035)",
    )
    parser.add_argument("profiles", nargs="*",
                        help=f"profiles to build (default: {'+'.join(DEFAULT_PROFILES)})")
    parser.add_argument("--all", action="store_true",
                        help=f"all 4 profiles ({'+'.join(ALL_PROFILES)}; ml is heavy ~2GB)")
    parser.add_argument("--force", action="store_true",
                        help="rebuild even if vsm-tools:<profile> exists")
    parser.add_argument("--list", action="store_true",
                        help="show image status")
    args = parser.parse_args()

    if args.list:
        return cmd_list()

    if args.all:
        profiles = ALL_PROFILES
    elif args.profiles:
        bad = [p for p in args.profiles if p not in ALL_PROFILES]
        if bad:
            print(f"unknown profiles: {bad} (valid: {ALL_PROFILES})", file=sys.stderr)
            return 2
        profiles = args.profiles
    else:
        profiles = DEFAULT_PROFILES

    print(f"── build_tools_images: {profiles} ──")
    results = {p: build_profile(p, force=args.force) for p in profiles}

    print(f"\n── summary ──")
    for p, ok in results.items():
        print(f"  {'✅' if ok else '✗'} vsm-tools:{p}")
    ok_all = all(results.values())
    if ok_all:
        print("\nAll tools images ready. Overlay will COPY --from these (zero network).")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())

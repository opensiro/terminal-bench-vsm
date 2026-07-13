#!/usr/bin/env bash
# cmd.sh <command-name> — распечатать handoff-промпт слэш-команды в stdout.
# (Обёртка над .claude/commands/<name>.md без front-matter — для headless или
# вставки в REPL.)
set -euo pipefail
cd "$(dirname "$0")/.."
cmd="${1:?usage: cmd.sh <command-name>}"
f=".claude/commands/$cmd.md"
if [ ! -f "$f" ]; then echo "missing: $f" >&2; exit 1; fi

printf '\n\033[1m=== VSMLITE COMMAND: %s ===\033[0m\n' "$cmd"
# Пропустить YAML front-matter (между первыми двумя '---').
awk 'BEGIN{fm=0} /^---$/{fm++; next} fm>=2{print}' "$f"

#!/usr/bin/env bash
# run.sh <system-dir> — собрать промпт системы и выполнить в claude -p (one-shot).
# Headless-путь (альтернатива спавну субагентов через Agent tool в REPL).
set -euo pipefail
cd "$(dirname "$0")/.."
sys="${1:?usage: run.sh <system-dir>}"

if ! command -v claude >/dev/null 2>&1; then
  echo "claude CLI не найден. Используй 'make prompt-$sys' и вставь в REPL." >&2
  exit 1
fi

scripts/prompt.sh "$sys" | claude -p

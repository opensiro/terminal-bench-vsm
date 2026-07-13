#!/usr/bin/env bash
# prompt.sh <system-dir> — собрать run-промпт системы и вывести в stdout.
# Склеивает: шапка + CLAUDE.md + systems/<sys>/{SOUL,SKILL,HEARTBEAT,TASK}.md.
# Правишь файлы системы → промпт обновляется сам. (Адаптация opensiro-arctic/vsm.)
set -euo pipefail
cd "$(dirname "$0")/.."
sys="${1:?usage: prompt.sh <system-dir>}"
mode="${MODE:-normal}"

files=(CLAUDE.md "systems/$sys/SOUL.md" "systems/$sys/SKILL.md" "systems/$sys/HEARTBEAT.md" "systems/$sys/TASK.md")
for f in "${files[@]}"; do
  if [ ! -f "$f" ]; then echo "missing: $f" >&2; exit 1; fi
done

printf '\n\033[1m=== VSMLITE RUN PROMPT ===\033[0m\n'
printf 'project : %s\n' "$PWD"
printf 'system  : %s\n' "$sys"
printf 'mode    : %s\n' "$mode"
printf '\nMANDATORY reads (inlined ниже): CLAUDE.md, systems/%s/{SOUL,SKILL,HEARTBEAT,TASK}.md\n' "$sys"
printf 'INVARIANT: ../vsm/ & ../src/ only via subagent child-dispatcher. S5 prepares, never decides for human.\n\n'
for f in "${files[@]}"; do
  echo "───────────── $f ─────────────"
  cat "$f"
  echo
done

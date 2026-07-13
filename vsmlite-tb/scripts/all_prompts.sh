#!/usr/bin/env bash
# all_prompts.sh — собрать run-промпты всех систем в runs/*.txt (gitignored).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p runs

for sys in s2-coordinator s3-optimizer s3-star-auditor s4-scout s5-guardian synthesis-operator; do
  out="runs/$sys.txt"
  scripts/prompt.sh "$sys" > "$out"
  echo "wrote $out"
done

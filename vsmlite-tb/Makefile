# Makefile — тонкий диспетчер к scripts/. Прямой вызов команд Claude Code — слэш-командами.
SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

MODE ?= normal

.PHONY: help prompt-% run-% all-prompts validate telemetry autonomy digest init-check eval-list eval-run eval-all eval-summary

help: ## показать это сообщение
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Prompt composer (CLAUDE.md + systems/<sys>/{SOUL,SKILL,HEARTBEAT,TASK}.md) ──
# usage: make prompt-s4 → собирает run-промпт s4-scout в stdout
prompt-%:
	@MODE=$(MODE) scripts/prompt.sh $(subst prompt-,,$@)

run-%:
	@MODE=$(MODE) scripts/run.sh $(subst run-,,$@)

all-prompts: ## собрать все run-промпты в runs/*.txt
	@scripts/all_prompts.sh

# ── Checks ──
validate: ## invariant-grep: нет прямого касания ../vsm/ и ../src/ из core
	@scripts/validate.sh

# ── Telemetry (forward-контракт vsmforge) ──
telemetry: ## эмитить monitor/data.js из state/ + issues/
	@python3 scripts/render_data.py

autonomy: ## посчитать A(t) и вердикт из state/ + ../vsm/
	@python3 scripts/autonomy.py

digest: ## дайджест изменений цикла для REPL-юзера
	@python3 scripts/cycle_digest.py

init-check: ## структурная проверка init-состояния (без flip meta.initialized)
	@scripts/validate.sh --init-check

# ── eval/: Terminal-Bench Dev Set v2 пайплайн ──
eval-list: ## список задач в датасете
	@python3 -m eval list

eval-run: ## прогнать одну задачу: make eval-run TASK=<task_id>
	@test -n "$(TASK)" || { echo "укажите TASK=<task_id> (см. make eval-list)"; exit 2; }
	@python3 -m eval run --task $(TASK)

eval-all: ## прогнать все задачи (по фильтру: FILTER=difficulty=medium LIMIT=5)
	@python3 -m eval run-all $(if $(FILTER),--filter $(FILTER)) $(if $(LIMIT),--limit $(LIMIT))

eval-summary: ## вывести pass-rate из state/dev_metrics.json
	@python3 -m eval summary

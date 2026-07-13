# Makefile — тонкий диспетчер к scripts/. Прямой вызов команд Claude Code — слэш-командами.
SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

MODE ?= normal

.PHONY: help prompt-% run-% all-prompts validate telemetry autonomy digest init-check

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

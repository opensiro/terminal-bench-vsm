#!/usr/bin/env bash
# validate.sh — структурный инвариант vsmlite.
# Главный инвариант: core vsmlite НЕ мутирует ../vsm/ и ../src/ напрямую —
# только child-dispatcher (исполнитель) + read-only collect_metrics.py.
# Разрешённые read-only операции над ../: open, ls, cat, git log/show, grep.
# Запрещённые mutation: git add/commit/checkout/branch/push/worktree, edit/Write над ../.
#
# Флаги:
#   (нет)            — invariant-grep
#   --init-check     — структурные проверки init (без flip), см. init/validate_init.md
set -euo pipefail
cd "$(dirname "$0")/.."

mode="${1:-invariant}"
green=0; yellow=0; red=0

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; green=$((green+1)); }
warn() { printf '  \033[33m⚠\033[0m %s\n' "$1"; yellow=$((yellow+1)); }
fail() { printf '  \033[31m✗\033[0m %s\n' "$1"; red=$((red+1)); }

echo "── vsmlite validate ($mode) ──"

# ── 1. Invariant-grep: мутации ../ только из child-dispatcher ──
echo "1. invariant: ../vsm/ и ../src/ mutation только из child-dispatcher"
# Паттерн реальных MUTATION (не любых упоминаний ../):
#   shell: cp/mv/rm/mkdir/touch c ../ ; git add/commit/checkout/branch/push/worktree c -C ../ или путём ../
#   python: open("../...","w"|"a"), shutil.{copy,move,rmtree}, Path("../...").write_text/mkdir
# Исключаем: строки-комментарии (^\s*#), read-only (git log/show, ls, cat, open r).
MUT_RE='(cp |mv |rm |mkdir |touch ).*\.\./(vsm|src)|(git -C \.\./(vsm|src) (add|commit|checkout|branch|push|worktree))|(git (add|commit|checkout|branch|push|worktree)).*\.\./(vsm|src)|(open\(\s*["\x27]\.\./(vsm|src).*["\x27],\s*["\x27][wa])|(shutil\.(copy|move|rmtree|copytree)).*\.\./(vsm|src)|(\.write_text|\.mkdir|\.unlink|\.rename)\(.*\.\./(vsm|src)'

mutation_hits=$(grep -rnE "$MUT_RE" --include='*.sh' --include='*.py' \
  scripts/ 2>/dev/null | grep -vE 'collect_metrics\.py' | grep -vE '^\s*#' || true)
if [ -n "$mutation_hits" ]; then
  fail "scripts/ содержат прямую mutation над ../ (допустимо только collect_metrics.py read-only):"
  echo "$mutation_hits" | sed 's/^/      /'
else
  ok "scripts/ не мутируют ../ напрямую (collect_metrics.py — read-only исключение)"
fi

# Слэш-команды не должны делать git/edit над ../ (они только спавнят child-dispatcher).
cmd_mutation=$(grep -rnE '(git (add|commit|checkout|branch|push|worktree)).*\.\./(vsm|src)|(Edit\(.*\.\./(vsm|src))|(Write\(.*\.\./(vsm|src))' \
  .claude/commands/ 2>/dev/null | grep -vE 'child-dispatcher' | grep -vE '^\s*#' || true)
if [ -n "$cmd_mutation" ]; then
  fail ".claude/commands/ содержат прямую mutation над ../ (должно через child-dispatcher):"
  echo "$cmd_mutation" | sed 's/^/      /'
else
  ok ".claude/commands/ мутируют ../ только через child-dispatcher"
fi

# Системные файлы (S2-S5, synthesis-operator) — только планировщик, не исполнитель.
sys_mutation=$(grep -rnE '(git (add|commit|checkout|branch|push|worktree)).*\.\./(vsm|src)|(Edit\(.*\.\./(vsm|src))|(Write\(.*\.\./(vsm|src))' \
  systems/ 2>/dev/null | grep -vE 'child-dispatcher' | grep -vE '^\s*#' || true)
if [ -n "$sys_mutation" ]; then
  warn "systems/ упоминают mutation над ../ (допустимо только как 'через child-dispatcher'):"
  echo "$sys_mutation" | sed 's/^/      /'
else
  ok "systems/ не мутируют ../ напрямую"
fi

# ── 2. Структурная консистентность модели ──
echo "2. модель vsmlite.yaml"
if [ ! -f vsmlite.yaml ]; then fail "vsmlite.yaml отсутствует"; else ok "vsmlite.yaml присутствует"; fi

# S3* cross-provider
if grep -q 'must_differ_from: s1' vsmlite.yaml 2>/dev/null; then
  ok "system_3_star.provider_constraint.must_differ_from: s1"
else
  fail "system_3_star.provider_constraint.must_differ_from НЕ равно s1 (критичный инвариант)"
fi

# basta_constraint (РОДИТЕЛЬСКИЙ — prepare_only; product S5 автономен по VSM-006)
if grep -q 'prepare_only' vsmlite.yaml 2>/dev/null; then
  ok "identity.basta_constraint.agent_role: prepare_only (родительский S5)"
else
  fail "basta_constraint не prepare_only (родительский S5 решает за человека — нарушение)"
fi

# ── 2b. Parent isolation (VSM-005) ──
echo "2b. parent isolation (VSM-005): vsm/ и src/ не ссылаются на родителя"
# Дочерний VSM не должен ссылаться на ../../vsmlite-tb/ (parent isolation).
# Исключение: одно структурное упоминание в README/CLAUDE как директория-сосед
# (не раскрывает роль vsmlite как оператора). Считаем упоминания роли vsmlite
# как оператора/родителя (не просто пути).
parent_leak=$(grep -rnE 'vsmlite[^/]*\s+(как|это|—)\s+(оператор|родитель|parent|operator)|vsmlite.*выращив|vsmlite.*синтез' ../vsm/ ../src/ 2>/dev/null | grep -vE '^\s*#' || true)
if [ -n "$parent_leak" ]; then
  fail "vsm/ или src/ раскрывают роль vsmlite как родителя (parent isolation нарушен):"
  echo "$parent_leak" | sed 's/^/      /'
else
  ok "vsm/ и src/ не раскрывают роль vsmlite как оператора (parent isolation)"
fi

# ── 2c. Benchmark membrane (VSM-002): продукт не знает про Terminal Bench ──
echo "2c. benchmark membrane (VSM-002): vsm/ и src/ без упоминаний оценочных стендов"
# Продукт (benchmark-agnostic) не должен упоминать Terminal-Bench / TB / harbor.
# Эти термины живут только в родителе (vsmlite-tb/, включая eval/).
# Мембрана VSM-002: при трансляции TB-задачи в продукт TB-фрейминг снимается.
# Допускаются negation-комментарии (напр. "НИКАКИХ упоминаний terminal bench") —
# это инвариант-напоминание, а не утечка фрейминга. Отфильтровываем строки,
# содержащие отрицание рядом с термином (упоминани|не |без |no |without).
tb_leak=$(grep -rinE 'terminal[ -]?bench|t[ -]?bench|harbor[ -]?framework|laude[ -]?institute' ../vsm/ ../src/ 2>/dev/null \
  | grep -viE 'без |не |no |without|упоминани|never|запрет|forbid|никак' \
  | grep -vE '^\s*#' || true)
if [ -n "$tb_leak" ]; then
  fail "vsm/ или src/ содержат упоминания Terminal-Bench/harbor (мембрана VSM-002 нарушена):"
  echo "$tb_leak" | sed 's/^/      /'
else
  ok "vsm/ и src/ не упоминают Terminal-Bench/harbor как факт (мембрана VSM-002 сохранена)"
fi

# ── 3. Структура каталогов ──
echo "3. структура"
for d in systems synthesis init issues state monitor scripts ref meta seed/child .claude/agents .claude/commands; do
  [ -d "$d" ] && ok "есть $d/" || fail "отсутствует $d/"
done

# ── 4. init-check (опц.) ──
if [ "$mode" = "--init-check" ]; then
  echo "4. init-check (без flip)"
  # ../vsm/ либо не существует (до init), либо материализован
  if [ -d ../vsm ]; then
    [ -f ../vsm/vsm.yaml ] && ok "../vsm/vsm.yaml присутствует" || warn "../vsm/ есть, но vsm.yaml отсутствует"
    [ -f ../vsm/.intent.yaml ] && ok "../vsm/.intent.yaml (Phase 0) присутствует" || warn "../vsm/.intent.yaml отсутствует"
    # S3* provider в дочернем
    if [ -f ../vsm/vsm.yaml ] && grep -q 'must_differ_from: s1' ../vsm/vsm.yaml 2>/dev/null; then
      ok "../vsm/vsm.yaml S3* provider differs from s1"
    else
      warn "../vsm/vsm.yaml: S3* provider_constraint не задан или не differs"
    fi
  else
    warn "../vsm/ не существует (это нормально до /vsmlite-init)"
  fi
fi

# ── Итог ──
echo "──"
printf 'verdict: '
if [ "$red" -gt 0 ]; then
  printf '\033[31mRED\033[0m (%d fail, %d warn, %d ok)\n' "$red" "$yellow" "$green"
  exit 1
elif [ "$yellow" -gt 0 ]; then
  printf '\033[33mYELLOW\033[0m (%d warn, %d ok)\n' "$yellow" "$green"
  exit 0
else
  printf '\033[32mGREEN\033[0m (%d ok)\n' "$green"
  exit 0
fi

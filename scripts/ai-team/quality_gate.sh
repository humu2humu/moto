#!/usr/bin/env bash
# 使い方: (worktree 内で) scripts/ai-team/quality_gate.sh [BASE]
#   環境変数:
#     AI_TEAM_TEST_CMD     テストコマンド (既定: python3 -m pytest -q)
#     AI_TEAM_REGRESSION=1 基準コミットでも全テストを実行し、回帰差分を比較する(遅いが厳密)
#     AI_TEAM_MAX_DIFF=400 差分行数の上限(超えると FAIL。分割を促す)
#
# 段階: 1 事前検査 → 2 回帰テストの存在 → 3 静的解析 → 4 テスト → 5 回帰差分 → 合否記録
# 合格時のみ <root>/.ai-team/state/gate/<branch>.json に PASS を記録する。
set -euo pipefail
source "$(dirname "$0")/common.sh"
here="$(cd "$(dirname "$0")" && pwd)"

top="$(git rev-parse --show-toplevel)"
cd "$top"
branch="$(git symbolic-ref --short HEAD)"
case "$branch" in main|master) echo "ERROR: $branch 上では実行しません。worktree で実行してください。" >&2; exit 1;; esac
base="$(ai_base_ref "${1:-}")"
mb="$(git merge-base "$base" HEAD)"
state="$(ai_state_dir)"
stamp="$state/state/gate/${branch//\//__}.json"
work="$(mktemp -d)"; trap 'rm -rf -- "$work"' EXIT
rm -f -- "$stamp"

fail=0
check() { printf '  %-34s %s\n' "$1" "$2" >&2; [ "$2" != "FAIL" ] || fail=1; }
added_lines() { git diff "$mb" -- "$@" | grep -E '^\+[^+]' || true; }

ai_log "quality gate: $branch vs $base (merge-base ${mb:0:10})"

# --- 1. 事前検査 -------------------------------------------------------------
dirty="$(git status --porcelain)"
[ -z "$dirty" ] && check "作業ツリーがクリーン" PASS || check "作業ツリーがクリーン(未コミットあり)" FAIL
[[ "$branch" == ai/* ]] && check "ブランチ命名 ai/<id>-<slug>" PASS || check "ブランチ命名 ai/<id>-<slug>" WARN

changed="$(git diff --name-only --diff-filter=ACMR "$mb" HEAD)"
[ -n "$changed" ] && check "変更が存在する" PASS || check "変更が存在する" FAIL

if git diff "$mb" HEAD | grep -qE '^\+(<<<<<<<|>>>>>>>|=======$)'; then check "コンフリクトマーカーなし" FAIL; else check "コンフリクトマーカーなし" PASS; fi

nlines="$(git diff --numstat "$mb" HEAD | awk '{a+=$1; d+=$2} END {print a+d+0}')"
if [ "$nlines" -le "${AI_TEAM_MAX_DIFF:-400}" ]; then check "差分サイズ ${nlines} 行" PASS; else check "差分サイズ ${nlines} 行 (> ${AI_TEAM_MAX_DIFF:-400})" FAIL; fi

if added_lines . | grep -qE 'AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|gh[pousr]_[A-Za-z0-9]{30,}|xox[abp]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9_-]{20,}|(api[_-]?key|secret|password|token)\s*[:=]\s*["'"'"'][^"'"'"'$]{12,}'; then
  check "秘密情報の混入なし" FAIL
else
  check "秘密情報の混入なし" PASS
fi

if [ "${AI_TEAM_ALLOW_BYPASS:-0}" != 1 ] && added_lines '*.py' | grep -qE 'pytest\.mark\.(skip|xfail)|pytest\.skip\(|unittest\.skip|#\s*noqa|#\s*type:\s*ignore|#\s*pragma:\s*no cover'; then
  check "テスト/解析の回避マーカー追加なし" FAIL
else
  check "テスト/解析の回避マーカー追加なし" PASS
fi

deleted_tests="$(git diff --name-only --diff-filter=D "$mb" HEAD | grep -E '(^|/)(tests?/|test_[^/]*\.py$|[^/]*_test\.py$)' || true)"
[ -z "$deleted_tests" ] && check "テストファイルの削除なし" PASS || check "テストファイルの削除なし ($deleted_tests)" FAIL

# --- 2. 回帰テストの存在 -------------------------------------------------------
tests_changed="$(printf '%s\n' "$changed" | grep -E '(^|/)(tests?/|test_[^/]*\.py$|[^/]*_test\.py$|conftest\.py$)' || true)"
src_changed="$(printf '%s\n' "$changed" | grep -E '\.py$' | grep -vE '(^|/)(tests?/|test_[^/]*\.py$|[^/]*_test\.py$|conftest\.py$)' || true)"
if [ -n "$src_changed" ] && [ -z "$tests_changed" ]; then check "修正に対応するテスト追加/変更" FAIL; else check "修正に対応するテスト追加/変更" PASS; fi

# --- 3. 静的解析(変更ファイルのみ・新規指摘のみを問題にする) --------------------
py_changed="$(printf '%s\n' "$changed" | grep -E '\.py$' || true)"
if [ -n "$py_changed" ] && command -v ruff >/dev/null; then
  # shellcheck disable=SC2086
  if ruff check --quiet $py_changed >"$work/ruff.txt" 2>&1; then check "ruff (変更ファイル)" PASS
  else check "ruff (変更ファイル)" FAIL; sed 's/^/      /' "$work/ruff.txt" | head -40 >&2; fi
else
  check "ruff" SKIP
fi
if [ -n "$py_changed" ] && command -v mypy >/dev/null && { [ -f mypy.ini ] || [ -f .mypy.ini ] || grep -qs '^\[tool\.mypy\]' pyproject.toml || grep -qs '^\[mypy\]' setup.cfg; }; then
  # shellcheck disable=SC2086
  if mypy $py_changed >"$work/mypy.txt" 2>&1; then check "mypy (変更ファイル)" PASS
  else check "mypy (変更ファイル)" FAIL; sed 's/^/      /' "$work/mypy.txt" | head -40 >&2; fi
else
  check "mypy (設定なし)" SKIP
fi

# --- 4. テスト -----------------------------------------------------------------
read -r -a test_cmd <<<"$(ai_test_cmd)"
if PYTHONPATH="$(ai_pythonpath_for "$top")" "${test_cmd[@]}" --junitxml="$work/head.xml" >"$work/test.txt" 2>&1; then
  check "テスト (HEAD)" PASS
else
  rc=$?
  check "テスト (HEAD, exit $rc)" FAIL
  tail -n 40 "$work/test.txt" | sed 's/^/      /' >&2
fi

# --- 5. 回帰差分(任意・厳密) ----------------------------------------------------
if [ "${AI_TEAM_REGRESSION:-0}" = 1 ]; then
  bwt="$work/base"
  git worktree add --quiet --detach "$bwt" "$mb"
  (cd "$bwt" && PYTHONPATH="$(ai_pythonpath_for "$bwt")" "${test_cmd[@]}" --junitxml="$work/base.xml" >/dev/null 2>&1) || true
  git worktree remove --force "$bwt"
  if python3 "$here/regression_diff.py" "$work/base.xml" "$work/head.xml" >&2; then check "回帰差分 (base→HEAD)" PASS
  else check "回帰差分 (base→HEAD)" FAIL; fi
else
  check "回帰差分 (AI_TEAM_REGRESSION=1 で有効)" SKIP
fi

# --- 合否 ----------------------------------------------------------------------
result=PASS; [ "$fail" = 0 ] || result=FAIL
printf '{"branch":"%s","head":"%s","base":"%s","merge_base":"%s","result":"%s","regression_diff":%s,"at":"%s"}\n' \
  "$branch" "$(git rev-parse HEAD)" "$base" "$mb" "$result" "${AI_TEAM_REGRESSION:-0}" "$(date -u +%FT%TZ)" > "$work/stamp.json"
[ "$result" = PASS ] && cp "$work/stamp.json" "$stamp"
ai_log "RESULT: $result"
[ "$result" = PASS ]

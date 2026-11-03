#!/usr/bin/env bash
# ai-team 共通関数。source して使う。
set -euo pipefail
# テスト実行で worktree に __pycache__ を作らない(クリーン判定を汚さない)
export PYTHONDONTWRITEBYTECODE=1

# メインチェックアウト(全 worktree 共通)のルート
ai_main_root() {
  dirname "$(git rev-parse --path-format=absolute --git-common-dir)"
}

ai_state_dir() {
  local d
  d="$(ai_main_root)/.ai-team"
  mkdir -p "$d/state/gate" "$d/tasks" "$d/reports"
  printf '%s\n' "$d"
}

# 比較基準ブランチ: 引数 > $AI_TEAM_BASE > origin/main > main > origin/master > master
ai_base_ref() {
  local want="${1:-${AI_TEAM_BASE:-}}" ref
  for ref in $want origin/main main origin/master master; do
    if git rev-parse --verify --quiet "$ref^{commit}" >/dev/null; then
      printf '%s\n' "$ref"; return 0
    fi
  done
  echo "ERROR: 基準ブランチが見つかりません (AI_TEAM_BASE を設定してください)" >&2
  return 1
}

# worktree のソースを優先して import させる(editable install がメイン側を指す問題の回避)
ai_pythonpath_for() {
  local dir="$1"
  printf '%s\n' "$dir/src:$dir${PYTHONPATH:+:$PYTHONPATH}"
}

# テスト実行コマンド(プロジェクトに合わせて AI_TEAM_TEST_CMD で上書き)
ai_test_cmd() {
  printf '%s\n' "${AI_TEAM_TEST_CMD:-python3 -m pytest -q -p no:cacheprovider}"
}

ai_log() { printf '[ai-team] %s\n' "$*" >&2; }

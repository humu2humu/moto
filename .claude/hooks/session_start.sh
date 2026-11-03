#!/usr/bin/env bash
# SessionStart: 共有メモリ(進行中タスク・worktree・教訓)をコンテキストへ注入する。
# 秘密情報は出力しない。失敗してもセッションは止めない。
set -uo pipefail
root="$(git -C "${CLAUDE_PROJECT_DIR:-.}" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || exit 0
root="$(dirname "$root")"
state="$root/.ai-team"

echo "## ai-team 状態 (SessionStart)"
echo "### worktree"
git -C "$root" worktree list 2>/dev/null | sed 's/^/- /'

if [ -d "$state/tasks" ]; then
  echo "### 進行中タスク"
  for d in "$state"/tasks/*/; do
    [ -d "$d" ] || continue
    id="$(basename "$d")"
    status="$(head -n1 "$d/STATUS" 2>/dev/null || echo unknown)"
    echo "- $id: $status"
  done
fi

if [ -f "$root/docs/ai-team/lessons.md" ]; then
  echo "### 教訓 (docs/ai-team/lessons.md 末尾 20 行)"
  tail -n 20 "$root/docs/ai-team/lessons.md"
fi
exit 0

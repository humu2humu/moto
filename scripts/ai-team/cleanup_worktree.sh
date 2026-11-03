#!/usr/bin/env bash
# 使い方: scripts/ai-team/cleanup_worktree.sh <TASK_ID>
# マージ済みかつクリーンな worktree だけを安全に片付ける(--force / -D は使わない)。
# 条件を満たさない場合は何も消さずに理由を表示する。判断は人間に委ねる。
set -euo pipefail
source "$(dirname "$0")/common.sh"
[ $# -eq 1 ] || { echo "usage: $0 <TASK_ID>" >&2; exit 64; }

root="$(ai_main_root)"; cd "$root"
path="$root/.worktrees/$1"
[ -d "$path" ] || { echo "worktree がありません: $path" >&2; exit 1; }
branch="$(git -C "$path" symbolic-ref --short HEAD)"
base="$(ai_base_ref)"

if [ -n "$(git -C "$path" status --porcelain)" ]; then
  echo "未コミットの変更があるため削除しません: $path" >&2; exit 1
fi
if ! git merge-base --is-ancestor "$branch" "$base"; then
  echo "$branch は $base にマージされていません。削除するかは人間が判断してください。" >&2; exit 1
fi
git worktree remove "$path"
git branch -d "$branch"
printf 'DONE merged into %s\n' "$base" > "$(ai_state_dir)/tasks/$1/STATUS"
ai_log "片付け完了: $path ($branch)"

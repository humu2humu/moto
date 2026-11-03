#!/usr/bin/env bash
# 使い方: scripts/ai-team/new_worktree.sh <TASK_ID> <slug> [BASE]
# 例:     scripts/ai-team/new_worktree.sh 142 s3-copy-metadata
#
# <root>/.worktrees/<TASK_ID> に ai/<TASK_ID>-<slug> ブランチの worktree を作り、
# <root>/.ai-team/tasks/<TASK_ID>/ に引き継ぎ用ディレクトリを用意する。
# 既存の worktree・ブランチは決して上書きしない。
set -euo pipefail
source "$(dirname "$0")/common.sh"

[ $# -ge 2 ] || { echo "usage: $0 <TASK_ID> <slug> [BASE]" >&2; exit 64; }
id="$1"; slug="$2"
[[ "$id" =~ ^[A-Za-z0-9_-]+$ ]]   || { echo "TASK_ID は英数字/-/_ のみ" >&2; exit 64; }
[[ "$slug" =~ ^[a-z0-9-]+$ ]]     || { echo "slug は小文字英数字/- のみ" >&2; exit 64; }

root="$(ai_main_root)"
cd "$root"
git fetch --quiet origin 2>/dev/null || ai_log "fetch 失敗(オフライン?)— ローカルの基準で続行"
base="$(ai_base_ref "${3:-}")"
branch="ai/${id}-${slug}"
path="$root/.worktrees/$id"

if [ -e "$path" ]; then echo "ERROR: $path は既に存在します(上書きしません)" >&2; exit 1; fi
if git rev-parse --verify --quiet "refs/heads/$branch" >/dev/null; then
  echo "ERROR: ブランチ $branch は既に存在します(上書きしません)" >&2; exit 1
fi

git worktree add -b "$branch" "$path" "$base" >&2
state="$(ai_state_dir)"
mkdir -p "$state/tasks/$id"
printf 'OPEN branch=%s base=%s\n' "$branch" "$base" > "$state/tasks/$id/STATUS"
printf '{"task":"%s","branch":"%s","worktree":"%s","base":"%s","base_sha":"%s","created":"%s"}\n' \
  "$id" "$branch" "$path" "$base" "$(git rev-parse "$base")" "$(date -u +%FT%TZ)" > "$state/tasks/$id/meta.json"

ai_log "worktree: $path"
ai_log "branch:   $branch (base $base)"
printf '%s\n' "$path"

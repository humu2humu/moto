#!/usr/bin/env bash
# チームの現状(worktree・タスク・gate 結果)を一覧表示する。読み取り専用。
set -euo pipefail
source "$(dirname "$0")/common.sh"
root="$(ai_main_root)"; state="$(ai_state_dir)"

echo "== worktrees"
git -C "$root" worktree list
echo
echo "== tasks"
for d in "$state"/tasks/*/; do
  [ -d "$d" ] || continue
  printf '%-12s %s\n' "$(basename "$d")" "$(head -n1 "$d/STATUS" 2>/dev/null || echo '-')"
  [ -f "$d/attempts.jsonl" ] && printf '%-12s attempts=%s\n' "" "$(wc -l <"$d/attempts.jsonl")"
done
echo
echo "== quality gate (PASS 記録)"
for f in "$state"/state/gate/*.json; do [ -f "$f" ] && cat "$f"; done
exit 0

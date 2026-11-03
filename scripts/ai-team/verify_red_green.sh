#!/usr/bin/env bash
# 使い方: (worktree 内で) scripts/ai-team/verify_red_green.sh [--base REF] <pytest node id>...
# 例:     scripts/ai-team/verify_red_green.sh tests/test_s3.py::test_copy_keeps_metadata
#
# 回帰テストが「本当にバグを捕まえる」ことを機械的に確認する。
#   RED  : 修正前のソース(merge-base) + 新しいテスト  → テストが失敗すること
#   GREEN: 修正後のソース(HEAD)       + 新しいテスト  → テストが成功すること
# どちらかが期待と違えば exit 1。テストが収集されない(exit 5)等も失敗扱い。
set -euo pipefail
source "$(dirname "$0")/common.sh"

base_arg=""
if [ "${1:-}" = "--base" ]; then base_arg="$2"; shift 2; fi
[ $# -ge 1 ] || { echo "usage: $0 [--base REF] <node id>..." >&2; exit 64; }

top="$(git rev-parse --show-toplevel)"
cd "$top"
base="$(ai_base_ref "$base_arg")"
mb="$(git merge-base "$base" HEAD)"
read -r -a test_cmd <<<"$(ai_test_cmd)"

tmp="$(mktemp -d)"
cleanup() { git -C "$top" worktree remove --force "$tmp/base" >/dev/null 2>&1 || true; rm -rf -- "$tmp"; }
trap cleanup EXIT

git worktree add --quiet --detach "$tmp/base" "$mb"
# ブランチで追加/変更したテスト関連ファイルだけを修正前ソースへ持ち込む
git diff --name-only --diff-filter=ACMR "$mb" HEAD \
  | grep -E '(^|/)(tests?/|test_[^/]*\.py$|[^/]*_test\.py$|conftest\.py$)' \
  | while IFS= read -r f; do mkdir -p "$tmp/base/$(dirname "$f")"; cp -- "$f" "$tmp/base/$f"; done

set +e
(cd "$tmp/base" && PYTHONPATH="$(ai_pythonpath_for "$tmp/base")" "${test_cmd[@]}" "$@" >"$tmp/red.txt" 2>&1)
red=$?
PYTHONPATH="$(ai_pythonpath_for "$top")" "${test_cmd[@]}" "$@" >"$tmp/green.txt" 2>&1
green=$?
set -e

ok=1
if [ "$red" = 1 ]; then ai_log "RED   OK  : 修正前ソースでテストが失敗した(バグを再現している)"
else ai_log "RED   NG  : 修正前ソースで exit $red(1 を期待)。テストがバグを再現していない/収集されていない"; tail -n 20 "$tmp/red.txt" >&2; ok=0; fi
if [ "$green" = 0 ]; then ai_log "GREEN OK  : 修正後ソースでテストが成功した"
else ai_log "GREEN NG  : 修正後ソースで exit $green"; tail -n 30 "$tmp/green.txt" >&2; ok=0; fi

[ "$ok" = 1 ]

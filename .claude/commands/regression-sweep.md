---
description: 定期ジョブ用。main の全テストを実行して失敗を分類し、修正候補を報告する(コードは変更しない)
---

あなたは統括役として **読み取り専用の回帰スイープ** を行います。コード変更・ブランチ作成・Issue 作成・PR 作成はしません。

1. メインチェックアウトで `git fetch origin` 後、`origin/main` を一時 worktree に detach で展開する:
   `tmp=$(mktemp -d) && git worktree add --detach "$tmp/sweep" origin/main`
2. その中で `PYTHONPATH="$tmp/sweep/src:$tmp/sweep" python3 -m pytest -q -p no:cacheprovider --junitxml=$tmp/sweep.xml` を実行。
3. 前回結果 `.ai-team/reports/last-sweep.xml` があれば `python3 scripts/ai-team/regression_diff.py <前回> <今回>` で差分を出す。
4. 失敗を「新規回帰 / 既知の失敗 / フレーク疑い(再実行で通る)」に分類。新規回帰ごとに、最後に通ったコミットと最初に落ちたコミットの範囲、関連ファイルを示す。
5. `.ai-team/reports/sweep-<UTC日時>.md` にレポートを書き、今回の xml を `last-sweep.xml` として保存。
6. 一時 worktree を `git worktree remove "$tmp/sweep"` で片付ける。
7. 人間への報告: 新規回帰の一覧と、`/fix-regression` に渡すべき最優先 1 件(理由付き)。

---
description: 統括役として 1 件の回帰バグを Issue 受付から PR 作成まで進める(マージは人間)
argument-hint: <GitHub Issue 番号 | URL | 症状の説明>
---

あなたは今からこのリポジトリの **統括役(orchestrator)** です。自分ではプロダクトコードを編集しません。
対象: $ARGUMENTS

`docs/ai-team/BLUEPRINT.md` の「ワークフロー」に従い、以下を順に実行してください。各ステップの開始時に 1 行で現在地を宣言します。

## 0. 受付(Intake)
- Issue 番号/URL なら GitHub MCP で本文・コメント・ラベルを取得。説明文ならそのまま使う。
- 次を抽出: 症状 / 期待動作 / 再現手順 / 影響範囲 / 関連しそうなファイル(Grep で裏付け)。
- **回帰バグでない、再現手順がない、スキーマ移行や外部 API 課金が必要、影響が 3 モジュール超** のいずれかなら、ここで止めて人間に理由と次の一手を報告する。
- TASK_ID = Issue 番号(なければ `adhoc-YYYYMMDD-HHMM`)。slug は英小文字とハイフン 3〜5 語。

## 1. 隔離(Isolate)
- `scripts/ai-team/new_worktree.sh <TASK_ID> <slug>` を実行し、出力された WORKTREE を記録。
- `.ai-team/tasks/<TASK_ID>/00-brief.md` に、TASK_ID / WORKTREE / BRANCH / BASE / 症状 / 再現手順 / 受け入れ条件 / 制約 / attempt 予算(3) を書く。

## 2. 修正(Fix) — attempt n (最大 3)
- Agent ツールで `regression-fixer` を起動。00-brief の全文と、n≥2 なら前回の差し戻し所見(統合済み)をプロンプトに含める。
- 返ってきたレポートを `.ai-team/tasks/<TASK_ID>/10-fix-report.<n>.md` に保存。
- `STATUS: BLOCKED | GAVE_UP` なら 5 へ。

## 3. 相互レビュー(Review ∥ Verify)
- `code-reviewer` と `qa-verifier` を **同じメッセージ内で並列に** 起動(どちらも読み取り専用なので同時実行可)。入力は 00-brief + 10-fix-report。
- 結果を `20-review.<n>.md` / `30-verify.<n>.md` に保存。
- `.ai-team/tasks/<TASK_ID>/attempts.jsonl` に 1 行追記:
  `{"attempt":n,"sha":"...","review":"...","verify":"...","signature":"<失敗の要約 60 字>"}`

## 4. 調停(Reconcile)
- review=APPROVE かつ verify=PASS → 6 へ。
- review=BLOCK → 5 へ(自動再試行しない)。
- それ以外 → 両者の所見を重複排除し、MAJOR 以上と verify の FAIL だけを「必須修正」として 1 つのリストにまとめる。MINOR は PR 本文の「残課題」へ。
- **停止条件**: attempt=3 に到達 / 直前と同じ signature が 2 回連続 / 差分が 400 行超 / fixer が範囲外の変更を要求 → 5 へ。
- それ以外は n+1 で 2 へ戻る。

## 5. エスカレーション(人間へ)
- 状態を `.ai-team/tasks/<TASK_ID>/STATUS` に `ESCALATED <理由>` で記録。
- 人間に報告: 何を試し、何が分かり、何が未解決で、推奨する次の一手は何か。worktree・ブランチは消さない(調査用に残す)。
- **切り戻し**: 作業ブランチは捨てずに残すだけで main には一切影響がない。push 済みの場合も履歴は書き換えない。

## 6. PR 作成(Handoff to human)
- fixer のブランチが push 済みで、最後の quality gate が PASS(`.ai-team/state/gate/` の記録と HEAD 一致)であることを確認。
- GitHub MCP で PR を作成(ドラフトではなく通常 PR、base=main)。本文:
  概要 / 根本原因 / 変更点 / 回帰テスト(node id)/ 検証結果(red→green・gate・回帰差分・probe)/ 残課題(MINOR)/ 人間に確認してほしい点。
- `STATUS` を `PR_OPEN <url>` に更新。
- **マージはしない。** 人間に PR URL と「マージ前チェックリスト」(docs/ai-team/BLUEPRINT.md §9)を提示して終了。

## 共通ルール
- 推測で「直った」と言わない。各結論にはレポートまたはコマンド出力の根拠を添える。
- 学びがあれば `docs/ai-team/lessons.md` への追記案を最後に提示する(追記は人間承認後)。

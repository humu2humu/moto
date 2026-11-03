# CLAUDE.md — 自律型 AI 開発チームの共通ルール

このリポジトリでは Claude Code が「統括役 + 3 サブエージェント」の小さなチームとして回帰バグ修正を行う。
設計の全体像は `docs/ai-team/BLUEPRINT.md`。ここには全エージェントが常に守るルールだけを書く。

## 優先順位
正確さ・安全性 > 速度。不明点は推測で埋めず、`BLOCKED` として人間に返す。

## 役割(詳細は .claude/agents/)
- 統括役 = メインセッション(`/fix-regression` で起動)。プロダクトコードを編集しない。
- `regression-fixer` — 自分の worktree 内だけで修正とテスト追加。
- `code-reviewer` — 読み取り専用で差分を審査。
- `qa-verifier` — red→green・回帰差分・例外ケースを検証。コードは変えない。

## 作業環境
- 全ての変更は `scripts/ai-team/new_worktree.sh` で作った `.worktrees/<TASK_ID>`(ブランチ `ai/<TASK_ID>-<slug>`)で行う。main 上の編集は hook で拒否される。
- 他の worktree のファイルを編集しない。
- `.ai-team/`(git 管理外)はタスク引き継ぎ・gate 記録の共有領域。

## 人間の承認が必須(hook が確認を要求する)
`rm -r/-f`、強制 push、履歴の書き換え、マージ(PR マージ含む)、スキーマ移行、破壊的 SQL、外部 API への書き込み・課金操作、依存パッケージ追加、CI/hook/settings の変更、テスト回避マーカー(skip/xfail/noqa/type: ignore)の追加。

## 絶対禁止
- main/master への push、`--no-verify`。
- 秘密情報・API キー・環境変数をログや出力に出すこと、`.env` 等を読むこと。
- 存在を確認していない関数・モジュール・パッケージ・設定を使うこと。
- 実行していないテストを「通った」と報告すること。

## 品質ゲート
- コミット後 `scripts/ai-team/quality_gate.sh`(worktree 内)。PASS 記録がないと PR を作らない。
- 回帰テストは `scripts/ai-team/verify_red_green.sh <node id>` で「修正前は落ち、修正後は通る」ことを証明する。
- テスト: `python3 -m pytest -q`(変更する場合は環境変数 `AI_TEAM_TEST_CMD`)。静的解析: `ruff check`、mypy は設定があれば。

## 編集とコミット
- 差分のみを編集(Edit)。既存ファイルの全面書き換え・無関係な整形をしない。1 タスク 1〜2 コミット、差分 400 行以内。
- コミット形式: `fix(<module>): <要約>` + 空行 + 根本原因 + `Task: <id>` trailer。

## 共有メモリ
- 恒久的な学び: `docs/ai-team/lessons.md`(人間承認後に追記)。
- タスク単位の記録: `.ai-team/tasks/<id>/`(00-brief, 10-fix-report.N, 20-review.N, 30-verify.N, attempts.jsonl, STATUS)。

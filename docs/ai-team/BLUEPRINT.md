# 自律型 AI 開発チーム 設計図 (Claude Code)

前提(ヒアリング結果): **Python / 運用者 1 名 / 最大のボトルネックは回帰バグ修正 / 安全レベル「標準」**
(worktree 内の編集・テスト・`ai/*` ブランチへの push・PR 作成までは自動。main への統合は人間承認)

この文書の内容はすべてリポジトリ内の実ファイルとして実装済み。設計と実装がずれた場合は実装(とそのテスト `tests/ai_team/`)が正。

---

## 1. 最初の用途の選定

| 用途 | 正解の判定(オラクル) | 差分の大きさ | 許容リスク | 人間のレビュー時間 | 判定 |
|---|---|---|---|---|---|
| **回帰バグの自動修正** | 失敗するテストが機械的に作れる | 小(〜100 行) | 低 | 短い(テスト+小差分) | **◎ 推奨** |
| 既存コードの改修 | 既存テスト頼み・意図が曖昧 | 中〜大 | 中 | 長い | ○ 第 2 段階 |
| 徹底レビュー/セキュリティ監査 | 主観的・誤検知の判定が人間依存 | なし(報告のみ) | 低 | 中 | ○ 補助として内包 |
| フルスタック機能開発 | 仕様そのものが不確定 | 大 | 高 | 長い | △ 後回し |
| API 連携 | 外部状態・課金・秘密情報が絡む | 中 | 高 | 中 | ✕ 初期は対象外 |

**推奨: 回帰バグ修正。** 「修正前は落ち、修正後は通るテスト」という客観的な合否があるため、エージェントの成果を機械的に検証でき(`verify_red_green.sh`)、1 人の運用者でもレビュー負荷が小さい。レビュー・監査能力は reviewer として同じループに組み込む。

---

## 2. チーム構成図

```
                         ┌──────────────────────────────┐
     GitHub Issue ─────▶ │   人間 (運用者・唯一の承認者)  │ ◀── PR / エスカレーション報告
     /fix-regression     └──────────────┬───────────────┘
                                        │ 起動・承認(マージ/破壊的操作)
                                        ▼
                ┌───────────────────────────────────────────────┐
                │ 統括役 (メインセッション, /fix-regression)      │
                │  受付→隔離→割当→調停→PR。コードは書かない       │
                │  共有メモリ: .ai-team/tasks/<id>/ , lessons.md │
                └──────┬───────────────────────┬────────────────┘
          00-brief     │                       │  10-fix-report
                       ▼                       ▼
     ┌──────────────────────────┐   ┌───────────────────────┐  ┌───────────────────────┐
     │ regression-fixer         │   │ code-reviewer         │  │ qa-verifier           │
     │ 書込: 自分の worktree のみ │   │ 読み取り専用           │  │ 書込: probes/ のみ     │
     │ テスト追加→最小修正→gate  │   │ 差分審査・根拠付き所見 │  │ red→green・回帰差分    │
     └────────────┬─────────────┘   └───────────┬───────────┘  └──────────┬────────────┘
                  │                             └──── 並列実行 ────────────┘
                  ▼                                       │ 20-review / 30-verify
     .worktrees/<id>  (branch ai/<id>-<slug>)  ◀──────────┘  同じ worktree を読むだけ
                  │
     ─────────────┼──────── 全ツール呼び出しは hooks を通過 ─────────────────────────
                  ▼
     guard_bash.py / guard_edit.py (PreToolUse) · post_edit_check.py (PostToolUse)
     stop_check.py (Stop) · session_start.sh (SessionStart)
```

---

## 3. 役割定義

| 役割 | 実体 | 担当範囲 | 入力 | 出力 | ツール | 書き込み範囲 |
|---|---|---|---|---|---|---|
| 統括役 | メインセッション + `.claude/commands/fix-regression.md` | 受付・隔離・割当・調停・停止判断・PR 作成 | Issue | PR / エスカレーション報告 | 全ツール(hook で制限) | `.ai-team/` のみ(main 編集は hook が拒否) |
| 修正担当 | `.claude/agents/regression-fixer.md` | 再現テスト・根本原因・最小修正・gate・push | 00-brief | 10-fix-report | Read, Grep, Glob, Edit, Write, Bash | 自分の worktree |
| 徹底レビュー役 | `.claude/agents/code-reviewer.md` | 正しさ・回帰・セキュリティ・テスト妥当性・捏造検出 | brief + fix-report | 20-review | Read, Grep, Glob, Bash | なし |
| 検証責任者 | `.claude/agents/qa-verifier.md` | red→green・回帰差分 gate・例外ケース探索・フレーク確認 | brief + fix-report | 30-verify | Read, Grep, Glob, Bash, Write | `.ai-team/tasks/<id>/probes/` |

**上位判断に回す条件(エスカレーション)**: 回帰でない/再現不能、スキーマ移行・外部 API 課金・依存追加が必要、影響 3 モジュール超、差分 400 行超、reviewer が BLOCK、3 回試行で未解決、同じ失敗が 2 回連続、検証対象の sha 不一致、仕様が曖昧(verifier の QUESTIONS)。

**作業の上書き・テスト回避の防止**: reviewer/verifier には Edit がなく、`guard_edit.py` が main 上の編集・別 worktree への書き込み・skip/xfail 追加を拒否/確認要求し、`quality_gate.sh` がテスト削除・回避マーカー・回帰テストなしを FAIL にし、`stop_check.py` が gate 未合格のまま終わることを止める。プロンプト・hook・スクリプトの三重防御。

---

## 4. エージェント間通信と引き継ぎ

Claude Code のサブエージェントは「統括役から呼ばれ、最終メッセージを返す」形で通信する。各サブエージェントは独立したコンテキストで動くため、引き継ぎは**ファイル + 定型レポート**で行う。

```
.ai-team/tasks/<TASK_ID>/
├── meta.json            new_worktree.sh が作成(branch, worktree, base, base_sha)
├── STATUS               OPEN | PR_OPEN <url> | ESCALATED <理由> | DONE
├── 00-brief.md          統括 → fixer(症状・再現・受け入れ条件・制約・attempt 予算)
├── 10-fix-report.N.md   fixer → 統括(STATUS, ROOT_CAUSE, CHANGED_FILES, REGRESSION_TESTS, EVIDENCE)
├── 20-review.N.md       reviewer → 統括(VERDICT, CHECKLIST, FINDINGS[重大度 file:line 根拠 提案])
├── 30-verify.N.md       verifier → 統括(VERDICT, RED_GREEN, GATE, FLAKE_CHECK, PROBES, QUESTIONS)
├── attempts.jsonl       試行ごとの {attempt, sha, review, verify, signature}
└── probes/              verifier の探索テスト(git 管理外)
```

- 各レポートの書式は各エージェント定義の「出力」節が正。統括役は返答をそのまま保存し、次の役割へ全文を渡す(要約による情報落ちを防ぐ)。
- 恒久メモリは `docs/ai-team/lessons.md`(git 管理、人間承認で追記)。`session_start.sh` が末尾 20 行と進行中タスクを毎セッション注入する。
- 別セッション間の協調(例: 夜間スイープ → 翌朝の修正)は `.ai-team/reports/` を介する。

---

## 5. ワークフロー(Issue → PR → 人間がマージ)

```
 Issue ──▶ 0 受付 ──(対象外)──────────────────────────────▶ 5 エスカレーション
             │ ok
             ▼
          1 隔離  new_worktree.sh <id> <slug> → .worktrees/<id> / ai/<id>-<slug>
             ▼
   ┌────▶ 2 修正 (fixer, attempt n≤3)
   │         │ テスト追加→RED確認→根本原因→最小修正→commit→quality_gate→push
   │         ▼
   │      3 相互レビュー  reviewer ∥ verifier(並列・読み取り専用)
   │         ▼
   │      4 調停  APPROVE & PASS ───────────────────────────▶ 6 PR 作成
   │         │ REQUEST_CHANGES / FAIL                            │
   └─────────┘ (必須修正リストを統合して差し戻し)                  ▼
             │ BLOCK / 3 回 / 同一失敗 2 連続 / 400 行超        人間: §9 を確認
             ▼                                                  → マージ(唯一の統合経路)
          5 エスカレーション(worktree は残す)                    → cleanup_worktree.sh
```

- **worktree への起動方法**: 統括役が `new_worktree.sh` で worktree を作り、その絶対パスを 00-brief に書いて fixer を起動する。fixer は最初に `cd <WORKTREE>` しブランチ名を照合する。ブランチ命名が決定的で、セッションをまたいで残り、gate 記録と対応づくため、Agent ツールの `isolation: "worktree"`(自動命名・自動削除)ではなくスクリプト管理を採用した。
- **相互レビューの調整**: reviewer と verifier は同じ worktree を読むだけなので並列で安全。所見の統合(重複排除、MAJOR 以上と verify FAIL だけを必須修正に)は統括役が行う。
- **例外ケースの検証箇所**: ステップ 3 の verifier(probe テスト・境界値・フレーク)と reviewer(呼び出し元の影響・境界値の実行確認)。
- **main への統合前の人による承認**: PR マージは `settings.json` の `ask` と `guard_bash.py` で人間確認必須。統括役はマージしない。

---

## 6. ツール構成(最小)

| ツール | 目的 | 権限範囲 |
|---|---|---|
| Bash | テスト・git・スクリプト実行 | `settings.json` の allow(読み取り系 git、pytest、ruff、mypy、ai-team スクリプト、`git push -u origin ai/*`)。それ以外は確認。破壊的操作は `guard_bash.py` が ask/deny |
| Read / Grep / Glob | コード探索 | 全員。`.env`・鍵ファイルは deny |
| Edit / Write | 差分編集 | fixer(自 worktree)、verifier(probes のみ)、統括(.ai-team のみ)。`guard_edit.py` で強制 |
| Agent | サブエージェント起動 | 統括役のみ使用 |
| 永続メモリ | `CLAUDE.md`(規約)/ `docs/ai-team/lessons.md`(教訓)/ `.ai-team/`(実行時状態) | lessons は人間承認で追記 |
| MCP: GitHub | Issue 取得・PR 作成 | マージ・ファイル直接書込・auto-merge は `ask` |
| MCP: ブラウザ / DB | **初期は導入しない** | Python の回帰修正には不要。導入時は DB を読み取り専用ユーザーで接続 |
| 定期ジョブ | `/regression-sweep`(main の全テスト→新規回帰の一覧) | 読み取り専用。Day 5 以降、Claude Code のスケジュール実行(クラウドの scheduled task、またはセッション内 `/loop`)で夜間に起動 |

GitHub MCP を自前の Claude Code CLI で使う場合の `.mcp.json` 例(トークンは環境変数から展開され、ファイルには書かない):

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": { "Authorization": "Bearer ${GITHUB_PAT}" }
    }
  }
}
```

---

## 7. worktree とブランチ戦略

| 項目 | 規約 |
|---|---|
| 場所 | `<repo>/.worktrees/<TASK_ID>`(`.gitignore` 済み) |
| ブランチ | `ai/<TASK_ID>-<slug>`(例 `ai/142-s3-copy-metadata`)。基準は `origin/main` |
| 1 タスク | 1 worktree・1 fixer・1〜2 コミット・差分 ≤ 400 行 |
| 履歴 | 書き換えない(rebase/amend/force push は人間確認)。差し戻しは追加コミット |
| main | 直接編集・直接 push 禁止。統合は PR マージのみ |
| 片付け | `cleanup_worktree.sh <id>`: マージ済み かつ クリーンな時だけ `git worktree remove` + `git branch -d`(強制なし) |
| Python の import | editable install はメインチェックアウトを指すため、スクリプトは `PYTHONPATH=<worktree>/src:<worktree>` を前置。`AI_TEAM_TEST_CMD` で上書き可 |

---

## 8. フック設定(`.claude/settings.json`)

| イベント | スクリプト | 動作 |
|---|---|---|
| SessionStart | `session_start.sh` | worktree・進行中タスク・教訓をコンテキストに注入 |
| PreToolUse(Bash) | `guard_bash.py` | **deny**: main への push、`--no-verify`、環境変数の一括出力、秘密ファイル読み出し、秘密変数の echo、hooksPath 変更。**ask**: `rm -r/-f`、強制 push・リモート削除、reset --hard / clean -f / branch -D / rebase、マージ、破壊的 SQL、マイグレーション、terraform/kubectl/publish、AWS 書き込み、curl の POST 等、`curl|sh`、sudo、依存追加 |
| PreToolUse(Edit 系) | `guard_edit.py` | **deny**: 秘密ファイル、main 上の編集、別 worktree への書き込み、読み取り専用エージェントのコード編集(hook 入力に `agent_type` がある場合)。**ask**: CI・hooks・settings・ai-team スクリプトの変更、skip/xfail/noqa/type: ignore の新規追加 |
| PostToolUse(Edit 系) | `post_edit_check.py` | 編集した .py の構文チェック + ruff。指摘をエージェントへ返す(自動修正しない) |
| Stop | `stop_check.py` | gate 未合格の `ai/*` ブランチが残っていれば 1 回だけ停止をブロック(`stop_hook_active` でループ防止) |

`settings.json` の `permissions` も同じ方針で allow/ask/deny を宣言しており、hook と二重に効く。hook 入力が壊れていれば Bash ガードはブロックする(フェイルクローズ)。

---

## 9. 品質保証計画

### 9.1 段階と担当
| 段階 | 内容 | 実装 | 担当 |
|---|---|---|---|
| 実行前 | brief の必須項目、worktree・ブランチ照合、再現手順の有無 | fixer の入力検査 / 統括の受付 | fixer・統括 |
| 編集時 | 構文・ruff、危険操作・回避マーカーの遮断 | hooks | 自動 |
| 事前検査 | クリーン・命名・コンフリクトマーカー・差分サイズ・秘密情報・回避マーカー・テスト削除 | `quality_gate.sh` §1 | 自動 |
| テストの存在 | ソース変更にはテスト変更が必須 | `quality_gate.sh` §2 | 自動 |
| 静的解析 | ruff / mypy(設定あれば)を変更ファイルに | `quality_gate.sh` §3 | 自動 |
| 自動テスト | 全テスト(junit 出力) | `quality_gate.sh` §4 | 自動 |
| 回帰差分 | merge-base でも全テスト → passed→failed と消失テストを検出 | `AI_TEAM_REGRESSION=1` + `regression_diff.py` | verifier |
| 回帰テストの有効性 | 修正前で落ち、修正後で通る | `verify_red_green.sh` | fixer・verifier |
| 例外ケース | 境界値 probe、フレーク 3 回 | qa-verifier | verifier |
| 審査 | 正しさ・回帰・セキュリティ・捏造・規約 | code-reviewer | reviewer |
| 統合前 | 下のチェックリスト | 人間 | 人間 |

### 9.2 自動復旧・切り戻し
- **テスト失敗時**: fixer が原因を修正して gate 再実行。同じ FAIL が 2 回続いたら fixer は止めて報告(`GAVE_UP`)。
- **同じ再試行の繰り返し**: 統括役が attempts.jsonl の `signature` を比較し、2 連続一致で打ち切り → エスカレーション。試行上限 3。
- **切り戻し**: すべての変更は `ai/*` ブランチ上にしか存在しないため、main への影響はゼロ。失敗したブランチは調査用に残し、捨てる判断は人間が行う(`git reset --hard`・ブランチ強制削除は hook が確認要求)。マージ後に問題が見つかった場合は `git revert <merge commit>` の PR を同じフローで作る(履歴は書き換えない)。
- **ガード自体の故障**: hook のテスト `tests/ai_team/` を CI と Day 4 の訓練で実行。hook 入力が解析不能なら Bash はブロック。

### 9.3 マージ前チェックリスト(人間)
- [ ] PR の根本原因の説明に納得できる(症状隠しでない)
- [ ] 回帰テストが Issue の症状そのものを表している
- [ ] 30-verify: RED_GREEN=OK、GATE(regression diff)=PASS、FLAKE 3/3
- [ ] 20-review: APPROVE、MINOR は把握済み
- [ ] 差分に無関係な変更・新規依存・設定変更が含まれない
- [ ] verifier の QUESTIONS(仕様判断)に回答済み
- [ ] CI が緑

---

## 10. 5 日間の導入計画

| 日 | ゴール | 作業 | 完了条件 |
|---|---|---|---|
| Day 1 基盤 | ガードが効く状態 | 本設定をマージ。`pip install pytest ruff`(+ mypy 設定があれば)。`AI_TEAM_TEST_CMD` をプロジェクトに合わせる。`python3 -m pytest tests/ai_team` | 58 テスト緑。手動で `rm -rf x` / `git push origin main` を試し ask/deny を確認 |
| Day 2 単独 | fixer 単体の品質を見る | 再現が簡単な既知回帰 1 件で fixer だけを起動し、レビューは人間が行う | red→green OK、gate PASS、差分が最小 |
| Day 3 チーム | 全ループ | `/fix-regression <issue>` を 2 件。reviewer/verifier の所見の質を確認し、プロンプトの誤検知を調整 | 2 件とも PR 作成、または妥当なエスカレーション |
| Day 4 失敗訓練 | 安全装置の実地確認 | 意図的に: 修正不能な Issue(上限で停止するか)、skip 追加を要求、`.env` 読み出しを要求、main 編集を要求、テスト削除で通そうとするブランチ | 全てブロック/エスカレーション。抜けたものは hook とテストに追加 |
| Day 5 定常化 | 継続運用 | `/regression-sweep` を夜間スケジュール化。lessons.md に Day 2〜4 の学びを追記。指標の基準値を記録 | 運用手順が 1 ページで回る |

**指標**: gate 初回合格率、平均試行回数、reviewer の MAJOR 件数、PR 1 件あたり人間のレビュー時間、マージ後 revert 件数(目標 0)。
**次段階の判断基準**: 2 週間で revert 0 かつ初回合格率 70% 以上なら、用途を「既存コードの小規模改修」に拡張する。

---

## 11. ファイル一覧

```
CLAUDE.md                              全エージェント共通ルール
.claude/settings.json                  permissions + hooks
.claude/agents/regression-fixer.md     修正担当 システムプロンプト
.claude/agents/code-reviewer.md        徹底レビュー役 システムプロンプト
.claude/agents/qa-verifier.md          検証責任者 システムプロンプト
.claude/commands/fix-regression.md     統括役ワークフロー (/fix-regression)
.claude/commands/regression-sweep.md   夜間スイープ (/regression-sweep)
.claude/hooks/*.py, *.sh               ガード・チェック
scripts/ai-team/new_worktree.sh        worktree + タスク作成
scripts/ai-team/quality_gate.sh        品質ゲート
scripts/ai-team/verify_red_green.sh    回帰テストの有効性検証
scripts/ai-team/regression_diff.py     JUnit 比較
scripts/ai-team/cleanup_worktree.sh    安全な片付け
scripts/ai-team/team_status.sh         状況一覧
tests/ai_team/                         上記のテスト
docs/ai-team/lessons.md                教訓ログ
```

---

## ここから始める

1. このブランチを main にマージする(このリポジトリは現在空なので、これが最初のコミットになる)。
2. 実際の Python プロジェクトのコードを main に入れ、依存をインストールする: `pip install -e . pytest ruff`
3. テストコマンドが既定(`python3 -m pytest -q`)と違えば、`.claude/settings.json` の `env` に `"AI_TEAM_TEST_CMD": "..."` を追加する。
4. ガードの動作確認: `python3 -m pytest -q tests/ai_team`
5. 再現手順がはっきりした回帰 Issue を 1 つ選び、Claude Code で実行する:
   ```
   /fix-regression 142
   ```
6. 作成された PR を §9.3 のチェックリストで確認してマージし、`scripts/ai-team/cleanup_worktree.sh 142` で片付ける。
7. 気づいたことを `docs/ai-team/lessons.md` に 1 行追記する。以降は §10 の Day 2 から進める。

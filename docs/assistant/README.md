# 毎日の質問アシスタント(GitHub Issue 版)

GitHub Issue に質問を書くと、Claude が Web で調べて同じ Issue にコメントで回答します。
実装は `.github/workflows/daily-assistant.yml`、質問テンプレートは `.github/ISSUE_TEMPLATE/question.yml`。

## ⚠️ 最初に: 公開リポジトリであること
`humu2humu/moto` は **public** です。Issue の質問と回答は誰でも読めます。
業務の質問をするなら、**このワークフローを private リポジトリに置く**ことを強く勧めます(ファイル 2 つをコピーするだけで動きます)。

## セットアップ(5 分)
1. **API キーを登録**: リポジトリの Settings → Secrets and variables → Actions → New repository secret
   - 名前 `ANTHROPIC_API_KEY`、値は Claude Console で発行したキー(従量課金)
   - Claude の Pro/Max プランで使う場合: ローカルで `claude setup-token` を実行して得たトークンを `CLAUDE_CODE_OAUTH_TOKEN` として登録し、
     ワークフローの `anthropic_api_key: ...` の行を `claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}` に置き換える
2. **ラベルを作成**: Issues → Labels → `question`(テンプレートが自動で付けるラベル)
3. このファイル群を既定ブランチ(main)にマージする(Issue イベントのワークフローは既定ブランチのものだけが動く)

## 使い方
- Issues → New issue → 「質問」テンプレート → 質問を書いて Submit。1〜3 分で回答コメントが付く
- 追加で聞きたいことは同じ Issue にコメント。それまでのやり取りを読んだうえで答える
- 既存の Issue に `question` ラベルを付けても回答が始まる
- 解決したら Issue を Close(Close しても追加コメントには反応する)

## できること / できないこと
| できる | できない |
|---|---|
| 一般知識の質問、文章の下書き・要約・翻訳 | カレンダー・メール・社内システムの参照(Actions からはあなたのアカウントに接続していない) |
| Web 検索による最新情報の確認(出典 URL 付き) | ファイルの変更・コードの push・他の Issue の操作 |
| 同じ Issue 内での追加質問 | 所有者以外からの質問への回答(仕様。課金と悪用の防止) |

## 安全設計
- 起動条件: 操作者がリポジトリ所有者 かつ `question` ラベル付き かつ PR ではない。Bot 自身のコメントでは起動しない(無限ループ防止)
- Claude の権限: `WebSearch`, `WebFetch`, `Write`(回答ファイル用), `gh issue view` のみ。投稿は後続ステップが固定の Issue に行う
- ワークフローの `GITHUB_TOKEN` 権限は `contents: read` と `issues: write` だけ
- 1 回あたり最大 12 ターン・15 分で打ち切り。費用の目安は Actions のログに出る使用量で確認する

## 調整ポイント
| 変えたいこと | 場所 |
|---|---|
| モデル(品質重視なら Opus) | `claude_args` の `--model` |
| 口調・回答方針 | `claude_args` の `--append-system-prompt` |
| 回答の長さ・費用上限 | `--max-turns`, `timeout-minutes` |

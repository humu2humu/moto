# 教訓ログ (lessons.md)

エージェントが繰り返し失敗したパターンと対策を 1 行ずつ記録する。追記は人間の承認後。
SessionStart フックが末尾 20 行を全エージェントのコンテキストに注入する。

形式: `- YYYY-MM-DD [タグ] 事象 → 対策`

- 2026-11-03 [setup] editable install はメインチェックアウトを指すため、worktree のテストが修正前コードを import しうる → スクリプトは PYTHONPATH に worktree の src/ と直下を前置する。
- 2026-11-03 [setup] テスト実行で worktree に __pycache__ が生成され gate の「クリーン」判定が落ちた → common.sh で PYTHONDONTWRITEBYTECODE=1 を設定。

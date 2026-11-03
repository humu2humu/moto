#!/usr/bin/env python3
"""PreToolUse(Bash) ガード。

- 破壊的・外部影響のあるコマンド → "ask"(人間の明示確認を要求)
- 秘密情報の漏洩・テスト回避・main 直 push → "deny"(実行させない)

Claude Code の hook 入力(JSON)を stdin で受け取り、判定を JSON で stdout に返す。
入力が壊れている場合はフェイルクローズ(exit 2 = ブロック)。
"""

from __future__ import annotations

import json
import re
import sys

I = re.IGNORECASE

# (pattern, reason) — 上から順に評価。DENY が ASK より優先。
DENY: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bgit\s+push\b[^|;&]*\s(origin\s+)?(\S+:)?(refs/heads/)?(main|master)\b"),
        "main/master への直接 push は禁止。PR 経由で人間がマージする。"),
    (re.compile(r"--no-verify\b"),
        "--no-verify によるフック回避は禁止。"),
    (re.compile(r"(^|[;&|]\s*)(env|export\s+-p|set|declare\s+-x)\s*($|[;&|>])|\bprintenv\b"),
        "環境変数の一括出力は秘密情報漏洩のため禁止。"),
    (re.compile(r"\b(cat|less|more|head|tail|bat|nl|strings|xxd|base64|grep|rg|awk|sed)\b[^|;&]*"
                r"(\.env(\.[\w-]+)?(\s|$|[\"'])|\.pem\b|\.key(\s|$)|id_rsa|id_ed25519|\.netrc|credentials(\.json)?(\s|$)|\.pgpass)"),
        "秘密情報ファイルの読み出しは禁止。"),
    (re.compile(r"\becho\b[^|;&]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL)\w*", I),
        "秘密情報を含む環境変数の表示は禁止。"),
    (re.compile(r"\bgit\s+config\b[^|;&]*core\.hooksPath"),
        "git フックの無効化・差し替えは禁止。"),
]

ASK: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\brm\s+([^|;&]*\s)?(-[a-zA-Z]*[rRf][a-zA-Z]*|--recursive|--force)\b"),
        "再帰/強制削除 (rm -r / -f)。"),
    (re.compile(r"\bgit\s+push\b[^|;&]*(\s--force(-with-lease)?\b|\s-[a-zA-Z]*f[a-zA-Z]*\b|\s\+\S+|\s--delete\b|\s:\S+)"),
        "強制 push / リモートブランチ削除。"),
    (re.compile(r"\bgit\s+(reset\s+[^|;&]*--hard|clean\s+[^|;&]*-[a-zA-Z]*f|branch\s+[^|;&]*-D\b|"
                r"checkout\s+[^|;&]*--\s+\.|restore\s+([^|;&]*\s)?\.(\s|$)|rebase\b|filter-branch\b|"
                r"filter-repo\b|stash\s+(drop|clear)\b|worktree\s+remove\s+[^|;&]*--force|update-ref\s+-d)"),
        "作業内容や履歴を破棄・書き換える git 操作。"),
    (re.compile(r"\bgit\s+merge\b|\bgh\s+pr\s+merge\b"),
        "マージは人間の承認が必須。"),
    (re.compile(r"\b(DROP\s+(TABLE|DATABASE|SCHEMA|INDEX)|TRUNCATE\b|DELETE\s+FROM\b|ALTER\s+TABLE)", I),
        "破壊的な SQL / スキーマ変更。"),
    (re.compile(r"\b(alembic\s+(upgrade|downgrade|stamp)|manage\.py\s+(migrate|flush)|"
                r"flask\s+db\s+(upgrade|downgrade)|prisma\s+migrate)\b"),
        "スキーマ移行は人間の承認が必須。"),
    (re.compile(r"\b(terraform\s+(apply|destroy)|pulumi\s+up|kubectl\s+(apply|delete)|helm\s+(install|upgrade|uninstall)|"
                r"docker\s+push|twine\s+upload|uv\s+publish|poetry\s+publish|npm\s+publish)\b"),
        "外部環境・課金・公開に影響する操作。"),
    (re.compile(r"\baws\s+\S+\s+(create|delete|put|run|terminate|start|update|invoke)", I),
        "AWS への書き込み操作(課金・外部影響)。"),
    (re.compile(r"\bcurl\b[^|;&]*(-X\s*(POST|PUT|PATCH|DELETE)|--data\b|-d\s)", I),
        "外部 API への書き込みリクエスト(課金の可能性)。"),
    (re.compile(r"\b(curl|wget)\b[^;&]*\|\s*(sudo\s+)?(ba|z)?sh\b"),
        "ダウンロードしたスクリプトの直接実行。"),
    (re.compile(r"(^|[;&|]\s*)sudo\b|\bmkfs\b|\bdd\s+if=|\bchmod\s+-R\s+777\b|\bchown\s+-R\b"),
        "システム権限を伴う操作。"),
    (re.compile(r"\bpip3?\s+install\b|\buv\s+(add|pip\s+install)\b|\bpoetry\s+add\b"),
        "依存関係の追加(存在しないパッケージ捏造・サプライチェーン対策)。"),
]


def decide(command: str) -> tuple[str | None, str]:
    for pattern, reason in DENY:
        if pattern.search(command):
            return "deny", f"[ai-team guard] 拒否: {reason}"
    for pattern, reason in ASK:
        if pattern.search(command):
            return "ask", f"[ai-team guard] 人間の確認が必要: {reason}"
    return None, ""


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print("[ai-team guard] hook 入力を解析できないためブロックしました。", file=sys.stderr)
        return 2
    if data.get("tool_name") != "Bash":
        return 0
    command = (data.get("tool_input") or {}).get("command") or ""
    decision, reason = decide(command)
    if decision:
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": reason,
                }
            },
            sys.stdout,
            ensure_ascii=False,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""PreToolUse(Edit|Write|MultiEdit|NotebookEdit) ガード。

1. 秘密情報ファイルへの書き込み → deny
2. main/master ブランチ上の追跡対象ファイル編集 → deny(作業は worktree で)
3. 別 worktree のファイル上書き → deny(他者の作業ブランチ保護)
4. テスト回避(skip/xfail/noqa/type: ignore の新規追加)→ ask
5. CI・hook・settings 自体の変更 → ask(エージェントが自分の枷を外すのを防ぐ)
6. qa-verifier / code-reviewer はコードを書き換えない(hook 入力に agent_type がある場合のみ有効)

例外: <repo>/.ai-team/ 配下(タスク・引き継ぎ・メモリ用の実行時領域)は常に許可。
緊急時の手動オーバーライド: AI_TEAM_ALLOW_MAIN_EDITS=1
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

SECRET_FILE = re.compile(r"(^|/)(\.env(\.[\w-]+)?|.*\.pem|.*\.key|id_rsa.*|id_ed25519.*|\.netrc|credentials(\.json)?|\.pgpass)$")
PROTECTED = re.compile(r"(^|/)(\.github/workflows/|\.claude/hooks/|\.claude/settings(\.local)?\.json$|scripts/ai-team/)")
BYPASS_MARKERS = [
    r"pytest\.mark\.skip",
    r"pytest\.skip\(",
    r"pytest\.mark\.xfail",
    r"unittest\.skip",
    r"#\s*noqa",
    r"#\s*type:\s*ignore",
    r"#\s*pragma:\s*no\s*cover",
]
READ_ONLY_AGENTS = {"code-reviewer", "qa-verifier"}


def git(cwd: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def existing_dir(path: Path) -> Path:
    p = path if path.is_dir() else path.parent
    while not p.exists() and p != p.parent:
        p = p.parent
    return p


def main_repo_root(cwd: Path) -> Path | None:
    common = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(common).parent if common else None


def count(markers: list[str], text: str) -> int:
    return sum(len(re.findall(m, text)) for m in markers)


def new_and_old_text(tool_input: dict, path: Path) -> tuple[str, str]:
    if "edits" in tool_input:  # MultiEdit
        new = "\n".join(e.get("new_string", "") for e in tool_input["edits"])
        old = "\n".join(e.get("old_string", "") for e in tool_input["edits"])
        return new, old
    if "new_string" in tool_input:  # Edit
        return tool_input.get("new_string", ""), tool_input.get("old_string", "")
    new = tool_input.get("content") or tool_input.get("new_source") or ""
    try:
        old = path.read_text(encoding="utf-8") if path.is_file() else ""
    except (OSError, UnicodeDecodeError):
        old = ""
    return new, old


def respond(decision: str, reason: str) -> int:
    json.dump(
        {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision,
                                "permissionDecisionReason": f"[ai-team guard] {reason}"}},
        sys.stdout, ensure_ascii=False,
    )
    return 0


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print("[ai-team guard] hook 入力を解析できないためブロックしました。", file=sys.stderr)
        return 2

    tool_input = data.get("tool_input") or {}
    raw = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not raw:
        return 0
    cwd = Path(data.get("cwd") or os.getcwd())
    path = Path(raw) if os.path.isabs(raw) else (cwd / raw)
    path = Path(os.path.normpath(path))
    posix = path.as_posix()

    if SECRET_FILE.search(posix):
        return respond("deny", f"秘密情報ファイル {path.name} への書き込みは禁止。")

    root = main_repo_root(existing_dir(path)) or main_repo_root(cwd)
    if root and (root / ".ai-team") in path.parents:
        return 0  # 実行時の共有メモリ・引き継ぎ領域

    agent = data.get("agent_type") or ""
    if agent in READ_ONLY_AGENTS:
        return respond("deny", f"{agent} はコードを変更しない役割。所見はレポートで返すこと。")

    file_top = git(existing_dir(path), "rev-parse", "--show-toplevel")
    if file_top:
        branch = git(Path(file_top), "symbolic-ref", "--short", "HEAD") or ""
        if branch in {"main", "master"} and os.environ.get("AI_TEAM_ALLOW_MAIN_EDITS") != "1":
            return respond("deny", f"{branch} ブランチ上での編集は禁止。scripts/ai-team/new_worktree.sh で worktree を作成して作業すること。")
        cwd_top = git(cwd, "rev-parse", "--show-toplevel")
        if root and cwd_top and cwd_top != file_top:
            worktrees = root / ".worktrees"
            if worktrees in Path(cwd_top).parents and worktrees in Path(file_top).parents:
                return respond("deny", f"別の worktree ({Path(file_top).name}) のファイルは上書きできない。自分の worktree 内だけを編集すること。")

    rel = os.path.relpath(posix, file_top) if file_top else posix
    if PROTECTED.search(rel.replace(os.sep, "/")):
        return respond("ask", f"{rel} は CI / ガード設定。変更には人間の確認が必要。")

    new, old = new_and_old_text(tool_input, path)
    added = [m for m in BYPASS_MARKERS if count([m], new) > count([m], old)]
    if added:
        return respond("ask", "テスト・静的解析の回避マーカーの追加を検出: " + ", ".join(added) + "。正当な理由がある場合のみ人間が承認する。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

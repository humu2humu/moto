#!/usr/bin/env python3
"""Stop フック: 未検証のまま作業を終えようとしていないか確認する。

ai/* ブランチの worktree で、base より先のコミットがある/未コミット変更があるのに、
現在の HEAD に対する quality gate の合格記録がない場合、一度だけ停止をブロックする。
stop_hook_active=True のとき(既に一度ブロック済み)は無限ループ防止のため通す。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def git(cwd: Path, *args: str) -> str:
    res = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, timeout=10, check=False)
    return res.stdout.strip() if res.returncode == 0 else ""


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if data.get("stop_hook_active"):
        return 0
    cwd = Path(data.get("cwd") or ".")
    common = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not common:
        return 0
    root = Path(common).parent
    stamps = root / ".ai-team" / "state" / "gate"

    unverified: list[str] = []
    for block in git(root, "worktree", "list", "--porcelain").split("\n\n"):
        fields = dict(line.split(" ", 1) for line in block.splitlines() if " " in line)
        branch = fields.get("branch", "").removeprefix("refs/heads/")
        wt = fields.get("worktree")
        if not wt or not branch.startswith("ai/"):
            continue
        head = fields.get("HEAD", "")
        dirty = bool(git(Path(wt), "status", "--porcelain"))
        stamp = stamps / (branch.replace("/", "__") + ".json")
        ok = False
        if stamp.is_file():
            try:
                rec = json.loads(stamp.read_text())
                ok = rec.get("result") == "PASS" and rec.get("head") == head and not dirty
            except (OSError, json.JSONDecodeError):
                ok = False
        has_work = dirty or bool(git(Path(wt), "log", "--oneline", "-1", f"{rec_base(root)}..HEAD"))
        if has_work and not ok:
            unverified.append(f"{branch} ({wt}){' [未コミット変更あり]' if dirty else ''}")

    if unverified:
        print(
            "[ai-team] quality gate に合格していない作業ブランチがあります:\n  - "
            + "\n  - ".join(unverified)
            + "\n終了する前に scripts/ai-team/quality_gate.sh を実行するか、"
              "未完了・未検証であることを明示して人間に報告してください。",
            file=sys.stderr,
        )
        return 2
    return 0


def rec_base(root: Path) -> str:
    for ref in ("origin/main", "main", "origin/master", "master"):
        if git(root, "rev-parse", "--verify", "--quiet", ref):
            return ref
    return "HEAD"


if __name__ == "__main__":
    sys.exit(main())

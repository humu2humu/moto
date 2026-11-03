#!/usr/bin/env python3
"""PostToolUse(Edit|Write|MultiEdit) 即時チェック。

編集された .py ファイルだけを対象に構文チェックと ruff(あれば)を実行し、
問題があれば exit 2 で stderr をエージェントへ返す(自動修正はしない=差分を汚さない)。
"""

from __future__ import annotations

import json
import py_compile
import shutil
import subprocess
import sys


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    path = (data.get("tool_input") or {}).get("file_path") or ""
    if not path.endswith(".py"):
        return 0
    try:
        py_compile.compile(path, doraise=True)
    except py_compile.PyCompileError as exc:
        print(f"[ai-team] 構文エラー: {exc.msg}", file=sys.stderr)
        return 2
    except OSError:
        return 0
    ruff = shutil.which("ruff")
    if ruff:
        res = subprocess.run([ruff, "check", "--quiet", "--output-format=concise", path],
                             capture_output=True, text=True, timeout=60, check=False)
        if res.returncode not in (0,):
            out = (res.stdout + res.stderr).strip()
            if out:
                print(f"[ai-team] ruff の指摘(この編集で導入したものなら修正すること):\n{out[:3000]}", file=sys.stderr)
                return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""2 つの JUnit XML を比較して回帰を検出する。

使い方: regression_diff.py BASE.xml HEAD.xml
  - base で成功 → head で失敗/エラー     : 回帰 (FAIL)
  - base に存在 → head に存在しない      : テスト消失 (FAIL — 削除によるすり抜け防止)
  - base で失敗 → head で成功            : 修正 (情報)
終了コード: 0 = 回帰なし, 1 = 回帰あり, 2 = 入力エラー
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def outcomes(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    root = ET.parse(path).getroot()
    for case in root.iter("testcase"):
        name = f"{case.get('classname', '')}::{case.get('name', '')}"
        tags = {child.tag for child in case}
        if tags & {"failure", "error"}:
            result[name] = "failed"
        elif "skipped" in tags:
            result[name] = "skipped"
        else:
            result[name] = "passed"
    return result


def compare(base: dict[str, str], head: dict[str, str]) -> tuple[list[str], list[str], list[str]]:
    regressed = sorted(n for n, o in base.items() if o == "passed" and head.get(n) in {"failed", "skipped"})
    missing = sorted(n for n in base if n not in head)
    fixed = sorted(n for n, o in base.items() if o == "failed" and head.get(n) == "passed")
    return regressed, missing, fixed


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        base, head = outcomes(Path(argv[1])), outcomes(Path(argv[2]))
    except (OSError, ET.ParseError) as exc:
        print(f"入力エラー: {exc}", file=sys.stderr)
        return 2
    regressed, missing, fixed = compare(base, head)
    for label, items in (("回帰 (passed→failed/skipped)", regressed), ("消失したテスト", missing), ("修正されたテスト", fixed)):
        print(f"{label}: {len(items)}")
        for n in items[:50]:
            print(f"  - {n}")
    return 1 if regressed or missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

"""worktree 作成 → 修正 → red→green 検証 → quality gate の一連をサンドボックス repo で検証する。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "ai-team"

BUGGY = "def add(a, b):\n    return a - b\n"
FIXED = "def add(a, b):\n    return a + b\n"
OLD_TEST = "from calc import add\n\n\ndef test_add_zero():\n    assert add(1, 0) == 1\n"
NEW_TEST = OLD_TEST + "\n\ndef test_add_positive():\n    assert add(2, 3) == 5\n"


def sh(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "AI_TEAM_TEST_CMD": f"{sys.executable} -m pytest -q -p no:cacheprovider"}
    return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, check=check, env=env, timeout=120)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "proj"
    r.mkdir()
    sh(r, "git", "init", "-q", "-b", "main")
    sh(r, "git", "config", "user.email", "t@example.com")
    sh(r, "git", "config", "user.name", "t")
    (r / "calc.py").write_text(BUGGY)
    (r / "tests").mkdir()
    (r / "tests" / "test_calc.py").write_text(OLD_TEST)
    sh(r, "git", "add", ".")
    sh(r, "git", "commit", "-qm", "init")
    return r


def make_worktree(repo: Path) -> Path:
    out = sh(repo, str(SCRIPTS / "new_worktree.sh"), "7", "add-sign")
    wt = Path(out.stdout.strip())
    sh(wt, "git", "config", "user.email", "t@example.com")
    return wt


def commit(wt: Path, msg: str) -> None:
    sh(wt, "git", "add", "-A")
    sh(wt, "git", "-c", "user.name=t", "commit", "-qm", msg)


def test_new_worktree_creates_branch_and_task(repo: Path) -> None:
    wt = make_worktree(repo)
    assert wt == repo / ".worktrees" / "7"
    assert sh(wt, "git", "symbolic-ref", "--short", "HEAD").stdout.strip() == "ai/7-add-sign"
    meta = json.loads((repo / ".ai-team" / "tasks" / "7" / "meta.json").read_text())
    assert meta["base"] == "main"
    # 二重作成は拒否(上書きしない)
    assert sh(repo, str(SCRIPTS / "new_worktree.sh"), "7", "add-sign", check=False).returncode != 0


def test_full_fix_passes_red_green_and_gate(repo: Path) -> None:
    wt = make_worktree(repo)
    (wt / "calc.py").write_text(FIXED)
    (wt / "tests" / "test_calc.py").write_text(NEW_TEST)
    commit(wt, "fix(calc): add returns sum")

    rg = sh(wt, str(SCRIPTS / "verify_red_green.sh"), "tests/test_calc.py::test_add_positive", check=False)
    assert rg.returncode == 0, rg.stderr

    gate = sh(wt, "env", "AI_TEAM_REGRESSION=1", str(SCRIPTS / "quality_gate.sh"), check=False)
    assert gate.returncode == 0, gate.stderr
    stamp = json.loads((repo / ".ai-team" / "state" / "gate" / "ai__7-add-sign.json").read_text())
    assert stamp["result"] == "PASS"


def test_test_that_does_not_reproduce_bug_fails_red_check(repo: Path) -> None:
    wt = make_worktree(repo)
    (wt / "calc.py").write_text(FIXED)
    weak = OLD_TEST + "\n\ndef test_add_zero_again():\n    assert add(0, 0) == 0\n"
    (wt / "tests" / "test_calc.py").write_text(weak)
    commit(wt, "fix(calc): weak test")
    rg = sh(wt, str(SCRIPTS / "verify_red_green.sh"), "tests/test_calc.py::test_add_zero_again", check=False)
    assert rg.returncode != 0
    assert "RED   NG" in rg.stderr


def test_gate_fails_without_regression_test(repo: Path) -> None:
    wt = make_worktree(repo)
    (wt / "calc.py").write_text(FIXED)
    commit(wt, "fix(calc): no test")
    gate = sh(wt, str(SCRIPTS / "quality_gate.sh"), check=False)
    assert gate.returncode != 0
    assert not (repo / ".ai-team" / "state" / "gate" / "ai__7-add-sign.json").exists()


def test_gate_fails_on_skip_marker(repo: Path) -> None:
    wt = make_worktree(repo)
    (wt / "calc.py").write_text(FIXED)
    (wt / "tests" / "test_calc.py").write_text("import pytest\n" + OLD_TEST.replace(
        "def test_add_zero", "@pytest.mark.skip\ndef test_add_zero"))
    commit(wt, "fix(calc): sneaky skip")
    assert sh(wt, str(SCRIPTS / "quality_gate.sh"), check=False).returncode != 0


def test_gate_detects_regression_against_base(repo: Path) -> None:
    wt = make_worktree(repo)
    # 既存テスト test_add_zero を壊す変更 + 新しいテスト
    (wt / "calc.py").write_text("def add(a, b):\n    return a + b + 1\n")
    (wt / "tests" / "test_calc.py").write_text(NEW_TEST.replace("== 5", "== 6"))
    commit(wt, "fix(calc): breaks zero case")
    gate = sh(wt, "env", "AI_TEAM_REGRESSION=1", str(SCRIPTS / "quality_gate.sh"), check=False)
    assert gate.returncode != 0
    assert "test_add_zero" in gate.stderr


def test_gate_refuses_main(repo: Path) -> None:
    assert sh(repo, str(SCRIPTS / "quality_gate.sh"), check=False).returncode != 0


def test_cleanup_refuses_unmerged(repo: Path) -> None:
    wt = make_worktree(repo)
    (wt / "calc.py").write_text(FIXED)
    commit(wt, "fix")
    res = sh(repo, str(SCRIPTS / "cleanup_worktree.sh"), "7", check=False)
    assert res.returncode != 0 and wt.exists()

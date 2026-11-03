"""daily-assistant ワークフローの安全条件が崩れていないことを確認する。"""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[2]
WF = yaml.safe_load((ROOT / ".github" / "workflows" / "daily-assistant.yml").read_text(encoding="utf-8"))
JOB = WF["jobs"]["answer"]


def test_triggers_are_issue_events_only() -> None:
    triggers = WF.get("on") or WF.get(True)  # PyYAML は `on` を True と読む
    assert set(triggers) == {"issues", "issue_comment"}


def test_only_owner_and_question_label_can_trigger() -> None:
    cond = JOB["if"]
    assert "github.event.sender.login == github.repository_owner" in cond
    assert "contains(github.event.issue.labels.*.name, 'question')" in cond
    assert "!github.event.issue.pull_request" in cond


def test_token_permissions_are_minimal() -> None:
    assert WF["permissions"] == {"contents": "read", "issues": "write"}


def test_claude_has_no_code_writing_or_push_tools() -> None:
    step = next(s for s in JOB["steps"] if s.get("id") == "claude")
    args = step["with"]["claude_args"]
    allowed = args.split("--allowedTools", 1)[1].split("\n", 1)[0]
    assert "Edit" not in allowed
    assert "git" not in allowed
    assert "Bash(gh issue view:*)" in allowed
    assert "Bash(*" not in allowed and '"Bash"' not in allowed
    assert "--max-turns" in args


def test_answer_is_written_outside_repo_and_posted_by_fixed_step() -> None:
    post = next(s for s in JOB["steps"] if s.get("name") == "Post answer")
    assert post["env"]["ANSWER_FILE"].startswith("${{ runner.temp }}")
    claude = next(s for s in JOB["steps"] if s.get("id") == "claude")
    assert "${{ runner.temp }}/answer.md" in claude["with"]["prompt"]
    assert "runner." not in str(JOB["env"])  # job レベル env では runner コンテキスト不可
    assert '"$ISSUE_NUMBER"' in post["run"]

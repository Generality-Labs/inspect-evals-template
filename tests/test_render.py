"""Render the template for each answer set and check the result."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests.conftest import ROOT, Rendered, render


def test_answers_file_stores_the_questions_only(rendered: Rendered) -> None:
    # package_name is derived from eval_name on every render (when: false), so it is
    # not stored; a later rename of eval_name re-derives it.
    answers = yaml.safe_load((rendered.path / ".copier-answers.yml").read_text())
    assert answers["eval_name"] == "sample-eval"
    assert "package_name" not in answers


@pytest.mark.parametrize("bad", ["My Eval", "my_eval", "Eval-1", "-eval", "eval-"])
def test_eval_name_must_be_kebab_case(template_src: Path, tmp_path: Path, bad: str) -> None:
    # copier raises a plain ValueError for a validator failure on non-interactive data.
    with pytest.raises(ValueError, match="kebab-case"):
        render(template_src, tmp_path / bad.replace(" ", "_"), eval_name=bad)


def test_message_after_copy_lists_next_steps() -> None:
    message = yaml.safe_load((ROOT / "copier.yml").read_text())["_message_after_copy"]
    for step in ["uv sync", "uv run pre-commit install", "git init", "uv.lock", "git add -A"]:
        assert step in message


def test_v1_files_are_gone(rendered: Rendered) -> None:
    for gone in [
        "MANAGED_FILES.md",
        ".template-version",
        ".template-sync-sha",
        "tools",
        "src/utils",
        ".claude/skills",
        "AUTOMATED_CHECKS.md",
        "BEST_PRACTICES.md",
        "EVALUATION_CHECKLIST.md",
        "TASK_VERSIONING.md",
        ".github/workflows/checks.yml",
        ".github/workflows/sync-template.yml",
        ".github/workflows/pr-template-check.yml",
        ".github/workflows/markdown-lint.yml",
        ".github/PULL_REQUEST_TEMPLATE.md",
        "src/examples/simple_qa",
    ]:
        assert not (rendered.path / gone).exists(), gone

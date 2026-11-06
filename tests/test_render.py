"""Render the template for each answer set and check the result."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
import yaml

from tests.conftest import ROOT, Rendered, layout_of, render, run, skeleton_test


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


def test_pyproject_fills_in_answers(rendered: Rendered) -> None:
    data = tomllib.loads((rendered.path / "pyproject.toml").read_text())
    assert data["project"]["name"] == "sample-eval"
    assert data["project"]["version"] == "0.1.0"
    assert data["project"]["requires-python"] == ">=3.12"
    assert data["project"]["entry-points"]["inspect_ai"] == {"sample_eval": "sample_eval"}
    assert data["tool"]["inspect-evals-lint"]["preset"] == layout_of(rendered)
    assert data["tool"]["setuptools"]["packages"]["find"]["include"] == ["sample_eval*"]


def test_layout_places_tests_and_readme(rendered: Rendered) -> None:
    flat = rendered.path / "tests/test_sample_eval.py"
    nested = rendered.path / "tests/sample_eval/test_sample_eval.py"
    eval_readme = rendered.path / "src/sample_eval/README.md"
    if layout_of(rendered) == "single-eval":
        assert flat.exists()
        assert not nested.exists()
        assert not eval_readme.exists()
        assert (
            "<!-- Usage: Automatically Generated -->" in (rendered.path / "README.md").read_text()
        )
        test_file = flat
    else:
        assert nested.exists()
        assert not flat.exists()
        assert eval_readme.exists()
        test_file = nested
    assert "def test_record_to_sample" in test_file.read_text()  # the include rendered content


def test_python_version_flows_through(template_src: Path, tmp_path: Path) -> None:
    out = render(template_src, tmp_path / "py313", python_version="3.13")
    data = tomllib.loads((out.path / "pyproject.toml").read_text())
    assert (out.path / ".python-version").read_text().strip() == "3.13"
    assert data["project"]["requires-python"] == ">=3.13"
    assert data["tool"]["ruff"]["target-version"] == "py313"
    assert data["tool"]["basedpyright"]["pythonVersion"] == "3.13"


@pytest.mark.parametrize("layout", ["multi-eval", "single-eval"])
def test_skip_if_exists_keeps_author_files(template_src: Path, tmp_path: Path, layout: str) -> None:
    out = render(template_src, tmp_path / layout, layout=layout)
    readme = out.path / "README.md"
    module = out.path / "src/sample_eval/sample_eval.py"
    test = skeleton_test(out)
    pyproject = out.path / "pyproject.toml"
    for f in (readme, module, test):
        f.write_text("edited by the author\n")
    pyproject.write_text("edited by the author\n")
    render(template_src, out.path, layout=layout)
    for f in (readme, module, test):
        assert f.read_text() == "edited by the author\n", f
    assert "edited by the author" not in pyproject.read_text()


def test_rendered_repo_tests_pass(synced: Rendered) -> None:
    result = run(synced.path, "uv", "run", "pytest", "-q")
    assert " passed" in result.stdout
    assert "failed" not in result.stdout


def test_ruff_clean(synced: Rendered) -> None:
    run(synced.path, "uv", "run", "ruff", "check")
    run(synced.path, "uv", "run", "ruff", "format", "--check")


def test_basedpyright_clean(synced: Rendered) -> None:
    run(synced.path, "uv", "run", "basedpyright", "src", "tests")


def test_lint_clean(synced: Rendered) -> None:
    run(synced.path, "uv", "run", "inspect-evals-lint", "--all")


def test_readmes_up_to_date(synced: Rendered) -> None:
    run(synced.path, "uv", "run", "inspect-evals-readmes", "generate", "--check")


def test_pre_commit_clean(synced: Rendered) -> None:
    # The synced fixture has already run git init and git add -A.
    run(synced.path, "uv", "run", "pre-commit", "run", "--all-files", "--show-diff-on-failure")
    # The fixture staged everything, so any hook rewrite shows as an unstaged change.
    changed = run(synced.path, "git", "diff", "--name-only").stdout
    assert changed == "", f"a hook rewrote a rendered file:\n{changed}"


def test_make_check(synced: Rendered) -> None:
    run(synced.path, "make", "check")


SHA_PIN = re.compile(r"^[0-9a-f]{40}$")


def _uses(workflow: Path) -> list[str]:
    data = yaml.safe_load(workflow.read_text())
    found: list[str] = []
    for job in data["jobs"].values():
        if "uses" in job:
            found.append(job["uses"])
        for step in job.get("steps", []):
            if "uses" in step:
                found.append(step["uses"])
    return found


def test_workflows_pin_third_party_actions(rendered: Rendered) -> None:
    workflows = sorted((rendered.path / ".github/workflows").glob("*.y*ml"))
    assert workflows
    for wf in workflows:
        for ref in _uses(wf):
            name, _, version = ref.partition("@")
            if name.startswith("Generality-Labs/"):
                assert version == "v1", (wf.name, ref)
            elif not name.startswith("./"):
                assert SHA_PIN.match(version), (wf.name, ref)


def test_ci_calls_python_ci_with_answers(rendered: Rendered) -> None:
    ci = yaml.safe_load((rendered.path / ".github/workflows/ci.yml").read_text())
    job = ci["jobs"]["ci"]
    assert (
        job["uses"] == "Generality-Labs/python-project-template/.github/workflows/python-ci.yml@v1"
    )
    assert job["with"] == {"python-version": "3.12", "typecheck-paths": "src tests"}


def test_template_update_opt_out(template_src: Path, tmp_path: Path) -> None:
    out = render(template_src, tmp_path / "no-update", use_template_update=False)
    assert not (out.path / ".github/workflows/template-update.yml").exists()
    assert (out.path / ".copier-answers.yml").exists()

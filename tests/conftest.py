"""Render the template into temp directories and run the results' own toolchains.

Copier renders the committed HEAD of a git repo, not its working tree, so the
template source is copied to a temp directory without .git first. That makes
uncommitted edits to copier.yml, template/ and includes/ what gets tested.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
from copier import run_copy

ROOT = Path(__file__).resolve().parents[1]

BASE_ANSWERS: dict[str, object] = {
    "eval_name": "sample-eval",
    "eval_description": "A sample evaluation for the template tests",
    "github_owner": "Generality-Labs",
    "github_username": "sample-user",
    "author_name": "Sample Author",
    "author_email": "sample@example.com",
}

ANSWER_SETS: dict[str, dict[str, object]] = {
    "defaults": {},
    "no-examples": {"include_examples": False},
    "full": {"use_claude_review": True, "include_llm_judge_example": True},
    "single-eval": {"layout": "single-eval", "include_examples": False},
}

_STRIPPED_ENV = {"VIRTUAL_ENV", "PYTEST_ADDOPTS", "PYTEST_CURRENT_TEST", "UV_PROJECT_ENVIRONMENT"}
_STRIPPED_PREFIXES = ("INSPECT_", "RUN_")


@dataclass(frozen=True)
class Rendered:
    name: str
    path: Path
    answers: dict[str, object]


def layout_of(r: Rendered) -> str:
    return str(r.answers.get("layout", "multi-eval"))


def skeleton_test(r: Rendered) -> Path:
    if layout_of(r) == "single-eval":
        return r.path / "tests/test_sample_eval.py"
    return r.path / "tests/sample_eval/test_sample_eval.py"


def render(src: Path, dst: Path, **data: object) -> Rendered:
    answers: dict[str, object] = {**BASE_ANSWERS, **data}
    run_copy(str(src), str(dst), data=answers, defaults=True, overwrite=True, quiet=True)
    return Rendered(name=dst.name, path=dst, answers=answers)


def clean_env() -> dict[str, str]:
    return {
        k: v
        for k, v in os.environ.items()
        if k not in _STRIPPED_ENV and not k.startswith(_STRIPPED_PREFIXES)
    }


def run(path: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args, cwd=path, env=clean_env(), text=True, capture_output=True, check=False
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"{' '.join(args)} in {path} exited {result.returncode}\n"
            f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
        )
    return result


@pytest.fixture(scope="session")
def template_src(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dst = tmp_path_factory.mktemp("template")
    shutil.copytree(ROOT / "template", dst / "template")
    shutil.copytree(ROOT / "includes", dst / "includes")
    shutil.copy(ROOT / "copier.yml", dst)
    return dst


@pytest.fixture(scope="session", params=list(ANSWER_SETS))
def rendered(
    request: pytest.FixtureRequest, template_src: Path, tmp_path_factory: pytest.TempPathFactory
) -> Rendered:
    name = request.param
    return render(template_src, tmp_path_factory.mktemp(name), **ANSWER_SETS[name])


@pytest.fixture(scope="session")
def synced(rendered: Rendered) -> Rendered:
    run(rendered.path, "uv", "sync", "--quiet")
    # pre-commit enumerates git ls-files, so every hook run needs a repo with everything staged.
    run(rendered.path, "git", "init", "-q")
    run(rendered.path, "git", "add", "-A")
    return rendered

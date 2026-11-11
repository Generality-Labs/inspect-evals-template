"""Run `copier update` on a rendered repo and check what an update changes.

`copier update` needs a template with version tags and a committed destination,
so these tests build both in temp directories.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from copier import run_copy, run_update

from tests.conftest import BASE_ANSWERS, run

FIRST_RELEASE = "1.0.0"
SECOND_RELEASE = "1.0.1"


def git(path: Path, *args: str) -> None:
    run(
        path,
        "git",
        "-c",
        "user.name=Template Tests",
        "-c",
        "user.email=tests@example.com",
        "-c",
        "commit.gpgsign=false",
        "-c",
        "tag.gpgsign=false",
        *args,
    )


def commit_all(path: Path, message: str) -> None:
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", message)


@pytest.fixture
def released_template(template_src: Path, tmp_path: Path) -> Path:
    """A git copy of the template with two releases that differ in one managed file."""
    src = tmp_path / "released-template"
    shutil.copytree(template_src, src)
    git(src, "init", "-q")
    commit_all(src, "first release")
    git(src, "tag", "-a", FIRST_RELEASE, "-m", FIRST_RELEASE)
    makefile = src / "template/Makefile"
    makefile.write_text(makefile.read_text() + "\n# changed in the second release\n")
    commit_all(src, "second release")
    git(src, "tag", "-a", SECOND_RELEASE, "-m", SECOND_RELEASE)
    return src


@pytest.fixture
def project(released_template: Path, tmp_path: Path) -> Path:
    """A committed repo rendered from the first release, examples included."""
    dst = tmp_path / "project"
    run_copy(
        str(released_template),
        str(dst),
        data=BASE_ANSWERS,
        defaults=True,
        vcs_ref=FIRST_RELEASE,
        quiet=True,
    )
    git(dst, "init", "-q")
    commit_all(dst, "initial commit")
    return dst


def test_examples_deleted_by_hand_stay_deleted_after_an_update(project: Path) -> None:
    shutil.rmtree(project / "src/examples")
    shutil.rmtree(project / "tests/examples")
    commit_all(project, "remove the examples")

    run_update(str(project), defaults=True, overwrite=True, vcs_ref=SECOND_RELEASE, quiet=True)

    assert "changed in the second release" in (project / "Makefile").read_text()
    assert not (project / "src/examples").exists()
    assert not (project / "tests/examples").exists()


def test_update_keeps_the_authors_root_readme(project: Path) -> None:
    (project / "README.md").write_text("# The author's README\n")
    commit_all(project, "rewrite the README")

    run_update(str(project), defaults=True, overwrite=True, vcs_ref=SECOND_RELEASE, quiet=True)

    assert (project / "README.md").read_text() == "# The author's README\n"


def test_update_with_include_examples_false_removes_the_examples(project: Path) -> None:
    # The route the README gives for removing the examples.
    run_update(
        str(project),
        data={"include_examples": False},
        defaults=True,
        overwrite=True,
        vcs_ref=SECOND_RELEASE,
        quiet=True,
    )

    assert not (project / "src/examples").exists()
    assert not (project / "tests/examples").exists()
    assert "inspect-swe" not in (project / "pyproject.toml").read_text()
    assert "src/examples" not in (project / "AGENTS.md").read_text()

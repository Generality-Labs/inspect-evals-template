# MANAGED FILE - Updates pulled from template. See MANAGED_FILES.md
"""Tests for the three-way merge logic used by sync-template.yml."""

import subprocess
import sys
from pathlib import Path

import pytest

# The scripts under test run in bash, and Python text-mode writes give CRLF
# line endings on Windows.
pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="needs bash and LF line endings"
)

SCRIPT = str(Path(__file__).resolve().parent.parent / "tools" / "sync_merge_file.sh")

BASE_CONTENT = """\
line1
line2
line3
line4
line5
"""


def run_merge(
    tmp_path: Path,
    base: str | None,
    ours: str,
    theirs: str,
) -> tuple[int, str]:
    """Run sync_merge_file.sh and return (exit_code, output_content)."""
    base_path = tmp_path / "base"
    ours_path = tmp_path / "ours"
    theirs_path = tmp_path / "theirs"
    output_path = tmp_path / "output"

    if base is not None:
        base_path.write_text(base)
    ours_path.write_text(ours)
    theirs_path.write_text(theirs)

    result = subprocess.run(
        [SCRIPT, str(base_path), str(ours_path), str(theirs_path), str(output_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    output = output_path.read_text() if output_path.exists() else ""
    return result.returncode, output


def test_no_base_falls_back_to_overwrite(tmp_path: Path) -> None:
    """First sync with no base → hard overwrite with theirs."""
    code, output = run_merge(
        tmp_path,
        base=None,
        ours="user content\n",
        theirs="template content\n",
    )
    assert code == 2
    assert output == "template content\n"


def test_only_template_changed(tmp_path: Path) -> None:
    """Template changed line3, user didn't touch anything → template change applied."""
    ours = BASE_CONTENT
    theirs = BASE_CONTENT.replace("line3", "line3-updated")

    code, output = run_merge(tmp_path, base=BASE_CONTENT, ours=ours, theirs=theirs)
    assert code == 0
    assert "line3-updated" in output
    assert "line3\n" not in output


def test_only_user_changed(tmp_path: Path) -> None:
    """User changed line2, template unchanged → user change preserved."""
    ours = BASE_CONTENT.replace("line2", "line2-custom")
    theirs = BASE_CONTENT

    code, output = run_merge(tmp_path, base=BASE_CONTENT, ours=ours, theirs=theirs)
    assert code == 0
    assert "line2-custom" in output


def test_both_changed_different_lines(tmp_path: Path) -> None:
    """User changed line1, template changed line5 → both preserved."""
    ours = BASE_CONTENT.replace("line1", "line1-custom")
    theirs = BASE_CONTENT.replace("line5", "line5-updated")

    code, output = run_merge(tmp_path, base=BASE_CONTENT, ours=ours, theirs=theirs)
    assert code == 0
    assert "line1-custom" in output
    assert "line5-updated" in output


def test_both_changed_same_line_conflicts(tmp_path: Path) -> None:
    """User and template both changed line3 → conflict markers."""
    ours = BASE_CONTENT.replace("line3", "line3-custom")
    theirs = BASE_CONTENT.replace("line3", "line3-updated")

    code, output = run_merge(tmp_path, base=BASE_CONTENT, ours=ours, theirs=theirs)
    assert code == 1
    assert "<<<<<<<" in output
    assert "line3-custom" in output
    assert "line3-updated" in output


def test_resolved_conflict_does_not_recur(tmp_path: Path) -> None:
    """After user resolves a conflict and keeps their version, next sync is clean.

    Simulates: base=current template (post-sync), user kept their line,
    template hasn't changed → no conflict.
    """
    current_template = BASE_CONTENT.replace("line3", "line3-updated")
    ours = current_template.replace("line3-updated", "line3-custom")
    theirs = current_template

    code, output = run_merge(tmp_path, base=current_template, ours=ours, theirs=theirs)
    assert code == 0
    assert "line3-custom" in output
    assert "<<<<<<<" not in output

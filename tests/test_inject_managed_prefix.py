# MANAGED FILE - Updates pulled from template. See MANAGED_FILES.md
"""Tests for the post-sync prefix injector used by sync workflows."""

import subprocess
import sys
from pathlib import Path

import pytest

# The scripts under test run in bash, and Python text-mode writes give CRLF
# line endings on Windows.
pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="needs bash and LF line endings"
)

SCRIPT = str(
    Path(__file__).resolve().parent.parent / "tools" / "inject_managed_prefix.sh"
)

PREFIX_TEXT = "MANAGED FILE - Updates pulled from template. See MANAGED_FILES.md"
LEGACY_PREFIX_TEXT = (
    "MANAGED FILE - Do not edit. Updates pulled from template. See MANAGED_FILES.md"
)
HASH_PREFIX = f"# {PREFIX_TEXT}"
HTML_PREFIX = f"<!-- {PREFIX_TEXT} -->"


def run_injector(tmp_path: Path, rel_path: str, content: str) -> str:
    """Write content to tmp_path/rel_path, run the injector, return new content."""
    target = tmp_path / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    subprocess.run(
        ["bash", SCRIPT, rel_path],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return target.read_text()


def test_markdown_gets_html_prefix_on_line_one(tmp_path: Path) -> None:
    out = run_injector(tmp_path, "AGENTS.md", "# Title\n\nbody\n")
    assert out.splitlines()[0] == HTML_PREFIX


def test_skill_md_prefix_goes_after_frontmatter(tmp_path: Path) -> None:
    content = "---\nname: foo\ndescription: a skill\n---\n\n# Foo\n"
    out = run_injector(tmp_path, ".claude/skills/foo/SKILL.md", content)
    lines = out.splitlines()
    assert lines[0] == "---", "frontmatter must still start at line 1"
    closing = next(i for i in range(1, len(lines)) if lines[i] == "---")
    assert lines[closing + 1] == HTML_PREFIX


def test_yaml_gets_hash_prefix_on_line_one(tmp_path: Path) -> None:
    out = run_injector(tmp_path, ".github/workflows/x.yml", "name: X\non: push\n")
    assert out.splitlines()[0] == HASH_PREFIX


def test_config_file_gets_hash_prefix(tmp_path: Path) -> None:
    out = run_injector(tmp_path, "tools/enforcement.config", "ENFORCE_RUFF=true\n")
    assert out.splitlines()[0] == HASH_PREFIX


def test_makefile_gets_hash_prefix(tmp_path: Path) -> None:
    out = run_injector(tmp_path, "Makefile", ".PHONY: install\ninstall:\n\techo ok\n")
    assert out.splitlines()[0] == HASH_PREFIX


def test_python_with_shebang_inserts_after_shebang(tmp_path: Path) -> None:
    content = '#!/usr/bin/env python3\n"""Doc."""\nprint("hi")\n'
    out = run_injector(tmp_path, "tools/x.py", content)
    lines = out.splitlines()
    assert lines[0] == "#!/usr/bin/env python3"
    assert lines[1] == HASH_PREFIX
    assert lines[2] == '"""Doc."""'


def test_python_without_shebang_inserts_on_line_one(tmp_path: Path) -> None:
    content = '"""Doc."""\nprint("hi")\n'
    out = run_injector(tmp_path, "tests/conftest.py", content)
    assert out.splitlines()[0] == HASH_PREFIX


def test_idempotent_on_second_run(tmp_path: Path) -> None:
    target = tmp_path / "x.yml"
    target.write_text("name: X\n")
    for _ in range(2):
        subprocess.run(
            ["bash", SCRIPT, "x.yml"], cwd=tmp_path, check=True, capture_output=True
        )
    assert target.read_text() == f"{HASH_PREFIX}\nname: X\n"


def test_skip_list_managed_files_md_unchanged(tmp_path: Path) -> None:
    out = run_injector(tmp_path, "MANAGED_FILES.md", "# Managed Files\nbody\n")
    assert PREFIX_TEXT not in out


def test_skip_list_tracking_files_unchanged(tmp_path: Path) -> None:
    for name in (".upstream-sync-sha", ".template-sync-sha", ".template-version"):
        out = run_injector(tmp_path, name, "deadbeef\n")
        assert out == "deadbeef\n"


def test_examples_directory_unchanged(tmp_path: Path) -> None:
    out = run_injector(tmp_path, "src/examples/foo/task.py", '"""Eval task."""\n')
    assert PREFIX_TEXT not in out


def test_unknown_extension_is_skipped(tmp_path: Path) -> None:
    out = run_injector(tmp_path, "data.bin", "binarycontent\n")
    assert out == "binarycontent\n"


def test_existing_heading_not_confused_with_prefix(tmp_path: Path) -> None:
    """Line 1 starting with `#` (a markdown heading) should still get the prefix."""
    out = run_injector(tmp_path, "BEST_PRACTICES.md", "# Best Practices\n\nbody\n")
    lines = out.splitlines()
    assert lines[0] == HTML_PREFIX
    assert lines[1] == "# Best Practices"


def test_skill_md_without_frontmatter_falls_back(tmp_path: Path) -> None:
    """SKILL.md missing frontmatter still gets a prefix on line 1."""
    out = run_injector(tmp_path, ".claude/skills/foo/SKILL.md", "# Foo\n\nbody\n")
    assert out.splitlines()[0] == HTML_PREFIX


def test_legacy_prefix_is_replaced_in_place(tmp_path: Path) -> None:
    """Files carrying the old 'Do not edit' wording are migrated, not duplicated."""
    legacy_yaml = f"# {LEGACY_PREFIX_TEXT}\nname: X\n"
    out = run_injector(tmp_path, ".github/workflows/x.yml", legacy_yaml)
    lines = out.splitlines()
    assert lines[0] == HASH_PREFIX
    assert lines[1] == "name: X"
    assert LEGACY_PREFIX_TEXT not in out


def test_legacy_prefix_in_skill_md_is_replaced(tmp_path: Path) -> None:
    """SKILL.md migration: legacy line-1 marker should be normalised to new wording."""
    content = (
        f"# {LEGACY_PREFIX_TEXT}\n---\nname: foo\ndescription: bar\n---\n\n# Foo\n"
    )
    out = run_injector(tmp_path, ".claude/skills/foo/SKILL.md", content)
    assert LEGACY_PREFIX_TEXT not in out
    assert PREFIX_TEXT in out


def test_executable_bit_preserved(tmp_path: Path) -> None:
    """Injector must not strip the executable bit from scripts."""
    target = tmp_path / "tools" / "x.sh"
    target.parent.mkdir(parents=True)
    target.write_text("#!/usr/bin/env bash\necho ok\n")
    target.chmod(0o755)
    subprocess.run(
        ["bash", SCRIPT, "tools/x.sh"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    assert target.stat().st_mode & 0o111, "executable bit should be preserved"


def test_missing_file_is_no_op(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", SCRIPT, "does-not-exist.yml"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0

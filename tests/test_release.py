"""Exercise the release workflow without making GitHub API requests."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.conftest import ROOT


@pytest.mark.posix_only
@pytest.mark.parametrize("state", ["missing", "existing", "error"])
def test_release_creates_or_updates_major_tag(tmp_path: Path, state: str) -> None:
    """The first release creates v2; later releases move it; lookup errors stop writes."""
    requests = tmp_path / "requests"
    gh = tmp_path / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        'printf "%s\\n" "$*" >> "$REQUESTS"\n'
        'case "$*" in\n'
        "  *git/matching-refs/tags/v2*)\n"
        '    case "$TAG_STATE" in\n'
        "      missing) echo false ;;\n"
        "      existing) echo true ;;\n"
        "      error) exit 1 ;;\n"
        "    esac ;;\n"
        '  *"-X POST"*|*"-X PATCH"*) exit 0 ;;\n'
        "  *) exit 1 ;;\n"
        "esac\n"
    )
    gh.chmod(0o755)
    workflow = yaml.safe_load((ROOT / ".github/workflows/bump-v2.yml").read_text())
    step = next(s for s in workflow["jobs"]["bump"]["steps"] if s["name"] == "Move v2")
    sha = "a" * 40
    result = subprocess.run(
        ["bash", "-c", step["run"]],
        env={
            "PATH": f"{tmp_path}{os.pathsep}{os.defpath}",
            "GITHUB_REPOSITORY": "example/template",
            "RELEASE_SHA": sha,
            "TAG_STATE": state,
            "REQUESTS": str(requests),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    calls = requests.read_text().splitlines()
    if state == "error":
        assert result.returncode != 0
        assert len(calls) == 1
    else:
        assert result.returncode == 0, result.stderr
        assert len(calls) == 2
        if state == "missing":
            assert calls[1] == (
                f"api -X POST repos/example/template/git/refs -f ref=refs/tags/v2 -f sha={sha}"
            )
        else:
            assert calls[1] == (
                f"api -X PATCH repos/example/template/git/refs/tags/v2 -f sha={sha} -F force=true"
            )

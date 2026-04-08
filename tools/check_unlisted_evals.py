#!/usr/bin/env python3
"""Check for eval directories missing eval.yaml or pyproject.toml registration.

Scans src/ for directories that look like evaluations (have an __init__.py)
but are missing eval.yaml or aren't registered in pyproject.toml entry points.
Excludes examples/ and utils/.

Usage:
    uv run python tools/check_unlisted_evals.py

Adapted from:
https://github.com/UKGovernmentBEIS/inspect_evals/blob/main/tools/check_unlisted_evals.py
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"

# Directories under src/ that are not evaluations
NON_EVAL_DIRS = {"examples", "utils"}


def get_eval_dirs() -> list[Path]:
    """Find directories under src/ that look like eval packages."""
    dirs = []
    for child in sorted(SRC_DIR.iterdir()):
        if not child.is_dir():
            continue
        if child.name in NON_EVAL_DIRS:
            continue
        if child.name.startswith(".") or child.name.startswith("_"):
            continue
        if child.name.endswith(".egg-info"):
            continue
        if (child / "__init__.py").exists():
            dirs.append(child)
    return dirs


def get_registered_evals() -> set[str]:
    """Read registered eval names from pyproject.toml entry points."""
    pyproject_path = REPO_ROOT / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    entry_points = data.get("project", {}).get("entry-points", {}).get("inspect_ai", {})
    return set(entry_points.keys())


def main() -> int:
    eval_dirs = get_eval_dirs()

    if not eval_dirs:
        print(
            "No evaluation directories found under src/ (this is expected for new repos)."
        )
        return 0

    registered = get_registered_evals()
    errors: list[str] = []

    for eval_dir in eval_dirs:
        name = eval_dir.name
        has_yaml = (eval_dir / "eval.yaml").exists()
        is_registered = name in registered

        if not has_yaml:
            errors.append(f"  {name}: missing eval.yaml")
        if not is_registered:
            errors.append(
                f"  {name}: not registered in pyproject.toml "
                f'(add: {name} = "{name}")'
            )

    if errors:
        print("Found evaluation directories with issues:")
        for error in errors:
            print(error)
        return 1

    print(f"All {len(eval_dirs)} evaluation(s) have eval.yaml and are registered.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

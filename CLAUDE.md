# Claude Code Instructions

This is the [inspect-evals-template](https://github.com/Generality-Labs/inspect-evals-template), a template for building [Inspect AI](https://inspect.aisi.org.uk/) evaluations as part of the [inspect_evals](https://github.com/UKGovernmentBEIS/inspect_evals) registry. It supports multiple evaluations in a single repository, with working examples in `src/examples/`.

## Running Commands

This project uses [uv](https://docs.astral.sh/uv/) (by Astral) for package management. **Do not use `pip install`, `python -m venv`, `source .venv/bin/activate`, or bare `python`/`pytest` commands.** Always use `uv` to run commands:

- `uv sync` — install/sync dependencies (replaces `pip install -e .`)
- `uv run pytest ...` — run tests (not `pytest` or `python -m pytest`)
- `uv run python ...` — run Python scripts (not `python` or `python3`)
- `uv run inspect eval ...` — run evaluations
- `uv run ruff ...` — run the linter
- `uv run mypy ...` — run the type checker

Note: `uv` is Astral's Python package manager. It is not related to `uvicorn` (an ASGI web server) — do not confuse them.

## Contributing

For development setup, submission requirements, and contribution guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Coding Style

When writing or modifying code in this repository, follow the guidelines in [BEST_PRACTICES.md](BEST_PRACTICES.md). Pay particular attention to the [Writing comments](BEST_PRACTICES.md#writing-comments) section before adding any comments.

## Evaluation Checklist

When creating or reviewing evaluations, refer to [EVALUATION_CHECKLIST.md](EVALUATION_CHECKLIST.md).

## Versioning

For when to bump an eval `task` version, see [TASK_VERSIONING.md](TASK_VERSIONING.md).

## Workflows

For common workflows (reviewing evals, making evaluation reports, checking agent trajectories, etc.), see [AGENTS.md](AGENTS.md).

## Pull Requests

When creating a pull request, always read `.github/PULL_REQUEST_TEMPLATE.md` and include its contents in the PR body. Fill in the checklist items and add your summary above them.

## How to Work

Understand before acting. Read the code, map the dependencies, and understand why things are the way they are before proposing changes. Present your analysis and tradeoffs to the user before implementing — let them decide what's worth changing. Don't start editing files based on assumptions or descriptions you haven't verified.

## Managed Files

This repo uses a managed file convention. See [MANAGED_FILES.md](MANAGED_FILES.md) for details on which files are managed (updated from the template) vs. user-owned.

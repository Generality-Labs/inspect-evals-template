# Changelog

All notable changes to this template will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Two things about versions here:

- **`v2` is a moving major tag.** Generated repos run `copier update --vcs-ref v2` on a schedule, so a release is what delivers a change to them. Publish a GitHub release for a `v2.X.Y` tag and `.github/workflows/bump-v2.yml` moves `v2` onto it.
- **Release tags are annotated; `v2` stays lightweight.** Copier reads a template's version through dunamai, which takes the newest tag on a commit by date and breaks ties by name. An annotated release tag outranks the lightweight `v2` on the same commit; the other way round copier would read the version as `2` and refuse every update as a downgrade. `bump-v2.yml` annotates the release tag if publishing left it lightweight.

## [Unreleased]

## [2.0.0] - 2026-11-XX

### Changed

- The template is a [copier](https://copier.readthedocs.io/) template. Repos are created with `uvx copier copy gh:Generality-Labs/inspect-evals-template my-eval`, record their answers in `.copier-answers.yml`, and receive template changes through `copier update` (weekly, by `template-update.yml`) instead of the sync workflows.
- Shared code comes from packages: `inspect-evals-utils` (dataset loaders, Hugging Face wrappers, ids, the README generator as `inspect-evals-readmes`), `pytest-inspect-evals` (test gates, markers, fixtures, assertions) and `inspect-evals-lint`.
- CI calls python-project-template's `python-ci.yml@v1` (ruff, basedpyright, pytest, pre-commit) plus a new `eval-checks.yml` (inspect-evals-lint and the README check). The pre-commit stack is python-project-template's (ruff through `uv run --locked`, uv-lock, actionlint, zizmor, mdformat).
- basedpyright in standard mode replaces mypy.
- A `layout` question picks the `multi-eval` or `single-eval` inspect-evals-lint layout, so an existing repo adopts the template without moving files.
- The `agentic` example takes an `agent` parameter (`react` or `claude_code` through inspect_swe) instead of using `basic_agent`.
- `gpqa` reads its version from `eval.yaml` with a five-line reader; `src/utils/` is gone.
- The eval's `pyproject.toml` has a static `version`; the task version stays in `eval.yaml`.
- The skills come from the `inspect-evals` plugin in [Generality-Labs/agent-skills](https://github.com/Generality-Labs/agent-skills), enabled through `.claude/settings.json` for Claude Code and installable in Codex and other agents.

### Added

- `.copier-answers.yml`, `template-update.yml`, `eval-checks.yml`, `dependabot.yml`, `zizmor.yml`, `.mdformat.toml`.
- A skeleton eval (`src/<package>/`), its `eval.yaml`, README with the generated sections plus "Deviations from the original implementation" and "Architecture" sections, and tests.
- `AGENTS.md` (with `CLAUDE.md` pointing at it) and a short `CONTRIBUTING.md`.
- `docs/MIGRATING.md` for repos created from v1.x.
- Questions `github_username`, `layout`, `include_examples`, `include_llm_judge_example`, `use_claude_review`, `use_template_update`, `license`.

### Removed

- `MANAGED_FILES.md`, `.template-version`, `.template-sync-sha`, `sync-template.yml`, `sync-upstream.yml`, `checks.yml`, `pr-template-check.yml`, the pull request template, `markdown-lint.yml`, `.markdownlint.yaml`, `.markdownlintignore`.
- `tools/` (all nine files) and their tests.
- `src/utils/` and `tests/utils/`.
- `.claude/skills/`.
- `AUTOMATED_CHECKS.md`, `BEST_PRACTICES.md`, `EVALUATION_CHECKLIST.md`, `TASK_VERSIONING.md` (linked from `AGENTS.md` instead).
- The `simple_qa` example.
- `mypy` and `setuptools_scm`.

### Fixed

- Creation preserves quotes, backslashes and Unicode in descriptions and author details, and rejects Python keywords and reserved template package names.
- Pre-commit's Python hooks use the selected `python_version`.
- The first v2 release creates the `v2` tag; subsequent releases update it. A failed tag lookup stops the workflow before it writes a ref.

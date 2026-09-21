# Managed Files

This repository separates files into **managed** and **user-owned** categories.

## What are managed files?

Managed files are maintained by the template maintainers and may be updated via the [sync mechanism](#sync-mechanism). They contain CI workflows, quality standards, linter configs, Claude skills, and shared tooling. You can customize managed files if needed — the sync mechanism uses three-way merging to preserve your changes when they don't conflict with template updates.

## What are user-owned files?

User-owned files are yours to create, edit, and maintain. They contain your evaluation code, tests, README, and eval metadata. The sync mechanism will never touch these files.

## Managed file list

This list of files is directly referenced by the sync-template.yml workflow.
This means that you can add or remove files to this section as needed.

<!-- MANAGED_FILES_START -->

- `.claude/skills/check-trajectories-workflow/SKILL.md`
- `agent_artefacts/trajectory_analysis/inspect_scout/analyze_validity.py`
- `agent_artefacts/trajectory_analysis/inspect_scout/extract_results.py`
- `agent_artefacts/trajectory_analysis/inspect_scout/run_all_scanners.py`
- `agent_artefacts/trajectory_analysis/inspect_scout/scanners.py`
- `agent_artefacts/trajectory_analysis/inspect_scout/utils.py`
- `.claude/skills/create-eval/SKILL.md`
- `.claude/skills/ensure-test-coverage/SKILL.md`
- `.claude/skills/eval-quality-workflow/SKILL.md`
- `.claude/skills/eval-report-workflow/SKILL.md`
- `.claude/skills/eval-validity-review/SKILL.md`
- `.claude/skills/investigate-dataset/SKILL.md`
- `.claude/skills/prepare-submission-workflow/SKILL.md`
- `.claude/skills/read-eval-logs/SKILL.md`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/actions/claude-setup/action.yaml`
- `.github/workflows/checks.yml`
- `.github/workflows/claude-review.yaml`
- `.github/workflows/markdown-lint.yml`
- `.github/workflows/pr-template-check.yml`
- `.github/workflows/sync-template.yml`
- `.github/workflows/sync-upstream.yml`
- `.markdownlint.yaml`
- `.pre-commit-config.yaml`
- `.template-sync-sha`
- `.upstream-sync-sha`
- `.template-version`
- `AGENTS.md`
- `AUTOMATED_CHECKS.md`
- `BEST_PRACTICES.md`
- `CONTRIBUTING.md`
- `EVALUATION_CHECKLIST.md`
- `MANAGED_FILES.md`
- `Makefile`
- `TASK_VERSIONING.md`
- `src/examples/`
- `tests/__init__.py`
- `tests/examples/`
- `tests/test_add_readme_section.py`
- `tests/test_generate_readmes.py`
- `tests/test_inject_managed_prefix.py`
- `tests/test_sync_merge.py`
- `tools/add_readme_section.py`
- `tools/check_posix_code.py`
- `tools/check_unlisted_evals.py`
- `tools/enforcement.config`
- `tools/generate_readmes.py`
- `tools/inject_managed_prefix.sh`
- `tools/list_large_files.sh`
- `tools/run_checks.sh`
- `tools/sync_merge_file.sh`

<!-- MANAGED_FILES_END -->

## User-owned files

These are yours — the sync mechanism will never modify them:

- `src/` — your evaluation source code
- `tests/<your_eval>/` — your tests
- `tests/conftest.py` — pytest fixtures and markers; the upstream version depends on `inspect_evals` package internals and is not synced
- `README.md` — your evaluation's documentation
- `pyproject.toml` — your project configuration (tool configs are managed, but `[project]` and `[project.entry-points]` sections are yours). Keep the `inspect-evals-lint` entry in the `dev` dependency group and the `[tool.inspect-evals-lint]` table: `checks.yml` and `tools/run_checks.sh` run `uv run inspect-evals-lint`, which needs the package installed. Repositories created before template v1.2.0 add both by hand.
- `agent_artefacts/` — runtime artefacts from agent workflows
- `LICENSE` — your chosen license. By default, the MIT license will be copied over, but this can be altered by you at any time.

## Sync mechanism

The `.github/workflows/sync-template.yml` workflow runs weekly (or on manual trigger) and:

1. Checks if the repository has had any PR activity in the last 7 days (skips inactive repos)
2. Fetches the latest template from the upstream repository
3. For each managed file, performs a **three-way merge** using the last-synced template commit as the base
4. Opens a PR if any managed files have changed
5. Your user-owned files are never touched

The three-way merge means that if you've customized a managed file and the template has changed a different part, both changes are preserved automatically. If both changed the same lines, the PR will contain conflict markers for you to resolve.

To manually trigger a sync, go to Actions > Sync Template Updates > Run workflow. Manual triggers always run, regardless of repository activity.

## What if I need to customize a managed file?

If you need to customize a managed file (e.g., add a custom ruff rule):

1. Make your change locally — the sync mechanism will preserve it
2. When the next sync PR arrives, your customization is automatically kept if it doesn't conflict with template changes
3. If there is a conflict (you and the template changed the same lines), resolve it in the PR
4. Consider opening an issue on the template repo if your customization would benefit all users

## Template version

The current template version is tracked in `.template-version`. This file is updated when managed files change materially.

# inspect-evals-template

A [copier](https://copier.readthedocs.io/) template for a repo that holds one [Inspect AI](https://inspect.aisi.org.uk/) evaluation.

```bash
uvx copier copy gh:Generality-Labs/inspect-evals-template my-eval
```

## What you get

A small repo that passes its own checks before any code is written: a skeleton task with `eval.yaml`, a README and tests; `pyproject.toml` with the shared packages pinned ([inspect-evals-utils](https://github.com/Generality-Labs/inspect-evals-utils), [pytest-inspect-evals](https://github.com/Generality-Labs/pytest-inspect-evals), [inspect-evals-lint](https://github.com/Generality-Labs/inspect-evals-lint)); CI that calls [python-project-template](https://github.com/Generality-Labs/python-project-template)'s shared workflow plus an eval-checks workflow; the pre-commit stack (ruff, zizmor, actionlint, mdformat); the `inspect-evals` skills enabled for Claude Code; and the Scout scanners for a transcript audit.

```text
my-eval/
  .copier-answers.yml
  .claude/settings.json
  .github/workflows/ci.yml, eval-checks.yml, template-update.yml
  .pre-commit-config.yaml, pyproject.toml, Makefile
  AGENTS.md, CLAUDE.md, CONTRIBUTING.md, README.md
  src/my_eval/my_eval.py, eval.yaml, README.md
  src/examples/gpqa, agentic            (if include_examples)
  tests/my_eval/test_my_eval.py
  agent_artefacts/trajectory_analysis/inspect_scout/
```

## Questions

| Question                    | Default           | Used for                                                       |
| --------------------------- | ----------------- | -------------------------------------------------------------- |
| `eval_name`                 |                   | repo, distribution and (with `-` as `_`) package name          |
| `eval_description`          |                   | `pyproject.toml`, README, `eval.yaml`                          |
| `github_owner`              | `Generality-Labs` | repository URLs                                                |
| `github_username`           | `github_owner`    | the contributor in `eval.yaml` and the README                  |
| `author_name`, `author_email` |                 | `pyproject.toml`, `LICENSE`                                    |
| `python_version`            | `3.12`            | `.python-version`, CI, `requires-python`                       |
| `layout`                    | `multi-eval`      | where tests and the eval README live (see below)               |
| `include_examples`          | yes               | ships `src/examples/` (gpqa, agentic) and their tests          |
| `include_llm_judge_example` | no                | adds the `llm_judge` example                                   |
| `use_template_update`       | yes               | weekly `copier update` pull request                            |
| `license`                   | MIT               | `LICENSE`                                                      |

`layout` matches the two [inspect-evals-lint](https://github.com/Generality-Labs/inspect-evals-lint) presets. `multi-eval` keeps tests under `tests/<package>/` and the eval README at `src/<package>/README.md`. `single-eval` keeps tests flat under `tests/` and uses the repo README as the eval README. An existing repo picks the layout it already has.

`eval_name` must be kebab-case and cannot be a Python keyword or one of the template's reserved package names: `examples`, `tests` and `src`. Descriptions and author details can contain quotes, backslashes and Unicode. The selected `python_version` also sets the interpreter used by pre-commit's Python hooks.

## Updating an existing repo

Repos created from the template get a weekly pull request from `copier update` when `use_template_update` is yes, and `uvx copier update` works by hand at any time. `README.md`, `src/<package>/` and `tests/<package>/` are never overwritten.

To move a repo made from v1.x onto this template, see [docs/MIGRATING.md](docs/MIGRATING.md).

## Skills

The `inspect-evals` skills come from [Generality-Labs/agent-skills](https://github.com/Generality-Labs/agent-skills).

- Claude Code: open the folder and trust it; the plugin loads from `.claude/settings.json`.
- Codex: `codex plugin marketplace add Generality-Labs/agent-skills` then `codex plugin add inspect-evals@generality`, once per machine.
- Other agents: `npx skills add Generality-Labs/agent-skills --agent <agent>`.

## Developing the template

`copier.yml` holds the questions, `template/` the generated repo (`.jinja` files are rendered, file names with `{% if %}` are conditional), and `includes/` the files shared between the two layouts.

```bash
uv sync
uv run pytest            # renders four answer sets and runs each result's checks and tests
uv run pytest --runslow  # also runs the agentic example's Docker test
```

Releases: add a section to `CHANGELOG.md`, tag `vX.Y.Z`, and publish a GitHub release for the tag. `bump-v2.yml` then annotates the tag and creates or moves `v2`, which is what `template-update.yml` in generated repos follows.

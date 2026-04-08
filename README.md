# Inspect Eval Template

A template repository for building [Inspect AI](https://inspect.aisi.org.uk/)
evaluations, part of the [inspect_evals](https://github.com/UKGovernmentBEIS/inspect_evals)
registry. Supports multiple evaluations in a single repository.

## Getting started

1. **Fork this repository** — click "Use this template" (or fork) on GitHub
   to create your own copy, then clone it:

   ```bash
   git clone https://github.com/<your-username>/<your-repo>.git
   cd <your-repo>
   ```

2. **Install dependencies and run**:

   ```bash
   # Install dependencies
   uv sync

   # Run an evaluation
   uv run inspect eval <eval_name>/<task_name> --model openai/gpt-4o

   # Run tests
   uv run pytest

   # Run linters
   uv run ruff check && uv run ruff format --check && uv run mypy .
   ```

## Quickstart

1. Fork and clone (see above), then `uv sync`
2. Copy an example: `cp -r src/examples/simple_qa src/my_eval`
3. Register it in `pyproject.toml`:

   ```toml
   [project.entry-points.inspect_ai]
   my_eval = "my_eval"
   ```

4. Run it: `uv run inspect eval my_eval/my_task --model openai/gpt-5-nano`

See `src/examples/` for complete working examples, including a real
benchmark adaptation (GPQA).

## Structure

Each evaluation lives in its own directory under `src/` and is registered via
entry points in `pyproject.toml`. Tests go in `tests/<eval_name>/`.

```text
src/
  <eval_name>/          # Your evaluation
    __init__.py         # Exports task function(s) for Inspect discovery
    <eval_name>.py      # Task implementation
    eval.yaml           # Evaluation metadata
  examples/             # Example evaluations (not registered)
tests/
  <eval_name>/          # Tests for your evaluation
  examples/             # Tests for examples
```

## Adding evaluations

1. Create a new directory under `src/` (e.g., `src/my_eval/`) with an
   `__init__.py` that exports your `@task` functions
2. Add an entry point in `pyproject.toml`:

   ```toml
   [project.entry-points.inspect_ai]
   my_eval = "my_eval"
   ```

3. Add the module name to `[tool.setuptools.packages.find]` include list
4. Add a mypy override for the new module

## Examples

The `src/examples/` directory contains three working evaluations demonstrating
common patterns. These are not registered as evaluations — they exist purely
as reference implementations you can copy from.

### Simple Q&A (`src/examples/simple_qa/`)

A straightforward question-answering evaluation using `match()` scoring.
Demonstrates dataset conversion, prompt templates, and few-shot examples.
Similar to evaluations like GPQA.

### LLM-as-Judge (`src/examples/llm_judge/`)

An evaluation that uses a language model to grade open-ended responses via
`model_graded_qa()`. Demonstrates custom grading templates and judge model
configuration. Similar to evaluations like Healthbench.

### GPQA (`src/examples/gpqa/`)

A real-world benchmark adaptation demonstrating external dataset loading,
multiple-choice scoring, and domain filtering. Adapted from the
[inspect_evals implementation](https://github.com/UKGovernmentBEIS/inspect_evals/tree/main/src/inspect_evals/gpqa).
Includes a fully-populated `eval.yaml` showing all available metadata fields.

### Agentic (`src/examples/agentic/`)

An agent-based evaluation where the model uses `bash()` and `python()` tools
in a Docker sandbox via `basic_agent()`. Demonstrates sandbox configuration
and tool-use scoring. Similar to evaluations like GAIA.

For more examples of production evaluations, see the
[inspect_evals](https://github.com/UKGovernmentBEIS/inspect_evals) registry,
which contains reference implementations of benchmarks like GPQA, GAIA,
HumanEval, and many others.

## Features

- **Multiple evaluation support** — add as many evaluations as needed, each
  with its own directory, tests, and metadata
- **Automated quality checks** — pre-commit hooks and CI for ruff, mypy,
  and pytest
- **Managed file sync** — template updates are synced automatically via
  GitHub Actions with three-way merging to preserve your customizations
  (see [MANAGED_FILES.md](MANAGED_FILES.md))

## CI workflows

The template includes several GitHub Actions workflows that run
automatically.

### Standard checks (always active)

- **Checks** (`checks.yml`) — runs ruff, mypy, pytest, and POSIX code
  checks on every push and PR
- **Markdown Lint** (`markdown-lint.yml`) — lints markdown files on PRs
- **Lint Evaluation** (`lint-new-evals.yml`) — checks evaluation code for
  POSIX-specific patterns on PRs
- **PR Template Check** (`pr-template-check.yml`) — verifies PRs include
  the required template checklist
- **Sync Template** (`sync-template.yml`) — weekly sync of managed files
  from the upstream template (skips inactive repos)

### Claude-powered workflows

These workflows use Claude to automate code review and issue resolution.
To enable them, add one of these secrets to your repository settings
(Settings > Secrets and variables > Actions > Secrets):

- **`ANTHROPIC_API_KEY`** — an Anthropic API key (recommended for most
  users). Create one at <https://console.anthropic.com/settings/keys>.
- **`ANTHROPIC_ROLE_ARN`** — an AWS IAM role ARN for Bedrock access via
  OIDC (for organisations using AWS Bedrock).

Without either secret, these workflows are skipped.

At time of writing, each Claude review costs roughly **$1** using
Claude Opus 4.6 ($5/$25 per million tokens input/output).

- **Claude Code Review** (`claude-review.yaml`) — reviews PRs against
  the evaluation standards in EVALUATION_CHECKLIST.md and
  BEST_PRACTICES.md. By default, reviews run only when triggered with a
  `/review` comment or manual dispatch. Optional repository variables
  (Settings > Variables > Actions):
  - `AUTO_REVIEW_ALL_COMMITS=true` — enable automatic reviews on every
    PR push
  - `CLAUDE_MODEL` — override the model (defaults to
    `claude-opus-4-6-20250725` for API key users)
- **Claude Fix Tests** (`claude-fix-tests.yaml`) — triggered when a
  reviewer requests changes. Analyses failing CI runs and pushes fixes
  directly to the PR branch.
- **Claude Issue Solver** (`claude-issue-solver.yaml`) — triggered by
  commenting `/claude` on an issue. Creates a PR that implements the
  requested changes.

## Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md) — development setup, testing, and
  submission guidelines
- [BEST_PRACTICES.md](BEST_PRACTICES.md) — evaluation design best practices
- [EVALUATION_CHECKLIST.md](EVALUATION_CHECKLIST.md) — quality checklist for
  evaluation review
- [TASK_VERSIONING.md](TASK_VERSIONING.md) — when to bump task versions

# Migrating a v1.x repo to template v2.0

v1.x copied files into the repo and synced them with a workflow. v2.0 is a copier template: the repo records its answers in `.copier-answers.yml`, and `copier update` applies template changes as a three-way merge. Shared code now comes from packages, and the skills from the `inspect-evals` plugin.

1. Write `.copier-answers.yml` at the repo root. Give every question an answer; `layout` is the one the repo already has (`multi-eval` for tests under `tests/<package>/`, `single-eval` for flat tests).

   ```yaml
   _src_path: gh:Generality-Labs/inspect-evals-template
   _commit: v2.0.0
   eval_name: lab-bench
   eval_description: LAB-Bench, a benchmark of biology research tasks
   github_owner: Generality-Labs
   github_username: your-handle
   author_name: Your Name
   author_email: you@example.com
   python_version: "3.12"
   layout: multi-eval
   include_examples: false
   include_llm_judge_example: false
   use_claude_review: false
   use_template_update: true
   license: MIT
   ```

   A repo with tests under `tests/<package>/` but its README at the root keeps `layout: multi-eval` and adds `readme_location = "repo-root"` under `[tool.inspect-evals-lint]` in `pyproject.toml`; `copier update` keeps that line.

1. Commit, then render the template into the repo. This is `copier copy`, not `copier update`: an update needs a previous render to diff against, and a v1 repo has none, so it would change nothing. With the answers file present copier reads the answers from it, replaces the managed files, leaves `README.md`, `src/<package>/` and the tests alone, and creates every v2 file that is missing.

   ```bash
   uvx copier copy --defaults --overwrite --vcs-ref v2.0.0 gh:Generality-Labs/inspect-evals-template .
   ```

   Without `--overwrite`, copier asks before replacing each existing file.

1. Review `git diff pyproject.toml` and put back your dependencies and entry point; keep the template's dependency groups and tool tables.

1. Delete the v1.x files copier leaves behind: `MANAGED_FILES.md`, `.template-version`, `.template-sync-sha`, `.github/workflows/sync-template.yml`, `.github/workflows/sync-upstream.yml`, `.github/workflows/checks.yml`, `.github/workflows/pr-template-check.yml`, `.github/workflows/markdown-lint.yml`, `.github/PULL_REQUEST_TEMPLATE.md`, `.markdownlint.yaml`, `.markdownlintignore`, `tools/`, `tests/test_*.py` for the tools, `src/utils/`, `.claude/skills/`, `AUTOMATED_CHECKS.md`, `BEST_PRACTICES.md`, `EVALUATION_CHECKLIST.md`, `TASK_VERSIONING.md` and `src/examples/simple_qa/`.

1. Replace the helper imports:

   - `from utils.metadata import load_version_from_yaml` and `EVAL_VERSION = load_version_from_yaml("my_eval")` become a reader in the task module:

     ```python
     from importlib import resources

     import yaml


     def _eval_version() -> str:
         text = resources.files(__package__).joinpath("eval.yaml").read_text(encoding="utf-8")
         return str(yaml.safe_load(text)["version"])


     EVAL_VERSION = _eval_version()
     ```

   - `from utils.sample_ids import create_stable_id` becomes `from inspect_evals_utils.ids import create_stable_id`.
   - `from utils.huggingface import ...` becomes `from inspect_evals_utils.huggingface import ...`.
   - Test helpers come from `pytest_inspect_evals.assertions` (`assert_eval_success`, `assert_task_structure`, `run_single_sample_eval`).

1. Sync and check:

   ```bash
   uv sync
   make check
   make test
   ```

1. Commit, push, and confirm CI is green. The weekly template-update workflow takes over from there.

lab-bench is the pilot for these steps; the other active repos follow once it is through.

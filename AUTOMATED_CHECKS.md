<!-- MANAGED FILE - Updates pulled from template. See MANAGED_FILES.md -->
# Automated Checks

> **Note for template users:** this document is synced from
> [inspect_evals](https://github.com/UKGovernmentBEIS/inspect_evals) where
> these checks are required for registry submission. In this template they
> are **recommended, not required** — autolint is advisory by default. See
> [Checks and enforcement](README.md#checks-and-enforcement) to opt in.

The automated checks are provided by the [inspect-evals-lint](https://github.com/Generality-Labs/inspect-evals-lint) package. It is installed through the `dev` dependency group and configured under `[tool.inspect-evals-lint]` in `pyproject.toml` (the `template` layout preset). Run it with:

```bash
uv run inspect-evals-lint <eval_name>
uv run inspect-evals-lint --all               # every evaluation and src/utils
uv run inspect-evals-lint --all --select IEBP # one category, or one rule by code or name
uv run inspect-evals-lint --explain IEBP002   # a rule's documentation
```

Every check is a *rule* with a code (`IEFS` file structure, `IECQ` code quality, `IETS` tests, `IEBP` best practices, then a number) and a name; either works in `--select`, `--ignore` and suppression comments. A rule reports one finding per site with a file and line, so CI annotates pull requests at the offending lines.

Evaluations live directly under `src/`, one package each, registered under `[project.entry-points.inspect_ai]`. `src/utils` is linted as a helper package: it runs the checks about code behaviour (private imports, score values, model roles, dependencies, tests for custom components) and not the ones about an evaluation's structure. `src/examples` is not linted. The package version is pinned in `pyproject.toml` and `uv.lock`; check implementations and their unit tests are maintained in the package repository.

To suppress a finding:

- Line-level: `# inspect-evals-lint: ignore[<rule>]` on the offending line (or any line of a multi-line statement), with a rule name or code, several comma-separated. A bare `ignore` is a configuration error.
- File-level: `# inspect-evals-lint: ignore-file[<rule>]` within the first ten lines of the file.
- Directory or package: `per-file-ignores = { "src/<eval_name>/<subdir>/**" = ["<rule>"] }` under `[tool.inspect-evals-lint]` in `pyproject.toml`; `exclude` lists globs the code rules never read at all, for code shipped into a sandbox.

You don't need to read these checks - they are presented here as a reference in case of linting errors. The canonical description of each rule, with the reasoning behind it, is its page at [inspect-evals-lint.generality.org](https://inspect-evals-lint.generality.org/CHECKS/); `--explain <rule>` prints the same text.

## File Structure (Automated)

- The evaluation is located in a sub-directory of `src/` (`package_location`)
- `__init__.py` exports task and related functions (`init_exports`)
- @task functions are contained within `src/<eval_name>/<eval_name>.py` (`main_file`)
- Task registered in `pyproject.toml` under `[project.entry-points.inspect_ai]` (`registry`)
- eval.yaml exists in the evaluation directory with all required fields (`eval_yaml`)
- README.md exists and has no TODO markers (`readme`)

## Code Quality (Automated)

- No imports from private inspect_ai modules (those starting with `_`) (`private_api_imports`)
- Score() calls use CORRECT/INCORRECT constants instead of literal strings (`score_constants`)
- `Score.unscored()` calls pass a `reason=`, and the former `metadata["unscored_reason"]` key does not appear (`unscored_reason`)
- Every suppression marker is one the linter reads (`suppression_syntax`, warns): a `# noautolint` comment or `.noautolint` file, a bare `ignore`, an `ignore-file` past the header or a selector naming no rule suppresses nothing, so it is reported at its line with the replacement in the hint.
- External eval-specific dependencies declared in `pyproject.toml` (`external_dependencies`). For `src/utils`, imports at module level must be in `[project].dependencies`, because every evaluation that imports the helper loads them; imports inside a function only need declaring in some optional group.

## Tests (Automated)

- Test directory exists at tests/<eval_name> (`tests_exist`)
- Test directory and subdirectories have `__init__.py` (`tests_init`). The template ships `tests/__init__.py`, so `tests/<eval_name>/` is imported as `tests.<eval_name>` and cannot shadow the `src/<eval_name>` package under pytest or mypy.
- At least one E2E test uses `mockllm/model` (`e2e_test`)
- `record_to_sample` is tested with a real sample (if used) (`record_to_sample_test`)
- Custom @solver decorated functions have tests (`custom_solver_tests`)
- Custom @scorer decorated functions have tests (`custom_scorer_tests`)
- Custom @tool decorated functions have tests (`custom_tool_tests`)

## Best Practices (Automated)

- `get_model()` only called inside @solver/@scorer decorated functions (`get_model_location`)
- Model roles supply a model, a `default=`, or `required=True` to prevent an unbound role from falling back to the model under evaluation (`model_role_resolution`)
- Sample() calls include an `id=` parameter for stable IDs (`sample_ids`)
- @task functions provide defaults for overridable parameters (solver, scorer, etc.) (`task_overridable_defaults`)
- Sandbox images pulled from a registry in compose files use an immutable tag or `@sha256` digest (`sandbox_image_pinning`). Untagged and `:latest` references fail; services built locally via `build:` and references interpolated from environment variables are skipped. Exceptions go under `[tool.inspect-evals-lint.allowlists.sandbox_image_pinning]` in `pyproject.toml`.
- An evaluation whose `eval.yaml` declares `metadata.requires.gpu` ships a `<eval>_sandbox_check` task with `kind: maintenance` that certifies its image on GPU hardware (`gpu_sandbox_check`).
- Dockerfile builds consume locked inputs (`dockerfile_locking`, warns): dependency installs use a committed `uv.lock` (`uv sync --locked`) or a hashed snapshot (`pip install --require-hashes -r`), `FROM` and `COPY --from` images carry an `@sha256` digest, Git dependencies name a full commit, and nothing is piped from `curl` into a shell. OS package installs cannot be locked and are named in the pass message.
- Dataset pinning is enforced at runtime: `hf_dataset()`, `load_dataset()`, `snapshot_download()`, and `hf_hub_download()` wrappers require a `revision=` keyword argument

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
uv run inspect-evals-lint --all-evals
```

Evaluations live directly under `src/`, one package each, registered under `[project.entry-points.inspect_ai]`. `src/utils` is linted as a helper package: it runs the checks about code behaviour (private imports, score values, model roles, dependencies, tests for custom components) and not the ones about an evaluation's structure. `src/examples` is not linted. The package version is pinned in `pyproject.toml` and `uv.lock`; check implementations and their unit tests are maintained in the package repository.

To suppress a check, use:

- Line-level: `# noautolint: <check_name>`
- File-level: `# noautolint-file: <check_name>` (at top of file)
- Directory-level: Add check name to `src/<eval_name>/<subdir>/.noautolint`
- Eval-level: Add check name to `src/<eval_name>/.noautolint` (this works for `utils` too)

You don't need to read these checks - they are presented here as a reference in case of linting errors. The canonical descriptions, including the reasoning behind each check, are in the package's [CHECKS.md](https://github.com/Generality-Labs/inspect-evals-lint/blob/main/docs/CHECKS.md).

## File Structure (Automated)

- The evaluation is located in a sub-directory of `src/` (`eval_location`)
- `__init__.py` exports task and related functions (`init_exports`)
- @task functions are contained within `src/<eval_name>/<eval_name>.py` (`main_file`)
- Task registered in `pyproject.toml` under `[project.entry-points.inspect_ai]` (`registry`)
- eval.yaml exists in the evaluation directory with all required fields (`eval_yaml`)
- README.md exists and has no TODO markers (`readme`)

## Code Quality (Automated)

- No imports from private inspect_ai modules (those starting with `_`) (`private_api_imports`)
- Score() calls use CORRECT/INCORRECT constants instead of literal strings (`score_constants`)
- `Score.unscored()` calls pass a `reason=`, and the former `metadata["unscored_reason"]` key does not appear (`unscored_reason`)
- External eval-specific dependencies declared in `pyproject.toml` (`external_dependencies`). For `src/utils`, imports at module level must be in `[project].dependencies`, because every evaluation that imports the helper loads them; imports inside a function only need declaring in some optional group.

## Tests (Automated)

- Test directory exists at tests/<eval_name> (`tests_exist`)
- Test directory and subdirectories have `__init__.py` (`tests_init`)
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
- Sandbox images pulled from a registry in compose files use an immutable tag or `@sha256` digest (`sandbox_image_pinning`). Untagged and `:latest` references fail; services built locally via `build:` and references interpolated from environment variables are skipped. Exceptions go under `[tool.inspect-evals-lint.sandbox-image-allowlist]` in `pyproject.toml`.
- Dataset pinning is enforced at runtime: `hf_dataset()`, `load_dataset()`, `snapshot_download()`, and `hf_hub_download()` wrappers require a `revision=` keyword argument

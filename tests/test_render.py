"""Render the template for each answer set and check the result."""

from __future__ import annotations

import ast
import json
import keyword
import re
import tomllib
from pathlib import Path

import pytest
import yaml
from copier import run_copy

from tests.conftest import (
    BASE_ANSWERS,
    ROOT,
    Rendered,
    layout_of,
    render,
    run,
    skeleton_test,
)


def test_answers_file_stores_the_questions_only(rendered: Rendered) -> None:
    # package_name is derived from eval_name on every render (when: false), so it is
    # not stored; a later rename of eval_name re-derives it.
    answers = yaml.safe_load((rendered.path / ".copier-answers.yml").read_text())
    assert answers["eval_name"] == "sample-eval"
    assert "package_name" not in answers


@pytest.mark.parametrize("bad", ["My Eval", "my_eval", "Eval-1", "-eval", "eval-"])
def test_eval_name_must_be_kebab_case(template_src: Path, tmp_path: Path, bad: str) -> None:
    # copier raises a plain ValueError for a validator failure on non-interactive data.
    with pytest.raises(ValueError, match="kebab-case"):
        render(template_src, tmp_path / bad.replace(" ", "_"), eval_name=bad)


@pytest.mark.parametrize(
    "bad", [word for word in keyword.kwlist if word.islower()] + ["examples", "tests", "src"]
)
def test_eval_name_rejects_reserved_names(template_src: Path, tmp_path: Path, bad: str) -> None:
    """Reject names that would produce invalid imports or overwrite template packages."""
    with pytest.raises(ValueError, match="reserved"):
        render(template_src, tmp_path / bad, eval_name=bad)


@pytest.mark.parametrize(
    "description",
    [
        'Tests "chain of thought" reasoning',
        "Checks C:\\new\\models\\",
        'Explains """quoted""" answers with Unicode 🧪',
    ],
)
def test_free_text_answers_are_escaped(
    template_src: Path, tmp_path: Path, description: str
) -> None:
    """Quotes and backslashes must preserve their meaning in TOML and Python."""
    author = 'Alex "Example" O\'Brien 🧪'
    email = '"alex.example"@example.com'
    out = render(
        template_src,
        tmp_path / "escaped",
        eval_description=description,
        author_name=author,
        author_email=email,
    )
    project = tomllib.loads((out.path / "pyproject.toml").read_text())["project"]
    assert project["description"] == description
    assert project["authors"] == [{"name": author, "email": email}]
    module = ast.parse((out.path / "src/sample_eval/sample_eval.py").read_text())
    assert ast.get_docstring(module) == description
    task = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "sample_eval"
    )
    docstring = ast.get_docstring(task)
    assert docstring is not None
    assert docstring.splitlines()[0] == description


def test_message_after_copy_lists_next_steps() -> None:
    message = yaml.safe_load((ROOT / "copier.yml").read_text())["_message_after_copy"]
    for step in ["uv sync", "uv run pre-commit install", "git init", "uv.lock", "git add -A"]:
        assert step in message
    # pre-commit install needs a git repo, so git init must come first.
    assert message.index("git init") < message.index("pre-commit install")


def test_v1_files_are_gone(rendered: Rendered) -> None:
    for gone in [
        "MANAGED_FILES.md",
        ".template-version",
        ".template-sync-sha",
        "tools",
        "src/utils",
        ".claude/skills",
        "AUTOMATED_CHECKS.md",
        "BEST_PRACTICES.md",
        "EVALUATION_CHECKLIST.md",
        "TASK_VERSIONING.md",
        ".github/workflows/checks.yml",
        ".github/workflows/sync-template.yml",
        ".github/workflows/pr-template-check.yml",
        ".github/workflows/markdown-lint.yml",
        ".github/PULL_REQUEST_TEMPLATE.md",
        "src/examples/simple_qa",
    ]:
        assert not (rendered.path / gone).exists(), gone


def test_pyproject_fills_in_answers(rendered: Rendered) -> None:
    data = tomllib.loads((rendered.path / "pyproject.toml").read_text())
    assert data["project"]["name"] == "sample-eval"
    assert data["project"]["version"] == "0.1.0"
    assert data["project"]["requires-python"] == ">=3.12"
    assert data["project"]["entry-points"]["inspect_ai"] == {"sample_eval": "sample_eval"}
    assert data["tool"]["inspect-evals-lint"]["preset"] == layout_of(rendered)
    assert data["tool"]["setuptools"]["packages"]["find"]["include"] == ["sample_eval*"]


def test_layout_places_tests_and_readme(rendered: Rendered) -> None:
    flat = rendered.path / "tests/test_sample_eval.py"
    nested = rendered.path / "tests/sample_eval/test_sample_eval.py"
    eval_readme = rendered.path / "src/sample_eval/README.md"
    if layout_of(rendered) == "single-eval":
        assert flat.exists()
        assert not nested.exists()
        assert not eval_readme.exists()
        assert (
            "<!-- Usage: Automatically Generated -->" in (rendered.path / "README.md").read_text()
        )
        test_file = flat
    else:
        assert nested.exists()
        assert not flat.exists()
        assert eval_readme.exists()
        test_file = nested
    assert "def test_record_to_sample" in test_file.read_text()  # the include rendered content


def test_python_version_flows_through(template_src: Path, tmp_path: Path) -> None:
    out = render(template_src, tmp_path / "py313", python_version="3.13")
    data = tomllib.loads((out.path / "pyproject.toml").read_text())
    assert (out.path / ".python-version").read_text().strip() == "3.13"
    assert data["project"]["requires-python"] == ">=3.13"
    assert data["tool"]["ruff"]["target-version"] == "py313"
    assert data["tool"]["basedpyright"]["pythonVersion"] == "3.13"
    ci = yaml.safe_load((out.path / ".github/workflows/ci.yml").read_text())
    assert ci["jobs"]["ci"]["with"]["python-version"] == "3.13"
    hooks = yaml.safe_load((out.path / ".pre-commit-config.yaml").read_text())
    assert hooks["default_language_version"]["python"] == "python3.13"


@pytest.mark.parametrize("layout", ["multi-eval", "single-eval"])
def test_skip_if_exists_keeps_author_files(template_src: Path, tmp_path: Path, layout: str) -> None:
    out = render(template_src, tmp_path / layout, layout=layout)
    readme = out.path / "README.md"
    module = out.path / "src/sample_eval/sample_eval.py"
    test = skeleton_test(out)
    pyproject = out.path / "pyproject.toml"
    for f in (readme, module, test):
        f.write_text("edited by the author\n")
    pyproject.write_text("edited by the author\n")
    render(template_src, out.path, layout=layout)
    for f in (readme, module, test):
        assert f.read_text() == "edited by the author\n", f
    assert "edited by the author" not in pyproject.read_text()


def test_rendered_repo_tests_pass(synced: Rendered) -> None:
    result = run(synced.path, "uv", "run", "pytest", "-q")
    assert " passed" in result.stdout
    assert "failed" not in result.stdout


def test_ruff_clean(synced: Rendered) -> None:
    run(synced.path, "uv", "run", "ruff", "check")
    run(synced.path, "uv", "run", "ruff", "format", "--check")


def test_basedpyright_clean(synced: Rendered) -> None:
    run(synced.path, "uv", "run", "basedpyright", "src", "tests")


def test_lint_clean(synced: Rendered) -> None:
    run(synced.path, "uv", "run", "inspect-evals-lint", "--all")


def test_readmes_up_to_date(synced: Rendered) -> None:
    run(synced.path, "uv", "run", "inspect-evals-readmes", "generate", "--check")


def test_pre_commit_clean(synced: Rendered) -> None:
    # The synced fixture has already run git init and git add -A.
    run(synced.path, "uv", "run", "pre-commit", "run", "--all-files", "--show-diff-on-failure")
    # The fixture staged everything, so any hook rewrite shows as an unstaged change.
    changed = run(synced.path, "git", "diff", "--name-only").stdout
    assert changed == "", f"a hook rewrote a rendered file:\n{changed}"


def test_make_check(synced: Rendered) -> None:
    run(synced.path, "make", "check")


def inspect_eval(r: Rendered, log_dir: Path, *args: str) -> None:
    run(
        r.path,
        "uv",
        "run",
        "inspect",
        "eval",
        *args,
        "--model",
        "mockllm/model",
        "--log-dir",
        str(log_dir),
        "--display",
        "none",
    )


MODEL_PROVIDER = re.compile(r"--model (\w+)/")


def test_docs_name_model_providers_whose_sdk_is_installed(synced: Rendered) -> None:
    # Inspect ships without the provider SDKs, so a documented `--model` command
    # fails on a fresh `uv sync` unless the SDK is a dependency.
    docs = [synced.path / "README.md", *synced.path.glob("src/**/README.md")]
    providers = {name for doc in docs for name in MODEL_PROVIDER.findall(doc.read_text())}
    assert "anthropic" in providers  # the first command in README.md
    for provider in sorted(providers):
        run(synced.path, "uv", "run", "python", "-c", f"import {provider}")


def test_task_modules_read_the_version_with_the_shared_reader(rendered: Rendered) -> None:
    modules = [p for p in rendered.path.glob("src/**/*.py") if "EVAL_VERSION =" in p.read_text()]
    assert modules
    for module in modules:
        text = module.read_text()
        assert "EVAL_VERSION = load_eval_version(__file__)" in text, module
        assert "import yaml" not in text, module
    pyproject = tomllib.loads((rendered.path / "pyproject.toml").read_text())
    assert not [d for d in pyproject["project"]["dependencies"] if d.startswith("pyyaml")]


def test_skeleton_runs_by_file_path(synced: Rendered, tmp_path: Path) -> None:
    # Inspect loads a task file given by path outside its package, so the module
    # cannot use __package__ to find eval.yaml.
    inspect_eval(synced, tmp_path, "src/sample_eval/sample_eval.py")


def test_skeleton_runs_by_registered_name(synced: Rendered, tmp_path: Path) -> None:
    inspect_eval(synced, tmp_path, "sample_eval/sample_eval")


def test_gpqa_example_runs_by_file_path(synced: Rendered, tmp_path: Path) -> None:
    if not synced.answers.get("include_examples", True):
        pytest.skip("this answer set has no examples")
    inspect_eval(synced, tmp_path, "src/examples/gpqa/gpqa.py", "--limit", "1", "--epochs", "1")


EVAL_TARGET = re.compile(r"inspect eval (\S+)")


def test_documented_eval_targets_exist(rendered: Rendered) -> None:
    # Only sample_eval has an inspect_ai entry point, so any other target has to
    # be the path of a rendered task file.
    docs = [
        *(rendered.path / name for name in ("README.md", "AGENTS.md", "CONTRIBUTING.md")),
        *rendered.path.glob("src/**/README.md"),
        *rendered.path.glob("src/**/*.py"),
    ]
    targets = {(doc, target) for doc in docs for target in EVAL_TARGET.findall(doc.read_text())}
    assert targets
    for doc, target in sorted(targets):
        if target.startswith("--") or "<" in target:  # `inspect eval --help`, placeholders
            continue
        where = (str(doc.relative_to(rendered.path)), target)
        if target.endswith(".py"):
            assert (rendered.path / target).is_file(), where
        else:
            assert target.split("/")[0] == "sample_eval", where


def test_readme_gives_a_run_command_for_each_example(rendered: Rendered) -> None:
    readme = (rendered.path / "README.md").read_text()
    examples = sorted(p.parent.name for p in rendered.path.glob("src/examples/*/eval.yaml"))
    for name in examples:
        assert f"uv run inspect eval src/examples/{name}/{name}.py" in readme
    if examples:
        assert "-T agent=claude_code" in readme
    else:
        assert "src/examples" not in readme


REMOVE_EXAMPLES = "copier update --defaults --data include_examples=false"


def test_docs_give_the_copier_route_for_removing_examples(rendered: Rendered) -> None:
    # tests/test_update.py runs this route. Deleting the folders by hand leaves the
    # inspect-swe dependency and the AGENTS.md line behind.
    readme = (rendered.path / "README.md").read_text()
    agents = (rendered.path / "AGENTS.md").read_text()
    if rendered.answers.get("include_examples", True):
        assert REMOVE_EXAMPLES in readme
        assert REMOVE_EXAMPLES in agents
        assert "delete them once" not in readme
    else:
        assert "include_examples" not in readme
        assert "include_examples" not in agents
    help_text = yaml.safe_load((ROOT / "copier.yml").read_text())["include_examples"]["help"]
    assert REMOVE_EXAMPLES in help_text


def test_gpqa_tests_that_download_carry_the_marker(synced: Rendered) -> None:
    if not synced.answers.get("include_examples", True):
        pytest.skip("this answer set has no examples")
    # Building the task downloads the CSV, so with the gate off only the three
    # tests that never build it may run.
    result = run(
        synced.path,
        "uv",
        "run",
        "pytest",
        "tests/examples/test_gpqa.py",
        "-q",
        "--color=no",
        env={"RUN_DATASET_DOWNLOAD_TESTS": "0"},
    )
    assert "3 passed, 6 skipped" in result.stdout


def test_docs_say_huggingface_tests_run_without_a_token(rendered: Rendered) -> None:
    for doc in ("CONTRIBUTING.md", "AGENTS.md"):
        text = (rendered.path / doc).read_text()
        assert "calls the Hugging Face Hub" in text, doc
        assert "run when `HF_TOKEN` is unset" in text, doc
        assert "skipped when `HF_TOKEN` is unset" not in text, doc
        assert "skipped without `HF_TOKEN`" not in text, doc


HF_MARKED_TEST = """\
import pytest


@pytest.mark.huggingface
def test_marked_huggingface() -> None:
    pass
"""


def test_huggingface_tests_run_without_a_token(synced: Rendered) -> None:
    # CI passes no HF_TOKEN to pytest, so a huggingface test has to run without one.
    probe = synced.path / "tests/test_huggingface_marker_probe.py"
    probe.write_text(HF_MARKED_TEST)
    try:
        result = run(
            synced.path,
            "uv",
            "run",
            "pytest",
            str(probe.relative_to(synced.path)),
            "-q",
            "--color=no",
            env={"HF_TOKEN": ""},
        )
    finally:
        probe.unlink()
    assert "1 passed" in result.stdout
    assert "HF_TOKEN is not set: 1 huggingface test(s) ran without authentication" in result.stdout


SHA_PIN = re.compile(r"^[0-9a-f]{40}$")


def _uses(workflow: Path) -> list[str]:
    data = yaml.safe_load(workflow.read_text())
    found: list[str] = []
    for job in data["jobs"].values():
        if "uses" in job:
            found.append(job["uses"])
        for step in job.get("steps", []):
            if "uses" in step:
                found.append(step["uses"])
    return found


def test_workflows_pin_third_party_actions(rendered: Rendered) -> None:
    workflows = sorted((rendered.path / ".github/workflows").glob("*.y*ml"))
    assert workflows
    for wf in workflows:
        for ref in _uses(wf):
            name, _, version = ref.partition("@")
            if name.startswith("Generality-Labs/"):
                assert version == "v1", (wf.name, ref)
            elif not name.startswith("./"):
                assert SHA_PIN.match(version), (wf.name, ref)


def test_ci_calls_python_ci_with_answers(rendered: Rendered) -> None:
    ci = yaml.safe_load((rendered.path / ".github/workflows/ci.yml").read_text())
    job = ci["jobs"]["ci"]
    assert (
        job["uses"] == "Generality-Labs/python-project-template/.github/workflows/python-ci.yml@v1"
    )
    assert job["with"] == {"python-version": "3.12", "typecheck-paths": "src tests"}


def test_template_update_opt_out(template_src: Path, tmp_path: Path) -> None:
    out = render(template_src, tmp_path / "no-update", use_template_update=False)
    assert not (out.path / ".github/workflows/template-update.yml").exists()
    assert (out.path / ".copier-answers.yml").exists()


def test_examples_follow_the_answers(rendered: Rendered) -> None:
    examples = rendered.path / "src/examples"
    tests = rendered.path / "tests/examples"
    pyproject = (rendered.path / "pyproject.toml").read_text()
    if rendered.answers.get("include_examples", True):
        assert (examples / "gpqa/gpqa.py").exists()
        assert (examples / "agentic/agentic.py").exists()
        assert (tests / "test_agentic.py").exists()
        assert "inspect-swe" in pyproject
    else:
        assert not examples.exists()
        assert not tests.exists()
        assert "inspect-swe" not in pyproject
    wants_judge = bool(rendered.answers.get("include_llm_judge_example", False))
    assert (examples / "llm_judge/llm_judge.py").exists() == wants_judge
    assert (tests / "test_llm_judge.py").exists() == wants_judge
    assert not (examples / "simple_qa").exists()


def test_no_claude_review_workflow(rendered: Rendered) -> None:
    # v2.0 does not ship the Claude review workflow that v1.x repos had.
    assert not (rendered.path / ".github/workflows/claude-review.yaml").exists()
    assert not (rendered.path / ".github/actions").exists()
    assert "claude-review" not in (rendered.path / ".github/zizmor.yml").read_text()
    assert "use_claude_review" not in (rendered.path / ".copier-answers.yml").read_text()


def test_claude_settings_enable_the_plugin(rendered: Rendered) -> None:
    settings = json.loads((rendered.path / ".claude/settings.json").read_text())
    marketplace = settings["extraKnownMarketplaces"]["generality"]["source"]
    assert marketplace == {
        "source": "github",
        "repo": "Generality-Labs/agent-skills",
        "ref": "v1.0.1",
    }
    assert settings["enabledPlugins"] == {"inspect-evals@generality": True}
    assert "Bash(uv run basedpyright:*)" in settings["permissions"]["allow"]
    assert "Bash(uv run mypy:*)" not in settings["permissions"]["allow"]


def test_scanners_ship_unchanged(rendered: Rendered) -> None:
    scout = rendered.path / "agent_artefacts/trajectory_analysis/inspect_scout"
    assert {p.name for p in scout.glob("*.py")} == {
        "analyze_validity.py",
        "extract_results.py",
        "run_all_scanners.py",
        "scanners.py",
        "utils.py",
    }


def test_docs_name_the_eval(rendered: Rendered) -> None:
    for doc in ["README.md", "AGENTS.md", "CONTRIBUTING.md"]:
        text = (rendered.path / doc).read_text()
        assert "{{" not in text, doc
        assert "TODO" not in text, doc
    readme = (rendered.path / "README.md").read_text()
    assert readme.startswith("# sample-eval\n")
    assert (rendered.path / "CLAUDE.md").read_text().strip() == "@AGENTS.md"
    assert "npx skills add Generality-Labs/agent-skills" in readme


@pytest.mark.docker
@pytest.mark.slow(120)
def test_agentic_react_runs_in_docker(template_src: Path, tmp_path: Path) -> None:
    out = render(template_src, tmp_path / "docker")
    run(out.path, "uv", "sync", "--quiet")
    result = run(
        out.path, "uv", "run", "pytest", "tests/examples/test_agentic.py", "--runslow", "-q"
    )
    assert "5 passed" in result.stdout


def test_answers_reach_the_skeleton(template_src: Path, tmp_path: Path) -> None:
    out = render(template_src, tmp_path / "widgets", eval_description="Counts widgets in images")
    module = (out.path / "src/sample_eval/sample_eval.py").read_text()
    assert module.startswith('"""Counts widgets in images"""')
    assert module.count("Counts widgets in images") == 2  # module and task docstrings
    assert "A sample evaluation for the template tests" not in module
    assert "Counts widgets in images" in (out.path / "src/sample_eval/eval.yaml").read_text()
    assert "Counts widgets in images" in (out.path / "src/sample_eval/README.md").read_text()
    assert 'description = "Counts widgets in images"' in (out.path / "pyproject.toml").read_text()


def test_adopting_an_existing_repo_replaces_managed_files(
    template_src: Path, tmp_path: Path
) -> None:
    # docs/MIGRATING.md: a v1 repo writes .copier-answers.yml and runs `copier copy` into itself.
    repo = tmp_path / "v1-repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text('[project]\nname = "sample-eval"\ndynamic = ["version"]\n')
    (repo / "README.md").write_text("# The author's README\n")
    (repo / "MANAGED_FILES.md").write_text("v1 leftovers\n")
    answers = "\n".join(f"{k}: {v}" for k, v in BASE_ANSWERS.items()) + "\n"
    (repo / ".copier-answers.yml").write_text(answers)
    run_copy(str(template_src), str(repo), defaults=True, overwrite=True, quiet=True)
    assert "inspect-evals-utils" in (repo / "pyproject.toml").read_text()
    assert (repo / "README.md").read_text() == "# The author's README\n"
    assert (repo / ".github/workflows/eval-checks.yml").exists()
    assert (repo / "src/sample_eval/sample_eval.py").exists()
    assert (repo / "MANAGED_FILES.md").exists()  # copier leaves v1 files for the author to delete

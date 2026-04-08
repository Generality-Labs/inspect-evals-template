#!/usr/bin/env python3
"""Generate and maintain auto-generated sections in per-eval README files.

Scans eval directories under src/, extracts metadata from eval.yaml and
task parameters from @task functions, and writes Usage, Options, Parameters,
and Contributors sections into README files between HTML comment tags.

Usage:
    uv run python tools/generate_readmes.py
    uv run python tools/generate_readmes.py --eval my_eval
    uv run python tools/generate_readmes.py --create-missing-readmes

Adapted from:
https://github.com/UKGovernmentBEIS/inspect_evals/blob/main/tools/generate_readmes.py
"""

import argparse
import importlib
import inspect
import logging
import os
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
logger = logging.getLogger(__name__)

CONTRIBUTORS_KEY = "Contributors: Automatically Generated"
OPTIONS_KEY = "Options: Automatically Generated"
USAGE_KEY = "Usage: Automatically Generated"
PARAMETERS_KEY = "Parameters: Automatically Generated"


# ---------------------------------------------------------------------------
# Lightweight metadata model (replaces inspect_evals.metadata.EvalMetadata)
# ---------------------------------------------------------------------------


@dataclass
class TaskInfo:
    name: str
    dataset_samples: int


@dataclass
class EvalInfo:
    title: str
    description: str
    path: str
    group: str
    contributors: list[str]
    tasks: list[TaskInfo]
    version: str
    arxiv: str | None = None
    dependency: str | None = None
    tags: list[str] = field(default_factory=list)

    @property
    def package_name(self) -> str:
        """The Python package name derived from the path (e.g. 'my_eval' or 'examples.gpqa')."""
        return self.path.removeprefix("src/").replace("/", ".")


def _load_eval_info(yaml_path: Path) -> EvalInfo:
    """Load an EvalInfo from an eval.yaml file."""
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    eval_name = yaml_path.parent.name
    tasks = [
        TaskInfo(name=t["name"], dataset_samples=t.get("dataset_samples", 0))
        for t in data.get("tasks", [])
    ]
    return EvalInfo(
        title=data.get("title", eval_name),
        description=data.get("description", ""),
        path=f"src/{eval_name}",
        group=data.get("group", ""),
        contributors=data.get("contributors", []),
        tasks=tasks,
        version=data.get("version", "1-A"),
        arxiv=data.get("arxiv"),
        dependency=data.get("dependency"),
        tags=data.get("tags", []),
    )


def discover_evals(src_dir: Path, include_examples: bool = False) -> list[EvalInfo]:
    """Discover all evaluations by scanning src/*/eval.yaml."""
    evals = []
    for yaml_path in sorted(src_dir.glob("*/eval.yaml")):
        if not include_examples and yaml_path.parent.name == "examples":
            continue
        evals.append(_load_eval_info(yaml_path))

    # Also check subdirectories of examples/ if requested
    if include_examples:
        for yaml_path in sorted(src_dir.glob("examples/*/eval.yaml")):
            info = _load_eval_info(yaml_path)
            # Fix the path/package for nested examples
            example_name = yaml_path.parent.name
            info.path = f"src/examples/{example_name}"
            evals.append(info)

    return evals


# ---------------------------------------------------------------------------
# README content helpers
# ---------------------------------------------------------------------------


class Contents:
    def __init__(self, contains_key: bool, prefix: list[str], suffix: list[str]):
        self.contains_key = contains_key
        self.prefix = prefix
        self.suffix = suffix


def readme_contents(file: Path, key: str) -> Contents:
    start_key = f"<!-- {key} -->"
    end_key = f"<!-- /{key} -->"

    readme_lines: list[str] = []
    with open(file, encoding="utf-8") as readme_file:
        readme_lines = readme_file.readlines()

    prefix: list[str] = []
    suffix: list[str] = []
    contains_key: bool = False
    collecting: str | None = "prefix"
    for line in readme_lines:
        line_content = line.rstrip("\r\n")
        if line_content == start_key:
            prefix.append(start_key)
            collecting = None
            contains_key = True
        elif line_content == end_key:
            suffix.append(end_key)
            collecting = "suffix"
        elif collecting == "prefix":
            prefix.append(line_content)
        elif collecting == "suffix":
            suffix.append(line_content)

    return Contents(prefix=prefix, suffix=suffix, contains_key=contains_key)


def rewrite_readme(file: Path, key: str, contents: list[str]) -> None:
    parsed = readme_contents(file, key)
    if parsed.contains_key:
        with open(file, "w", encoding="utf-8") as readme_file:
            readme_file.write(
                "\n".join(parsed.prefix + contents + parsed.suffix) + "\n"
            )


def rewrite_task_readme(eval_info: EvalInfo, key: str, contents: list[str]) -> None:
    readme_path = Path(__file__).parent.parent / eval_info.path / "README.md"
    rewrite_readme(readme_path, key, contents)


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def link_md(text: str, href: str) -> str:
    return f"[{text}]({href})"


def contributor_links(contributors: list[str]) -> list[str]:
    return [
        link_md(f"@{c.strip()}", f"https://github.com/{c.strip()}")
        for c in contributors
    ]


def build_contributors_section(eval_info: EvalInfo) -> list[str]:
    return [f"Contributed by {', '.join(contributor_links(eval_info.contributors))}"]


def build_options_section(eval_info: EvalInfo) -> list[str]:
    task_list = [task.name for task in eval_info.tasks]
    task_names = (task_list * 3)[:3]

    template = textwrap.dedent("""
        ## Options

        You can control a variety of options from the command line. For example:

        ```bash
        uv run inspect eval {pkg}/{task1} --limit 10
        uv run inspect eval {pkg}/{task2} --max-connections 10
        uv run inspect eval {pkg}/{task3} --temperature 0.5
        ```

        See `uv run inspect eval --help` for all available options.
    """)

    rendered = template.format(
        pkg=eval_info.package_name,
        task1=task_names[0],
        task2=task_names[1],
        task3=task_names[2],
    ).strip()

    return rendered.split("\n")


def build_usage_section(eval_info: EvalInfo) -> list[str]:
    formatted_tasks = [
        f"{eval_info.package_name}/{task.name}" for task in eval_info.tasks
    ]

    bash_tasks = "\n".join(
        f"uv run inspect eval {t} --model openai/gpt-5-nano" for t in formatted_tasks
    )

    python_commands = ", ".join(t.name for t in eval_info.tasks)

    template = textwrap.dedent("""\
        ## Usage

        First, install dependencies:

        ```bash
        uv sync
        ```

        Then run evaluations:

        ```bash
        {bash_tasks}
        ```

        You can also import tasks as Python objects:

        ```python
        from inspect_ai import eval
        from {package} import {python_commands}
        eval({first_task})
        ```

        After running evaluations, view logs with:

        ```bash
        uv run inspect view
        ```

        If you don't want to specify `--model` each time, create a `.env` file:

        ```bash
        INSPECT_EVAL_MODEL=anthropic/claude-opus-4-1-20250805
        ANTHROPIC_API_KEY=<anthropic-api-key>
        ```""")

    rendered = template.format(
        bash_tasks=bash_tasks,
        package=eval_info.package_name,
        python_commands=python_commands,
        first_task=eval_info.tasks[0].name,
    )

    return rendered.split("\n")


# ---------------------------------------------------------------------------
# Parameter extraction
# ---------------------------------------------------------------------------


def _parse_docstring_parameters(docstring: str) -> dict[str, str]:
    """Parse parameter descriptions from a function's docstring.

    Args:
        docstring: The function's docstring

    Returns:
        Dictionary mapping parameter names to their descriptions
    """
    docstring_params: dict[str, str] = {}
    if not docstring:
        return docstring_params

    # Match from "Args:" until we hit another section or end of string
    args_match = re.search(
        r"Args:\s*\n(.*?)(?:\n\s{0,8}[A-Z]\w+:|\Z)", docstring, re.DOTALL
    )
    if not args_match:
        return docstring_params

    args_section = args_match.group(1)

    # Detect the indentation level used for parameter names
    indent_match = re.search(r"^( +)\w", args_section, re.MULTILINE)
    param_indent = indent_match.group(1) if indent_match else r"\s+"

    # Match parameter descriptions
    param_pattern = (
        r"^{indent}(\*{{0,2}}\w+)(?:\s*\([^)]+\))?\s*:\s*(.+?)(?=^{indent}\*{{0,2}}\w+\s*(?:\([^)]+\))?\s*:|\Z)"
    ).format(indent=re.escape(param_indent))
    matches = re.finditer(param_pattern, args_section, re.MULTILINE | re.DOTALL)

    for match in matches:
        param_name = match.group(1).strip().lstrip("*")
        param_desc = match.group(2).strip()

        # Convert bullet lists to comma-separated
        param_desc = re.sub(r":\s*\n\s*[-*]\s+", ": ", param_desc, count=1)
        param_desc = re.sub(r"\n\s*[-*]\s+", ", ", param_desc)

        # Collapse whitespace
        param_desc = re.sub(r"\s+", " ", param_desc)

        docstring_params[param_name] = param_desc

    return docstring_params


def _clean_type_string(type_str: str) -> str:
    """Clean up type string by removing module prefixes."""
    type_str = type_str.replace("typing.", "")
    type_str = type_str.replace("collections.abc.", "")
    type_str = type_str.replace("pathlib._local.", "pathlib.")
    type_str = type_str.replace("NoneType", "None")
    # Remove inspect_ai internal module paths
    type_str = type_str.replace("inspect_ai.model._model.", "")
    type_str = type_str.replace("inspect_ai.solver._solver.", "")
    type_str = type_str.replace("inspect_ai.scorer._scorer.", "")
    type_str = type_str.replace("inspect_ai.util._sandbox.environment.", "")
    type_str = type_str.replace("inspect_ai.dataset._dataset.", "inspect_ai.dataset.")
    return type_str


def _format_type_annotation(annotation: Any) -> str | None:
    """Format a type annotation as a string."""
    if annotation == inspect.Parameter.empty:
        return None

    type_str = str(annotation)

    if "typing." in type_str or "collections.abc." in type_str:
        return _clean_type_string(type_str)
    elif any(
        type_str.startswith(f"{t}[")
        for t in ["list", "dict", "tuple", "set", "frozenset"]
    ):
        return _clean_type_string(type_str)
    elif "|" in type_str:
        # Python 3.10+ union syntax (e.g. int | None)
        return _clean_type_string(type_str)
    elif hasattr(annotation, "__name__"):
        return annotation.__name__
    else:
        return _clean_type_string(type_str)


def _clean_default_value(value: Any) -> str:
    """Clean up default value representation."""
    if callable(value):
        return f"{value.__name__}"
    return repr(value)


def _build_parameter_info(
    param_name: str, param: inspect.Parameter, docstring_params: dict[str, str]
) -> dict[str, Any]:
    """Build parameter information dictionary from inspect.Parameter."""
    param_info: dict[str, Any] = {"name": param_name}

    param_info["type_str"] = _format_type_annotation(param.annotation)

    if param.default != inspect.Parameter.empty:
        param_info["default"] = _clean_default_value(param.default)
    else:
        param_info["default"] = None

    param_info["description"] = docstring_params.get(param_name, "")

    return param_info


def _format_parameter(param: dict[str, Any]) -> str:
    """Format a single parameter as a markdown list item."""
    line_parts = [f"- `{param['name']}`"]

    if param["type_str"]:
        line_parts.append(f" ({param['type_str']})")

    line_parts.append(":")

    if param["description"]:
        desc = param["description"]
        # Remove existing default value patterns from description
        desc = re.sub(
            r"\s*\(defaults?(?:\s+to|:)\s*[^)]+\)",
            "",
            desc,
            flags=re.IGNORECASE,
        )
        desc = re.sub(
            r"\.\s+defaults?\s+to\s+\S+\.?\s*$", ".", desc, flags=re.IGNORECASE
        )
        line_parts.append(f" {desc}")

    if param["default"] is not None:
        line_parts.append(f" (default: `{param['default']}`)")

    return "".join(line_parts)


def extract_task_parameters(task_name: str, package_name: str) -> list[dict[str, Any]]:
    """Extract parameter information from a @task decorated function.

    Tries to import the task function from the package __init__
    (which should export @task functions).

    Args:
        task_name: Name of the task function
        package_name: Python package name (e.g. "my_eval" or "examples.gpqa")

    Returns:
        List of parameter dictionaries with name, type_str, default, and description
    """
    task_func = None

    # Import the package and look for the task function
    try:
        pkg = importlib.import_module(package_name)
        if hasattr(pkg, task_name):
            task_func = getattr(pkg, task_name)
    except (ImportError, ModuleNotFoundError):
        pass

    if task_func is None:
        logger.warning(
            f"Could not find task function '{task_name}' in package '{package_name}'"
        )
        return []

    try:
        sig = inspect.signature(task_func)
        docstring = inspect.getdoc(task_func)
        docstring_params = _parse_docstring_parameters(docstring or "")

        return [
            _build_parameter_info(param_name, param, docstring_params)
            for param_name, param in sig.parameters.items()
            if param_name != "self"
        ]
    except Exception as e:
        logger.warning(f"Could not extract parameters for {task_name}: {e}")
        return []


def _all_tasks_have_same_parameters(
    all_task_params: dict[str, list[dict[str, Any]]],
) -> bool:
    """Check if all tasks have identical parameters."""
    if len(all_task_params) <= 1:
        return True

    param_lists = list(all_task_params.values())
    return all(
        len(params) == len(param_lists[0])
        and all(
            p1["name"] == p2["name"]
            and p1["type_str"] == p2["type_str"]
            and p1["default"] == p2["default"]
            for p1, p2 in zip(params, param_lists[0])
        )
        for params in param_lists
    )


def build_parameters_section(eval_info: EvalInfo) -> list[str]:
    """Build the Parameters section for a task README."""
    content: list[str] = []

    all_task_params: dict[str, list[dict[str, Any]]] = {}
    for task in eval_info.tasks:
        parameters = extract_task_parameters(task.name, eval_info.package_name)
        all_task_params[task.name] = parameters

    all_same = _all_tasks_have_same_parameters(all_task_params)

    content.append("## Parameters")
    content.append("")

    if len(all_task_params) == 1 or all_same:
        task_names = list(all_task_params.keys())
        formatted_task_names = ", ".join(f"`{task_name}`" for task_name in task_names)
        content.append(f"### {formatted_task_names}")
        content.append("")
        parameters = list(all_task_params.values())[0]
        if parameters:
            for param in parameters:
                content.append(_format_parameter(param))
        else:
            content.append("No task parameters.")
    else:
        for task_name, parameters in all_task_params.items():
            content.append(f"### `{task_name}`")
            content.append("")
            if parameters:
                for param in parameters:
                    content.append(_format_parameter(param))
            else:
                content.append("No task parameters.")
            content.append("")

    return content


# ---------------------------------------------------------------------------
# README scaffolding
# ---------------------------------------------------------------------------


def generate_basic_readme(eval_info: EvalInfo) -> list[str]:
    """Generate basic README content for a new eval."""
    template = textwrap.dedent(f"""\
        # {eval_info.title}

        TODO: Add one or two paragraphs about your evaluation. Everything between <!-- *: Automatically Generated --> tags is written automatically based on the information in eval.yaml. Make sure to set up your eval in eval.yaml correctly and then place your custom README text outside of these tags to prevent it from being overwritten.

        <!-- {CONTRIBUTORS_KEY} -->
        <!-- /{CONTRIBUTORS_KEY} -->

        <!-- {USAGE_KEY} -->
        <!-- /{USAGE_KEY} -->

        <!-- {OPTIONS_KEY} -->
        <!-- /{OPTIONS_KEY} -->

        <!-- {PARAMETERS_KEY} -->
        <!-- /{PARAMETERS_KEY} -->

        ## Dataset

        TODO: Briefly describe the dataset and include an example if helpful.

        ## Scoring

        TODO: Explain how the evaluation is scored and any metrics reported.

        ## Evaluation Report

        TODO: A brief summary of results for your evaluation implementation compared against a standard set of existing results.

        ## Changelog
        """)

    return template.strip().split("\n")


def readme_exists(eval_info: EvalInfo) -> bool:
    readme_path = Path(__file__).parent.parent / eval_info.path / "README.md"
    return readme_path.exists()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def generate_readmes(
    eval_filter: str | None = None,
    create_missing: bool = False,
    include_examples: bool = False,
) -> None:
    """Generate/update README sections for all discovered evals.

    Args:
        eval_filter: If set, only process this eval (package name, e.g. "my_eval"
            or "examples.gpqa").
        create_missing: Create README files for evals that don't have them.
        include_examples: Also process example evaluations under src/examples/.
    """
    src_dir = Path(__file__).parent.parent / "src"
    evals = discover_evals(src_dir, include_examples=include_examples)

    if eval_filter:
        evals = [e for e in evals if e.package_name == eval_filter]
        if not evals:
            print(f"No eval found matching '{eval_filter}'")
            return

    if not evals:
        print("No evaluations found under src/")
        return

    for eval_info in evals:
        print(f"Processing: {eval_info.title} ({eval_info.path})")

        if create_missing and not readme_exists(eval_info):
            readme_path = Path(__file__).parent.parent / eval_info.path / "README.md"
            content = generate_basic_readme(eval_info)
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write("\n".join(content))
            print(f"  Created README: {readme_path}")

        if not readme_exists(eval_info):
            print("  Skipping (no README.md)")
            continue

        rewrite_task_readme(
            eval_info, CONTRIBUTORS_KEY, build_contributors_section(eval_info)
        )
        rewrite_task_readme(eval_info, USAGE_KEY, build_usage_section(eval_info))
        rewrite_task_readme(eval_info, OPTIONS_KEY, build_options_section(eval_info))
        rewrite_task_readme(
            eval_info, PARAMETERS_KEY, build_parameters_section(eval_info)
        )
        print("  Updated auto-generated sections")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate and maintain auto-generated README sections"
    )
    parser.add_argument(
        "--eval",
        default=None,
        help="Only process this eval (package name, e.g. 'my_eval' or 'examples.gpqa')",
    )
    parser.add_argument(
        "--create-missing-readmes",
        action="store_true",
        default=False,
        help="Create README files for evals that don't have them",
    )
    parser.add_argument(
        "--include-examples",
        action="store_true",
        default=False,
        help="Also process example evaluations under src/examples/",
    )
    args = parser.parse_args()

    generate_readmes(
        eval_filter=args.eval,
        create_missing=args.create_missing_readmes,
        include_examples=args.include_examples,
    )

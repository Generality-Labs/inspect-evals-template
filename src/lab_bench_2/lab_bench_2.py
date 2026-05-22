"""LAB-Bench 2: a benchmark of biology research tasks (arXiv:2604.09554).

A single parameterized task selects a dataset `tag` and a file-delivery `mode`,
and accepts an optional `solver` (defaulting to the benchmark's "bare"
single-turn `generate()`).
"""

from __future__ import annotations

from typing import Literal

from inspect_ai import Task, task
from inspect_ai.solver import Solver

from lab_bench_2.dataset import load_lab_bench_2_dataset
from lab_bench_2.scorers import scorer_for_tag
from lab_bench_2.solvers import bare
from utils.metadata import load_version_from_yaml

Mode = Literal["file", "inject", "retrieve"]

SUPPORTED_TAGS = ("litqa3",)

EVAL_VERSION = load_version_from_yaml("lab_bench_2")


@task
def lab_bench_2(
    tag: str = "litqa3",
    mode: Mode = "inject",
    solver: Solver | None = None,
) -> Task:
    """LAB-Bench 2 evaluation task.

    Args:
        tag: Which LAB-Bench 2 subset to run. Phase 1 supports only "litqa3".
        mode: How a question's data files are delivered to the model. A no-op
            for tags without files (such as litqa3). Options:

            - ``file``: Files uploaded via API. Smart routing: PDFs/images →
              context; other files → provider-side filesystem/container when
              code execution is enabled, else context.
            - ``inject``: Text file contents concatenated into the prompt as
              text.
            - ``retrieve``: Only file names/stems are given; prompt instructs
              the agent to retrieve the necessary sequences or data from a
              source of its choosing. File contents are withheld.
        solver: The solver to run. Defaults to ``bare()`` (the benchmark's "bare"
            configuration: a plain single-turn ``generate()``) when not provided.
            Pass any Inspect solver to override, e.g. ``-T solver=bare`` on the CLI.
    """
    if tag not in SUPPORTED_TAGS:
        raise NotImplementedError(
            f"tag={tag!r} is not implemented yet; supported tags: {list(SUPPORTED_TAGS)}."
        )
    return Task(
        dataset=load_lab_bench_2_dataset(tag),
        solver=solver or bare(),
        scorer=scorer_for_tag(tag),
        version=EVAL_VERSION,
    )

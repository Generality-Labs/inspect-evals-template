"""Solvers for the LAB-Bench 2 evaluation.

The reference benchmark runs each model in two configurations: `bare` (no tools,
single-turn) and an agentic configuration with provider-native tools.
"""

from __future__ import annotations

from inspect_ai.solver import Solver, generate, solver


@solver
def bare() -> Solver:
    """The benchmark's "bare" configuration: a plain single-turn ``generate()``."""
    return generate()

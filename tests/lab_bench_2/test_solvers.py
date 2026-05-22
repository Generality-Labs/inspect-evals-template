from inspect_ai.solver import Solver

from lab_bench_2.solvers import bare


def test_bare_returns_solver() -> None:
    assert isinstance(bare(), Solver)

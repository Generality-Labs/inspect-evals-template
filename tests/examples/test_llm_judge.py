"""Tests for the LLM-graded example evaluation."""

from inspect_ai import eval
from inspect_ai.model import ModelOutput, get_model
from inspect_ai.scorer import CORRECT, INCORRECT
from pytest_inspect_evals.assertions import assert_eval_success

from examples.llm_judge.llm_judge import llm_judge


def test_end_to_end() -> None:
    [log] = eval(
        tasks=llm_judge(),
        model="mockllm/model",
    )
    assert_eval_success(log)


def test_correct_grading() -> None:
    [log] = eval(
        tasks=llm_judge(),
        model=get_model(
            "mockllm/model",
            custom_outputs=[
                # Solver response
                ModelOutput.from_content(
                    model="mockllm/model",
                    content="A stack uses LIFO, a queue uses FIFO.",
                ),
                # Judge response
                ModelOutput.from_content(
                    model="mockllm/model",
                    content="GRADE: C",
                ),
            ],
        ),
        limit=1,
    )
    assert_eval_success(log)
    assert log.samples is not None
    scores = log.samples[0].scores
    assert scores is not None
    assert scores["model_graded_qa"].value == CORRECT


def test_incorrect_grading() -> None:
    [log] = eval(
        tasks=llm_judge(),
        model=get_model(
            "mockllm/model",
            custom_outputs=[
                # Solver response
                ModelOutput.from_content(
                    model="mockllm/model",
                    content="They are the same thing.",
                ),
                # Judge response
                ModelOutput.from_content(
                    model="mockllm/model",
                    content="GRADE: I",
                ),
            ],
        ),
        limit=1,
    )
    assert_eval_success(log)
    assert log.samples is not None
    scores = log.samples[0].scores
    assert scores is not None
    assert scores["model_graded_qa"].value == INCORRECT

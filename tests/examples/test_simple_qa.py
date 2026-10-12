"""Tests for the simple Q&A example evaluation."""

from inspect_ai import eval
from inspect_ai.model import ModelOutput, get_model
from pytest_inspect_evals.assertions import assert_eval_success

from examples.simple_qa.simple_qa import record_to_sample, simple_qa


def test_record_to_sample() -> None:
    record = {
        "id": "geo_1",
        "question": "What is the longest river in Africa?",
        "answer": "Nile",
        "category": "geography",
    }
    sample = record_to_sample(record)
    assert sample.input == "What is the longest river in Africa?"
    assert sample.target == "Nile"
    assert sample.id == "geo_1"
    assert sample.metadata is not None
    assert sample.metadata["category"] == "geography"


def test_end_to_end() -> None:
    [log] = eval(
        tasks=simple_qa(),
        model="mockllm/model",
    )
    assert_eval_success(log)


def test_end_to_end_correct() -> None:
    [log] = eval(
        tasks=simple_qa(),
        model=get_model(
            "mockllm/model",
            custom_outputs=[
                ModelOutput.from_content(
                    model="mockllm/model",
                    content="ANSWER: Nile",
                ),
            ],
        ),
        limit=1,
    )
    assert_eval_success(log)


def test_fewshot() -> None:
    [log] = eval(
        tasks=simple_qa(fewshot=2),
        model="mockllm/model",
        limit=1,
    )
    assert_eval_success(log)

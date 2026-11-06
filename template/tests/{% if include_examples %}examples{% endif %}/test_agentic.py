"""Tests for the agentic example evaluation."""

import pytest
from inspect_ai import eval
from inspect_ai.model import ModelOutput, get_model
from pytest_inspect_evals.assertions import assert_eval_success

from examples.agentic.agentic import agentic_eval


@pytest.mark.docker
@pytest.mark.slow(30)
def test_end_to_end() -> None:
    [log] = eval(
        tasks=agentic_eval(message_limit=5),
        model="mockllm/model",
        limit=1,
    )
    assert_eval_success(log)


@pytest.mark.docker
def test_correct_answer_scoring() -> None:
    """Test that the scorer correctly identifies the right answer."""
    [log] = eval(
        tasks=agentic_eval(message_limit=3),
        model=get_model(
            "mockllm/model",
            custom_outputs=[
                ModelOutput.from_content(
                    model="mockllm/model",
                    content="ANSWER: 77",
                ),
            ],
        ),
        limit=1,
    )
    assert_eval_success(log)

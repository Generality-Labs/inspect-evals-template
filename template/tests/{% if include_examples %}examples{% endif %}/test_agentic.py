"""Tests for the agentic example evaluation."""

import pytest
from inspect_ai import eval
from inspect_ai.model import ModelOutput, get_model
from inspect_ai.scorer import CORRECT
from pytest_inspect_evals.assertions import assert_eval_success, assert_task_structure

from examples.agentic.agentic import AGENTS, agentic_eval


def test_react_task_structure() -> None:
    assert_task_structure(agentic_eval(), sandbox_type="docker")


def test_claude_code_task_structure() -> None:
    # Claude Code needs a real model; only the task's shape is checked here.
    assert_task_structure(agentic_eval(agent="claude_code"), sandbox_type="docker")


def test_unknown_agent_raises() -> None:
    with pytest.raises(ValueError, match=r"react.*claude_code"):
        agentic_eval(agent="other")  # type: ignore[arg-type]


def test_agents_constant_matches_literal() -> None:
    assert AGENTS == ("react", "claude_code")


@pytest.mark.docker
@pytest.mark.slow(60)
def test_react_end_to_end() -> None:
    model = get_model(
        "mockllm/model",
        custom_outputs=[
            ModelOutput.for_tool_call(
                "mockllm/model", tool_name="submit", tool_arguments={"answer": "77"}
            ),
        ],
    )
    [log] = eval(tasks=agentic_eval(message_limit=5), model=model, limit=1)
    assert_eval_success(log, expected_sample_count=1)
    assert log.samples is not None
    assert log.samples[0].scores is not None
    assert log.samples[0].scores["includes"].value == CORRECT

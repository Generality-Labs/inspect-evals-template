"""Example agentic evaluation with a Docker sandbox and a choice of agent.

Shows the pattern for evaluations like GAIA: give an agent access to tools
(bash, python) in a sandboxed environment and score whether it finds the
correct answer. The `agent` parameter selects Inspect's ReAct agent or Claude
Code (through inspect_swe), so the same task can be run with both.
"""

from pathlib import Path
from typing import Literal, get_args

import inspect_swe
from inspect_ai import Task, task
from inspect_ai.agent import Agent, react
from inspect_ai.dataset import Sample
from inspect_ai.scorer import includes
from inspect_ai.tool import bash, python

SYSTEM_PROMPT = """
You are a helpful assistant that solves tasks by writing and executing code.
You have access to a bash shell and Python interpreter in a sandboxed environment.
Report the final answer on its own, without extra explanation.
""".strip()

DEFAULT_MESSAGE_LIMIT = 30

COMPOSE_FILE = str(Path(__file__).parent / "compose.yaml")

AgentName = Literal["react", "claude_code"]
AGENTS: tuple[str, ...] = get_args(AgentName)

DATASET = [
    Sample(
        input="Find the sum of all prime numbers less than 20.",
        target="77",
        id="primes_sum",
    ),
    Sample(
        input=("Using Python, compute the factorial of 12 and report the result."),
        target="479001600",
        id="factorial_12",
    ),
    Sample(
        input=(
            "Write a Python script to count how many leap years there are "
            "between 1900 and 2000 (inclusive). A leap year is divisible by 4, "
            "except centuries must also be divisible by 400."
        ),
        target="24",
        id="leap_years",
    ),
]


def _agent(agent: AgentName) -> Agent:
    """Build the agent named by the task parameter."""
    if agent == "react":
        return react(prompt=SYSTEM_PROMPT, tools=[bash(), python()])
    if agent == "claude_code":
        return inspect_swe.claude_code(system_prompt=SYSTEM_PROMPT)
    raise ValueError(f"agent must be one of {', '.join(AGENTS)}, got {agent!r}")


@task
def agentic_eval(
    agent: AgentName = "react",
    message_limit: int = DEFAULT_MESSAGE_LIMIT,
) -> Task:
    """Agentic evaluation where an agent uses tools to solve problems.

    Args:
        agent: Which agent runs the task: Inspect's ReAct agent with bash and
            python tools, or Claude Code through inspect_swe. Both run in the
            same Docker sandbox.
        message_limit: Maximum number of messages in the agent conversation.
    """
    return Task(
        dataset=DATASET,
        solver=_agent(agent),
        scorer=includes(),
        message_limit=message_limit,
        sandbox=("docker", COMPOSE_FILE),
    )

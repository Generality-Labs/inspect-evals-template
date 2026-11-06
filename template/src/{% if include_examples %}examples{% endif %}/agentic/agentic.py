"""Example agentic evaluation with a Docker sandbox.

Shows the pattern for evaluations like GAIA: give an agent access to tools
(bash, python) in a sandboxed environment and score whether it finds the
correct answer.
"""

from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.scorer import includes
from inspect_ai.solver import basic_agent, system_message
from inspect_ai.tool import bash, python

SYSTEM_PROMPT = """
You are a helpful assistant that solves tasks by writing and executing code.
You have access to a bash shell and Python interpreter in a sandboxed environment.

When you have found the answer, submit it by printing: ANSWER: <your answer>
""".strip()

DEFAULT_MESSAGE_LIMIT = 30

COMPOSE_FILE = str(Path(__file__).parent / "compose.yaml")

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


@task
def agentic_eval(
    message_limit: int = DEFAULT_MESSAGE_LIMIT,
) -> Task:
    """Agentic evaluation where models use tools to solve problems.

    Args:
        message_limit: Maximum number of messages in the agent conversation.
    """
    return Task(
        dataset=DATASET,
        solver=[
            system_message(SYSTEM_PROMPT),
            basic_agent(
                tools=[bash(), python()],
                message_limit=message_limit,
            ),
        ],
        scorer=includes(),
        sandbox=("docker", COMPOSE_FILE),
    )

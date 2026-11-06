"""Example LLM-graded evaluation demonstrating model-as-judge scoring.

Shows the pattern for evaluations like Healthbench: generate a response to an
open-ended question, then use a judge model to evaluate correctness against
a reference answer and grading criteria.
"""

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.scorer import model_graded_qa
from inspect_ai.solver import generate

GRADING_TEMPLATE = """
You are evaluating an AI assistant's response to a question.

Question: {question}
AI Response: {answer}
Reference Answer: {criterion}

Evaluate whether the AI's response is correct and complete.
Consider:
1. Factual accuracy compared to the reference answer
2. Completeness of the response
3. Clarity and coherence

Grade the response as:
- GRADE: C (Correct) if the response is factually accurate and reasonably complete
- GRADE: I (Incorrect) if the response contains errors or is missing key information
""".strip()


DATASET = [
    Sample(
        input="Explain the difference between a stack and a queue in computer science.",
        target=(
            "A stack follows LIFO (Last In, First Out) order: the most recently "
            "added element is removed first. A queue follows FIFO (First In, First "
            "Out) order: the earliest added element is removed first."
        ),
        id="ds_stack_queue",
    ),
    Sample(
        input="What is the time complexity of binary search and why?",
        target=(
            "Binary search has O(log n) time complexity because it halves the "
            "search space with each comparison, requiring at most log2(n) steps "
            "to find an element in a sorted array of n elements."
        ),
        id="ds_binary_search",
    ),
    Sample(
        input=(
            "Describe the CAP theorem and its implications for distributed systems."
        ),
        target=(
            "The CAP theorem states that a distributed system cannot simultaneously "
            "guarantee all three of: Consistency (all nodes see the same data), "
            "Availability (every request gets a response), and Partition tolerance "
            "(the system works despite network failures). In practice, since network "
            "partitions are unavoidable, systems must choose between consistency "
            "and availability during a partition."
        ),
        id="ds_cap_theorem",
    ),
    Sample(
        input="What is the difference between TCP and UDP?",
        target=(
            "TCP is a connection-oriented protocol that guarantees reliable, ordered "
            "delivery of data through acknowledgments and retransmission. UDP is a "
            "connectionless protocol that sends data without guarantees of delivery "
            "or ordering, making it faster but less reliable. TCP is used for web "
            "browsing and email; UDP is used for streaming and gaming."
        ),
        id="ds_tcp_udp",
    ),
]


@task
def llm_judge() -> Task:
    r"""LLM-graded evaluation of open-ended technical responses.

    The judge model can be overridden via CLI:

        inspect eval examples/llm_judge --model openai/gpt-4o \
            --model-roles judge=anthropic/claude-sonnet-4-20250514
    """
    return Task(
        dataset=DATASET,
        solver=generate(),
        scorer=model_graded_qa(template=GRADING_TEMPLATE),
    )

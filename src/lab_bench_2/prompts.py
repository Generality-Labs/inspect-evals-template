"""Prompts and answer parsing for the LAB-Bench 2 evaluation.

The semantic-judge rubric below is an original formulation of the grading
methodology described in the LAB-Bench 2 paper (arXiv:2604.09554). It is not
copied from the reference implementation.
"""

from __future__ import annotations

import re

JUDGE_VERDICT_CORRECT = "correct"
JUDGE_VERDICT_INCORRECT = "incorrect"
JUDGE_VERDICT_UNSURE = "unsure"

SEMANTIC_JUDGE_TEMPLATE = """\
You are grading a candidate answer to a scientific question against a reference answer.

Decide whether the candidate answer is correct. Be rigorous but fair:
- Accept answers that are semantically or numerically equivalent to the reference, \
even if worded differently, unless the question demands specific details or precision.
- Accept reasonable numerical approximations unless the question specifies a required precision.
- Treat the answer as correct only if it clearly conveys the same core conclusion as the reference.

Question:
{question}

Reference answer:
{reference}

Candidate answer:
{answer}

First explain your reasoning in one or two sentences. Then, on the final line, \
output exactly one of:
GRADE: correct
GRADE: incorrect
GRADE: unsure
"""

_GRADE_PATTERN = re.compile(r"GRADE\s*:\s*(correct|incorrect|unsure)", re.IGNORECASE)

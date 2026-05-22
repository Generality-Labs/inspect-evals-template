"""Scorers for the LAB-Bench 2 evaluation."""

from __future__ import annotations

from inspect_ai.model import GenerateConfig, get_model
from inspect_ai.scorer import (
    CORRECT,
    INCORRECT,
    Score,
    Scorer,
    Target,
    accuracy,
    scorer,
    stderr,
)
from inspect_ai.solver import TaskState

from lab_bench_2.prompts import (
    _GRADE_PATTERN,
    JUDGE_VERDICT_CORRECT,
    SEMANTIC_JUDGE_TEMPLATE,
)

DEFAULT_GRADER_MODEL = "anthropic/claude-sonnet-4-5"
GRADER_ROLE = "grader"


@scorer(metrics=[accuracy(), stderr()])
def semantic_judge_scorer() -> Scorer:
    """Grade an open-ended answer against the reference using a judge model."""

    async def score(state: TaskState, target: Target) -> Score:
        answer = state.output.completion.strip()
        if not answer:
            return Score(
                value=INCORRECT, answer="", explanation="No answer was produced."
            )

        grader = get_model(
            role=GRADER_ROLE,
            default=DEFAULT_GRADER_MODEL,
            config=GenerateConfig(temperature=0.0),
        )

        prompt = SEMANTIC_JUDGE_TEMPLATE.format(
            question=state.input_text,
            reference=target.text,
            answer=answer,
        )
        result = await grader.generate(prompt)
        verdict = parse_judge_verdict(result.completion)
        value = CORRECT if verdict == JUDGE_VERDICT_CORRECT else INCORRECT
        return Score(
            value=value,
            answer=answer,
            explanation=result.completion,
            metadata={"verdict": verdict},
        )

    return score


SCORERS_BY_TAG = {
    "litqa3": semantic_judge_scorer,
}


def scorer_for_tag(tag: str) -> Scorer:
    """Return the scorer for a tag, or raise if the tag is not yet implemented."""
    factory = SCORERS_BY_TAG.get(tag)
    if factory is None:
        raise NotImplementedError(
            f"No scorer implemented for tag={tag!r}; "
            f"supported tags: {sorted(SCORERS_BY_TAG)}."
        )
    return factory()


def parse_judge_verdict(text: str) -> str | None:
    """Return the judge's verdict, or None if no verdict line is present.

    When multiple verdict lines appear (e.g. the rubric words echoed earlier in
    the reasoning), the last match is taken as the final verdict.
    """
    matches = _GRADE_PATTERN.findall(text or "")
    if not matches:
        return None
    return str(matches[-1]).lower()

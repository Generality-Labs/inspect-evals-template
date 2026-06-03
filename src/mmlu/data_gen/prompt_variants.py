"""Hand-authored MMLU/MMMLU prompt variants and the helper that wraps items.

In Total Eval Error (Messing 2026) the MMLU "prompt variant" is the instruction
wrapper around a question, not a rewording of the question itself. Following the
paper (SI Appendix O, Assumption 1), the variants are a small hand-written set of
templates that differ only in instruction phrasing and framing while holding
constant the task, the answer format (a single letter A-D), the reasoning mode
(direct answer), and the verbatim question and choices. ``V_1`` is the canonical
MMLU benchmark prompt, included as one of the variants.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from mmlu.data_gen.categories import FR_SUBJECT_NAMES

logger = logging.getLogger(__name__)

ANSWER_LETTERS = "ABCD"
NUM_VARIANTS = 5
VARIANT_IDS = [f"V_{i}" for i in range(1, NUM_VARIANTS + 1)]
ORIGINAL_VARIANT_ID = "V_1"
LANGUAGES = ("en", "fr")

# Each template fills {subject}, {question}, and {choices}. The choices block and
# the trailing answer cue are held constant across variants (output format); only
# the instruction phrasing and framing change. V_1 is the canonical MMLU prompt.
EN_TEMPLATES = [
    "The following are multiple choice questions (with answers) about {subject}.\n"
    "\n{question}\n{choices}\nAnswer:",
    "Answer the following multiple-choice question about {subject}. Reply with "
    "only the letter (A, B, C, or D) of the correct option.\n"
    "\n{question}\n{choices}\nAnswer:",
    "Here is a question on {subject}. Choose the single best answer and respond "
    "with just its letter.\n"
    "\n{question}\n{choices}\nAnswer:",
    "You are taking an exam on {subject}. Read the question and the four options "
    "below, then give only the letter (A-D) of the correct answer.\n"
    "\n{question}\n{choices}\nAnswer:",
    "Consider the {subject} question below. Which of the four options is correct? "
    "Output only the corresponding letter.\n"
    "\n{question}\n{choices}\nAnswer:",
]

FR_TEMPLATES = [
    "Les questions suivantes sont des questions à choix multiples (avec "
    "réponses) sur {subject}.\n"
    "\n{question}\n{choices}\nRéponse :",
    "Répondez à la question à choix multiples suivante sur "
    "{subject}. Indiquez uniquement la lettre (A, B, C ou D) de la bonne "
    "réponse.\n"
    "\n{question}\n{choices}\nRéponse :",
    "Voici une question sur {subject}. Choisissez la meilleure réponse et "
    "répondez en donnant seulement sa lettre.\n"
    "\n{question}\n{choices}\nRéponse :",
    "Vous passez un examen sur {subject}. Lisez la question et les quatre options "
    "ci-dessous, puis donnez uniquement la lettre (A à D) de la bonne "
    "réponse.\n"
    "\n{question}\n{choices}\nRéponse :",
    "Considérez la question suivante sur {subject}. Laquelle des quatre "
    "options est correcte ? N'indiquez que la lettre correspondante.\n"
    "\n{question}\n{choices}\nRéponse :",
]

TEMPLATES: dict[str, list[str]] = {"en": EN_TEMPLATES, "fr": FR_TEMPLATES}


def subject_label(subject: str, language: str) -> str:
    """Return the human-readable subject label used inside a prompt.

    English uses the de-underscored slug; French uses the hand-authored name when
    available, falling back to the de-underscored slug otherwise.
    """
    spaced = subject.replace("_", " ")
    if language == "fr":
        if subject not in FR_SUBJECT_NAMES:
            logger.warning(
                "No French name for subject %r; falling back to %r.", subject, spaced
            )
        return FR_SUBJECT_NAMES.get(subject, spaced)
    return spaced


def render_choices(row: Mapping[str, object]) -> str:
    """Render the four answer choices as ``A. ...`` lines (constant across variants)."""
    return "\n".join(f"{letter}. {row[f'choice_{letter}']}" for letter in ANSWER_LETTERS)


def render_prompt(row: Mapping[str, object], variant_id: str, language: str) -> str:
    """Render one item under one prompt variant.

    Args:
        row: An item row exposing ``subject``, ``question``, and ``choice_A``..
            ``choice_D`` (e.g. a record from ``selected_items_{en,fr}.csv``).
        variant_id: One of ``VARIANT_IDS`` (``V_1``..``V_5``).
        language: ``"en"`` or ``"fr"``; selects the template set and subject label.

    Returns:
        The fully rendered user message sent to the system under test.

    Raises:
        ValueError: if ``language`` or ``variant_id`` is unknown.
    """
    if language not in TEMPLATES:
        raise ValueError(f"Unknown language {language!r}; expected one of {LANGUAGES}.")
    if variant_id not in VARIANT_IDS:
        raise ValueError(f"Unknown variant_id {variant_id!r}; expected one of {VARIANT_IDS}.")
    template = TEMPLATES[language][VARIANT_IDS.index(variant_id)]
    return template.format(
        subject=subject_label(str(row["subject"]), language),
        question=row["question"],
        choices=render_choices(row),
    )

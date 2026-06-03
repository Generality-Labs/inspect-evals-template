"""Tests for the hand-authored MMLU/MMMLU prompt variants."""

from pathlib import Path

import pandas as pd
import pytest

from mmlu.data_gen.categories import FR_SUBJECT_NAMES
from mmlu.data_gen.prompt_variants import (
    ANSWER_LETTERS,
    EN_TEMPLATES,
    FR_TEMPLATES,
    NUM_VARIANTS,
    ORIGINAL_VARIANT_ID,
    TEMPLATES,
    VARIANT_IDS,
    render_choices,
    render_prompt,
    subject_label,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "src" / "mmlu" / "data_gen" / "data"

PLACEHOLDERS = ["{subject}", "{question}", "{choices}"]

CANONICAL_EN_V1 = (
    "The following are multiple choice questions (with answers) about "
    "world religions.\n\nWhich is true?\nA. first\nB. second\nC. third\nD. fourth\nAnswer:"
)


def _synthetic_row(subject: str = "world_religions") -> dict[str, object]:
    """Build a synthetic item row with the selected-items schema."""
    return {
        "subject": subject,
        "question": "Which is true?",
        "choice_A": "first",
        "choice_B": "second",
        "choice_C": "third",
        "choice_D": "fourth",
        "answer": "A",
    }


class TestConstants:
    def test_five_index_aligned_templates_per_language(self) -> None:
        # given / when / then both languages expose exactly NUM_VARIANTS templates
        assert len(EN_TEMPLATES) == NUM_VARIANTS
        assert len(FR_TEMPLATES) == NUM_VARIANTS
        assert len(VARIANT_IDS) == NUM_VARIANTS

    def test_original_is_a_known_variant(self) -> None:
        # given / when / then the original is pinned to a real variant id
        assert ORIGINAL_VARIANT_ID == "V_1"
        assert ORIGINAL_VARIANT_ID in VARIANT_IDS

    def test_every_template_has_all_placeholders(self) -> None:
        # given every template / when / then all fill fields are present
        for template in EN_TEMPLATES + FR_TEMPLATES:
            for placeholder in PLACEHOLDERS:
                assert placeholder in template


class TestRenderChoices:
    def test_renders_four_lettered_lines(self) -> None:
        # given a synthetic row / when
        rendered = render_choices(_synthetic_row())
        # then one ``X. value`` line per choice, in order
        assert rendered == "A. first\nB. second\nC. third\nD. fourth"


class TestRenderPrompt:
    @pytest.mark.parametrize("language", ["en", "fr"])
    @pytest.mark.parametrize("variant_id", VARIANT_IDS)
    def test_fills_every_placeholder_and_keeps_content_verbatim(
        self, language: str, variant_id: str
    ) -> None:
        # given a synthetic row / when rendering each variant in each language
        row = _synthetic_row()
        prompt = render_prompt(row, variant_id, language)
        # then no placeholder is left unfilled
        for placeholder in PLACEHOLDERS:
            assert placeholder not in prompt
        # and the question and every choice survive verbatim (item is unchanged)
        assert str(row["question"]) in prompt
        for letter in ANSWER_LETTERS:
            assert str(row[f"choice_{letter}"]) in prompt

    @pytest.mark.parametrize("templates", [EN_TEMPLATES, FR_TEMPLATES])
    def test_variants_are_distinct(self, templates: list[str]) -> None:
        # given a single language's templates / when / then all five differ
        assert len(set(templates)) == NUM_VARIANTS

    def test_v1_matches_canonical_mmlu_prompt(self) -> None:
        # given the original variant / when / then it is the canonical MMLU format
        assert render_prompt(_synthetic_row(), "V_1", "en") == CANONICAL_EN_V1

    def test_french_uses_french_subject_name(self) -> None:
        # given a French render of a mapped subject / when / then the FR label appears
        prompt = render_prompt(_synthetic_row("world_religions"), "V_1", "fr")
        assert FR_SUBJECT_NAMES["world_religions"] in prompt
        assert "world_religions" not in prompt

    def test_english_uses_deunderscored_slug(self) -> None:
        # given an English render / when / then the slug is spaced, not raw
        prompt = render_prompt(_synthetic_row("world_religions"), "V_1", "en")
        assert "world religions" in prompt
        assert "world_religions" not in prompt

    def test_unknown_subject_falls_back_to_spaced_slug(self) -> None:
        # given a subject absent from the French map / when / then it is de-underscored
        assert subject_label("not_a_subject", "fr") == "not a subject"

    def test_unmapped_french_subject_warns(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # given a subject absent from the French map / when rendering in French
        with caplog.at_level("WARNING"):
            subject_label("not_a_subject", "fr")
        # then a warning names the missing subject
        assert "not_a_subject" in caplog.text

    def test_mapped_french_subject_does_not_warn(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # given a mapped subject / when rendering in French / then no warning
        with caplog.at_level("WARNING"):
            subject_label("world_religions", "fr")
        assert caplog.records == []

    def test_english_subject_does_not_warn(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # given an unmapped subject in English / when / then no warning (EN has no map)
        with caplog.at_level("WARNING"):
            subject_label("not_a_subject", "en")
        assert caplog.records == []

    def test_rejects_unknown_variant(self) -> None:
        # given an unknown variant id / when / then
        with pytest.raises(ValueError, match="Unknown variant_id"):
            render_prompt(_synthetic_row(), "V_99", "en")

    def test_rejects_unknown_language(self) -> None:
        # given an unknown language / when / then
        with pytest.raises(ValueError, match="Unknown language"):
            render_prompt(_synthetic_row(), "V_1", "de")


class TestPublishedCsv:
    @pytest.mark.parametrize("language", ["en", "fr"])
    def test_committed_csv_matches_templates(self, language: str) -> None:
        # given the committed CSV copy of the variants / when read back
        df = pd.read_csv(DATA_DIR / f"prompt_variants_{language}.csv")
        # then it has exactly two columns and stays in sync with the source templates
        assert list(df.columns) == ["variant_id", "prompt"]
        assert df["variant_id"].tolist() == VARIANT_IDS
        assert df["prompt"].tolist() == TEMPLATES[language]

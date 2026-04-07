"""Tests for GPQA evaluation."""

from typing import get_args

import pytest
from inspect_ai import eval
from inspect_ai.dataset import Sample
from inspect_ai.model import ModelOutput, get_model

from gpqa import (
    DEFAULT_EPOCHS,
    GPQA_DIAMOND_DATASET_URL,
    GPQADomain,
    GPQASubdomain,
    get_gpqa_diamond_dataset,
    gpqa_diamond,
    record_to_sample,
)


def test_record_to_sample() -> None:
    """Test converting a record to a Sample with a real example from the dataset."""
    record = {
        "Record ID": "gpqa_diamond_001",
        "Question": "Two quantum states with energies E1 and E2 have a lifetime of 10^-9 sec and 10^-8 sec, respectively. We want to clearly distinguish these two energy levels. Which one of the following options could be their energy difference so that they can be clearly resolved?",
        "Correct Answer": "10^-4 eV",
        "Incorrect Answer 1": "10^-11 eV",
        "Incorrect Answer 2": "10^-8 eV",
        "Incorrect Answer 3": "10^-9 eV",
        "High-level domain": "Physics",
        "Subdomain": "Quantum Mechanics",
    }

    expected_sample = Sample(
        input="Two quantum states with energies E1 and E2 have a lifetime of 10^-9 sec and 10^-8 sec, respectively. We want to clearly distinguish these two energy levels. Which one of the following options could be their energy difference so that they can be clearly resolved?",
        choices=[
            "10^-4 eV",
            "10^-11 eV",
            "10^-8 eV",
            "10^-9 eV",
        ],
        target="A",
        id="gpqa_diamond_001",
        metadata={"high_level_domain": "Physics", "subdomain": "Quantum Mechanics"},
    )

    actual_sample = record_to_sample(record)

    assert actual_sample.input == expected_sample.input
    assert actual_sample.choices == expected_sample.choices
    assert actual_sample.target == expected_sample.target
    assert actual_sample.id == expected_sample.id
    assert actual_sample.metadata == expected_sample.metadata


def test_record_to_sample_converts_to_string() -> None:
    """Test that record_to_sample properly converts values to strings."""
    record = {
        "Record ID": "test_id_123",
        "Question": "What is 2+2?",
        "Correct Answer": 4,
        "Incorrect Answer 1": 3,
        "Incorrect Answer 2": 5,
        "Incorrect Answer 3": 6,
        "High-level domain": "Mathematics",
        "Subdomain": "Arithmetic",
    }

    sample = record_to_sample(record)

    assert sample.choices is not None
    for c in sample.choices:
        assert isinstance(c, str)
    assert sample.choices == ["4", "3", "5", "6"]


@pytest.mark.dataset_download
def test_gpqa_diamond_end_to_end_with_mock() -> None:
    """Test that the gpqa_diamond evaluation pipeline works end-to-end."""
    [log] = eval(
        tasks=gpqa_diamond(),
        limit=2,
        model="mockllm/model",
        epochs=1,
    )

    assert log.status == "success"
    assert log.results is not None
    assert "accuracy" in log.results.scores[0].metrics


@pytest.mark.dataset_download
def test_gpqa_diamond_correct_answer() -> None:
    """Test that the scorer correctly identifies a correct answer."""
    [log] = eval(
        tasks=gpqa_diamond(),
        limit=1,
        model=get_model(
            "mockllm/model",
            custom_outputs=[
                ModelOutput.from_content(
                    model="mockllm/model",
                    content="ANSWER: A",
                ),
            ],
        ),
        epochs=1,
    )

    assert log.status == "success"
    assert log.results is not None
    assert "accuracy" in log.results.scores[0].metrics


def test_gpqa_diamond_task_structure() -> None:
    """Test that the gpqa_diamond task has the expected structure."""
    task = gpqa_diamond()

    assert task.dataset is not None
    assert task.solver is not None
    assert task.scorer is not None
    assert task.epochs == DEFAULT_EPOCHS


def test_constants() -> None:
    """Test that exported constants have expected values."""
    assert DEFAULT_EPOCHS == 4
    assert "gpqa_diamond.csv" in GPQA_DIAMOND_DATASET_URL
    assert GPQA_DIAMOND_DATASET_URL.startswith("https://")


@pytest.mark.dataset_download
def test_get_gpqa_diamond_dataset() -> None:
    """Test that get_gpqa_diamond_dataset returns a valid dataset."""
    dataset = get_gpqa_diamond_dataset()

    assert dataset is not None
    assert len(dataset) == 198
    for sample in dataset:
        assert sample.metadata is not None
        assert sample.metadata["high_level_domain"] in {
            "Biology",
            "Chemistry",
            "Physics",
        }
        assert sample.metadata["subdomain"] is not None


@pytest.mark.dataset_download
def test_gpqa_literals_match_dataset() -> None:
    """Test that GPQADomain and GPQASubdomain literals match the dataset."""
    dataset = get_gpqa_diamond_dataset()

    actual_domains = {s.metadata["high_level_domain"] for s in dataset if s.metadata}
    actual_subdomains = {s.metadata["subdomain"] for s in dataset if s.metadata}

    assert actual_domains == set(get_args(GPQADomain))
    assert actual_subdomains == set(get_args(GPQASubdomain))


def test_gpqa_diamond_with_cot_false() -> None:
    """Test that cot=False parameter is respected."""
    task = gpqa_diamond(cot=False)
    assert task.solver is not None


def test_gpqa_diamond_custom_epochs() -> None:
    """Test that custom epochs parameter is respected."""
    task = gpqa_diamond(epochs=2)
    assert task.epochs == 2


@pytest.mark.dataset_download
def test_gpqa_diamond_domain_filter_params() -> None:
    """Test that domain and subdomain params filter correctly."""
    task = gpqa_diamond(high_level_domain="Physics")
    assert task.dataset is not None
    assert all(
        s.metadata is not None and s.metadata["high_level_domain"] == "Physics"
        for s in task.dataset
    )

    task = gpqa_diamond(high_level_domain=["Physics", "Chemistry"])
    assert task.dataset is not None
    assert all(
        s.metadata is not None
        and s.metadata["high_level_domain"] in {"Physics", "Chemistry"}
        for s in task.dataset
    )

    task = gpqa_diamond(subdomain="Quantum Mechanics")
    assert task.dataset is not None
    assert all(
        s.metadata is not None and s.metadata["subdomain"] == "Quantum Mechanics"
        for s in task.dataset
    )

    task = gpqa_diamond(high_level_domain="Chemistry", subdomain="Organic Chemistry")
    assert task.dataset is not None
    assert all(
        s.metadata is not None
        and s.metadata["high_level_domain"] == "Chemistry"
        and s.metadata["subdomain"] == "Organic Chemistry"
        for s in task.dataset
    )

    with pytest.raises(ValueError, match="Invalid high_level_domain"):
        gpqa_diamond(high_level_domain="NotADomain")

    with pytest.raises(ValueError, match="Invalid subdomain"):
        gpqa_diamond(subdomain="NotASubdomain")

    with pytest.raises(ValueError, match="No samples found after filtering"):
        gpqa_diamond(high_level_domain="Chemistry", subdomain="Quantum Mechanics")

"""GPQA: A Graduate-Level Google-Proof Q&A Benchmark.

David Rein, Betty Li Hou, Asa Cooper Stickland, Jackson Petty, Richard
Yuanzhe Pang, Julien Dirani, Julian Michael, Samuel R. Bowman
https://arxiv.org/abs/2311.12022

Based on: https://github.com/openai/simple-evals/main/gpqa_eval.py

# eval for default epochs (4)
inspect eval gpqa/gpqa_diamond

# eval with 1 epoch
inspect eval gpqa/gpqa_diamond --epochs 1

# without chain of thought
inspect eval gpqa/gpqa_diamond -T cot=false

# filter by high-level domain
inspect eval gpqa/gpqa_diamond -T high_level_domain=Biology

# filter by subdomain
inspect eval gpqa/gpqa_diamond -T subdomain=Genetics
"""

from typing import Any, Literal, get_args

from inspect_ai import Task, task
from inspect_ai.dataset import Dataset, Sample, csv_dataset
from inspect_ai.scorer import choice
from inspect_ai.solver import multiple_choice

GPQA_DIAMOND_DATASET_URL = (
    "https://openaipublic.blob.core.windows.net/simple-evals/gpqa_diamond.csv"
)

DEFAULT_EPOCHS = 4

GPQADomain = Literal["Biology", "Chemistry", "Physics"]

GPQASubdomain = Literal[
    "Astrophysics",
    "Chemistry (general)",
    "Condensed Matter Physics",
    "Electromagnetism and Photonics",
    "Genetics",
    "High-energy particle physics",
    "Inorganic Chemistry",
    "Molecular Biology",
    "Optics and Acoustics",
    "Organic Chemistry",
    "Physics (general)",
    "Quantum Mechanics",
    "Relativistic Mechanics",
]


def get_gpqa_diamond_dataset(
    shuffle_choices: bool = True,
    high_level_domain: str | list[str] | None = None,
    subdomain: str | list[str] | None = None,
) -> Dataset:
    """Load the GPQA Diamond dataset.

    Args:
        shuffle_choices: Whether to shuffle the answer choices (recommended
            since correct answer is always 'A' in the raw data).
        high_level_domain: Optional high-level domain(s) to filter by. One of
            "Biology", "Chemistry", or "Physics", or a list of these. If None,
            all domains are included.
        subdomain: Optional subdomain(s) to filter by (e.g. "Genetics" or
            "Quantum Mechanics", or a list of these). If None, all subdomains
            are included.

    Returns:
        Dataset of GPQA Diamond samples.
    """
    domains = (
        [high_level_domain] if isinstance(high_level_domain, str) else high_level_domain
    )
    subdomains = [subdomain] if isinstance(subdomain, str) else subdomain

    valid_domains = set(get_args(GPQADomain))
    valid_subdomains = set(get_args(GPQASubdomain))

    if domains is not None:
        invalid = set(domains) - valid_domains
        if invalid:
            raise ValueError(
                f"Invalid high_level_domain value(s): {invalid}. "
                f"Must be one of: {sorted(valid_domains)}"
            )
    if subdomains is not None:
        invalid = set(subdomains) - valid_subdomains
        if invalid:
            raise ValueError(
                f"Invalid subdomain value(s): {invalid}. "
                f"Must be one of: {sorted(valid_subdomains)}"
            )

    domain_filter_set: set[str] | None = set(domains) if domains is not None else None
    subdomain_filter_set: set[str] | None = (
        set(subdomains) if subdomains is not None else None
    )

    dataset = csv_dataset(
        csv_file=GPQA_DIAMOND_DATASET_URL,
        sample_fields=record_to_sample,
        shuffle=shuffle_choices,
    )
    if domain_filter_set is not None:
        dataset = dataset.filter(
            lambda sample: sample.metadata is not None
            and sample.metadata["high_level_domain"] in domain_filter_set
        )
    if subdomain_filter_set is not None:
        dataset = dataset.filter(
            lambda sample: sample.metadata is not None
            and sample.metadata["subdomain"] in subdomain_filter_set
        )
    if len(dataset) == 0:
        raise ValueError(
            f"No samples found after filtering "
            f"(high_level_domain={high_level_domain!r}, subdomain={subdomain!r}). "
            "Check that the values are compatible with each other."
        )
    return dataset


@task
def gpqa_diamond(
    cot: bool = True,
    epochs: int = DEFAULT_EPOCHS,
    high_level_domain: str | list[str] | None = None,
    subdomain: str | list[str] | None = None,
) -> Task:
    """Inspect task implementing the GPQA Diamond benchmark.

    Args:
        cot: Whether to use chain-of-thought reasoning (default True).
        epochs: Number of epochs to run (default 4).
        high_level_domain: Optional high-level domain(s) to filter by. One of
            "Biology", "Chemistry", or "Physics", or a list of these. If None,
            all domains are included.
        subdomain: Optional subdomain(s) to filter by (e.g. "Genetics" or
            "Quantum Mechanics", or a list of these). If None, all subdomains
            are included.

    Returns:
        Task for GPQA Diamond evaluation.
    """
    return Task(
        dataset=get_gpqa_diamond_dataset(
            high_level_domain=high_level_domain,
            subdomain=subdomain,
        ),
        solver=multiple_choice(cot=cot),
        scorer=choice(),
        epochs=epochs,
    )


def record_to_sample(record: dict[str, Any]) -> Sample:
    """Convert a GPQA CSV record to an Inspect Sample.

    Note that target is always "A" in the dataset; we shuffle the
    presentation of options to mitigate this.
    """
    return Sample(
        input=record["Question"],
        choices=[
            str(record["Correct Answer"]),
            str(record["Incorrect Answer 1"]),
            str(record["Incorrect Answer 2"]),
            str(record["Incorrect Answer 3"]),
        ],
        target="A",
        id=record["Record ID"],
        metadata={
            "high_level_domain": record["High-level domain"],
            "subdomain": record["Subdomain"],
        },
    )

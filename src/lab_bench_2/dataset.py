"""Dataset loading for the LAB-Bench 2 evaluation.

The questions live in a single (gated) HuggingFace dataset broken up by tags.
"""

from __future__ import annotations

from typing import Any

from inspect_ai.dataset import Dataset, Sample, hf_dataset

LAB_BENCH_2_DATASET_PATH = "EdisonScientific/labbench2"
LAB_BENCH_2_DATASET_REVISION = "27d12d72af24e3f70db8a99df63e567366cbdb80"
LAB_BENCH_2_DATASET_SPLIT = "train"


def record_to_sample(record: dict[str, Any]) -> Sample:
    """Map a raw LAB-Bench 2 record to an Inspect Sample.

    Used for file-less tags (e.g. litqa3): the question becomes the input and
    the dataset's `ideal` field becomes the target the judge grades against.
    """
    question = record["question"]
    prompt_suffix = record.get("prompt_suffix") or ""
    input_text = f"{question}\n\n{prompt_suffix}".strip() if prompt_suffix else question
    return Sample(
        input=input_text,
        target=record["ideal"],
        id=record["id"],
        metadata={
            "tag": record.get("tag"),
            "type": record.get("type") or None,
            "sources": record.get("sources") or [],
        },
    )


def load_lab_bench_2_dataset(tag: str, limit: int | None = None) -> Dataset:
    """Load a single LAB-Bench 2 tag, pinned to a fixed dataset revision.

    Args:
        tag: The dataset config to load (e.g. "litqa3").
        limit: Optional cap on the number of samples loaded.
    """
    return hf_dataset(
        path=LAB_BENCH_2_DATASET_PATH,
        name=tag,
        split=LAB_BENCH_2_DATASET_SPLIT,
        revision=LAB_BENCH_2_DATASET_REVISION,
        sample_fields=record_to_sample,
        limit=limit,
    )

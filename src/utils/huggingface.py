"""Helpers for HuggingFace dataset integration.

Two distinct concerns live here:

1. **Schema assertions** (``DatasetInfosDict``,
   ``get_dataset_infos_dict``, ``assert_huggingface_dataset_structure``) —
   lock down a dataset's ``splits`` and ``features`` so an upstream schema
   change (e.g. a renamed column) fails a quick local test rather than
   silently producing samples with empty fields at eval time.

2. **Retry-aware wrappers** (``hf_dataset``, ``load_dataset``,
   ``snapshot_download``, ``hf_hub_download``, and friends) — wrap the
   underlying inspect_ai / datasets / huggingface_hub APIs with exponential
   backoff and jitter so HuggingFace's intermittent rate limits (HTTP 429)
   and transient gateway errors (HTTP 502) are absorbed without surfacing.
   The wrappers also require a ``revision=`` keyword so HF resources are
   pinned for reproducibility. Adapted from
   https://github.com/UKGovernmentBEIS/inspect_evals/blob/main/src/inspect_evals/utils/huggingface.py
   (the upstream's telemetry hooks are stubbed out).

Typical schema-assertion usage in ``tests/<eval_name>/test_<eval_name>.py``:

    import pytest
    from utils.huggingface import (
        DatasetInfosDict,
        assert_huggingface_dataset_structure,
        get_dataset_infos_dict,
    )

    HF_DATASET_PATH = "org/dataset-name"

    @pytest.fixture(scope="module")
    def dataset_infos() -> DatasetInfosDict:
        return get_dataset_infos_dict(HF_DATASET_PATH)

    @pytest.mark.huggingface
    def test_dataset_structure(dataset_infos: DatasetInfosDict) -> None:
        assert_huggingface_dataset_structure(
            dataset_infos,
            {
                "configs": {
                    "default": {
                        "splits": ["test"],
                        "features": {
                            "question": "string",
                            "answer": "string",
                        },
                    }
                }
            },
        )

Typical wrapper usage in eval code:

    from utils.huggingface import hf_dataset

    dataset = hf_dataset(
        path="org/dataset-name",
        split="test",
        revision="abc1234...",   # required
        sample_fields=record_to_sample,
    )
"""

from __future__ import annotations

import os
from typing import Any, Callable, TypedDict, TypeVar

import backoff
import datasets
import huggingface_hub
import inspect_ai.dataset
from datasets.exceptions import DatasetGenerationError
from huggingface_hub.errors import HfHubHTTPError, LocalEntryNotFoundError
from requests.exceptions import ReadTimeout
from typing_extensions import ParamSpec

DatasetInfosDict = dict[str, Any]


# ---------------------------------------------------------------------------
# Schema assertions
# ---------------------------------------------------------------------------


def get_dataset_infos_dict(path: str, revision: str | None = None) -> DatasetInfosDict:
    """Load the metadata for a HuggingFace dataset without downloading samples.

    Returns a dict keyed by config name; each entry contains `splits` (list of
    split names) and `features` (mapping of column name to dtype string).
    """
    from datasets import get_dataset_config_names, load_dataset_builder

    config_names = get_dataset_config_names(path, revision=revision) or ["default"]
    infos: DatasetInfosDict = {"configs": {}}
    for config in config_names:
        builder = load_dataset_builder(
            path,
            name=None if config == "default" and len(config_names) == 1 else config,
            revision=revision,
            # trust_remote_code=False, # As of datasets==4.0.0, trust remote code is no longer supported
        )
        info = builder.info
        infos["configs"][config] = {
            "splits": sorted((info.splits or {}).keys()),
            "features": {
                name: str(feature) for name, feature in (info.features or {}).items()
            },
        }
    return infos


def assert_huggingface_dataset_structure(
    actual: DatasetInfosDict, expected: DatasetInfosDict
) -> None:
    """Assert that `actual` contains the splits and features described in `expected`.

    `actual` is a dict produced by `get_dataset_infos_dict`. `expected` may
    be a partial spec: extra splits/features in `actual` are allowed, but
    every split/feature listed in `expected` must be present and the feature
    dtypes must match.
    """
    actual_configs = actual.get("configs", {})
    expected_configs = expected.get("configs", {})
    for config_name, expected_config in expected_configs.items():
        assert config_name in actual_configs, (
            f"Expected config {config_name!r} not found; available: "
            f"{sorted(actual_configs)}"
        )
        actual_config = actual_configs[config_name]
        for expected_split in expected_config.get("splits", []):
            assert expected_split in actual_config["splits"], (
                f"Config {config_name!r} missing split {expected_split!r}; "
                f"available: {actual_config['splits']}"
            )
        for feature, expected_dtype in expected_config.get("features", {}).items():
            assert feature in actual_config["features"], (
                f"Config {config_name!r} missing feature {feature!r}; "
                f"available: {sorted(actual_config['features'])}"
            )
            actual_dtype = actual_config["features"][feature]
            assert expected_dtype in actual_dtype, (
                f"Config {config_name!r} feature {feature!r} expected dtype "
                f"matching {expected_dtype!r}, got {actual_dtype!r}"
            )


# ---------------------------------------------------------------------------
# Retry-aware HF / inspect_ai dataset wrappers
# ---------------------------------------------------------------------------


def _record_backoff(details: object) -> None:
    """Telemetry hook stub.

    Upstream records HF call patterns to its own telemetry; the template
    no-ops since contributors aren't running registry-scale batch jobs.
    """


def _record_hf_call(_name: str) -> None:
    """Telemetry hook stub. See ``_record_backoff``."""


Jitterer = Callable[[float], float]


class BackoffConfig(TypedDict):
    max_tries: int
    initial_wait_mins: int
    max_wait_mins: int
    jitter: Jitterer | None


P = ParamSpec("P")
R = TypeVar("R")


# CI runs a denser cluster of HF requests than an individual contributor;
# allow more retry attempts there.
HF_RATE_LIMIT_WINDOW_MINS = 5
STANDARD_BACKOFF_CONFIG: BackoffConfig = {
    "max_tries": 3,
    "initial_wait_mins": 1,
    "max_wait_mins": HF_RATE_LIMIT_WINDOW_MINS,
    "jitter": backoff.full_jitter,
}
CI_BACKOFF_CONFIG: BackoffConfig = {
    "max_tries": 5,
    "initial_wait_mins": 1,
    "max_wait_mins": HF_RATE_LIMIT_WINDOW_MINS,
    "jitter": backoff.full_jitter,
}

BACKOFF_CONFIG = CI_BACKOFF_CONFIG if os.getenv("CI") else STANDARD_BACKOFF_CONFIG

TRANSIENT_ERROR_CODES = {
    429: "Too many requests... likely the HF rate limit policy has been violated",
    502: "Bad gateway... likely a transient server-side / network issue",
}


def hf_backoff_policy(
    max_tries: int,
    initial_wait_mins: int,
    max_wait_mins: int,
    jitter: Jitterer | None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator: retry HF-bound calls with exponential backoff + jitter.

    See HF rate limits: https://huggingface.co/docs/hub/rate-limits#rate-limit-tiers
    See ``Adding Jitter``: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
    """
    return backoff.on_exception(
        backoff.expo,
        (
            HfHubHTTPError,
            LocalEntryNotFoundError,
            FileNotFoundError,
            ValueError,
            DatasetGenerationError,
            OSError,
        ),
        max_tries=max_tries,
        factor=60 * initial_wait_mins,
        max_value=60 * max_wait_mins,
        jitter=jitter,
        on_backoff=_record_backoff,
        giveup=lambda e: not should_retry(e),
    )


def should_retry(err: Exception) -> bool:
    """Return True if the exception is a transient HF failure worth retrying.

    ``HfHubHTTPError`` is retried for 429 (rate limit) and 502 (bad gateway).
    ``LocalEntryNotFoundError`` is retried because once HF rate-limits, the
    library tries the local cache and raises this if there is no local copy.
    ``FileNotFoundError`` is retried only when its message indicates the
    same network-cache-miss path (see datasets/load.py).
    ``ValueError`` is retried only when its message indicates a missing
    cache.
    ``ReadTimeout`` is retried when the URL points at huggingface.co.
    """
    if isinstance(err, LocalEntryNotFoundError):
        return True

    if isinstance(err, HfHubHTTPError):
        response = err.response
        return response is not None and response.status_code in TRANSIENT_ERROR_CODES

    if isinstance(err, DatasetGenerationError):
        return True

    if isinstance(err, FileNotFoundError):
        inferred_network_errors = [
            "An error happened while trying to locate the file on the Hub "
            "and we cannot find the requested files in the local cache. "
            "Please check your connection and try again or make sure your "
            "Internet connection is on.",
            "on the Hugging Face Hub either",
        ]
        return any(
            inferred_network_error in str(err)
            for inferred_network_error in inferred_network_errors
        )

    if isinstance(err, ValueError):
        return "Couldn't find cache for" in str(err)

    if isinstance(err, ReadTimeout):
        return "huggingface.co" in str(err)

    return False


def _ensure_revision(func_name: str, kwargs: dict[str, Any]) -> None:
    if not kwargs.get("revision"):
        raise TypeError(
            f"{func_name}() requires a 'revision' keyword argument "
            "to ensure reproducibility. Pass a specific commit hash or tag."
        )


@hf_backoff_policy(**BACKOFF_CONFIG)
def hf_dataset(*args: Any, **kwargs: Any) -> inspect_ai.dataset.Dataset:
    """Call ``inspect_ai.dataset.hf_dataset`` with exponential backoff and retry."""
    _record_hf_call("hf_dataset")
    _ensure_revision("hf_dataset", kwargs)
    return inspect_ai.dataset.hf_dataset(*args, **kwargs)


@hf_backoff_policy(**BACKOFF_CONFIG)
def load_dataset(*args: Any, **kwargs: Any) -> datasets.Dataset:
    """Call ``datasets.load_dataset`` with exponential backoff and retry."""
    _record_hf_call("load_dataset")
    _ensure_revision("load_dataset", kwargs)
    return datasets.load_dataset(*args, **kwargs)


@hf_backoff_policy(**BACKOFF_CONFIG)
def snapshot_download(*args: Any, **kwargs: Any) -> Any:
    """Call ``huggingface_hub.snapshot_download`` with exponential backoff and retry."""
    _record_hf_call("snapshot_download")
    _ensure_revision("snapshot_download", kwargs)
    return huggingface_hub.snapshot_download(*args, **kwargs)


@hf_backoff_policy(**BACKOFF_CONFIG)
def hf_hub_download(*args: Any, **kwargs: Any) -> Any:
    """Call ``huggingface_hub.hf_hub_download`` with exponential backoff and retry."""
    _record_hf_call("hf_hub_download")
    _ensure_revision("hf_hub_download", kwargs)
    return huggingface_hub.hf_hub_download(*args, **kwargs)


@hf_backoff_policy(**BACKOFF_CONFIG)
def sentence_transformer(*args: Any, **kwargs: Any) -> Any:
    """Call ``sentence_transformers.SentenceTransformer`` with exponential backoff and retry."""
    from sentence_transformers import SentenceTransformer

    _record_hf_call("sentence_transformer")
    _ensure_revision("sentence_transformer", kwargs)
    return SentenceTransformer(*args, **kwargs)


@hf_backoff_policy(**BACKOFF_CONFIG)
def transformers_pipeline(*args: Any, **kwargs: Any) -> Any:
    """Call ``transformers.pipeline`` with exponential backoff and retry."""
    import transformers

    _record_hf_call("transformers_pipeline")
    _ensure_revision("transformers_pipeline", kwargs)
    return transformers.pipeline(*args, **kwargs)


@hf_backoff_policy(**BACKOFF_CONFIG)
def auto_model_for_sequence_classification(*args: Any, **kwargs: Any) -> Any:
    """Call ``transformers.AutoModelForSequenceClassification.from_pretrained`` with backoff."""
    from transformers import AutoModelForSequenceClassification

    _record_hf_call("auto_model_for_sequence_classification")
    _ensure_revision("auto_model_for_sequence_classification", kwargs)
    return AutoModelForSequenceClassification.from_pretrained(*args, **kwargs)


@hf_backoff_policy(**BACKOFF_CONFIG)
def auto_tokenizer(*args: Any, **kwargs: Any) -> Any:
    """Call ``transformers.AutoTokenizer.from_pretrained`` with backoff."""
    from transformers import AutoTokenizer

    _record_hf_call("auto_tokenizer")
    _ensure_revision("auto_tokenizer", kwargs)
    return AutoTokenizer.from_pretrained(*args, **kwargs)

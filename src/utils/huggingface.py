"""Helpers for asserting the schema of HuggingFace datasets used by evals.

The goal is to lock down the dataset's `splits` and `features` so that an
upstream schema change (e.g. a renamed column) fails a quick local test
rather than silently producing samples with empty fields at eval time.

Typical usage in `tests/<eval_name>/test_<eval_name>.py`:

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
"""

from __future__ import annotations

from typing import Any

DatasetInfosDict = dict[str, Any]


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

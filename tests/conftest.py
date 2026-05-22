"""Shared test configuration and fixtures."""

import logging
import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="Run slow tests",
    )


def pytest_configure(config: pytest.Config) -> None:
    logging.basicConfig(level=logging.INFO)


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    _skip_slow_and_dataset_download_tests(config, items)
    _hf_apply_collection_markers(items)


def _skip_slow_and_dataset_download_tests(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    run_slow = config.getoption("--runslow") or os.environ.get(
        "RUN_SLOW_TESTS", ""
    ).lower() in ("1", "true", "yes", "on")

    run_dataset_download = os.environ.get(
        "RUN_DATASET_DOWNLOAD_TESTS", "1"
    ).lower() not in ("0", "false", "no", "off")

    skip_slow = pytest.mark.skip(reason="Need --runslow or RUN_SLOW_TESTS=1 to run")
    skip_dataset = pytest.mark.skip(reason="RUN_DATASET_DOWNLOAD_TESTS=0")

    for item in items:
        if "slow" in item.keywords and not run_slow:
            item.add_marker(skip_slow)
        if "dataset_download" in item.keywords and not run_dataset_download:
            item.add_marker(skip_dataset)


def _hf_apply_collection_markers(items: list[pytest.Item]) -> None:
    hf_items = [item for item in items if "huggingface" in item.keywords]

    if not hf_items:
        return

    if not os.environ.get("HF_TOKEN"):
        for item in hf_items:
            item.add_marker(pytest.mark.skip(reason=f"HF_TOKEN not set ({item.name})"))

    else:
        for item in hf_items:
            item.add_marker(pytest.mark.flaky(reruns=2, reruns_delay=60.0))

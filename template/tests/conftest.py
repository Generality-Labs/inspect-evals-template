"""Shared test configuration and fixtures.

Test gates (--runslow, RUN_SLOW_TESTS and so on), markers and shared fixtures
come from the pytest-inspect-evals plugin, which loads automatically.
"""

import logging

import pytest


def pytest_configure(config: pytest.Config) -> None:
    logging.basicConfig(level=logging.INFO)

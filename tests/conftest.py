"""Shared pytest policy for credential-free and opt-in external tests."""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register an explicit switch for paid provider evaluation."""
    parser.addoption(
        "--run-external",
        action="store_true",
        default=False,
        help="run opt-in tests that call the configured external provider",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Keep provider calls opt-in and sync Playwright tests after async tests."""
    browser_items = [item for item in items if "page" in item.fixturenames]
    items[:] = [item for item in items if item not in browser_items] + browser_items

    if not config.getoption("--run-external"):
        skip_external = pytest.mark.skip(reason="use --run-external to enable")
        for item in items:
            if "external" in item.keywords:
                item.add_marker(skip_external)

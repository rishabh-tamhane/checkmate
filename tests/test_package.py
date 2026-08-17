"""Tests for the installable Checkmate package."""

from checkmate import __version__


def test_package_has_expected_version() -> None:
    """The initial package exposes its release version."""
    assert __version__ == "0.1.0"

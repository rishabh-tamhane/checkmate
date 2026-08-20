"""Tests for the installable Checkmate package."""

from importlib.metadata import version

from checkmate import __version__


def test_package_version_comes_from_installed_metadata() -> None:
    """The package exposes the version declared by installed metadata."""
    assert __version__ == version("checkmate")

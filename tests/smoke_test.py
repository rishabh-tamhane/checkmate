"""Verify that an installed Checkmate distribution can be imported."""

from checkmate import __version__

assert __version__ == "0.1.0"

"""Tests for the approved package boundaries."""

import ast
import importlib
from pathlib import Path

from checkmate.application.ports import PdfRenderer, ReceiptParser

PACKAGE_ROOT = Path(__file__).parents[1] / "src" / "checkmate"
DOMAIN_ROOT = PACKAGE_ROOT / "domain"
FORBIDDEN_DOMAIN_IMPORTS = {"fastapi", "pydantic", "openai", "reportlab"}
SKELETON_MODULES = (
    "checkmate.domain.models",
    "checkmate.domain.money",
    "checkmate.domain.splitting",
    "checkmate.domain.validation",
    "checkmate.application.models",
    "checkmate.application.services",
    "checkmate.adapters.receipt_parser",
    "checkmate.adapters.pdf_renderer",
)


def test_domain_uses_only_the_standard_library() -> None:
    """Domain modules stay independent from web and vendor packages."""
    imported_roots: set[str] = set()
    for source_path in DOMAIN_ROOT.glob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(
                    alias.name.partition(".")[0] for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.partition(".")[0])

    assert imported_roots.isdisjoint(FORBIDDEN_DOMAIN_IMPORTS)


def test_approved_module_skeleton_is_importable() -> None:
    """Each planned layer exists without importing a vendor SDK."""
    for module_name in SKELETON_MODULES:
        importlib.import_module(module_name)


def test_external_boundaries_are_application_owned_protocols() -> None:
    """Parser and renderer boundaries exist before concrete adapters."""
    assert ReceiptParser.__module__ == "checkmate.application.ports"
    assert PdfRenderer.__module__ == "checkmate.application.ports"

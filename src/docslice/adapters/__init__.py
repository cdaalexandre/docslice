"""Adapters - re-exports."""

from docslice.adapters.epub_reader import extract_epub  # noqa: F401
from docslice.adapters.pdf_reader import extract_pdf  # noqa: F401

__all__ = ["extract_pdf", "extract_epub"]

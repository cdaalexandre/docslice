"""Adapters - re-exports."""

from __future__ import annotations

from docslice.adapters.docx_writer import write_txt_as_docx  # noqa: F401
from docslice.adapters.epub_reader import extract_epub  # noqa: F401
from docslice.adapters.pdf_reader import extract_pdf  # noqa: F401

__all__ = [
    "extract_epub",
    "extract_pdf",
    "write_txt_as_docx",
]

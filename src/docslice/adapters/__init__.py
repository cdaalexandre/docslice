"""Adapters - re-exports."""

from __future__ import annotations

from docslice.adapters.epub_reader import extract_epub  # noqa: F401
from docslice.adapters.gdocs_auth import (  # noqa: F401
    build_drive_service,
    load_credentials,
)
from docslice.adapters.gdocs_writer import GoogleDocsUploader  # noqa: F401
from docslice.adapters.pdf_reader import extract_pdf  # noqa: F401

__all__ = [
    "GoogleDocsUploader",
    "build_drive_service",
    "extract_epub",
    "extract_pdf",
    "load_credentials",
]

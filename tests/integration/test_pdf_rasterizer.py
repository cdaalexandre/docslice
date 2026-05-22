"""Tests - pdf_rasterizer adapter, integration with a real fitz PDF.

Percival & Gregory, Architecture Patterns, Cap. 5:
'Integration tests exercise the adapter against the real
dependency, isolated with tmp_path.'
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import fitz
import pytest

from docslice.adapters.pdf_rasterizer import rasterize_pdf

if TYPE_CHECKING:
    from pathlib import Path


def _make_pdf(path: Path, pages: int) -> None:
    """Build a minimal multi-page PDF at path for testing."""
    doc = fitz.open()
    for n in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {n + 1}")
    doc.save(str(path))
    doc.close()


class TestRasterizePdf:
    """Integration tests for the pdf_rasterizer adapter."""

    def test_one_png_per_page(self, tmp_path: Path) -> None:
        pdf = tmp_path / "sample.pdf"
        _make_pdf(pdf, pages=3)

        images = rasterize_pdf(pdf, tmp_path / "images", dpi=72)

        assert [p.name for p in images] == [
            "sample_page00001.png",
            "sample_page00002.png",
            "sample_page00003.png",
        ]

    def test_files_exist_and_nonempty(self, tmp_path: Path) -> None:
        pdf = tmp_path / "sample.pdf"
        _make_pdf(pdf, pages=2)

        images = rasterize_pdf(pdf, tmp_path / "images", dpi=72)

        for image in images:
            assert image.exists()
            assert image.stat().st_size > 0

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            rasterize_pdf(tmp_path / "nope.pdf", tmp_path / "out")

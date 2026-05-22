"""Tests - rasterize_document service layer with a Fake.

Percival & Gregory, Architecture Patterns, Cap. 3.c.ii:
'Why Not Just Patch It Out? - every call to mock.patch
is a ticking time bomb.'
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from docslice.service_layer.rasterizer import rasterize_document

if TYPE_CHECKING:
    from pathlib import Path


class FakePageRasterizer:
    """Test double that records calls and returns canned image paths."""

    def __init__(self, pages: int = 3) -> None:
        self.pages = pages
        self.calls: list[tuple[Path, Path, int]] = []

    def __call__(self, path: Path, output_dir: Path, dpi: int) -> list[Path]:
        self.calls.append((path, output_dir, dpi))
        return [output_dir / f"page{n + 1:05d}.png" for n in range(self.pages)]


class TestRasterizeDocument:
    """Tests for the rasterize_document use case."""

    def test_returns_one_path_per_page(self, tmp_path: Path) -> None:
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"fake pdf")
        rasterizer = FakePageRasterizer(pages=4)

        images = rasterize_document(pdf, tmp_path / "out", rasterizer=rasterizer)

        assert len(images) == 4

    def test_images_go_in_page_images_subdir(self, tmp_path: Path) -> None:
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"fake pdf")
        rasterizer = FakePageRasterizer()

        rasterize_document(pdf, tmp_path / "out", rasterizer=rasterizer)

        called_output_dir = rasterizer.calls[0][1]
        assert called_output_dir == tmp_path / "out" / "page_images"

    def test_dpi_is_forwarded(self, tmp_path: Path) -> None:
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"fake pdf")
        rasterizer = FakePageRasterizer()

        rasterize_document(pdf, tmp_path / "out", 150, rasterizer=rasterizer)

        assert rasterizer.calls[0][2] == 150

    def test_non_pdf_raises_value_error(self, tmp_path: Path) -> None:
        epub = tmp_path / "book.epub"
        epub.write_bytes(b"fake epub")

        with pytest.raises(ValueError, match="requires a PDF"):
            rasterize_document(epub, tmp_path / "out")

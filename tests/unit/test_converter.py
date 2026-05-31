"""Tests - converter service layer with Fakes.

Percival & Gregory, Architecture Patterns, Cap. 3.c.ii:
'Why Not Just Patch It Out? - every call to mock.patch
is a ticking time bomb.'

Percival & Gregory, Cap. 13:
'Declaring an explicit dependency is an example of the dependency
inversion principle.'
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from docslice.service_layer.converter import ConvertResult, convert

if TYPE_CHECKING:
    from pathlib import Path


class FakeExtractor:
    """Test double that returns canned text instead of reading files.

    Percival & Gregory, Cap. 3: 'Bob loves using lists to build
    simple test doubles.'
    """

    def __init__(self, text: str = "Fake paragraph one.\n\nFake paragraph two.") -> None:
        self.text = text
        self.calls: list[Path] = []

    def __call__(self, path: Path) -> str:
        self.calls.append(path)
        return self.text


class FakeDocxWriter:
    """Test double that touches an empty file at docx_path."""

    def __init__(self) -> None:
        self.calls: list[tuple[Path, Path]] = []

    def __call__(self, txt_path: Path, docx_path: Path) -> Path:
        self.calls.append((txt_path, docx_path))
        docx_path.parent.mkdir(parents=True, exist_ok=True)
        docx_path.write_bytes(b"FAKE_DOCX_BYTES")
        return docx_path


class FakeMarkdownWriter:
    """Test double that records calls and writes canned md bytes."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Path]] = []

    def __call__(self, text: str, md_path: Path) -> Path:
        self.calls.append((text, md_path))
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_bytes(b"FAKE_MD_BYTES")
        return md_path


class FakePageRasterizer:
    """Test double that records calls and returns canned image paths."""

    def __init__(self, pages: int = 3) -> None:
        self.pages = pages
        self.calls: list[tuple[Path, Path, int]] = []

    def __call__(self, path: Path, output_dir: Path, dpi: int) -> list[Path]:
        self.calls.append((path, output_dir, dpi))
        return [output_dir / f"page{n + 1:05d}.png" for n in range(self.pages)]


class TestConvert:
    """Tests for the convert orchestration."""

    def test_produces_txt_file(self, tmp_path: Path) -> None:
        input_file = tmp_path / "test.pdf"
        input_file.write_bytes(b"fake pdf content")
        output_dir = tmp_path / "output"
        extractor = FakeExtractor()
        docx_writer = FakeDocxWriter()

        result = convert(
            input_file,
            output_dir,
            extractor=extractor,
            docx_writer=docx_writer,
        )

        assert isinstance(result, ConvertResult)
        assert result.txt_path.exists()
        content = result.txt_path.read_text(encoding="utf-8")
        assert "Fake paragraph one." in content
        assert "Fake paragraph two." in content

    def test_extractor_receives_correct_path(self, tmp_path: Path) -> None:
        input_file = tmp_path / "book.epub"
        input_file.write_bytes(b"fake epub content")
        output_dir = tmp_path / "output"
        extractor = FakeExtractor()
        docx_writer = FakeDocxWriter()

        convert(
            input_file,
            output_dir,
            extractor=extractor,
            docx_writer=docx_writer,
        )

        assert len(extractor.calls) == 1
        assert extractor.calls[0] == input_file

    def test_produces_consolidated_docx(self, tmp_path: Path) -> None:
        input_file = tmp_path / "test.pdf"
        input_file.write_bytes(b"fake pdf content")
        output_dir = tmp_path / "output"
        extractor = FakeExtractor()
        docx_writer = FakeDocxWriter()

        result = convert(
            input_file,
            output_dir,
            extractor=extractor,
            docx_writer=docx_writer,
        )

        assert result.docx_path.exists()
        assert result.docx_path.suffix == ".docx"
        # First call is always the consolidated docx.
        assert docx_writer.calls[0] == (result.txt_path, result.docx_path)

    def test_small_file_no_split(self, tmp_path: Path) -> None:
        input_file = tmp_path / "small.pdf"
        input_file.write_bytes(b"tiny")
        output_dir = tmp_path / "output"
        extractor = FakeExtractor(text="Short text.")
        docx_writer = FakeDocxWriter()

        result = convert(
            input_file,
            output_dir,
            max_txt_bytes=1_000_000,
            max_orig_bytes=1_000_000,
            extractor=extractor,
            docx_writer=docx_writer,
        )

        assert result.txt_parts == []
        assert result.docx_parts == []
        assert result.original_parts == []
        # Only the consolidated docx was written.
        assert len(docx_writer.calls) == 1

    def test_large_text_splits_with_matching_docx_parts(self, tmp_path: Path) -> None:
        input_file = tmp_path / "big.pdf"
        input_file.write_bytes(b"x" * 100)
        output_dir = tmp_path / "output"
        large_text = ("Content here. " * 50 + "\n\n") * 20
        extractor = FakeExtractor(text=large_text)
        docx_writer = FakeDocxWriter()

        result = convert(
            input_file,
            output_dir,
            max_txt_bytes=500,
            max_orig_bytes=500,
            extractor=extractor,
            docx_writer=docx_writer,
        )

        assert len(result.txt_parts) >= 2
        assert len(result.docx_parts) == len(result.txt_parts)
        # Calls = 1 consolidated + 1 per chunk.
        assert len(docx_writer.calls) == 1 + len(result.txt_parts)

    def test_unsupported_format_raises(self, tmp_path: Path) -> None:
        input_file = tmp_path / "file.docx"
        input_file.write_bytes(b"fake")
        output_dir = tmp_path / "output"

        with pytest.raises(ValueError, match="Unsupported format"):
            convert(input_file, output_dir)

    def test_strips_control_chars_in_pipeline(self, tmp_path: Path) -> None:
        # Wiring proof: if a corrupt extractor leaks C0 control bytes
        # (the exact failure mode of the JPX-broken PDF that motivated
        # commit 33b6a1d), the convert() pipeline must scrub them
        # before writing to disk. NUL/BEL/SO/US specifically are not
        # whitespace for the normalize_text regex - only
        # strip_control_chars handles them - so removing the call
        # from the pipeline would fail this test.
        input_file = tmp_path / "corrupt.pdf"
        input_file.write_bytes(b"fake pdf content")
        output_dir = tmp_path / "output"
        contaminated = "Chapter\x00 one\x07 has\x0e stray\x1f bytes."
        extractor = FakeExtractor(text=contaminated)
        docx_writer = FakeDocxWriter()

        result = convert(
            input_file,
            output_dir,
            extractor=extractor,
            docx_writer=docx_writer,
        )

        content = result.txt_path.read_text(encoding="utf-8")
        # No XML-illegal C0 control chars survive (TAB/LF/CR are fine).
        for ch in content:
            assert ch in "\t\n\r" or ord(ch) >= 0x20
        # Readable text is preserved end-to-end.
        assert "Chapter one has stray bytes." in content

    def test_rasterize_flag_populates_page_images(self, tmp_path: Path) -> None:
        input_file = tmp_path / "test.pdf"
        input_file.write_bytes(b"fake pdf content")
        output_dir = tmp_path / "output"
        rasterizer = FakePageRasterizer(pages=5)

        result = convert(
            input_file,
            output_dir,
            extractor=FakeExtractor(),
            docx_writer=FakeDocxWriter(),
            rasterize=True,
            rasterizer=rasterizer,
        )

        assert len(result.page_images) == 5
        assert len(rasterizer.calls) == 1

    def test_rasterize_skipped_for_non_pdf(self, tmp_path: Path) -> None:
        input_file = tmp_path / "book.epub"
        input_file.write_bytes(b"fake epub content")
        output_dir = tmp_path / "output"
        rasterizer = FakePageRasterizer()

        result = convert(
            input_file,
            output_dir,
            extractor=FakeExtractor(),
            docx_writer=FakeDocxWriter(),
            rasterize=True,
            rasterizer=rasterizer,
        )

        assert result.page_images == []
        assert rasterizer.calls == []

    def test_produces_full_markdown(self, tmp_path: Path) -> None:
        # Wiring proof: the convert() pipeline must emit <stem>.md from
        # the raw (structure-preserving) text, alongside txt and docx.
        input_file = tmp_path / "test.pdf"
        input_file.write_bytes(b"fake pdf content")
        output_dir = tmp_path / "output"
        md_writer = FakeMarkdownWriter()

        result = convert(
            input_file,
            output_dir,
            extractor=FakeExtractor(),
            docx_writer=FakeDocxWriter(),
            md_writer=md_writer,
        )

        assert result.md_path.exists()
        assert result.md_path.suffix == ".md"
        assert result.md_path.name == "test.md"
        assert len(md_writer.calls) == 1

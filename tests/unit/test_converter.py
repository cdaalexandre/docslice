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

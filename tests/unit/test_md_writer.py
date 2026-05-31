"""Tests - write_markdown adapter with real files.

write_markdown has no external dependency beyond the filesystem, so
we test the real function against tmp_path (Percival & Gregory,
Cap. 3.c.ii: prefer real over mock when there is no boundary).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from docslice.adapters.md_writer import write_markdown

if TYPE_CHECKING:
    from pathlib import Path


class TestWriteMarkdown:
    """Tests for the Markdown writer adapter."""

    def test_creates_md_file(self, tmp_path: Path) -> None:
        md = tmp_path / "out.md"
        result = write_markdown("# Title\n\nBody.", md)
        assert result == md
        assert md.exists()
        assert md.stat().st_size > 0

    def test_writes_lf_not_crlf(self, tmp_path: Path) -> None:
        md = tmp_path / "out.md"
        write_markdown("line one\nline two\n", md)
        raw = md.read_bytes()
        assert b"\r\n" not in raw

    def test_preserves_markdown_structure(self, tmp_path: Path) -> None:
        md = tmp_path / "out.md"
        text = "# Heading\n\n- item one\n- item two\n\n|a|b|\n|---|---|\n"
        write_markdown(text, md)
        out = md.read_text(encoding="utf-8")
        assert "# Heading" in out
        assert "- item one" in out
        assert "|---|---|" in out

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        md = tmp_path / "nested" / "dir" / "out.md"
        write_markdown("content", md)
        assert md.exists()

    def test_preserves_unicode(self, tmp_path: Path) -> None:
        md = tmp_path / "out.md"
        write_markdown("Acao em Sao Paulo. Cafe.", md)
        out = md.read_text(encoding="utf-8")
        assert "Acao em Sao Paulo. Cafe." in out

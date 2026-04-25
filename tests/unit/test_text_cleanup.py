"""Tests - text cleanup (domain layer, pure logic).

Piramide de testes: Percival & Gregory, Cap. 5.
'Lots of unit tests, few integration tests.'
"""

from __future__ import annotations

from docslice.domain.text_cleanup import (
    flatten_pseudo_tables,
    normalize_text,
    remove_page_markers,
    remove_picture_markers,
)


class TestNormalizeText:
    """Tests for normalize_text."""

    def test_empty_string(self) -> None:
        assert normalize_text("") == ""

    def test_single_paragraph(self) -> None:
        result = normalize_text("  Hello   world  ")
        assert result == "Hello world"

    def test_preserves_paragraph_break(self) -> None:
        raw = "First paragraph.\n\nSecond paragraph."
        result = normalize_text(raw)
        assert "\n\n" in result
        assert "First paragraph." in result
        assert "Second paragraph." in result

    def test_collapses_excessive_blank_lines(self) -> None:
        raw = "Line one.\n\n\n\n\nLine two."
        result = normalize_text(raw)
        assert result == "Line one.\n\nLine two."

    def test_normalizes_crlf(self) -> None:
        raw = "Line one.\r\nLine two.\r\nLine three."
        result = normalize_text(raw)
        assert "\r" not in result
        assert "Line one." in result

    def test_removes_form_feed(self) -> None:
        raw = "Before\fAfter"
        result = normalize_text(raw)
        assert "\f" not in result

    def test_strips_trailing_whitespace(self) -> None:
        raw = "Hello   \nWorld   "
        result = normalize_text(raw)
        lines = result.split("\n")
        for line in lines:
            assert line == line.rstrip()

    def test_collapses_internal_spaces(self) -> None:
        raw = "Hello    world     test"
        result = normalize_text(raw)
        assert result == "Hello world test"

    def test_tabs_become_spaces(self) -> None:
        raw = "Hello\tworld"
        result = normalize_text(raw)
        assert "\t" not in result
        assert result == "Hello world"

    def test_real_world_pdf_noise(self) -> None:
        raw = (
            "Chapter 1\n\n"
            "   This is a paragraph with   extra   spaces.  \n"
            "\n\n\n"
            "   Next paragraph here.  \n"
            "\f"
            "   Page footer noise   \n"
        )
        result = normalize_text(raw)
        assert "\f" not in result
        paragraphs = result.split("\n\n")
        assert len(paragraphs) >= 2


class TestRemovePageMarkers:
    """Tests for remove_page_markers."""

    def test_removes_standalone_number(self) -> None:
        text = "Some text\n  42  \nMore text"
        result = remove_page_markers(text)
        assert "42" not in result
        assert "Some text" in result

    def test_removes_dashed_number(self) -> None:
        text = "Text\n- 42 -\nMore"
        result = remove_page_markers(text)
        assert "42" not in result

    def test_removes_page_prefix(self) -> None:
        text = "Text\nPage 42\nMore"
        result = remove_page_markers(text)
        assert "Page 42" not in result

    def test_preserves_numbers_in_sentences(self) -> None:
        text = "There are 42 items in this list."
        result = remove_page_markers(text)
        assert "42" in result

    def test_preserves_normal_content(self) -> None:
        text = "Normal text without page numbers."
        result = remove_page_markers(text)
        assert result == text


class TestRemovePictureMarkers:
    """Tests for remove_picture_markers."""

    def test_empty_string(self) -> None:
        assert remove_picture_markers("") == ""

    def test_preserves_text_with_no_markers(self) -> None:
        text = "Plain markdown text with no picture markers at all."
        result = remove_picture_markers(text)
        assert result == text

    def test_removes_basic_omitted_marker(self) -> None:
        text = "Before\n**==> picture [223 x 3] intentionally omitted <==**\nAfter"
        result = remove_picture_markers(text)
        assert "==> picture" not in result
        assert "Before" in result
        assert "After" in result

    def test_removes_marker_inside_table_with_br(self) -> None:
        # Markers can appear embedded inside markdown tables that
        # use <br> separators - regex matches inline (not anchored).
        text = "|cell content<br>**==> picture [6 x 10] intentionally omitted <==**<br>more|"
        result = remove_picture_markers(text)
        assert "==> picture" not in result
        assert "cell content" in result
        assert "more" in result

    def test_handles_multiple_dimensions(self) -> None:
        # Various WxH values from real Bates output.
        text = (
            "**==> picture [424 x 514] intentionally omitted <==**\n"
            "**==> picture [6 x 10] intentionally omitted <==**\n"
            "**==> picture [1 x 1] intentionally omitted <==**\n"
        )
        result = remove_picture_markers(text)
        assert "==> picture" not in result

    def test_removes_start_end_wrappers_keeps_inner_text(self) -> None:
        text = (
            "**----- Start of picture text -----**<br>\n"
            "Figure caption: anatomy of the lung.<br>\n"
            "**----- End of picture text -----**<br>"
        )
        result = remove_picture_markers(text)
        assert "Start of picture text" not in result
        assert "End of picture text" not in result
        assert "Figure caption: anatomy of the lung." in result


class TestFlattenPseudoTables:
    """Tests for flatten_pseudo_tables."""

    def test_empty_string(self) -> None:
        assert flatten_pseudo_tables("") == ""

    def test_preserves_text_without_pipes(self) -> None:
        text = "Plain text\n\nNo pipes here at all."
        result = flatten_pseudo_tables(text)
        assert result == text

    def test_preserves_real_table_with_separator(self) -> None:
        # A pipe row followed by '|---' is a real markdown table.
        text = "|Header A<br>data line|\n|---|\n|next row|"
        result = flatten_pseudo_tables(text)
        assert result == text

    def test_flattens_pseudo_table_without_separator(self) -> None:
        # A pipe row NOT followed by separator is misclassified prose.
        text = "|item one<br>item two<br>item three|\n\nFollow-up paragraph."
        result = flatten_pseudo_tables(text)
        assert "<br>" not in result
        assert "item one" in result
        assert "item three" in result
        # First line should not start with a pipe anymore.
        first_line = result.split("\n")[0]
        assert not first_line.startswith("|")

    def test_internal_pipes_become_newlines(self) -> None:
        # Pseudo-table with column-separator pipes inside the row.
        text = "|aaa<br>bbb|XXX<br>YYY|\n\nNext paragraph."
        result = flatten_pseudo_tables(text)
        # No pipes survive in the flattened block (before the blank line).
        first_block = result.split("\n\n")[0]
        assert "|" not in first_block
        assert "aaa" in result
        assert "XXX" in result

    def test_pipe_line_without_br_is_left_alone(self) -> None:
        # A '|' line without <br> is not a pseudo-table - leave it.
        text = "|just a pipe line|\n\nNormal text after."
        result = flatten_pseudo_tables(text)
        assert result == text

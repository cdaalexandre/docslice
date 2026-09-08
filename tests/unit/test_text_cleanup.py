"""Tests - text cleanup (domain layer, pure logic).

Piramide de testes: Percival & Gregory, Cap. 5.
'Lots of unit tests, few integration tests.'
"""

from __future__ import annotations

from docslice.domain.text_cleanup import (
    flatten_pseudo_tables,
    normalize_markdown,
    normalize_text,
    remove_page_markers,
    remove_picture_markers,
    strip_control_chars,
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
    """Tests for remove_page_markers.

    The three 'removes' tests used to place the marker between two
    prose lines. That encoded the old bug: any bare number on its own
    line was deleted regardless of context. They now use the isolated
    form a real footer takes after normalize_text.
    """

    def test_removes_isolated_number(self) -> None:
        text = "End of one page.\n\n42\n\nStart of the next."
        result = remove_page_markers(text)
        assert "42" not in result
        assert "End of one page." in result
        assert "Start of the next." in result

    def test_removes_isolated_dashed_number(self) -> None:
        text = "End of one page.\n\n- 42 -\n\nStart of the next."
        result = remove_page_markers(text)
        assert "42" not in result

    def test_removes_isolated_page_prefix(self) -> None:
        text = "End of one page.\n\nPage 42\n\nStart of the next."
        result = remove_page_markers(text)
        assert "Page 42" not in result

    def test_removes_marker_at_start_of_text(self) -> None:
        # Nothing above counts as blank on that side.
        text = "42\n\nBody text."
        result = remove_page_markers(text)
        assert result.strip() == "Body text."

    def test_removes_marker_at_end_of_text(self) -> None:
        # Nothing below counts as blank on that side.
        text = "Body text.\n\n42"
        result = remove_page_markers(text)
        assert result.strip() == "Body text."

    def test_removes_several_markers_in_one_pass(self) -> None:
        text = "Page one body.\n\n1\n\nPage two body.\n\n2\n\nPage three body."
        result = remove_page_markers(text)
        for body in ("Page one body.", "Page two body.", "Page three body."):
            assert body in result
        assert "\n1\n" not in result
        assert "\n2\n" not in result

    def test_preserves_numbers_in_sentences(self) -> None:
        text = "There are 42 items in this list."
        result = remove_page_markers(text)
        assert result == text

    def test_preserves_normal_content(self) -> None:
        text = "Normal text without page numbers."
        result = remove_page_markers(text)
        assert result == text

    def test_line_count_is_stable(self) -> None:
        # Markers become empty lines, never disappear - downstream
        # byte-offset splitting must not see lines vanish here.
        text = "Body.\n\n42\n\nMore body."
        result = remove_page_markers(text)
        assert len(result.split("\n")) == len(text.split("\n"))


class TestRemovePageMarkersIsolationGuard:
    """Regression tests - the isolation guard exists for these cases.

    Every text here matched the old regex and was silently deleted.
    Each one is real content, not a footer.
    """

    def test_preserves_year_in_broken_citation(self) -> None:
        # A layout break drops the year onto its own line.
        text = "Ramalho\n2022\nFluent Python"
        result = remove_page_markers(text)
        assert result == text

    def test_preserves_article_number_after_line_break(self) -> None:
        # Brazilian legal PDFs strand article numbers between prose
        # lines. Deleting them corrupts the document silently.
        text = "Art. 155\n312\nSubtrair coisa alheia"
        result = remove_page_markers(text)
        assert result == text

    def test_preserves_value_from_broken_table(self) -> None:
        text = "Total\n1500\nreais"
        result = remove_page_markers(text)
        assert result == text

    def test_preserves_marker_blank_above_only(self) -> None:
        # One blank side is not enough; a footer is blank on both.
        text = "Paragraph ends.\n\n42\nGlued next line."
        result = remove_page_markers(text)
        assert result == text

    def test_preserves_marker_blank_below_only(self) -> None:
        text = "Glued previous line.\n42\n\nParagraph starts."
        result = remove_page_markers(text)
        assert result == text

    def test_preserves_numbered_list_items(self) -> None:
        # Enumerations survive because prose touches them.
        text = "1\nFirst item\n2\nSecond item"
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


class TestStripControlChars:
    """Tests for strip_control_chars."""

    def test_empty_string(self) -> None:
        assert strip_control_chars("") == ""

    def test_preserves_text_with_no_control_chars(self) -> None:
        text = "Plain text with punctuation, numbers 42, no control bytes."
        result = strip_control_chars(text)
        assert result == text

    def test_strips_null_byte(self) -> None:
        # NULL byte is the canonical lxml/python-docx killer.
        text = "Hello\x00World"
        result = strip_control_chars(text)
        assert result == "HelloWorld"
        assert "\x00" not in result

    def test_strips_bell_and_vertical_tab(self) -> None:
        # BEL (0x07) and VT (0x0B) are XML-illegal C0 control chars.
        text = "alpha\x07beta\x0bgamma"
        result = strip_control_chars(text)
        assert result == "alphabetagamma"

    def test_strips_form_feed_defensive(self) -> None:
        # In the real pipeline normalize_text converts form-feed to
        # newline first, so this is a defensive no-op. Tested in case
        # pipeline ordering changes upstream.
        text = "before\x0cafter"
        result = strip_control_chars(text)
        assert result == "beforeafter"

    def test_strips_full_c0_range_except_tab_lf_cr(self) -> None:
        # Sweep all 32 C0 control chars; only TAB, LF, CR survive.
        all_c0 = "".join(chr(i) for i in range(0x20))
        result = strip_control_chars(all_c0)
        assert result == "\t\n\r"

    def test_preserves_tab_lf_cr(self) -> None:
        # XML 1.0 Char production explicitly allows these three.
        text = "col1\tcol2\nline two\rline three"
        result = strip_control_chars(text)
        assert result == text

    def test_preserves_high_ascii_and_unicode(self) -> None:
        # Everything >= 0x20 survives - Latin-1 accents and beyond-BMP.
        text = "ASCII printable !@#$%^&*() acentos a-e-c greek alpha-beta"
        result = strip_control_chars(text)
        assert result == text

    def test_real_world_pymupdf_noise(self) -> None:
        # Realistic: paragraph contaminated by stray C0 bytes from a
        # corrupt PDF (JPX header errors leaking through pymupdf4llm).
        raw = (
            "Chapter 1: Introduction\x00\n\n"
            "This is a paragraph\x07 with embedded\x0b control\x1f bytes.\n"
            "It must remain readable\x0e after cleanup.\n"
        )
        result = strip_control_chars(raw)
        # No XML-illegal control chars remain (TAB/LF/CR are fine).
        for ch in result:
            assert ch in "\t\n\r" or ord(ch) >= 0x20
        assert "Chapter 1: Introduction" in result
        assert "This is a paragraph with embedded control bytes." in result
        assert "It must remain readable after cleanup." in result


class TestNormalizeMarkdown:
    """Tests for normalize_markdown (structure-preserving normalizer)."""

    def test_normalizes_crlf(self) -> None:
        raw = "# Title\r\n\r\nBody line.\r\n"
        result = normalize_markdown(raw)
        assert "\r" not in result
        assert "# Title" in result

    def test_form_feed_becomes_newline(self) -> None:
        raw = "Before\fAfter"
        result = normalize_markdown(raw)
        assert "\f" not in result
        assert "Before" in result
        assert "After" in result

    def test_preserves_heading_markers(self) -> None:
        raw = "# H1\n\n## H2\n\n### H3\n"
        result = normalize_markdown(raw)
        assert "# H1" in result
        assert "## H2" in result
        assert "### H3" in result

    def test_preserves_list_indentation(self) -> None:
        # normalize_text would collapse leading spaces; this must not.
        raw = "- top\n  - nested\n    - deeper\n"
        result = normalize_markdown(raw)
        assert "  - nested" in result
        assert "    - deeper" in result

    def test_preserves_table_pipes(self) -> None:
        raw = "|col a|col b|\n|---|---|\n|1|2|\n"
        result = normalize_markdown(raw)
        assert "|col a|col b|" in result
        assert "|---|---|" in result

    def test_does_not_collapse_internal_spaces(self) -> None:
        # Code spans / aligned content keep their spacing.
        raw = "word    word\n"
        result = normalize_markdown(raw)
        assert "word    word" in result

    def test_strips_trailing_whitespace(self) -> None:
        raw = "Heading   \nBody   \n"
        result = normalize_markdown(raw)
        for line in result.split("\n"):
            assert line == line.rstrip()

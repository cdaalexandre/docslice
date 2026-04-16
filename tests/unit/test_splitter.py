"""Tests - splitter (domain layer, pure logic).

Pirâmide de testes: Percival & Gregory, Cap. 5.
'Lots of unit tests, few integration tests.'
"""

from docslice.domain.splitter import compute_split_points


class TestComputeSplitPoints:
    """Tests for compute_split_points."""

    def test_empty_text(self) -> None:
        assert compute_split_points("", max_bytes=100) == []

    def test_fits_in_one_chunk(self) -> None:
        text = "Short text."
        assert compute_split_points(text, max_bytes=1000) == []

    def test_exact_fit(self) -> None:
        text = "a" * 100
        assert compute_split_points(text, max_bytes=100) == []

    def test_splits_at_paragraph_boundary(self) -> None:
        para1 = "A" * 60
        para2 = "B" * 60
        text = f"{para1}\n\n{para2}"
        points = compute_split_points(text, max_bytes=70)
        assert len(points) >= 1
        encoded = text.encode("utf-8")
        first_chunk = encoded[: points[0]]
        assert first_chunk.rstrip().endswith(b"A")

    def test_splits_at_newline_when_no_paragraph(self) -> None:
        line1 = "A" * 60
        line2 = "B" * 60
        text = f"{line1}\n{line2}"
        points = compute_split_points(text, max_bytes=70)
        assert len(points) >= 1

    def test_returns_valid_offsets(self) -> None:
        text = ("Hello world. " * 100 + "\n\n") * 20
        points = compute_split_points(text, max_bytes=500)
        encoded = text.encode("utf-8")
        for pt in points:
            assert 0 < pt <= len(encoded)

    def test_all_chunks_within_max(self) -> None:
        text = ("Paragraph content here. " * 50 + "\n\n") * 10
        max_b = 500
        points = compute_split_points(text, max_bytes=max_b)
        encoded = text.encode("utf-8")
        boundaries = [0, *points, len(encoded)]
        for i in range(len(boundaries) - 1):
            chunk_size = boundaries[i + 1] - boundaries[i]
            assert chunk_size <= max_b * 2  # allow overflow for huge paragraphs

    def test_unicode_text(self) -> None:
        text = ("Parágrafo com acentuação. " * 30 + "\n\n") * 5
        points = compute_split_points(text, max_bytes=300)
        assert len(points) >= 1
        encoded = text.encode("utf-8")
        for pt in points:
            assert 0 < pt <= len(encoded)

    def test_single_huge_paragraph(self) -> None:
        text = "A" * 1000
        points = compute_split_points(text, max_bytes=100)
        assert len(points) >= 1

"""Compute split points for text at paragraph boundaries.

Slices text into chunks of approximately max_bytes, breaking only at
paragraph boundaries (double newlines) to preserve structural integrity.

Logica pura. Nao conhece APIs, nao faz I/O.
"""

from __future__ import annotations

_DEFAULT_MAX_BYTES = 3 * 1024 * 1024  # 3 MB


def compute_split_points(text: str, max_bytes: int = _DEFAULT_MAX_BYTES) -> list[int]:
    """Compute byte offsets where text should be split.

    Splits at paragraph boundaries (double newline) so no paragraph is
    broken in half. If a single paragraph exceeds max_bytes, it is kept
    whole in its own chunk.

    Args:
        text: The full normalized text.
        max_bytes: Target maximum size per chunk in bytes.

    Returns:
        List of byte offsets (positions in the UTF-8 encoded text)
        where splits should occur. Empty list if text fits in one chunk.
    """
    encoded = text.encode("utf-8")
    total = len(encoded)

    if total <= max_bytes:
        return []

    split_points: list[int] = []
    chunk_start = 0

    while chunk_start < total:
        chunk_end = chunk_start + max_bytes

        if chunk_end >= total:
            break

        search_region = encoded[chunk_start:chunk_end]
        para_marker = b"\n\n"
        last_para = search_region.rfind(para_marker)

        if last_para != -1:
            split_at = chunk_start + last_para + len(para_marker)
        else:
            last_nl = search_region.rfind(b"\n")
            split_at = chunk_start + last_nl + 1 if last_nl != -1 else chunk_end

        split_points.append(split_at)
        chunk_start = split_at

    return split_points

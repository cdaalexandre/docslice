"""Adapter - file I/O operations: write text, split binary and text files.

Fundamentacao: Ramalho, Fluent Python, Cap. 4.
'Beware of Encoding Defaults - the worst bugs are the silent mojibake kind.'

All open() calls use encoding='utf-8' explicitly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from docslice.log import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger(__name__)

_DEFAULT_MAX_BYTES = 3 * 1024 * 1024  # 3 MB


def write_text(text: str, output_path: Path) -> Path:
    """Write text to a file with UTF-8 encoding and LF line endings.

    Uses write_bytes (not write_text) to bypass Path.write_text's
    default newline translation. On Windows that translation emits
    CRLF, which breaks the split pipeline invariant:

      - compute_split_points operates on text.encode("utf-8") in
        memory (LF only).
      - split_text_file operates on path.read_bytes() from disk.

    Both must see the SAME byte sequence; otherwise the last chunk
    on disk inherits the extra CRLF bytes and can exceed max_bytes.

    Args:
        text: Content to write.
        output_path: Destination file path.

    Returns:
        The path written to.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(text.encode("utf-8"))
    logger.info("Wrote %d bytes to %s", output_path.stat().st_size, output_path)
    return output_path


def split_text_file(path: Path, split_points: list[int], output_dir: Path) -> list[Path]:
    """Split a text file at the given byte offsets.

    Args:
        path: Source text file.
        split_points: Byte offsets where splits occur (from domain.splitter).
        output_dir: Directory for output parts.

    Returns:
        List of paths to the generated parts.
    """
    content = path.read_bytes()
    stem = path.stem
    suffix = path.suffix
    boundaries = [0, *split_points, len(content)]

    output_dir.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []

    for i in range(len(boundaries) - 1):
        chunk = content[boundaries[i] : boundaries[i + 1]]
        part_path = output_dir / f"{stem}_part{i + 1:03d}{suffix}"
        part_path.write_bytes(chunk)
        parts.append(part_path)
        logger.debug("Text part %d: %d bytes -> %s", i + 1, len(chunk), part_path)

    logger.info("Split text into %d parts in %s", len(parts), output_dir)
    return parts


def split_binary_file(
    path: Path,
    max_bytes: int = _DEFAULT_MAX_BYTES,
    output_dir: Path | None = None,
) -> list[Path]:
    """Split a binary file into chunks of approximately max_bytes.

    Args:
        path: Source binary file.
        max_bytes: Maximum size per chunk in bytes.
        output_dir: Directory for output parts. Defaults to path.parent.

    Returns:
        List of paths to the generated parts.
    """
    dest = output_dir or path.parent
    dest.mkdir(parents=True, exist_ok=True)

    file_size = path.stat().st_size
    if file_size <= max_bytes:
        logger.info("File %s (%d bytes) fits in one chunk, no split needed", path, file_size)
        return [path]

    stem = path.stem
    suffix = path.suffix
    parts: list[Path] = []

    with open(path, "rb") as fh:
        part_num = 0
        while True:
            chunk = fh.read(max_bytes)
            if not chunk:
                break
            part_num += 1
            part_path = dest / f"{stem}_part{part_num:03d}{suffix}"
            part_path.write_bytes(chunk)
            parts.append(part_path)
            logger.debug("Binary part %d: %d bytes -> %s", part_num, len(chunk), part_path)

    logger.info("Split binary into %d parts in %s", len(parts), dest)
    return parts

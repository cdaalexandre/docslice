"""Adapter - write Markdown text to a .md file with LF line endings.

Fundamentacao: Ramalho, Fluent Python, Cap. 4.
'Beware of Encoding Defaults - the worst bugs are the silent mojibake kind.'

Sibling of file_io.write_text: same LF invariant, same write_bytes
discipline. Kept as its own adapter so the .md output boundary is
explicit and injectable via the MarkdownWriter protocol. Isolated I/O:
the .md write path lives here only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from docslice.log import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger(__name__)


def write_markdown(text: str, md_path: Path) -> Path:
    """Write Markdown text to a file with UTF-8 encoding and LF line endings.

    Uses write_bytes (not write_text) to bypass Path.write_text's
    default newline translation, which emits CRLF on Windows and would
    pollute the repository and the byte-level invariants the rest of
    the pipeline relies on.

    Args:
        text: Markdown content to write.
        md_path: Destination .md file path. Parent directory is created
            if missing.

    Returns:
        The md_path argument, for chainability.
    """
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_bytes(text.encode("utf-8"))
    logger.info("Wrote %d bytes to %s", md_path.stat().st_size, md_path)
    return md_path

"""Service layer - orchestrates extraction, cleanup, splitting, and writing.

Fundamentacao: Percival & Gregory, Architecture Patterns, Cap. 4.e.
'Introducing a Service Layer - define a clear boundary for our use cases.'

Dependency injection via function parameters: extractors and I/O functions
are passed in, making the service layer testable with Fakes.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from docslice.adapters.file_io import split_binary_file, split_text_file, write_text
from docslice.domain.splitter import compute_split_points
from docslice.domain.text_cleanup import normalize_text, remove_page_markers
from docslice.log import get_logger

if TYPE_CHECKING:
    from pathlib import Path

    from docslice.adapters.protocols import TextExtractor

logger = get_logger(__name__)

_DEFAULT_MAX_TXT_BYTES = 500 * 1024  # 500 KB
_DEFAULT_MAX_ORIG_BYTES = 3 * 1024 * 1024  # 3 MB

_EXTRACTORS: dict[str, str] = {
    ".pdf": "docslice.adapters.pdf_reader:extract_pdf",
    ".epub": "docslice.adapters.epub_reader:extract_epub",
}


@dataclass(frozen=True)
class ConvertResult:
    """Result of a conversion operation."""

    input_path: Path
    txt_path: Path
    txt_parts: list[Path] = field(default_factory=list)
    original_parts: list[Path] = field(default_factory=list)


def _resolve_extractor(suffix: str) -> TextExtractor:
    """Resolve the appropriate extractor for a file extension."""
    dotted = suffix.lower()
    if dotted not in _EXTRACTORS:
        supported = ", ".join(_EXTRACTORS)
        msg = f"Unsupported format '{dotted}'. Supported: {supported}"
        raise ValueError(msg)

    module_path, func_name = _EXTRACTORS[dotted].rsplit(":", 1)
    module = importlib.import_module(module_path)
    return getattr(module, func_name)  # type: ignore[no-any-return]


def convert(
    input_path: Path,
    output_dir: Path,
    max_txt_bytes: int = _DEFAULT_MAX_TXT_BYTES,
    max_orig_bytes: int = _DEFAULT_MAX_ORIG_BYTES,
    *,
    extractor: TextExtractor | None = None,
) -> ConvertResult:
    """Full pipeline: detect format -> extract -> clean -> split -> write.

    Args:
        input_path: Path to PDF or EPUB file.
        output_dir: Directory for all output files.
        max_txt_bytes: Target TXT chunk size in bytes (~500 KB default).
        max_orig_bytes: Target original binary chunk size in bytes (~3 MB default).
        extractor: Optional injected extractor (for testing with Fakes).

    Returns:
        ConvertResult with paths to all generated files.
    """
    from pathlib import Path as _Path

    logger.info("Starting conversion: %s", input_path)

    extract = extractor or _resolve_extractor(_Path(input_path).suffix)

    logger.info("Extracting text...")
    raw_text = extract(input_path)

    logger.info("Normalizing text...")
    clean_text = normalize_text(raw_text)
    clean_text = remove_page_markers(clean_text)

    txt_path = _Path(output_dir) / f"{_Path(input_path).stem}.txt"
    write_text(clean_text, txt_path)

    split_points = compute_split_points(clean_text, max_txt_bytes)
    txt_parts: list[_Path] = []
    if split_points:
        txt_parts_dir = _Path(output_dir) / "txt_parts"
        txt_parts = split_text_file(txt_path, split_points, txt_parts_dir)

    original_parts: list[_Path] = []
    if _Path(input_path).stat().st_size > max_orig_bytes:
        orig_parts_dir = _Path(output_dir) / "original_parts"
        original_parts = split_binary_file(input_path, max_orig_bytes, orig_parts_dir)

    logger.info(
        "Conversion complete: %d txt parts, %d original parts",
        len(txt_parts),
        len(original_parts),
    )

    return ConvertResult(
        input_path=input_path,
        txt_path=txt_path,
        txt_parts=txt_parts,
        original_parts=original_parts,
    )

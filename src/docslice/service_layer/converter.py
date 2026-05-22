"""Service layer - orchestrates extraction, cleanup, splitting, and writing.

Fundamentacao: Percival & Gregory, Architecture Patterns, Cap. 4.e.
'Introducing a Service Layer - define a clear boundary for our use cases.'

Dependency injection via function parameters: extractors and writers
are passed in, making the service layer testable with Fakes.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from docslice.adapters.docx_writer import write_txt_as_docx
from docslice.adapters.file_io import split_binary_file, split_text_file, write_text
from docslice.domain.splitter import compute_split_points
from docslice.domain.text_cleanup import (
    flatten_pseudo_tables,
    normalize_text,
    remove_page_markers,
    remove_picture_markers,
    strip_control_chars,
)
from docslice.log import get_logger
from docslice.service_layer.rasterizer import rasterize_document

if TYPE_CHECKING:
    from pathlib import Path

    from docslice.adapters.protocols import DocxWriter, PageRasterizer, TextExtractor

logger = get_logger(__name__)

_DEFAULT_MAX_TXT_BYTES = 300 * 1024  # 300 KB
_DEFAULT_MAX_ORIG_BYTES = 3 * 1024 * 1024  # 3 MB
_DEFAULT_IMAGE_DPI = 200  # dots per inch for --images

_EXTRACTORS: dict[str, str] = {
    ".pdf": "docslice.adapters.pdf_reader:extract_pdf",
    ".epub": "docslice.adapters.epub_reader:extract_epub",
}


@dataclass(frozen=True)
class ConvertResult:
    """Result of a conversion operation."""

    input_path: Path
    txt_path: Path
    docx_path: Path
    txt_parts: list[Path] = field(default_factory=list)
    docx_parts: list[Path] = field(default_factory=list)
    original_parts: list[Path] = field(default_factory=list)
    page_images: list[Path] = field(default_factory=list)


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
    rasterize: bool = False,
    image_dpi: int = _DEFAULT_IMAGE_DPI,
    extractor: TextExtractor | None = None,
    docx_writer: DocxWriter | None = None,
    rasterizer: PageRasterizer | None = None,
) -> ConvertResult:
    """Full pipeline: detect format -> extract -> clean -> split -> write.

    Generates, in order:
        1. <stem>.txt (full normalized text)
        2. <stem>.docx (full text as Word doc, Drive-uploadable)
        3. txt_parts/<stem>_partNNN.txt (~max_txt_bytes each)
        4. docx_parts/<stem>_partNNN.docx (one per TXT chunk)
        5. original_parts/<stem>_partNNN.<ext> (only if input file
           is larger than max_orig_bytes)
        6. page_images/<stem>_pageNNNNN.png (only if rasterize=True
           and the input is a PDF)

    Args:
        input_path: Path to PDF or EPUB file.
        output_dir: Directory for all output files.
        max_txt_bytes: Target TXT chunk size in bytes (~300 KB default).
        max_orig_bytes: Target original binary chunk size in bytes
            (~3 MB default).
        rasterize: If True, also render each PDF page to a PNG.
            Ignored (with a warning) for non-PDF input.
        image_dpi: Render resolution for the page images, in DPI.
        extractor: Optional injected extractor (for testing with Fakes).
        docx_writer: Optional injected docx writer (for testing with Fakes).
        rasterizer: Optional injected rasterizer (for testing with Fakes).

    Returns:
        ConvertResult with paths to all generated files.
    """
    logger.info("Starting conversion: %s", input_path)

    extract = extractor or _resolve_extractor(input_path.suffix)
    write_docx = docx_writer or write_txt_as_docx

    logger.info("Extracting text...")
    raw_text = extract(input_path)

    logger.info("Normalizing text...")
    clean_text = normalize_text(raw_text)
    clean_text = strip_control_chars(clean_text)
    clean_text = remove_page_markers(clean_text)
    clean_text = remove_picture_markers(clean_text)
    clean_text = flatten_pseudo_tables(clean_text)

    stem = input_path.stem

    txt_path = output_dir / f"{stem}.txt"
    write_text(clean_text, txt_path)

    docx_path = output_dir / f"{stem}.docx"
    write_docx(txt_path, docx_path)

    split_points = compute_split_points(clean_text, max_txt_bytes)
    txt_parts: list[Path] = []
    docx_parts: list[Path] = []
    if split_points:
        txt_parts_dir = output_dir / "txt_parts"
        txt_parts = split_text_file(txt_path, split_points, txt_parts_dir)

        docx_parts_dir = output_dir / "docx_parts"
        for txt_part in txt_parts:
            docx_part = docx_parts_dir / f"{txt_part.stem}.docx"
            write_docx(txt_part, docx_part)
            docx_parts.append(docx_part)

    original_parts: list[Path] = []
    if input_path.stat().st_size > max_orig_bytes:
        orig_parts_dir = output_dir / "original_parts"
        original_parts = split_binary_file(input_path, max_orig_bytes, orig_parts_dir)

    page_images: list[Path] = []
    if rasterize:
        if input_path.suffix.lower() == ".pdf":
            page_images = rasterize_document(
                input_path,
                output_dir,
                image_dpi,
                rasterizer=rasterizer,
            )
        else:
            logger.warning("Skipping --images: %s is not a PDF", input_path.name)

    logger.info(
        "Conversion complete: %d txt parts, %d docx parts, %d original parts, %d page images",
        len(txt_parts),
        len(docx_parts),
        len(original_parts),
        len(page_images),
    )

    return ConvertResult(
        input_path=input_path,
        txt_path=txt_path,
        docx_path=docx_path,
        txt_parts=txt_parts,
        docx_parts=docx_parts,
        original_parts=original_parts,
        page_images=page_images,
    )

"""Entrypoint CLI - user-facing interface.

Fundamentacao: Percival & Gregory, Architecture Patterns, Cap. 4.e.
'The entrypoint is the thinnest possible layer.'
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from docslice.log import get_logger, setup_logging
from docslice.service_layer.converter import convert
from docslice.service_layer.rasterizer import rasterize_document

logger = get_logger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="docslice",
        description="Extract PDF/EPUB to TXT and DOCX; slice into chunks for LLM indexing.",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to a PDF or EPUB file.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: <input_stem>_output/).",
    )
    parser.add_argument(
        "--max-txt-kb",
        type=float,
        default=300.0,
        help="Target TXT chunk size in KB (default: 300).",
    )
    parser.add_argument(
        "--max-orig-mb",
        type=float,
        default=3.0,
        help="Target original binary chunk size in MB (default: 3.0).",
    )
    image_group = parser.add_mutually_exclusive_group()
    image_group.add_argument(
        "--images",
        action="store_true",
        help="Also render each PDF page to a PNG in page_images/.",
    )
    image_group.add_argument(
        "--images-only",
        action="store_true",
        help="Render PDF pages to PNGs and skip TXT/DOCX conversion.",
    )
    parser.add_argument(
        "--image-dpi",
        type=int,
        default=200,
        help="Resolution in DPI for --images / --images-only (default: 200).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed log output.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress informational messages.",
    )
    return parser


def main() -> None:
    """CLI entrypoint."""
    parser = _build_parser()
    args = parser.parse_args()

    setup_logging(verbose=args.verbose, quiet=args.quiet)

    input_path: Path = args.input.resolve()
    if not input_path.exists():
        logger.error("File not found: %s", input_path)
        sys.exit(1)

    output_dir: Path = (
        args.output_dir.resolve()
        if args.output_dir
        else input_path.parent / f"{input_path.stem}_output"
    )

    if args.images_only:
        try:
            images = rasterize_document(input_path, output_dir, args.image_dpi)
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            logger.error("Rasterization failed: %s", exc)
            sys.exit(1)
        logger.info("Page images: %d files in %s", len(images), output_dir / "page_images")
        return

    max_txt_bytes = int(args.max_txt_kb * 1024)
    max_orig_bytes = int(args.max_orig_mb * 1024 * 1024)

    try:
        result = convert(
            input_path,
            output_dir,
            max_txt_bytes,
            max_orig_bytes,
            rasterize=args.images,
            image_dpi=args.image_dpi,
        )
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        logger.error("Conversion failed: %s", exc)
        sys.exit(1)

    logger.info("Full text: %s", result.txt_path)
    logger.info("Full docx: %s", result.docx_path)
    if result.txt_parts:
        logger.info("Text parts: %d files in %s/", len(result.txt_parts), output_dir)
    if result.docx_parts:
        logger.info("Docx parts: %d files in %s/", len(result.docx_parts), output_dir)
    if result.original_parts:
        logger.info("Original parts: %d files", len(result.original_parts))
    if result.page_images:
        logger.info(
            "Page images: %d files in %s",
            len(result.page_images),
            output_dir / "page_images",
        )

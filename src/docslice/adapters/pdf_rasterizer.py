"""Adapter - rasterize PDF pages to PNG images via fitz (PyMuPDF).

Fundamentacao: Percival & Gregory, Architecture Patterns, Cap. 2.g.
'What Is a Port and What Is an Adapter, in Python?'

Sibling of pdf_reader: same MuPDF C core, same adapter shape. Where
pdf_reader returns extracted text, this module renders each page to
a PNG file. Isolated I/O - PyMuPDF rendering and PNG writing live
here only, so swapping the rendering backend changes only this file.

Page numbering uses 5 zero-padded digits (page00001.png) so the
files sort correctly in a directory listing up to the 30k-page
scale this project targets.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from docslice.log import get_logger

logger = get_logger(__name__)

_DEFAULT_DPI = 200
_PROGRESS_EVERY = 500


def rasterize_pdf(path: Path, output_dir: Path, dpi: int = _DEFAULT_DPI) -> list[Path]:
    """Render every page of a PDF to its own PNG image file.

    Args:
        path: Path to the PDF file.
        output_dir: Directory for the PNG files. Created if missing.
        dpi: Render resolution in dots per inch. Higher means sharper
            images and larger files; 150 is light, 200-300 is crisp.

    Returns:
        Paths to the generated PNG files, in page order (one per page).

    Raises:
        FileNotFoundError: If path does not exist.
        RuntimeError: If fitz cannot open the PDF.
    """
    p = Path(path)
    if not p.exists():
        msg = f"PDF file not found: {path}"
        raise FileNotFoundError(msg)

    try:
        doc = fitz.open(str(p))
    except Exception as exc:
        msg = f"Cannot open PDF: {path}"
        raise RuntimeError(msg) from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    total = len(doc)
    images: list[Path] = []

    for i, page in enumerate(doc):
        pixmap = page.get_pixmap(dpi=dpi)
        image_path = output_dir / f"{p.stem}_page{i + 1:05d}.png"
        pixmap.save(str(image_path))
        images.append(image_path)
        if (i + 1) % _PROGRESS_EVERY == 0:
            logger.info("Rasterized %d / %d pages", i + 1, total)

    doc.close()
    logger.info("Rasterization complete: %d pages -> %s", total, output_dir)
    return images

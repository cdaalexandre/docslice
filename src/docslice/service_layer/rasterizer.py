"""Service layer - the rasterize use case: PDF pages to image files.

Fundamentacao: Percival & Gregory, Architecture Patterns, Cap. 4.e.
'Introducing a Service Layer - define a clear boundary for our use cases.'

Rasterizing is a standalone use case (CLI --images-only) and also a
step the convert pipeline can add (CLI --images). Both paths go
through rasterize_document, so the PDF guard and the page_images
directory layout live in exactly one place.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from docslice.adapters.pdf_rasterizer import rasterize_pdf
from docslice.log import get_logger

if TYPE_CHECKING:
    from pathlib import Path

    from docslice.adapters.protocols import PageRasterizer

logger = get_logger(__name__)

_DEFAULT_IMAGE_DPI = 200
_PAGE_IMAGES_DIRNAME = "page_images"


def rasterize_document(
    input_path: Path,
    output_dir: Path,
    image_dpi: int = _DEFAULT_IMAGE_DPI,
    *,
    rasterizer: PageRasterizer | None = None,
) -> list[Path]:
    """Render every page of a PDF to a PNG under output_dir/page_images/.

    Args:
        input_path: Path to the source document. Must be a PDF.
        output_dir: Base output directory. Images go in a
            'page_images' subdirectory.
        image_dpi: Render resolution for the page images, in DPI.
        rasterizer: Optional injected rasterizer (for testing with Fakes).

    Returns:
        Paths to the generated PNG files, one per page.

    Raises:
        ValueError: If input_path is not a PDF.
        FileNotFoundError: If input_path does not exist.
    """
    suffix = input_path.suffix.lower()
    if suffix != ".pdf":
        msg = f"Rasterizing requires a PDF, got '{suffix}'."
        raise ValueError(msg)

    render = rasterizer or rasterize_pdf
    images_dir = output_dir / _PAGE_IMAGES_DIRNAME

    logger.info("Rasterizing %s at %d DPI", input_path, image_dpi)
    images = render(input_path, images_dir, image_dpi)
    logger.info("Rasterization produced %d page images", len(images))
    return images

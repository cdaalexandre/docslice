"""Domain - re-exports."""

from __future__ import annotations

from docslice.domain.splitter import compute_split_points  # noqa: F401
from docslice.domain.text_cleanup import (  # noqa: F401
    normalize_text,
    remove_page_markers,
)

__all__ = ["compute_split_points", "normalize_text", "remove_page_markers"]

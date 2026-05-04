"""Adapter protocols - explicit interfaces for the adapter layer.

Fundamentacao: Percival & Gregory, Architecture Patterns, Cap. 2.
'The Repository in the Abstract - define the interface before
the implementation.'

Ramalho, Fluent Python, Cap. 13.
'Protocol provides structural subtyping - a.k.a. static duck typing.'

Usage:
    Production code uses the real adapter (pdf_reader.extract_pdf).
    Tests inject a Fake that satisfies the Protocol.
    The type checker verifies both implement the same interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pathlib import Path


class TextExtractor(Protocol):
    """Interface for text extraction (PDF, EPUB, fake).

    Adapters implement __call__ so they can be passed as plain callables.
    """

    def __call__(self, path: Path) -> str:
        """Extract text from a file at the given path."""
        ...


class FileSplitter(Protocol):
    """Interface for splitting a file into chunks."""

    def __call__(self, path: Path, max_bytes: int) -> list[Path]:
        """Split a file into parts of at most max_bytes."""
        ...


class GDocsWriter(Protocol):
    """Interface for uploading a TXT file as a Google Doc.

    Implementations convert plain text into a native Google Doc
    via the Drive API (mimeType=application/vnd.google-apps.document)
    and return the resulting document URL.
    """

    def __call__(
        self,
        txt_path: Path,
        display_name: str,
        folder_id: str | None,
    ) -> str:
        """Upload txt_path as a Google Doc and return its URL."""
        ...

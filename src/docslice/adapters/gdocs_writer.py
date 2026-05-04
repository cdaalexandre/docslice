"""Adapter - upload TXT files to Drive as native Google Docs.

Fundamentacao: Percival & Gregory, Architecture Patterns, Cap. 2.
'Ports and Adapters - isolate external boundaries.'

Ramalho, Fluent Python, Cap. 13.
'Protocol provides structural subtyping.'

Drive API automatically converts the uploaded source file to a
native Google Doc when metadata.mimeType is set to
'application/vnd.google-apps.document'. This avoids the multi-call
overhead of the Docs API (documents.batchUpdate with insertText) and
stays within Drive's per-user write quota for large batches.

Source size limits (verified 2024): up to ~50 MB raw / ~1 M chars in
the resulting Google Doc. Our 300 KB TXT chunks fit with wide margin.

Dependency injection: the constructor takes a pre-built Drive service.
Tests pass a FakeService satisfying the same duck-typed shape, so
the upload path is exercised without mock.patch.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from docslice.log import get_logger

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

logger = get_logger(__name__)

_GOOGLE_DOC_MIMETYPE = "application/vnd.google-apps.document"
_TXT_MIMETYPE = "text/plain"


class GoogleDocsUploader:
    """Upload TXT files to Drive with automatic Google Doc conversion.

    Receives an authenticated Drive service via DI; tests inject a
    Fake satisfying the same interface (.files().create(...).execute()).
    """

    def __init__(self, service: Any) -> None:
        """Initialize with a built googleapiclient Drive service.

        Args:
            service: googleapiclient.discovery.Resource for Drive v3,
                typically obtained via build_drive_service().
        """
        self._service = service

    def __call__(
        self,
        txt_path: Path,
        display_name: str,
        folder_id: str | None = None,
    ) -> str:
        """Upload txt_path as a Google Doc and return the doc URL.

        Args:
            txt_path: Path to the TXT file to upload.
            display_name: Document name in Drive (extension stripped).
            folder_id: Optional Drive folder ID to place the doc in.
                When None, the doc lands in My Drive root.

        Returns:
            webViewLink (URL) to open the created Google Doc.

        Raises:
            RuntimeError: If the Drive API call fails.
        """
        metadata: dict[str, Any] = {
            "name": display_name,
            "mimeType": _GOOGLE_DOC_MIMETYPE,
        }
        if folder_id:
            metadata["parents"] = [folder_id]

        media = MediaFileUpload(str(txt_path), mimetype=_TXT_MIMETYPE)

        try:
            created: dict[str, Any] = (
                self._service.files()
                .create(
                    body=metadata,
                    media_body=media,
                    fields="id, name, webViewLink",
                )
                .execute()
            )
        except HttpError as exc:
            msg = f"Drive upload failed for {txt_path}: {exc}"
            raise RuntimeError(msg) from exc

        doc_id = created.get("id", "<unknown>")
        link = created.get("webViewLink", "<no link>")
        logger.info("Uploaded %s as Google Doc id=%s", display_name, doc_id)
        return str(link)

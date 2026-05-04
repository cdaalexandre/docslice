"""Tests - GoogleDocsUploader with Fake Drive service.

Percival & Gregory, Cap. 3.c.ii: 'every call to mock.patch
is a ticking time bomb.' Tests use Fakes with .calls lists,
mirroring tests/unit/test_converter.py's FakeExtractor pattern.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
from googleapiclient.errors import HttpError

from docslice.adapters.gdocs_writer import GoogleDocsUploader

if TYPE_CHECKING:
    from pathlib import Path


class FakeRequest:
    """Stub for googleapiclient request returned by .create()."""

    def __init__(self, response: dict[str, Any], *, raise_http: bool = False) -> None:
        self.response = response
        self.raise_http = raise_http
        self.executed = False

    def execute(self) -> dict[str, Any]:
        self.executed = True
        if self.raise_http:
            resp = SimpleNamespace(status=500, reason="Server Error")
            raise HttpError(resp=resp, content=b"boom")
        return self.response


class FakeFilesResource:
    """Stub for service.files() exposing .create()."""

    def __init__(
        self,
        response: dict[str, Any] | None = None,
        *,
        raise_http: bool = False,
    ) -> None:
        self.calls: list[dict[str, Any]] = []
        self._response = response or {
            "id": "fake_doc_123",
            "name": "fake",
            "webViewLink": "https://docs.google.com/document/d/fake_doc_123",
        }
        self._raise = raise_http

    def create(
        self,
        body: dict[str, Any],
        media_body: Any,
        fields: str,
    ) -> FakeRequest:
        self.calls.append({"body": body, "media_body": media_body, "fields": fields})
        return FakeRequest(self._response, raise_http=self._raise)


class FakeService:
    """Stub for googleapiclient Drive service."""

    def __init__(
        self,
        response: dict[str, Any] | None = None,
        *,
        raise_http: bool = False,
    ) -> None:
        self._files = FakeFilesResource(response, raise_http=raise_http)

    def files(self) -> FakeFilesResource:
        return self._files


class TestGoogleDocsUploader:
    """Tests for the upload-as-Google-Doc behaviour."""

    def test_uploads_with_doc_mimetype(self, tmp_path: Path) -> None:
        txt = tmp_path / "doc.txt"
        txt.write_bytes(b"hello world")
        service = FakeService()
        uploader = GoogleDocsUploader(service)

        link = uploader(txt, "My Doc")

        assert link == "https://docs.google.com/document/d/fake_doc_123"
        calls = service.files().calls
        assert len(calls) == 1
        body = calls[0]["body"]
        assert body["name"] == "My Doc"
        assert body["mimeType"] == "application/vnd.google-apps.document"
        assert "parents" not in body

    def test_uploads_to_folder_when_provided(self, tmp_path: Path) -> None:
        txt = tmp_path / "doc.txt"
        txt.write_bytes(b"hello")
        service = FakeService()
        uploader = GoogleDocsUploader(service)

        uploader(txt, "Doc In Folder", folder_id="folder_abc123")

        body = service.files().calls[0]["body"]
        assert body["parents"] == ["folder_abc123"]

    def test_passes_correct_fields_filter(self, tmp_path: Path) -> None:
        txt = tmp_path / "doc.txt"
        txt.write_bytes(b"hi")
        service = FakeService()
        uploader = GoogleDocsUploader(service)

        uploader(txt, "Some Doc")

        assert service.files().calls[0]["fields"] == "id, name, webViewLink"

    def test_raises_runtime_error_on_http_failure(self, tmp_path: Path) -> None:
        txt = tmp_path / "doc.txt"
        txt.write_bytes(b"hi")
        service = FakeService(raise_http=True)
        uploader = GoogleDocsUploader(service)

        with pytest.raises(RuntimeError, match="Drive upload failed"):
            uploader(txt, "Failing Doc")

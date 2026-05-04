"""Adapter - Google OAuth credential loading and Drive service factory.

Fundamentacao: Percival & Gregory, Architecture Patterns, Cap. 2.
'Ports and Adapters - external integrations live in adapters.'

Ramalho, Fluent Python, Cap. 4.
'Beware of Encoding Defaults - the worst bugs are silent mojibake.'

Standard Google OAuth 2.0 desktop flow:
    1. credentials.json (client secret) - downloaded from Google Cloud
       Console -> APIs & Services -> Credentials -> OAuth 2.0 Client
       IDs (application type: Desktop app).
    2. First call: opens a browser, user consents, token.json saved.
    3. Subsequent calls: token.json is reused or silently refreshed.

Scope: drive.file - access only to files created or opened by this
application. Narrower than drive (full Drive access).

This module is boundary-only: the OAuth dance and the Drive client
build are tested manually via the CLI flag in PR-B, not via mock.patch.
The pure logic (upload, metadata) lives in gdocs_writer.py and is
fully unit-tested with a Fake service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from docslice.log import get_logger

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

logger = get_logger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def load_credentials(credentials_path: Path, token_path: Path) -> Credentials:
    """Load, refresh, or create Google OAuth credentials.

    On first call, opens a browser for user consent and saves the
    resulting token. On subsequent calls, reuses or silently refreshes
    the cached token.

    Args:
        credentials_path: OAuth client secret JSON downloaded from
            Google Cloud Console.
        token_path: Where the access/refresh token is cached.

    Returns:
        Authenticated Credentials usable by googleapiclient.

    Raises:
        FileNotFoundError: If credentials_path does not exist.
    """
    if not credentials_path.exists():
        msg = (
            f"OAuth credentials file not found: {credentials_path}. "
            "Download it from Google Cloud Console -> APIs & Services -> "
            "Credentials -> OAuth 2.0 Client IDs (Desktop app)."
        )
        raise FileNotFoundError(msg)

    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(  # type: ignore[no-untyped-call]
            str(token_path),
            SCOPES,
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired Drive token")
            creds.refresh(Request())  # type: ignore[no-untyped-call]
        else:
            logger.info("Starting OAuth flow (browser will open)")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path),
                SCOPES,
            )
            creds = flow.run_local_server(port=0)

        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_bytes(creds.to_json().encode("utf-8"))
        logger.info("Saved Drive token to %s", token_path)

    return creds


def build_drive_service(credentials: Credentials) -> Any:
    """Build a Drive v3 API service from authenticated credentials.

    Args:
        credentials: Authenticated Credentials object.

    Returns:
        googleapiclient.discovery.Resource for the Drive API.
        Typed as Any because googleapiclient ships no public stubs;
        callers consume it via the GDocsWriter Protocol boundary.
    """
    return build("drive", "v3", credentials=credentials, cache_discovery=False)

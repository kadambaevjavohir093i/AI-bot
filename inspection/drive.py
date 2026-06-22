"""Upload inspection PDF to Google Drive using a service account."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from . import config


def upload_pdf(pdf_path: Path, filename: str) -> Optional[str]:
    """Upload pdf_path to Google Drive. Returns the shareable URL or None."""
    if not config.GOOGLE_SERVICE_ACCOUNT_FILE or not config.GOOGLE_DRIVE_FOLDER_ID:
        return None

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        creds = service_account.Credentials.from_service_account_file(
            config.GOOGLE_SERVICE_ACCOUNT_FILE,
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        service = build("drive", "v3", credentials=creds)

        file_metadata = {
            "name": filename,
            "parents": [config.GOOGLE_DRIVE_FOLDER_ID],
        }
        media = MediaFileUpload(str(pdf_path), mimetype="application/pdf")
        uploaded = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        file_id = uploaded.get("id")

        # Make it readable by anyone with the link
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()

        return f"https://drive.google.com/file/d/{file_id}/view"
    except Exception as exc:
        print(f"[Drive] Upload failed: {exc}")
        return None

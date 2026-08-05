from __future__ import annotations

from google.auth import default
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload


DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"


def _service():
    credentials, _ = default(scopes=[DRIVE_SCOPE])
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def upsert_pdf(*, content: bytes, filename: str, folder_id: str, notion_page_id: str) -> str:
    service = _service()
    escaped_page_id = notion_page_id.replace("'", "\\'")
    escaped_folder_id = folder_id.replace("'", "\\'")
    query = (
        f"'{escaped_folder_id}' in parents and trashed = false and "
        f"appProperties has {{ key='notion_page_id' and value='{escaped_page_id}' }}"
    )
    existing = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, webViewLink)",
        pageSize=2,
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
    ).execute().get("files", [])

    media = MediaInMemoryUpload(content, mimetype="application/pdf", resumable=False)
    if existing:
        result = service.files().update(
            fileId=existing[0]["id"],
            body={"name": filename},
            media_body=media,
            fields="id, webViewLink",
            supportsAllDrives=True,
        ).execute()
    else:
        result = service.files().create(
            body={
                "name": filename,
                "parents": [folder_id],
                "mimeType": "application/pdf",
                "appProperties": {"notion_page_id": notion_page_id},
            },
            media_body=media,
            fields="id, webViewLink",
            supportsAllDrives=True,
        ).execute()

    return result.get("webViewLink") or f"https://drive.google.com/file/d/{result['id']}/view"

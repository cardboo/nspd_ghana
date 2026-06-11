"""
Document file storage with two drivers:

  local        — files under UPLOADS_DIR (development; serverless instances
                 have no persistent disk, so this is dev-only)
  vercel_blob  — Vercel Blob via its REST API (production on Vercel;
                 requires BLOB_READ_WRITE_TOKEN)

The documents table stores which driver and key each file was saved with,
so existing files keep working if the driver setting changes later.
"""

import re
import uuid
from pathlib import Path

import requests
from fastapi import HTTPException

from ..config import settings

BLOB_API_BASE = "https://blob.vercel-storage.com"
BLOB_API_VERSION = "7"

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}


def validate_upload(original_name: str, size_bytes: int) -> str:
    """Validate extension and size; returns the lowercase extension."""
    extension = Path(original_name or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"File type not allowed. Accepted: {allowed}")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds the {settings.max_upload_mb} MB limit")
    if size_bytes == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    return extension


def _safe_name(original_name: str) -> str:
    base = Path(original_name).name
    return re.sub(r"[^A-Za-z0-9._-]", "_", base)[:100]


def save(application_id: int, original_name: str, content_type: str, data: bytes) -> tuple:
    """Store the file; returns (driver, storage_key)."""
    extension = Path(original_name).suffix.lower()
    unique = f"{uuid.uuid4().hex}{extension}"

    if settings.storage_driver == "vercel_blob":
        pathname = f"nspd-documents/{application_id}/{unique}"
        response = requests.put(
            f"{BLOB_API_BASE}/{pathname}",
            data=data,
            headers={
                "Authorization": f"Bearer {settings.blob_token}",
                "x-api-version": BLOB_API_VERSION,
                "x-content-type": content_type or "application/octet-stream",
            },
            timeout=30,
        )
        if response.status_code not in (200, 201):
            raise HTTPException(status_code=502, detail="Blob storage upload failed")
        url = response.json().get("url", "")
        if not url:
            raise HTTPException(status_code=502, detail="Blob storage returned no URL")
        return "vercel_blob", url

    # local driver
    directory = settings.uploads_dir / str(application_id)
    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / unique
    file_path.write_bytes(data)
    return "local", f"{application_id}/{unique}"


def load_local(storage_key: str) -> bytes:
    """Read a locally stored file, guarding against path traversal."""
    uploads_root = settings.uploads_dir.resolve()
    file_path = (uploads_root / storage_key).resolve()
    if uploads_root not in file_path.parents:
        raise HTTPException(status_code=404, detail="Document file not found")
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Document file not found")
    return file_path.read_bytes()


def delete(driver: str, storage_key: str) -> None:
    """Best-effort removal of the stored bytes (metadata row is removed by the caller)."""
    if driver == "vercel_blob":
        try:
            requests.post(
                f"{BLOB_API_BASE}/delete",
                json={"urls": [storage_key]},
                headers={
                    "Authorization": f"Bearer {settings.blob_token}",
                    "x-api-version": BLOB_API_VERSION,
                },
                timeout=15,
            )
        except requests.RequestException:
            pass
        return

    uploads_root = settings.uploads_dir.resolve()
    file_path = (uploads_root / storage_key).resolve()
    if uploads_root in file_path.parents and file_path.is_file():
        file_path.unlink(missing_ok=True)

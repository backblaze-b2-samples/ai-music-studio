import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.service.files import (
    FileKeyError,
    FileNotFoundError,
    bulk_remove_files,
    get_download_url,
    get_file,
    get_files,
    get_preview_url,
    get_stats,
    get_upload_activity,
    remove_file,
)
from app.types import DailyUploadCount, FileMetadata, UploadStats


class BulkDeleteRequest(BaseModel):
    keys: list[str] = Field(..., min_length=1, max_length=1000)


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/files", response_model=list[FileMetadata])
async def list_files_endpoint(prefix: str = "", limit: int = 100):
    try:
        return get_files(prefix=prefix, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get("/files/stats", response_model=UploadStats)
async def stats_endpoint():
    return get_stats()


@router.get("/files/stats/activity", response_model=list[DailyUploadCount])
async def upload_activity_endpoint(days: int = 7):
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 90")
    return get_upload_activity(days=days)


@router.post("/files/bulk-delete")
async def bulk_delete_files_endpoint(body: BulkDeleteRequest):
    """Delete up to 1000 files in a single S3 DeleteObjects call.

    Registered BEFORE any `/files/{key:path}` route so FastAPI doesn't treat
    `bulk-delete` as a key. Returns `{deleted: [...], errors: [...]}` so the
    UI can show partial success without a second round-trip.
    """
    try:
        deleted, errors = bulk_remove_files(body.keys)
    except FileKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to delete files") from None
    logger.info(
        "Bulk file delete: requested=%d deleted=%d errors=%d",
        len(body.keys),
        len(deleted),
        len(errors),
    )
    return {"deleted": deleted, "errors": errors}


@router.get("/files/{key:path}/download")
async def download_file_endpoint(key: str):
    try:
        url = get_download_url(key)
    except FileKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    return {"url": url}


@router.get("/files/{key:path}/preview")
async def preview_file_endpoint(key: str):
    """Return a presigned URL for inline preview. Does not count as a download."""
    try:
        url = get_preview_url(key)
    except FileKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    return {"url": url}


@router.get("/files/{key:path}", response_model=FileMetadata)
async def get_file_endpoint(key: str):
    try:
        return get_file(key)
    except FileKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.delete("/files/{key:path}")
async def delete_file_endpoint(key: str):
    try:
        remove_file(key)
    except FileKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to delete file") from None
    logger.info("File deleted: key=%s", key)
    return {"deleted": True, "key": key}

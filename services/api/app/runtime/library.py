import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.service.library import (
    AudioAssetNotFound,
    AudioKeyError,
    bulk_delete_audio_assets,
    delete_audio_asset,
    get_download_url,
    get_playback_url,
    list_audio_assets,
)
from app.types import AudioAsset


class BulkDeleteRequest(BaseModel):
    keys: list[str] = Field(..., min_length=1, max_length=1000)


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/library", response_model=list[AudioAsset])
async def list_library_endpoint(limit: int = 100):
    try:
        return list_audio_assets(limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post("/library/bulk-delete")
async def bulk_delete_library_endpoint(body: BulkDeleteRequest):
    """Delete up to 1000 audio assets in a single S3 DeleteObjects call.

    Registered BEFORE any `/library/{key:path}` route so FastAPI doesn't
    treat `bulk-delete` as a key. Returns `{deleted, errors}` so the UI can
    show partial success.
    """
    try:
        deleted, errors = bulk_delete_audio_assets(body.keys)
    except AudioKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to delete assets") from None
    logger.info(
        "Bulk audio delete: requested=%d deleted=%d errors=%d",
        len(body.keys),
        len(deleted),
        len(errors),
    )
    return {"deleted": deleted, "errors": errors}


@router.get("/library/{key:path}/playback")
async def playback_endpoint(key: str):
    try:
        url = get_playback_url(key)
    except AudioKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except AudioAssetNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    return {"url": url, "expires_in": 600}


@router.get("/library/{key:path}/download")
async def library_download_endpoint(key: str):
    try:
        url = get_download_url(key)
    except AudioKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except AudioAssetNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    return {"url": url, "expires_in": 600}


@router.delete("/library/{key:path}")
async def library_delete_endpoint(key: str):
    try:
        delete_audio_asset(key)
    except AudioKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to delete asset") from None
    logger.info("Audio asset deleted: key=%s", key)
    return {"deleted": True, "key": key}

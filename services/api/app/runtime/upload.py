import logging

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile

from app.config import settings
from app.runtime.auth import UserContext, require_user
from app.runtime.metrics import record_upload
from app.service.projects import (
    ProjectIdError,
    ProjectNotFound,
    get_project,
    project_prefix,
)
from app.service.upload import UploadError, process_upload
from app.types import FileUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter()


async def _read_upload(request: Request, file: UploadFile) -> tuple[bytes, int | None]:
    content_length_header = request.headers.get("content-length")
    content_length = int(content_length_header) if content_length_header else None
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)  # 1MB chunks
        if not chunk:
            break
        total += len(chunk)
        if total > settings.max_file_size:
            raise HTTPException(status_code=413, detail="File too large")
        chunks.append(chunk)
    return b"".join(chunks), content_length


@router.post("/upload", response_model=FileUploadResponse)
async def upload(request: Request, file: UploadFile):
    content_type = file.content_type or "application/octet-stream"
    file_data, content_length = await _read_upload(request, file)
    try:
        result = process_upload(
            file_data=file_data,
            filename=file.filename or "",
            content_type=content_type,
            content_length=content_length,
        )
    except UploadError as e:
        logger.warning("Upload rejected: %s", e.detail)
        record_upload(success=False)
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None

    record_upload(success=True)
    logger.info(
        "File uploaded: key=%s size=%d type=%s",
        result.key,
        result.size_bytes,
        result.content_type,
    )
    return result


@router.post("/projects/{project_id}/reference", response_model=FileUploadResponse)
async def upload_project_reference(
    project_id: str,
    request: Request,
    file: UploadFile,
    user: UserContext = Depends(require_user),
):
    content_type = file.content_type or "application/octet-stream"
    file_data, content_length = await _read_upload(request, file)
    try:
        _ = get_project(project_id, user.user_id)
        result = process_upload(
            file_data=file_data,
            filename=file.filename or "",
            content_type=content_type,
            content_length=content_length,
            key_prefix=f"{project_prefix(project_id)}reference/",
            audio_only=True,
        )
    except ProjectIdError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except ProjectNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except UploadError as e:
        logger.warning("Reference upload rejected: %s", e.detail)
        record_upload(success=False)
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None

    record_upload(success=True)
    logger.info("Reference uploaded: key=%s size=%d", result.key, result.size_bytes)
    return result

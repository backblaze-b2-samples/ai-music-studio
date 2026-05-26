import functools
import io
import mimetypes
from datetime import UTC, datetime
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import settings
from app.types import FileMetadata
from app.types.formatting import humanize_bytes


def _guess_content_type(key: str) -> str:
    mime, _ = mimetypes.guess_type(key)
    return mime or "application/octet-stream"


def _split_key(key: str) -> tuple[str, str]:
    """Return (folder, filename) from an object key."""
    parts = key.rsplit("/", 1)
    if len(parts) == 2:
        return parts[0] + "/", parts[1]
    return "", parts[0]


def _public_url(key: str) -> str | None:
    """Build a public URL for an object key, percent-encoding the path."""
    if not settings.b2_public_url:
        return None
    return f"{settings.b2_public_url}/{quote(key, safe='/')}"


@functools.lru_cache(maxsize=1)
def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.b2_endpoint,
        region_name=settings.b2_region or None,
        aws_access_key_id=settings.b2_key_id,
        aws_secret_access_key=settings.b2_application_key,
        config=Config(
            signature_version="s3v4",
            user_agent_extra="b2ai-ai-music-studio",
        ),
    )


def check_connectivity() -> bool:
    try:
        client = get_s3_client()
        client.head_bucket(Bucket=settings.b2_bucket_name)
        return True
    except Exception:
        return False


def upload_file(
    file_data: bytes,
    key: str,
    content_type: str,
    metadata: dict[str, str] | None = None,
) -> FileMetadata:
    """Upload file to B2. Raises RuntimeError on S3 failure.

    `metadata` is forwarded as S3 user metadata (HTTP `x-amz-meta-*` headers
    on GET/HEAD). Keys and values must be ASCII strings; non-ASCII content
    will be rejected by S3 at PUT time, so callers serialize aggressively.
    """
    client = get_s3_client()
    params: dict = {
        "Bucket": settings.b2_bucket_name,
        "Key": key,
        "Body": io.BytesIO(file_data),
        "ContentType": content_type,
    }
    if metadata:
        params["Metadata"] = metadata
    try:
        client.put_object(**params)
    except ClientError as e:
        raise RuntimeError(f"B2 upload failed for '{key}': {e}") from e
    folder, filename = _split_key(key)
    size = len(file_data)
    return FileMetadata(
        key=key,
        filename=filename,
        folder=folder,
        size_bytes=size,
        size_human=humanize_bytes(size),
        content_type=content_type,
        uploaded_at=datetime.now(UTC),
        url=_public_url(key),
    )


def list_files(prefix: str = "", max_keys: int = 1000) -> list[FileMetadata]:
    """List files from B2. Raises RuntimeError on S3 failure."""
    client = get_s3_client()
    try:
        response = client.list_objects_v2(
            Bucket=settings.b2_bucket_name,
            Prefix=prefix,
            MaxKeys=max_keys,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 list failed: {e}") from e
    files: list[FileMetadata] = []
    for obj in response.get("Contents", []):
        folder, filename = _split_key(obj["Key"])
        files.append(
            FileMetadata(
                key=obj["Key"],
                filename=filename,
                folder=folder,
                size_bytes=obj["Size"],
                size_human=humanize_bytes(obj["Size"]),
                content_type=_guess_content_type(obj["Key"]),
                uploaded_at=obj["LastModified"],
                url=_public_url(obj["Key"]),
            )
        )
    files.sort(key=lambda f: f.uploaded_at, reverse=True)
    return files


def get_file_metadata(key: str) -> FileMetadata | None:
    client = get_s3_client()
    try:
        response = client.head_object(
            Bucket=settings.b2_bucket_name, Key=key
        )
    except ClientError as e:
        # Only treat 404/NoSuchKey as "not found"; re-raise other errors
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise

    folder, filename = _split_key(key)
    return FileMetadata(
        key=key,
        filename=filename,
        folder=folder,
        size_bytes=response["ContentLength"],
        size_human=humanize_bytes(response["ContentLength"]),
        content_type=response.get("ContentType", _guess_content_type(key)),
        uploaded_at=response["LastModified"],
        url=_public_url(key),
    )


def delete_file(key: str) -> None:
    """Delete an object from B2. Raises RuntimeError on failure."""
    client = get_s3_client()
    try:
        client.delete_object(Bucket=settings.b2_bucket_name, Key=key)
    except ClientError as e:
        raise RuntimeError(f"B2 delete failed for '{key}': {e}") from e


def delete_files_batch(keys: list[str]) -> tuple[list[str], list[dict]]:
    """Delete multiple objects in a single S3 DeleteObjects call.

    Returns `(deleted_keys, errors)` where `errors` is a list of
    `{"Key": str, "Code": str, "Message": str}` dicts for objects S3 refused
    to delete. The API permits up to 1000 keys per request — callers must
    chunk above that. An empty input list returns two empty lists.

    Raises RuntimeError on a transport-level failure.
    """
    if not keys:
        return [], []
    client = get_s3_client()
    deleted: list[str] = []
    errors: list[dict] = []
    # S3 DeleteObjects caps at 1000 entries per call; chunk defensively.
    for i in range(0, len(keys), 1000):
        chunk = keys[i : i + 1000]
        try:
            response = client.delete_objects(
                Bucket=settings.b2_bucket_name,
                Delete={"Objects": [{"Key": k} for k in chunk], "Quiet": False},
            )
        except ClientError as e:
            raise RuntimeError(f"B2 batch delete failed: {e}") from e
        deleted.extend(d["Key"] for d in response.get("Deleted", []))
        for err in response.get("Errors", []):
            errors.append(
                {
                    "Key": err.get("Key", ""),
                    "Code": err.get("Code", ""),
                    "Message": err.get("Message", ""),
                }
            )
    return deleted, errors


def get_presigned_url(
    key: str, filename: str | None = None, expires_in: int = 600
) -> str:
    """Generate a presigned download URL. Raises RuntimeError on failure."""
    client = get_s3_client()
    params: dict = {"Bucket": settings.b2_bucket_name, "Key": key}
    if filename:
        # RFC 5987 encoding for non-ASCII filenames
        encoded = quote(filename, safe="")
        params["ResponseContentDisposition"] = (
            f"attachment; filename=\"{encoded}\"; filename*=UTF-8''{encoded}"
        )
    else:
        params["ResponseContentDisposition"] = "attachment"
    try:
        return client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 presign failed for '{key}': {e}") from e


def get_upload_stats() -> dict:
    """Paginate through all objects and return aggregate stats.

    Raises RuntimeError on S3 failure.
    """
    client = get_s3_client()
    contents: list[dict] = []
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "MaxKeys": 1000}
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            contents.extend(response.get("Contents", []))
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 stats query failed: {e}") from e

    total_size = sum(obj["Size"] for obj in contents)
    today = datetime.now(UTC).date()
    uploads_today = sum(
        1 for obj in contents if obj["LastModified"].date() == today
    )
    return {
        "total_files": len(contents),
        "total_size_bytes": total_size,
        "total_size_human": humanize_bytes(total_size),
        "uploads_today": uploads_today,
    }


# Audio Library helpers live in `b2_tracks.py` and are re-exported via
# `app.repo.__init__`. Keeping them in their own module lets the generic
# helpers above stay focused on the full-bucket explorer.

"""B2 helpers scoped to the music-studio `projects/` prefix.

Canonical key layout (kept stable as an architectural invariant — see
AGENTS.md §2):

  projects/<project-id>/project.json
  projects/<project-id>/tracks/<track-id>/audio.<ext>
  projects/<project-id>/tracks/<track-id>/track.json
  projects/<project-id>/tracks/<track-id>/stems/<stem-name>.wav
  projects/<project-id>/reference/<safe-filename>

Service code calls these helpers; raw boto3 stays in repo/.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from botocore.exceptions import ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client

PROJECTS_PREFIX = "projects/"


def _bucket() -> str:
    return settings.b2_bucket_name


def put_json(key: str, payload: dict, metadata: dict[str, str] | None = None) -> None:
    """Write a JSON document to B2.

    Used for `project.json` and per-track `track.json` sidecars. The value
    is serialized with `json.dumps(sort_keys=True)` so manifests round-trip
    deterministically when compared/diffed offline.
    """
    body = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    client = get_s3_client()
    params: dict = {
        "Bucket": _bucket(),
        "Key": key,
        "Body": body,
        "ContentType": "application/json",
    }
    if metadata:
        params["Metadata"] = metadata
    try:
        client.put_object(**params)
    except ClientError as e:
        raise RuntimeError(f"B2 put_json failed for '{key}': {e}") from e


def get_json(key: str) -> dict | None:
    """Read a JSON document from B2. Returns None if missing."""
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=_bucket(), Key=key)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise RuntimeError(f"B2 get_json failed for '{key}': {e}") from e
    body = response["Body"].read()
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"B2 get_json: invalid JSON at '{key}': {e}") from e


def list_project_keys(prefix: str, max_keys: int = 1000) -> list[dict]:
    """List raw S3 objects under a project-scoped prefix.

    Returned dicts contain at least: Key, Size, LastModified — matching
    the shape returned by `list_audio_objects`.
    """
    if not prefix.startswith(PROJECTS_PREFIX):
        raise ValueError("list_project_keys requires a `projects/...` prefix")
    client = get_s3_client()
    contents: list[dict] = []
    kwargs: dict = {"Bucket": _bucket(), "Prefix": prefix, "MaxKeys": max_keys}
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            contents.extend(response.get("Contents", []))
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 list under '{prefix}' failed: {e}") from e
    return contents


def list_project_root_prefixes() -> list[str]:
    """Return the immediate child prefixes under `projects/` (one per project).

    Uses `Delimiter="/"` so we get the project IDs without listing every
    descendant object. Cheap and bounded.
    """
    client = get_s3_client()
    prefixes: list[str] = []
    kwargs: dict = {
        "Bucket": _bucket(),
        "Prefix": PROJECTS_PREFIX,
        "Delimiter": "/",
        "MaxKeys": 1000,
    }
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            for cp in response.get("CommonPrefixes", []) or []:
                p = cp.get("Prefix")
                if p:
                    prefixes.append(p)
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 list project prefixes failed: {e}") from e
    return prefixes


def delete_project_tree(project_id: str) -> tuple[list[str], list[dict]]:
    """Delete every object under `projects/<project-id>/`.

    Lists the whole subtree and calls `DeleteObjects` in chunks of 1000.
    Returns `(deleted_keys, errors)` so callers can surface partial
    failures. Used by archive/delete flows.
    """
    prefix = f"{PROJECTS_PREFIX}{project_id}/"
    objects = list_project_keys(prefix, max_keys=10_000)
    keys = [o["Key"] for o in objects]
    if not keys:
        return [], []
    client = get_s3_client()
    deleted: list[str] = []
    errors: list[dict] = []
    for i in range(0, len(keys), 1000):
        chunk = keys[i : i + 1000]
        try:
            response = client.delete_objects(
                Bucket=_bucket(),
                Delete={"Objects": [{"Key": k} for k in chunk], "Quiet": False},
            )
        except ClientError as e:
            raise RuntimeError(f"B2 project delete failed: {e}") from e
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


def presign_track_playback(key: str, expires_in: int = 600) -> str:
    """Inline-playback presigned GET for a project-scoped track or stem.

    Mirrors `presign_audio_playback`; lives here so callers in the
    music-studio service layer never have to reach across to the
    library-flavored module.
    """
    client = get_s3_client()
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": _bucket(), "Key": key},
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 track presign failed for '{key}': {e}") from e


def head_keys_parallel(keys: list[str], max_workers: int = 10) -> dict[str, dict]:
    """HEAD a list of keys in parallel; map key -> head response.

    Mirror of `head_track_objects_parallel` but lives in this module so
    project-scoped callers don't have to import from the audio-flavored
    helper. Missing keys (404) are silently dropped.
    """
    if not keys:
        return {}
    client = get_s3_client()
    bucket = _bucket()

    def _one(key: str) -> tuple[str, dict | None]:
        try:
            return key, client.head_object(Bucket=bucket, Key=key)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchKey"):
                return key, None
            raise

    out: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for key, head in pool.map(_one, keys):
            if head is not None:
                out[key] = head
    return out

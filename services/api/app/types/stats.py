from pydantic import BaseModel


class DailyUploadCount(BaseModel):
    date: str
    uploads: int
    duration_ms: int = 0


class UploadStats(BaseModel):
    """Audio-aware dashboard metrics.

    Mirrors the shape consumed by `apps/web/src/components/dashboard/*`.
    `total_files` / `total_size_*` cover everything in the bucket so the
    underlying explorer keeps working; the audio-specific aggregates surface
    the metrics the dashboard tiles actually render. `formats` is a sparse
    map of extension -> count (e.g. {"wav": 5, "mp3": 12}).
    """

    total_files: int
    total_size_bytes: int
    total_size_human: str
    uploads_today: int
    total_downloads: int
    # Audio-aware aggregates
    total_audio_assets: int
    total_duration_ms: int
    audio_size_bytes: int = 0
    audio_size_human: str = "0 B"
    formats: dict[str, int] = {}

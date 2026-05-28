"""Small token-bucket rate limiter for costly generation requests."""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock

from app.config import settings


@dataclass
class _Bucket:
    tokens: float
    updated_at: float


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__("Rate limit exceeded")


_lock = Lock()
_buckets: dict[str, _Bucket] = {}


def check_generation_rate_limit(client_id: str) -> None:
    capacity = max(1, settings.generation_rate_limit_capacity)
    window = max(1, settings.generation_rate_limit_window_sec)
    refill_per_sec = capacity / window
    now = time.monotonic()
    with _lock:
        bucket = _buckets.get(client_id)
        if bucket is None:
            _buckets[client_id] = _Bucket(tokens=capacity - 1, updated_at=now)
            return
        elapsed = now - bucket.updated_at
        bucket.tokens = min(capacity, bucket.tokens + elapsed * refill_per_sec)
        bucket.updated_at = now
        if bucket.tokens >= 1:
            bucket.tokens -= 1
            return
        retry_after = max(1, round((1 - bucket.tokens) / refill_per_sec))
        raise RateLimitExceeded(retry_after)

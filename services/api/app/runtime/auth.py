"""Optional bearer-token auth for shared deployments."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException

from app.config import settings


@dataclass(frozen=True)
class UserContext:
    user_id: str


async def require_user(
    authorization: str | None = Header(default=None),
    x_studio_user: str | None = Header(default=None),
) -> UserContext:
    if settings.studio_auth_token:
        expected = f"Bearer {settings.studio_auth_token}"
        if authorization != expected:
            raise HTTPException(status_code=401, detail="Not authorized")
    user_id = (x_studio_user or settings.studio_default_owner_id).strip() or "local"
    return UserContext(user_id=user_id)

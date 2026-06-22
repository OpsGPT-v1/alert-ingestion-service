import logging
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)


async def validate_project_webhook(project_id: str, webhook_token: str) -> dict[str, Any]:
    url = f"{settings.core_api_url.rstrip('/')}/internal/projects/{project_id}/monitoring-sources/validate"
    headers = {"X-Internal-API-Key": settings.internal_api_key}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(url, params={"token": webhook_token}, headers=headers)
    except Exception as exc:
        logger.warning("Core API webhook validation failed: %s", exc.__class__.__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not validate project webhook token",
        ) from exc

    if response.status_code == 401:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid project webhook token")
    if response.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Core API validation failed")
    return response.json()

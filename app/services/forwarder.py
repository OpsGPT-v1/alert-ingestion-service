import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def forward_alerts_to_analysis(alerts: list[dict[str, Any]]) -> tuple[int, int]:
    if not alerts:
        return 0, 0

    url = f"{settings.ai_analysis_service_url.rstrip('/')}/analysis/alerts"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json={"alerts": alerts})
            response.raise_for_status()
            data = response.json()
            return int(data.get("processed_count", len(alerts))), int(data.get("failed_count", 0))
    except Exception as exc:
        logger.warning("Forwarding to AI Analysis failed: %s", exc.__class__.__name__)
        return 0, len(alerts)

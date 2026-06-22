from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class NormalizedAlertRead(BaseModel):
    id: int
    alert_id: str
    project_id: str | None
    source: str
    source_type: str
    service_name: str
    alert_name: str
    alert_type: str
    severity: str
    message: str
    description: str | None
    environment: str
    namespace: str | None
    cluster: str | None
    pod: str | None
    deployment: str | None
    instance: str | None
    job: str | None
    status: str
    starts_at: datetime | None
    ends_at: datetime | None
    generator_url: str | None
    fingerprint: str | None
    labels: dict[str, Any]
    annotations: dict[str, Any]
    raw_alert: dict[str, Any]
    forwarding_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertWebhookResponse(BaseModel):
    status: str
    source: str
    project_id: str | None
    received_alert_count: int
    normalized_alert_count: int
    forwarding_enabled: bool
    forwarded_count: int
    failed_forward_count: int

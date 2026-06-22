import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.models import AlertIngestionLog, NormalizedAlert, RawAlert
from app.schemas.schemas import AlertWebhookResponse, NormalizedAlertRead
from app.services.core_client import validate_project_webhook
from app.services.forwarder import forward_alerts_to_analysis
from app.services.normalizer import normalize_alert

router = APIRouter(tags=["alerts"])


def extract_alerts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    alerts = payload.get("alerts")
    if not isinstance(alerts, list) or not alerts:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Alertmanager payload alerts[] is required")
    return [item if isinstance(item, dict) else {"raw_value": item} for item in alerts]


async def process_alertmanager_payload(
    payload: dict[str, Any],
    db: Session,
    project_id: str | None = None,
    validate_project: bool = False,
    webhook_token: str | None = None,
) -> AlertWebhookResponse:
    if validate_project:
        if not project_id or not webhook_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project webhook path is incomplete")
        await validate_project_webhook(project_id, webhook_token)

    alerts = extract_alerts(payload)
    payload_id = f"PAY-{uuid.uuid4().hex[:12].upper()}"
    raw_record = RawAlert(
        payload_id=payload_id,
        project_id=project_id,
        source="prometheus_alertmanager",
        raw_payload=payload,
    )
    db.add(raw_record)

    normalized_records: list[NormalizedAlert] = []
    for raw_alert in alerts:
        normalized = normalize_alert(raw_alert, project_id)
        record = NormalizedAlert(**normalized)
        normalized_records.append(record)
        db.add(record)
        db.add(
            AlertIngestionLog(
                alert_id=record.alert_id,
                project_id=project_id,
                event_type="alert_normalized",
                message=f"Normalized {record.alert_name} for {record.service_name}",
            )
        )
    db.commit()
    for record in normalized_records:
        db.refresh(record)

    forwarded_count = 0
    failed_forward_count = 0
    if settings.enable_analysis_forwarding:
        outbound = [NormalizedAlertRead.model_validate(record).model_dump(mode="json") for record in normalized_records]
        forwarded_count, failed_forward_count = await forward_alerts_to_analysis(outbound)
        forwarding_status = "forwarded" if failed_forward_count == 0 else "failed"
    else:
        forwarding_status = "skipped"

    for record in normalized_records:
        record.forwarding_status = forwarding_status
    db.commit()

    return AlertWebhookResponse(
        status="processed",
        source="prometheus_alertmanager",
        project_id=project_id,
        received_alert_count=len(alerts),
        normalized_alert_count=len(normalized_records),
        forwarding_enabled=settings.enable_analysis_forwarding,
        forwarded_count=forwarded_count,
        failed_forward_count=failed_forward_count,
    )


@router.post("/alerts/webhook/project/{project_id}/{webhook_token}", response_model=AlertWebhookResponse)
async def project_alertmanager_webhook(
    project_id: str,
    webhook_token: str,
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
) -> AlertWebhookResponse:
    return await process_alertmanager_payload(
        payload,
        db,
        project_id=project_id,
        validate_project=True,
        webhook_token=webhook_token,
    )


@router.post("/alerts/webhook/prometheus-alertmanager", response_model=AlertWebhookResponse)
async def prometheus_alertmanager_webhook(
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
) -> AlertWebhookResponse:
    return await process_alertmanager_payload(payload, db)


@router.post("/alerts/manual", response_model=AlertWebhookResponse)
async def manual_alert(
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
) -> AlertWebhookResponse:
    return await process_alertmanager_payload(payload, db)


@router.post("/alerts/webhook/grafana", status_code=status.HTTP_410_GONE)
def deprecated_grafana_webhook() -> dict:
    return {"status": "deprecated", "message": "Grafana webhooks are not supported in Phase 1"}


@router.post("/alerts/webhook/azure-monitor", status_code=status.HTTP_410_GONE)
def deprecated_azure_monitor_webhook() -> dict:
    return {"status": "deprecated", "message": "Azure Monitor webhooks are not supported in Phase 1"}

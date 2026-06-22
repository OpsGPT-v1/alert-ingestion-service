from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RawAlert(Base):
    __tablename__ = "alert_raw_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    source: Mapped[str] = mapped_column(String(80), default="prometheus_alertmanager", nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class NormalizedAlert(Base):
    __tablename__ = "alert_normalized_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    source: Mapped[str] = mapped_column(String(80), default="prometheus_alertmanager", nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), default="prometheus_alertmanager", nullable=False)
    service_name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    alert_name: Mapped[str] = mapped_column(String(200), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    environment: Mapped[str] = mapped_column(String(80), nullable=False)
    namespace: Mapped[str | None] = mapped_column(String(160), nullable=True)
    cluster: Mapped[str | None] = mapped_column(String(160), nullable=True)
    pod: Mapped[str | None] = mapped_column(String(200), nullable=True)
    deployment: Mapped[str | None] = mapped_column(String(200), nullable=True)
    instance: Mapped[str | None] = mapped_column(String(200), nullable=True)
    job: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generator_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    fingerprint: Mapped[str | None] = mapped_column(String(200), nullable=True)
    labels: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    annotations: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    raw_alert: Mapped[dict] = mapped_column(JSONB, nullable=False)
    forwarding_status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class AlertIngestionLog(Base):
    __tablename__ = "alert_ingestion_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

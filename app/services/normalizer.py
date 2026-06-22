import uuid
from datetime import datetime
from typing import Any


def parse_datetime(value: Any) -> datetime | None:
    if not value or not isinstance(value, str) or value.startswith("0001-01-01"):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def first_label(labels: dict[str, Any], keys: list[str], default: str) -> str:
    for key in keys:
        value = labels.get(key)
        if value:
            return str(value)
    return default


def normalize_severity(raw_value: Any, status: str) -> str:
    value = str(raw_value or status or "").lower()
    if value in {"critical", "high", "page", "p0", "p1", "sev0", "sev1"}:
        return "critical"
    if value in {"warning", "warn", "medium", "p2", "sev2", "sev3"}:
        return "warning"
    if value in {"info", "informational", "low", "p3", "p4", "sev4", "resolved"}:
        return "informational"
    return "warning"


def infer_alert_type(alert_name: str, message: str, description: str | None, labels: dict[str, Any]) -> str:
    haystack = " ".join(
        [
            alert_name,
            message,
            description or "",
            " ".join(str(value) for value in labels.values()),
        ]
    ).lower()
    rules = [
        (("cpu", "throttle", "load"), "cpu"),
        (("memory", "oom"), "memory"),
        (("latency", "duration", "slow", "p95", "p99"), "api_latency"),
        (("db", "database", "postgres", "mysql", "sql", "connection"), "database"),
        (("500", "error", "exception", "errorrate"), "application_error"),
        (("pod", "container", "kubernetes", "k8s", "crashloop", "restart"), "kubernetes"),
        (("down", "unavailable", "healthcheck", "uptime"), "availability"),
        (("network", "dns", "tcp", "packet"), "network"),
        (("disk", "filesystem", "storage"), "disk"),
    ]
    for keywords, alert_type in rules:
        if any(keyword in haystack for keyword in keywords):
            return alert_type
    return "custom"


def normalize_alert(raw_alert: dict[str, Any], project_id: str | None) -> dict[str, Any]:
    labels = raw_alert.get("labels") if isinstance(raw_alert.get("labels"), dict) else {}
    annotations = raw_alert.get("annotations") if isinstance(raw_alert.get("annotations"), dict) else {}
    status = str(raw_alert.get("status") or "firing").lower()
    alert_name = str(labels.get("alertname") or "UnknownAlert")
    message = str(annotations.get("summary") or labels.get("alertname") or "Prometheus alert received")
    description = annotations.get("description")
    fingerprint = raw_alert.get("fingerprint")

    return {
        "alert_id": str(fingerprint or f"ALT-{uuid.uuid4().hex[:12].upper()}"),
        "project_id": project_id,
        "source": "prometheus_alertmanager",
        "source_type": "prometheus_alertmanager",
        "service_name": first_label(labels, ["service", "app", "application", "deployment", "job"], "unknown-service"),
        "alert_name": alert_name,
        "alert_type": infer_alert_type(alert_name, message, description, labels),
        "severity": normalize_severity(labels.get("severity"), status),
        "message": message,
        "description": description,
        "environment": first_label(labels, ["environment", "env", "namespace"], "production"),
        "namespace": labels.get("namespace"),
        "cluster": labels.get("cluster"),
        "pod": labels.get("pod"),
        "deployment": labels.get("deployment"),
        "instance": labels.get("instance"),
        "job": labels.get("job"),
        "status": status if status in {"firing", "resolved"} else "firing",
        "starts_at": parse_datetime(raw_alert.get("startsAt")),
        "ends_at": parse_datetime(raw_alert.get("endsAt")),
        "generator_url": raw_alert.get("generatorURL"),
        "fingerprint": str(fingerprint) if fingerprint else None,
        "labels": labels,
        "annotations": annotations,
        "raw_alert": raw_alert,
        "forwarding_status": "pending",
    }

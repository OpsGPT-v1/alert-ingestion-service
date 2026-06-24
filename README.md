# OpsGPT Alert Ingestion Service

The **Alert Ingestion Service** is the ingestion gateway of the OpsGPT incident management pipeline. It handles incoming webhook alerts from monitoring tools (primarily Prometheus Alertmanager), normalizes divergent payloads into a standardized relational schema, logs raw alert content, and forwards normalized events to the downstream AI analysis correlation service.

---

## Architecture Flow

```mermaid
graph LR
    Prometheus[Prometheus Alertmanager] -->|1. Webhook Post| Ingestion[Alert Ingestion Service]
    Ingestion -->|2. Validate Project Key| Core[Core API Service]
    Ingestion -->|3. Persist Logs & Alerts| DB[(PostgreSQL Database)]
    Ingestion -->|4. Forward if enabled| AI[AI Analysis Service]
```

---

## Normalization Engine Details

Monitoring tools export alerts with varying structures. The ingestion service automatically parses raw payloads and maps them to standard schema properties using the following rules:

### 1. Label Extraction & Precedence

*   **Service Name (`service_name`)**: Extracted from labels by scanning the following keys in order:
    1. `service`
    2. `app`
    3. `application`
    4. `deployment`
    5. `job`
    *Fallback: `unknown-service`*
*   **Environment (`environment`)**: Extracted from labels by scanning:
    1. `environment`
    2. `env`
    3. `namespace`
    *Fallback: `production`*
*   **Infrastructure Fields**: Directly maps `namespace`, `cluster`, `pod`, `deployment`, `instance`, and `job` if they exist in the raw labels dictionary.

### 2. Severity Classification

The engine maps custom alert levels to three standard severities (`critical`, `warning`, `informational`):

| Internal Severity | Matches (Raw Label / Alert Status) |
| :--- | :--- |
| **`critical`** | `critical`, `high`, `page`, `p0`, `p1`, `sev0`, `sev1` |
| **`warning`** | `warning`, `warn`, `medium`, `p2`, `sev2`, `sev3` |
| **`informational`** | `info`, `informational`, `low`, `p3`, `p4`, `sev4`, `resolved` |

### 3. Alert Type Inference (`alert_type`)

The service inspects alert names, messages, descriptions, and labels for key phrases to classify the alert type:

| Inferred Type | Scanning Keywords |
| :--- | :--- |
| `cpu` | `cpu`, `throttle`, `load` |
| `memory` | `memory`, `oom` |
| `api_latency` | `latency`, `duration`, `slow`, `p95`, `p99` |
| `database` | `db`, `database`, `postgres`, `mysql`, `sql`, `connection` |
| `application_error` | `500`, `error`, `exception`, `errorrate` |
| `kubernetes` | `pod`, `container`, `kubernetes`, `k8s`, `crashloop`, `restart` |
| `availability` | `down`, `unavailable`, `healthcheck`, `uptime` |
| `network` | `network`, `dns`, `tcp`, `packet` |
| `disk` | `disk`, `filesystem`, `storage` |
| *`custom`* | *Matches if no criteria above is met.* |

---

## API Endpoints Reference

All endpoints are exposed under `/api/*` or the root path.

### 1. Ingestion Routes (`/alerts`)

| Method | Path | Auth | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/alerts/webhook/project/{project_id}/{webhook_token}` | Custom | **Project-Specific Webhook**. Validates the token against the Core API service database. Normalizes all items in the `alerts` payload. |
| `POST` | `/alerts/webhook/prometheus-alertmanager` | None | **Default Global Webhook**. Processes Prometheus payloads without verifying project tokens. |
| `POST` | `/alerts/manual` | None | **Manual API Entrypoint**. Allows developer/mock ingestion for test suites. |
| `POST` | `/alerts/webhook/grafana` | None | **Deprecated (410 GONE)**. |
| `POST` | `/alerts/webhook/azure-monitor` | None | **Deprecated (410 GONE)**. |

---

## Webhook Payload Compatibility

The service is natively compatible with standard Prometheus Alertmanager webhooks. Payloads must contain an `alerts` list containing JSON dictionaries.

### Sample Prometheus Webhook Payload

```json
{
  "receiver": "opsgpt-webhook",
  "status": "firing",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "HighMemoryUsage",
        "severity": "critical",
        "service": "billing-service",
        "namespace": "prod",
        "pod": "billing-pod-89a1"
      },
      "annotations": {
        "summary": "Pod billing-pod-89a1 is using 94% memory",
        "description": "Kubernetes OOM killer risk."
      },
      "startsAt": "2026-06-24T18:00:00Z",
      "generatorURL": "http://prometheus:9090",
      "fingerprint": "a3b4c5d6e7f8"
    }
  ]
}
```

---

## Downstream Forwarding Mechanism

Once alerts are normalized and committed to the database, they are forwarded to the **AI Analysis Service** at `/api/analysis/alerts` via a POST request containing JSON-serialized alert lists.
*   **Toggle Control**: Forwarding is controlled by the `ENABLE_ANALYSIS_FORWARDING` setting. If disabled, alerts are committed to the DB with status `skipped` instead of `forwarded`.

---

## Key Configurations & Environment Variables

| Environment Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://opsgpt_user:opsgpt_password@opsgpt-db:5432/opsgpt_db` | Connection string to PostgreSQL database. |
| `AI_ANALYSIS_SERVICE_URL` | `http://ai-analysis-service:8003` | Destination endpoint for the correlation engine. |
| `CORE_API_URL` | `http://core-api-service:8001` | Connection endpoint for validation calls. |
| `INTERNAL_API_KEY` | `change-me-internal-key` | Secret key used to authorize internal validation requests. |
| `ENABLE_ANALYSIS_FORWARDING` | `True` | Flag to enable or disable correlation routing. |
| `CORS_ORIGINS` | `*` | Allowed CORS origins list. |
| `DB_INIT_MAX_ATTEMPTS` | `30` | Number of times to check database connection on startup. |
| `DB_INIT_DELAY_SECONDS` | `2` | Delay between database connection checks. |

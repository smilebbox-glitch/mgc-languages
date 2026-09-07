# Observability v5.7

OpenTelemetry is optional and disabled by default. Enable with `OTEL_ENABLED=true` and set an approved `OTEL_EXPORTER_OTLP_ENDPOINT`. Failure to initialize/export telemetry must not stop the application.

Pinned Python packages for this release: OpenTelemetry SDK/OTLP 1.44.0 and FastAPI/SQLAlchemy instrumentation 0.65b0. Instrumentation packages are beta, so pilot validation is required before making traces an operational dependency.

Included artifacts:
- `deploy/observability/otel-collector.yaml`
- `deploy/observability/grafana-dashboard-v5.7.json`
- `deploy/observability/prometheus-rules-v5.7.yml`

Central Prometheus/SIEM/trace backend remains an IT integration responsibility.

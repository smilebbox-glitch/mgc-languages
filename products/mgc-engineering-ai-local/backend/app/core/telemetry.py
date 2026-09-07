from app.core.config import get_settings


def setup_telemetry(app) -> None:
    cfg = get_settings()
    if not cfg.otel_exporter_otlp_endpoint:
        return
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": "mgc-engineering-ai-api"}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=cfg.otel_exporter_otlp_endpoint.rstrip("/") + "/v1/traces")))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)

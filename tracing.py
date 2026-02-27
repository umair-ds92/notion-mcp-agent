"""
tracing.py — OpenTelemetry distributed tracing setup.

Instruments FastAPI and outbound HTTP calls automatically.
Exports traces to an OTLP endpoint (e.g. Jaeger, Grafana Tempo,
Datadog, or any OTel-compatible backend).

If OTEL_ENABLED is False (default), this module is a no-op —
tracing is completely optional and adds zero overhead when disabled.

Usage:
    Call setup_tracing() once at application startup, before the
    FastAPI app is created.

Environment variables:
    OTEL_ENABLED          — set to "true" to enable (default: false)
    OTEL_SERVICE_NAME     — service name in traces (default: notion-mcp-agent)
    OTEL_EXPORTER_ENDPOINT— OTLP gRPC endpoint (default: http://localhost:4317)
"""

import config
from logger import get_logger

log = get_logger(__name__)


def setup_tracing(app=None) -> None:
    """
    Initialise OpenTelemetry tracing.
    Pass the FastAPI app instance to auto-instrument all routes.
    Safe to call even when tracing is disabled.
    """
    if not config.OTEL_ENABLED:
        log.info("tracing_disabled")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        resource = Resource.create({"service.name": config.OTEL_SERVICE_NAME})
        provider = TracerProvider(resource=resource)

        exporter = OTLPSpanExporter(endpoint=config.OTEL_EXPORTER_ENDPOINT)
        provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)

        # Auto-instrument FastAPI routes
        if app is not None:
            FastAPIInstrumentor.instrument_app(app)

        # Auto-instrument outbound HTTP calls (used by OpenAI client)
        HTTPXClientInstrumentor().instrument()

        log.info("tracing_enabled", extra={
            "service": config.OTEL_SERVICE_NAME,
            "endpoint": config.OTEL_EXPORTER_ENDPOINT,
        })

    except ImportError:
        log.warning("tracing_deps_missing", extra={
            "hint": "Run: pip install opentelemetry-sdk opentelemetry-exporter-otlp "
                    "opentelemetry-instrumentation-fastapi opentelemetry-instrumentation-httpx"
        })
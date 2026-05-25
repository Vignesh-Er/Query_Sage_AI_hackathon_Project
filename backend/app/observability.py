import logging
from contextlib import contextmanager
from opentelemetry import trace
from opentelemetry.trace import SpanKind
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from app.config import settings

logger = logging.getLogger(__name__)

def setup_telemetry(app_name: str):
    """
    Sets up OpenTelemetry TracerProvider with OTLPSpanExporter.
    Fails silently and defaults to standard no-op provider if collector is offline.
    """
    try:
        endpoint = getattr(settings, "QUERYSAGE_OTLP_ENDPOINT", "http://localhost:4317")
        exporter = OTLPSpanExporter(endpoint=endpoint, timeout=2)
        processor = BatchSpanProcessor(exporter)
        provider = TracerProvider()
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        return trace.get_tracer(app_name)
    except Exception as e:
        logger.warning(f"Telemetry unavailable: {str(e)}")
        return trace.get_tracer(app_name)

@contextmanager
def instrument_pipeline_stage(tracer, stage_name: str, query_fingerprint: str, db_system: str):
    """
    Context manager to trace individual pipeline stages with stable DB semantic conventions.
    """
    try:
        with tracer.start_as_current_span(stage_name, kind=SpanKind.INTERNAL) as span:
            span.set_attribute("db.system.name", db_system)
            span.set_attribute("db.operation.name", stage_name)
            span.set_attribute("querysage.query.fingerprint", query_fingerprint)
            yield span
    except Exception:
        yield None

def record_finding_event(span, finding: dict):
    """
    Records a QuerySage rule violation finding event in the current span.
    """
    try:
        if span:
            severity_val = finding.get("severity", 0)
            if isinstance(severity_val, int):
                severity_str = str(severity_val)
            else:
                severity_str = severity_val

            span.add_event(
                "querysage.finding",
                attributes={
                    "rule_id": finding.get("rule_id", ""),
                    "severity": severity_str,
                    "category": finding.get("category", "")
                }
            )
    except Exception:
        pass

def record_regression_event(span, regression: dict):
    """
    Records a QuerySage cost regression event in the current span.
    """
    try:
        if span:
            span.add_event(
                "querysage.regression",
                attributes={
                    "cost_delta_percent": regression.get("cost_delta_percent", regression.get("delta_percent", 0.0)),
                    "regression_type": regression.get("regression_type", "")
                }
            )
    except Exception:
        pass

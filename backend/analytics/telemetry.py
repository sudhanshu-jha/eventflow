"""
OpenTelemetry configuration and instrumentation for the EventFlow backend.

This module provides complete observability setup including:
- Distributed tracing
- Metrics collection
- Log correlation
- Auto-instrumentation for Pyramid, SQLAlchemy, Celery, Redis, and requests
"""

import os
import logging
from functools import wraps

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_NAMESPACE, DEPLOYMENT_ENVIRONMENT
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator

# Instrumentation imports
from opentelemetry.instrumentation.wsgi import OpenTelemetryMiddleware
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

logger = logging.getLogger(__name__)

# Global variables to track initialization state
_tracer_provider = None
_meter_provider = None
_is_initialized = False


def get_resource() -> Resource:
    """Create OpenTelemetry resource with service information."""
    service_name = os.environ.get('OTEL_SERVICE_NAME', 'eventflow-backend')
    service_namespace = os.environ.get('OTEL_SERVICE_NAMESPACE', 'eventflow')
    deployment_env = os.environ.get('OTEL_DEPLOYMENT_ENVIRONMENT', 'development')
    
    return Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_NAMESPACE: service_namespace,
        DEPLOYMENT_ENVIRONMENT: deployment_env,
        "service.version": "1.0.0",
    })


def setup_tracing() -> TracerProvider:
    """Configure and setup distributed tracing."""
    global _tracer_provider
    
    if _tracer_provider is not None:
        return _tracer_provider
    
    resource = get_resource()
    _tracer_provider = TracerProvider(resource=resource)
    
    # Configure OTLP exporter
    otlp_endpoint = os.environ.get('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://localhost:4317')
    
    try:
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=True,
        )
        span_processor = BatchSpanProcessor(otlp_exporter)
        _tracer_provider.add_span_processor(span_processor)
        logger.info(f"OTLP trace exporter configured to {otlp_endpoint}")
    except Exception as e:
        logger.warning(f"Failed to configure OTLP trace exporter: {e}")
    
    # Set the global tracer provider
    trace.set_tracer_provider(_tracer_provider)
    
    return _tracer_provider


def setup_metrics() -> MeterProvider:
    """Configure and setup metrics collection."""
    global _meter_provider
    
    if _meter_provider is not None:
        return _meter_provider
    
    resource = get_resource()
    otlp_endpoint = os.environ.get('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://localhost:4317')
    
    try:
        otlp_exporter = OTLPMetricExporter(
            endpoint=otlp_endpoint,
            insecure=True,
        )
        metric_reader = PeriodicExportingMetricReader(
            otlp_exporter,
            export_interval_millis=60000,  # Export every 60 seconds
        )
        _meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader],
        )
        metrics.set_meter_provider(_meter_provider)
        logger.info(f"OTLP metrics exporter configured to {otlp_endpoint}")
    except Exception as e:
        logger.warning(f"Failed to configure OTLP metrics exporter: {e}")
        _meter_provider = MeterProvider(resource=resource)
        metrics.set_meter_provider(_meter_provider)
    
    return _meter_provider


def setup_propagation():
    """Configure context propagation for distributed tracing."""
    propagator = CompositePropagator([
        TraceContextTextMapPropagator(),
        W3CBaggagePropagator(),
    ])
    set_global_textmap(propagator)
    logger.info("W3C Trace Context and Baggage propagation configured")


def instrument_sqlalchemy(engine=None):
    """Instrument SQLAlchemy for automatic tracing."""
    try:
        if engine:
            SQLAlchemyInstrumentor().instrument(engine=engine)
        else:
            SQLAlchemyInstrumentor().instrument()
        logger.info("SQLAlchemy instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument SQLAlchemy: {e}")


def instrument_celery():
    """Instrument Celery for automatic tracing."""
    try:
        CeleryInstrumentor().instrument()
        logger.info("Celery instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument Celery: {e}")


def instrument_redis():
    """Instrument Redis for automatic tracing."""
    try:
        RedisInstrumentor().instrument()
        logger.info("Redis instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument Redis: {e}")


def instrument_requests():
    """Instrument requests library for automatic tracing."""
    try:
        RequestsInstrumentor().instrument()
        logger.info("Requests instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument requests: {e}")


def instrument_logging():
    """Instrument logging for trace correlation."""
    try:
        LoggingInstrumentor().instrument(set_logging_format=True)
        logger.info("Logging instrumentation enabled with trace correlation")
    except Exception as e:
        logger.warning(f"Failed to instrument logging: {e}")


def get_wsgi_middleware(app):
    """Wrap WSGI application with OpenTelemetry middleware."""
    return OpenTelemetryMiddleware(app)


def init_telemetry(engine=None, enable_celery=False):
    """
    Initialize all OpenTelemetry components.
    
    Args:
        engine: SQLAlchemy engine to instrument (optional)
        enable_celery: Whether to enable Celery instrumentation
    
    Returns:
        Tuple of (tracer_provider, meter_provider)
    """
    global _is_initialized
    
    if _is_initialized:
        logger.debug("Telemetry already initialized, skipping")
        return _tracer_provider, _meter_provider
    
    logger.info("Initializing OpenTelemetry...")
    
    # Setup core components
    setup_propagation()
    tracer_provider = setup_tracing()
    meter_provider = setup_metrics()
    
    # Setup auto-instrumentation
    instrument_sqlalchemy(engine)
    instrument_redis()
    instrument_requests()
    instrument_logging()
    
    if enable_celery:
        instrument_celery()
    
    _is_initialized = True
    logger.info("OpenTelemetry initialization complete")
    
    return tracer_provider, meter_provider


def get_tracer(name: str = __name__):
    """Get a tracer instance for manual instrumentation."""
    return trace.get_tracer(name)


def get_meter(name: str = __name__):
    """Get a meter instance for custom metrics."""
    return metrics.get_meter(name)


# Convenience decorators for manual instrumentation
def traced(name: str = None, attributes: dict = None):
    """
    Decorator to trace a function.
    
    Usage:
        @traced("my_operation")
        def my_function():
            pass
    """
    def decorator(func):
        span_name = name or func.__name__
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer(func.__module__)
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.set_status(trace.StatusCode.ERROR, str(e))
                    span.record_exception(e)
                    raise
        return wrapper
    return decorator


# Custom metrics for EventFlow
class EventFlowMetrics:
    """Custom metrics for EventFlow application."""
    
    def __init__(self):
        meter = get_meter("eventflow")
        
        # Request metrics
        self.request_counter = meter.create_counter(
            name="eventflow.requests.total",
            description="Total number of requests",
            unit="1",
        )
        
        self.request_duration = meter.create_histogram(
            name="eventflow.requests.duration",
            description="Request duration in milliseconds",
            unit="ms",
        )
        
        # Event metrics
        self.events_processed = meter.create_counter(
            name="eventflow.events.processed",
            description="Total number of events processed",
            unit="1",
        )
        
        self.events_failed = meter.create_counter(
            name="eventflow.events.failed",
            description="Total number of failed event processing",
            unit="1",
        )
        
        # User metrics
        self.active_users = meter.create_up_down_counter(
            name="eventflow.users.active",
            description="Number of active users",
            unit="1",
        )
    
    def record_request(self, method: str, endpoint: str, status_code: int, duration_ms: float):
        """Record a request metric."""
        attributes = {
            "http.method": method,
            "http.route": endpoint,
            "http.status_code": status_code,
        }
        self.request_counter.add(1, attributes)
        self.request_duration.record(duration_ms, attributes)
    
    def record_event_processed(self, event_type: str, success: bool = True):
        """Record an event processing metric."""
        attributes = {"event.type": event_type}
        if success:
            self.events_processed.add(1, attributes)
        else:
            self.events_failed.add(1, attributes)


# Singleton metrics instance
_eventflow_metrics = None


def get_eventflow_metrics() -> EventFlowMetrics:
    """Get the EventFlow metrics singleton."""
    global _eventflow_metrics
    if _eventflow_metrics is None:
        _eventflow_metrics = EventFlowMetrics()
    return _eventflow_metrics


def shutdown_telemetry():
    """Gracefully shutdown telemetry providers."""
    global _tracer_provider, _meter_provider, _is_initialized
    
    if _tracer_provider:
        _tracer_provider.shutdown()
    if _meter_provider:
        _meter_provider.shutdown()
    
    _is_initialized = False
    logger.info("OpenTelemetry shutdown complete")

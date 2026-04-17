"""OpenTelemetry metrics initialization.

Provides a single meter for the application. When OTEL_EXPORTER_OTLP_ENDPOINT
is not set, the SDK no-ops — no metrics are exported and no errors are raised.
"""
from __future__ import annotations

import logging

from opentelemetry import metrics
from opentelemetry.metrics import Meter

logger = logging.getLogger(__name__)

_provider = None


def init_metrics(service_name: str, endpoint: str | None = None) -> Meter:
    global _provider

    if not endpoint:
        logger.debug("OTEL_EXPORTER_OTLP_ENDPOINT not set — metrics disabled")
        return metrics.get_meter("review_removal_tracker")

    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource

    resource = Resource.create({"service.name": service_name})
    exporter = OTLPMetricExporter(endpoint=endpoint, insecure=True)
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=5000)
    _provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(_provider)

    logger.info("OTel metrics enabled — exporting to %s", endpoint)
    return metrics.get_meter("review_removal_tracker")


def shutdown_metrics() -> None:
    if _provider is not None:
        _provider.shutdown()

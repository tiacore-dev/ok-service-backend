import logging
from unittest.mock import Mock
from uuid import uuid4

from flask import Flask
from prometheus_client import CollectorRegistry

from app import setup_metrics, setup_tracing
from logger import PrometheusHandler


class _CounterSpy:
    def __init__(self) -> None:
        self.labels_calls: list[dict[str, str]] = []
        self.inc_calls = 0

    def labels(self, **labels: str) -> "_CounterSpy":
        self.labels_calls.append(labels)
        return self

    def inc(self) -> None:
        self.inc_calls += 1


def test_prometheus_handler_uses_only_bounded_level_label(monkeypatch, capsys):
    log_counter = _CounterSpy()
    error_counter = _CounterSpy()
    monkeypatch.setattr("logger.log_messages_counter", log_counter)
    monkeypatch.setattr("logger.error_counter", error_counter)

    handler = PrometheusHandler()
    handler.emit(logging.LogRecord("ok_service", logging.WARNING, __file__, 1, "warning", (), None))
    handler.emit(logging.LogRecord("ok_service", logging.ERROR, __file__, 1, "error", (), None))

    assert log_counter.labels_calls == [{"level": "WARNING"}, {"level": "ERROR"}]
    assert log_counter.inc_calls == 2
    assert error_counter.inc_calls == 1
    assert capsys.readouterr().out == ""


def test_metrics_use_route_template_instead_of_uuid_path():
    app = Flask(__name__)
    registry = CollectorRegistry()

    @app.get("/works/<uuid:work_id>")
    def get_work(work_id):
        return {"id": str(work_id)}

    setup_metrics(app, registry=registry)
    client = app.test_client()
    first_work_id = uuid4()
    second_work_id = uuid4()

    client.get(f"/works/{first_work_id}")
    client.get(f"/works/{second_work_id}")
    metrics = registry.collect()
    samples = [
        sample
        for metric in metrics
        for sample in metric.samples
        if sample.name == "flask_http_request_duration_seconds_count"
    ]

    assert len(samples) == 1
    assert samples[0].labels["url_rule"] == "/works/<uuid:work_id>"
    assert str(first_work_id) not in str(samples[0].labels)
    assert str(second_work_id) not in str(samples[0].labels)


def test_setup_logger_disables_root_propagation(monkeypatch, tmp_path):
    monkeypatch.setattr("logger.os.getcwd", lambda: str(tmp_path))
    logger_name = "ok_service.test_logging_metrics"
    app_logger = logging.getLogger(logger_name)
    app_logger.handlers.clear()

    configured_logger = __import__("logger").setup_logger(logger_name)

    try:
        assert configured_logger.propagate is False
        assert sum(isinstance(handler, PrometheusHandler) for handler in configured_logger.handlers) == 1
    finally:
        for handler in configured_logger.handlers:
            handler.close()
        configured_logger.handlers.clear()


def test_setup_logger_uses_info_level_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.setattr("logger.os.getcwd", lambda: str(tmp_path))
    logger_name = "ok_service.test_default_log_level"
    app_logger = logging.getLogger(logger_name)
    app_logger.handlers.clear()

    configured_logger = __import__("logger").setup_logger(logger_name)

    try:
        assert configured_logger.level == logging.INFO
    finally:
        for handler in configured_logger.handlers:
            handler.close()
        configured_logger.handlers.clear()


def test_setup_tracing_uses_configured_otlp_endpoint(monkeypatch):
    app = Flask(__name__)
    app.config.update(
        OTEL_SERVICE_NAME="ok-service-test",
        OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="http://jaeger:4318/v1/traces",
        OTEL_EXPORTER_OTLP_TIMEOUT=7,
    )
    provider = Mock()
    tracer_provider = Mock(return_value=provider)
    exporter = Mock()
    otlp_exporter = Mock(return_value=exporter)
    processor = Mock()
    batch_processor = Mock(return_value=processor)
    instrumentor = Mock()
    flask_instrumentor = Mock(return_value=instrumentor)
    resource = Mock()

    monkeypatch.setattr("app.TracerProvider", tracer_provider)
    monkeypatch.setattr("app.Resource", resource)
    monkeypatch.setattr("app.OTLPSpanExporter", otlp_exporter)
    monkeypatch.setattr("app.BatchSpanProcessor", batch_processor)
    monkeypatch.setattr("app.FlaskInstrumentor", flask_instrumentor)
    setup_tracing(app)

    resource.create.assert_called_once_with({"service.name": "ok-service-test"})
    otlp_exporter.assert_called_once_with(
        endpoint="http://jaeger:4318/v1/traces", timeout=7
    )
    batch_processor.assert_called_once_with(exporter)
    provider.add_span_processor.assert_called_once_with(processor)
    instrumentor.instrument_app.assert_called_once_with(app, tracer_provider=provider)

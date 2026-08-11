import logging
import os

from opentelemetry.trace import Span, get_current_span
from prometheus_client import Counter

error_counter = Counter('flask_errors_total', 'Total number of errors')
log_messages_counter = Counter(
    'log_messages_total',
    'Total number of log messages handled by the application logger',
    ['level'],
)


class LokiFormatter(logging.Formatter):
    def format(self, record):
        # Получим текущий span, если есть
        span: Span = get_current_span()
        trace_id = "unknown"

        if span and span.get_span_context().trace_id:
            trace_id = format(span.get_span_context().trace_id, '032x')

        # Пользовательская информация
        user_info = getattr(record, "login", {})
        if isinstance(user_info, dict):
            user_id = user_info.get("user_id", "unknown")
            login = user_info.get("login", "unknown")
            role = user_info.get("role", "unknown")
        elif isinstance(user_info, str):
            user_id = "system"
            login = user_info
            role = "system"
        else:
            user_id = login = role = "unknown"

        base_msg = super().format(record)
        return f"{base_msg} [trace_id={trace_id} user_id={user_id} login={login} role={role}]"


class PrometheusHandler(logging.Handler):
    def emit(self, record):
        try:
            log_messages_counter.labels(level=record.levelname).inc()
            if record.levelno >= logging.ERROR:
                error_counter.inc()
        except Exception:  # noqa: BLE001 - telemetry failures must not break logging
            self.handleError(record)


class SkipMetricsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.getMessage())
        return "/metrics" not in msg


def setup_logger(name: str = "ok_service", log_file: str = "ok_service.log") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    # The application logger owns its handlers. Propagation to the root logger
    # would format and emit every record a second time (for example, via Gunicorn).
    logger.propagate = False

    formatter = LokiFormatter("%(asctime)s %(levelname)s: %(message)s")
    skip_metrics_filter = SkipMetricsFilter()

    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.addFilter(skip_metrics_filter)
        logger.addHandler(console_handler)

    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)

    if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.addFilter(skip_metrics_filter)
        logger.addHandler(file_handler)

    if not any(isinstance(h, PrometheusHandler) for h in logger.handlers):
        prometheus_handler = PrometheusHandler()
        prometheus_handler.addFilter(skip_metrics_filter)
        logger.addHandler(prometheus_handler)

    return logger

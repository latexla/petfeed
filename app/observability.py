"""Logging and Sentry setup shared by the API and the bot."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

from app.config import settings

_RESERVED_LOG_ATTRS = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename", "funcName",
    "levelname", "levelno", "lineno", "message", "module", "msecs", "msg", "name",
    "pathname", "process", "processName", "relativeCreated", "stack_info", "thread",
    "threadName", "taskName",
}


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str):
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "service": self.service,
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_ATTRS or key.startswith("_"):
                continue
            payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(service: str) -> None:
    """Replace root handlers with one configured for the current environment."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if settings.APP_ENV == "production":
        handler.setFormatter(JsonFormatter(service))
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-5s %(name)s: %(message)s")
        )
    root.addHandler(handler)


def setup_sentry(service: str) -> None:
    """No-op if SENTRY_DSN is empty."""
    if not settings.SENTRY_DSN:
        return
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_ENV,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
    )
    sentry_sdk.set_tag("service", service)


def setup_observability(service: str) -> None:
    setup_logging(service)
    setup_sentry(service)

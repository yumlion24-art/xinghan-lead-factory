from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime
from typing import Any

import structlog
from structlog.types import EventDict

from lead_factory.settings import Settings

SECRET_KEYS = {"api_key", "authorization", "password", "secret", "token"}


def _timestamp(_: Any, __: str, event_dict: EventDict) -> EventDict:
    event_dict["timestamp"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return event_dict


def _redact(_: Any, __: str, event_dict: EventDict) -> EventDict:
    def clean(value: Any, key: str = "") -> Any:
        if key.lower() in SECRET_KEYS or any(part in key.lower() for part in ("secret", "token")):
            return "[REDACTED]"
        if isinstance(value, dict):
            return {nested_key: clean(nested_value, nested_key) for nested_key, nested_value in value.items()}
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    return {key: clean(value, key) for key, value in event_dict.items()}


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(level=settings.log_level.upper(), stream=sys.stdout, force=True)
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            _timestamp,
            _redact,
            structlog.processors.JSONRenderer(sort_keys=True),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=False,
    )

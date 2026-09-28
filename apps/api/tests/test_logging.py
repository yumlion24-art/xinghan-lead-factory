import json

import structlog

from lead_factory.logging import configure_logging
from lead_factory.settings import Settings


def test_structured_logs_include_context_and_redact_secrets(capsys) -> None:
    configure_logging(Settings(_env_file=None, log_level="INFO"))

    structlog.get_logger(component="collector").info(
        "fetch_finished",
        request_id="req-1",
        api_key="super-secret",
    )

    event = json.loads(capsys.readouterr().out)
    assert event["level"] == "info"
    assert event["component"] == "collector"
    assert event["event"] == "fetch_finished"
    assert event["request_id"] == "req-1"
    assert event["api_key"] == "[REDACTED]"
    assert event["timestamp"].endswith("Z")


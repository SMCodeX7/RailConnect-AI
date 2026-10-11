import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }

        for field in (
            "request_id",
            "method",
            "route",
            "status_code",
            "duration_ms",
        ):
            if hasattr(record, field):
                payload[field] = getattr(record, field)

        return json.dumps(payload, separators=(",", ":"))


def configure_logging() -> None:
    logger = logging.getLogger("railconnect")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if any(handler.name == "railconnect-json" for handler in logger.handlers):
        return

    handler = logging.StreamHandler()
    handler.set_name("railconnect-json")
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

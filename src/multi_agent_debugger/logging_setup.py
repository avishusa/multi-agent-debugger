"""Structured logging setup.

One module, one job: configure `structlog` so every event is a JSON-able
record with stable field names. All other modules call `get_logger()` to
get a configured logger; they never call `logging.basicConfig` or import
`structlog` directly.

Why structlog over stdlib logging:
  - First-class structured events (`log.info("event", key=value)`).
  - Context binding flows fields through the call stack.
  - Pluggable renderers (pretty for dev, JSON for prod) with no code changes.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from multi_agent_debugger.config import get_settings


def _drop_color_message_key(_: Any, __: str, event_dict: EventDict) -> EventDict:
    """Remove the `color_message` key uvicorn-style libraries sometimes inject."""
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging() -> None:
    """Configure structlog. Idempotent. Call once at process startup."""
    settings = get_settings()

    # Note: `add_logger_name` is NOT in this list — it requires stdlib-style
    # loggers with a `.name` attribute, which `PrintLogger` does not have.
    # We attach a logger name explicitly via `get_logger(name).bind(logger=name)`
    # in `get_logger` below, which keeps the field name `logger` but avoids
    # the incompatibility.
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _drop_color_message_key,
    ]

    if settings.log_format == "json":
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a configured logger, optionally pre-bound with a `logger` field."""
    logger: structlog.stdlib.BoundLogger = structlog.get_logger()
    if name is not None:
        logger = logger.bind(logger=name)
    return logger

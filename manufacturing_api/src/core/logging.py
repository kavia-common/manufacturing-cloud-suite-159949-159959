from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Optional


# Context variables for enriched logging
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
tenant_id_var: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)


class LoggingContextFilter(logging.Filter):
    """
    Logging filter that injects correlation_id and tenant_id from contextvars
    into each log record so formatters can include them.

    If no values are present in the context, placeholders are used.
    """

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        cid = correlation_id_var.get()
        tid = tenant_id_var.get()
        setattr(record, "correlation_id", cid or "-")
        setattr(record, "tenant_id", tid or "-")
        return True


# PUBLIC_INTERFACE
def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logging with a structured format and context filter."""
    handler = logging.StreamHandler(stream=sys.stdout)
    fmt = (
        "%(asctime)s | %(levelname)s | %(name)s | cid=%(correlation_id)s | tenant=%(tenant_id)s | "
        "%(message)s"
    )
    formatter = logging.Formatter(fmt=fmt)
    handler.setFormatter(formatter)
    handler.addFilter(LoggingContextFilter())

    root = logging.getLogger()
    # Remove pre-existing default handlers configured elsewhere (e.g., basicConfig)
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(handler)
    root.setLevel(level)

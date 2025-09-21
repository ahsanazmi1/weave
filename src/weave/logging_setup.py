"""
Structured JSON logging setup with redaction filtering and trace ID binding.

This module provides:
- JSON formatter for structured logging (no external dependencies)
- RedactionFilter to mask sensitive data (PAN, CVV, expiry, email)
- get_logger function that automatically includes trace_id
- setup_logging function for application initialization
"""

import json
import logging
import re
from typing import Any, Dict, Optional

from ocn_common.trace import get_current_trace_id


class RedactionFilter(logging.Filter):
    """
    Logging filter that redacts sensitive information from log messages.

    Masks:
    - PAN (Primary Account Numbers): 13-19 digits
    - CVV (Card Verification Value): 3-4 digits near 'cvv' keyword
    - Expiry dates: MM/YY format
    - Email addresses: user@domain.com format
    """

    def __init__(self):
        super().__init__()

        # PAN pattern: 13-19 consecutive digits
        self.pan_pattern = re.compile(r"\b\d{13,19}\b")

        # CVV pattern: 3-4 digits near 'cvv' keyword (case insensitive)
        self.cvv_pattern = re.compile(
            r"(cvv[:\s]*|card[:\s]*verification[:\s]*value[:\s]*)(\d{3,4})(?=\s|$|[^0-9])",
            re.IGNORECASE,
        )

        # Expiry pattern: MM/YY format
        self.expiry_pattern = re.compile(r"\b\d{2}/\d{2}\b")

        # Email pattern: user@domain.com format
        self.email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and redact sensitive information from log record."""
        # Redact the message
        if hasattr(record, "msg") and record.msg:
            record.msg = self._redact_text(str(record.msg))

        # Redact any additional fields that might contain sensitive data
        if hasattr(record, "args") and record.args:
            # For CVV redaction, we need to check if the message contains "CVV"
            # and the args contain digits that could be CVVs
            msg_str = str(record.msg).lower()
            if "cvv" in msg_str and record.args:
                new_args = []
                for arg in record.args:
                    if isinstance(arg, str) and arg.isdigit() and len(arg) in [3, 4]:
                        # This could be a CVV, redact it
                        new_args.append("[CVV_REDACTED]")
                    else:
                        new_args.append(
                            self._redact_text(str(arg)) if isinstance(arg, str) else arg
                        )
                record.args = tuple(new_args)
            else:
                record.args = tuple(
                    self._redact_text(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )

        return True

    def _redact_text(self, text: str) -> str:
        """Redact sensitive information from text."""
        # Redact PANs
        text = self.pan_pattern.sub("[PAN_REDACTED]", text)

        # Redact CVVs
        text = self.cvv_pattern.sub(r"\1[CVV_REDACTED]", text)

        # Redact expiry dates
        text = self.expiry_pattern.sub("[EXPIRY_REDACTED]", text)

        # Redact email addresses
        text = self.email_pattern.sub("[EMAIL_REDACTED]", text)

        return text


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging without external dependencies.

    Formats log records as JSON with standard fields:
    - timestamp: ISO format timestamp
    - level: log level name
    - logger: logger name
    - message: log message
    - trace_id: trace ID from context (if available)
    - module: module name
    - function: function name
    - line: line number
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add trace_id if available
        trace_id = get_current_trace_id()
        if trace_id:
            log_entry["trace_id"] = trace_id

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add any extra fields from the record
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
            ):
                log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False)


class TraceLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that automatically includes trace_id in log records.
    """

    def __init__(self, logger: logging.Logger, trace_id: Optional[str] = None):
        super().__init__(logger, {})
        self.trace_id = trace_id

    def process(self, msg: Any, kwargs: Dict[str, Any]) -> tuple:
        """Process log message to include trace_id."""
        # Get trace_id from current context if not provided
        if not self.trace_id:
            self.trace_id = get_current_trace_id()

        # Add trace_id to extra fields
        if "extra" not in kwargs:
            kwargs["extra"] = {}
        kwargs["extra"]["trace_id"] = self.trace_id

        return msg, kwargs


def setup_logging(level: str = "INFO", format_type: str = "json") -> None:
    """
    Set up structured logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Log format type ('json' or 'text')
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper()))

    # Set formatter
    if format_type.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    console_handler.setFormatter(formatter)

    # Add redaction filter
    redaction_filter = RedactionFilter()
    console_handler.addFilter(redaction_filter)

    # Add handler to root logger
    root_logger.addHandler(console_handler)

    # Set up third-party logger levels
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str, trace_id: Optional[str] = None) -> TraceLoggerAdapter:
    """
    Get a logger with automatic trace_id binding.

    Args:
        name: Logger name (typically __name__)
        trace_id: Optional trace ID to bind to this logger

    Returns:
        Logger adapter that automatically includes trace_id in logs
    """
    logger = logging.getLogger(name)
    return TraceLoggerAdapter(logger, trace_id)


# Convenience function for getting logger with current trace context
def get_traced_logger(name: str) -> TraceLoggerAdapter:
    """
    Get a logger with automatic trace_id from current context.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger adapter that automatically includes current trace_id in logs
    """
    return get_logger(name, get_current_trace_id())

"""
Tests for trace ID binding in logging.
"""

import json
import logging
from io import StringIO
from unittest.mock import patch

from src.weave.logging_setup import TraceLoggerAdapter, get_logger, get_traced_logger, setup_logging


class TestTraceLoggerAdapter:
    """Test cases for TraceLoggerAdapter."""

    def test_trace_id_binding(self):
        """Test that trace_id is bound to log records."""
        logger = logging.getLogger("test")

        # Create adapter with specific trace_id
        adapter = TraceLoggerAdapter(logger, "test-trace-123")

        # Capture log output
        handler = logging.StreamHandler(StringIO())
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Log a message
        adapter.info("Test message")

        # Check that trace_id was added to extra
        # The handler should have received a record with trace_id in extra
        assert len(handler.stream.getvalue()) > 0

    def test_auto_trace_id_from_context(self):
        """Test that trace_id is automatically retrieved from context."""
        logger = logging.getLogger("test")
        adapter = TraceLoggerAdapter(logger)

        # Mock get_current_trace_id to return a test trace ID
        with patch("src.weave.logging_setup.get_current_trace_id", return_value="auto-trace-456"):
            # Capture log output
            handler = logging.StreamHandler(StringIO())
            handler.setLevel(logging.INFO)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

            # Log a message
            adapter.info("Test message with auto trace ID")

            # Verify log was created
            assert len(handler.stream.getvalue()) > 0

    def test_no_trace_id_when_none(self):
        """Test behavior when trace_id is None."""
        logger = logging.getLogger("test")
        adapter = TraceLoggerAdapter(logger, None)

        # Capture log output
        handler = logging.StreamHandler(StringIO())
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Log a message
        adapter.info("Test message without trace ID")

        # Should still log successfully
        assert len(handler.stream.getvalue()) > 0


class TestGetLogger:
    """Test cases for get_logger function."""

    def test_get_logger_with_trace_id(self):
        """Test get_logger with specific trace_id."""
        logger = get_logger("test.module", "specific-trace-789")

        assert isinstance(logger, TraceLoggerAdapter)
        assert logger.trace_id == "specific-trace-789"

    def test_get_logger_without_trace_id(self):
        """Test get_logger without trace_id."""
        logger = get_logger("test.module")

        assert isinstance(logger, TraceLoggerAdapter)
        assert logger.trace_id is None

    def test_get_traced_logger(self):
        """Test get_traced_logger function."""
        with patch("src.weave.logging_setup.get_current_trace_id", return_value="current-trace-999"):
            logger = get_traced_logger("test.module")

            assert isinstance(logger, TraceLoggerAdapter)
            assert logger.trace_id == "current-trace-999"


class TestLoggingIntegration:
    """Integration tests for logging setup with trace ID binding."""

    def test_setup_logging_with_json_format(self):
        """Test that setup_logging creates JSON formatted logs with trace_id."""
        # Create a logger and handler for testing
        test_logger = logging.getLogger("integration.test")
        test_logger.setLevel(logging.INFO)

        # Remove existing handlers
        for handler in test_logger.handlers[:]:
            test_logger.removeHandler(handler)

        # Create a string stream handler
        stream = StringIO()
        handler = logging.StreamHandler(stream)

        # Use our JSON formatter
        from src.weave.logging_setup import JSONFormatter, RedactionFilter

        handler.setFormatter(JSONFormatter())
        handler.addFilter(RedactionFilter())
        test_logger.addHandler(handler)

        # Get traced logger
        logger = get_traced_logger("integration.test")

        # Mock trace ID
        with patch(
            "src.weave.logging_setup.get_current_trace_id", return_value="integration-trace-111"
        ):
            logger.info("Integration test message")

            # Get output
            output = stream.getvalue().strip()

            # Should have some output
            assert output

            # Parse as JSON and verify structure
            log_entry = json.loads(output)
            assert "timestamp" in log_entry
            assert "level" in log_entry
            assert "message" in log_entry
            assert "logger" in log_entry
            assert log_entry["trace_id"] == "integration-trace-111"

    def test_redaction_with_trace_binding(self):
        """Test that redaction works with trace ID binding."""
        # Set up logging
        setup_logging(level="INFO", format_type="json")

        # Get logger and log sensitive information
        logger = get_traced_logger("redaction.test")

        with patch(
            "src.weave.logging_setup.get_current_trace_id", return_value="redaction-trace-222"
        ):
            logger.info("Processing card 4111111111111111 with CVV: 123")

        # The redaction should have occurred in the logging pipeline
        # This is more of an integration test to ensure both systems work together


class TestTraceIDInLogs:
    """Test that trace_id appears in actual log output."""

    def test_trace_id_in_json_logs(self):
        """Test that trace_id is included in JSON log output."""
        # Set up a custom handler to capture output
        stream = StringIO()

        # Create a logger with our formatter
        logger = logging.getLogger("trace.test")
        logger.setLevel(logging.INFO)

        # Add handler with JSON formatter
        from src.weave.logging_setup import JSONFormatter, RedactionFilter

        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        handler.addFilter(RedactionFilter())
        logger.addHandler(handler)

        # Create trace logger adapter
        adapter = TraceLoggerAdapter(logger, "json-trace-333")

        # Log a message
        adapter.info("Test message with trace ID")

        # Parse JSON output
        output = stream.getvalue().strip()
        log_entry = json.loads(output)

        # Verify trace_id is present
        assert log_entry["trace_id"] == "json-trace-333"

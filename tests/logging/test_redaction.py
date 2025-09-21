"""
Tests for redaction filtering in logging.
"""

import logging

from src.weave.logging_setup import RedactionFilter, JSONFormatter


class TestRedactionFilter:
    """Test cases for RedactionFilter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.redaction_filter = RedactionFilter()

    def test_pan_redaction(self):
        """Test PAN (Primary Account Number) redaction."""
        test_cases = [
            ("Card number 4111111111111111 is valid", "Card number [PAN_REDACTED] is valid"),
            ("Processing 1234567890123456789", "Processing [PAN_REDACTED]"),
            ("Invalid card 1234567890123", "Invalid card [PAN_REDACTED]"),
            ("Short number 123456789012345", "Short number [PAN_REDACTED]"),
            ("Long number 1234567890123456789", "Long number [PAN_REDACTED]"),
            ("No card here", "No card here"),  # Should not be redacted
            ("123456789012", "123456789012"),  # 12 digits - should not be redacted
            ("12345678901234567890", "12345678901234567890"),  # 20 digits - should not be redacted
        ]

        for input_text, expected in test_cases:
            result = self.redaction_filter._redact_text(input_text)
            assert result == expected, f"Failed for input: {input_text}"

    def test_cvv_redaction(self):
        """Test CVV redaction."""
        test_cases = [
            ("CVV: 123", "CVV: [CVV_REDACTED]"),
            ("cvv 456", "cvv [CVV_REDACTED]"),
            ("Card verification value: 789", "Card verification value: [CVV_REDACTED]"),
            ("CARD VERIFICATION VALUE 1234", "CARD VERIFICATION VALUE [CVV_REDACTED]"),
            ("Security code is 999", "Security code is 999"),  # Should not be redacted
            ("Code 12", "Code 12"),  # Should not be redacted (too short)
            ("CVV: 12345", "CVV: 12345"),  # Should not be redacted (too long)
        ]

        for input_text, expected in test_cases:
            result = self.redaction_filter._redact_text(input_text)
            assert result == expected, f"Failed for input: {input_text}"

    def test_expiry_redaction(self):
        """Test expiry date redaction."""
        test_cases = [
            ("Expires 12/25", "Expires [EXPIRY_REDACTED]"),
            ("Valid until 01/30", "Valid until [EXPIRY_REDACTED]"),
            ("Expiry: 03/28", "Expiry: [EXPIRY_REDACTED]"),
            ("Date 99/99", "Date [EXPIRY_REDACTED]"),  # Invalid but matches pattern
            ("Year 2025", "Year 2025"),  # Should not be redacted
            ("Month 12", "Month 12"),  # Should not be redacted
            ("12/25/2025", "[EXPIRY_REDACTED]/2025"),  # Partial match
        ]

        for input_text, expected in test_cases:
            result = self.redaction_filter._redact_text(input_text)
            assert result == expected, f"Failed for input: {input_text}"

    def test_email_redaction(self):
        """Test email address redaction."""
        test_cases = [
            ("Contact user@example.com", "Contact [EMAIL_REDACTED]"),
            ("Email: test.user@domain.org", "Email: [EMAIL_REDACTED]"),
            ("Send to admin@company.co.uk", "Send to [EMAIL_REDACTED]"),
            ("User+tag@sub.domain.com", "[EMAIL_REDACTED]"),
            ("Invalid email user@", "Invalid email user@"),  # Should not be redacted
            ("Not an email", "Not an email"),  # Should not be redacted
        ]

        for input_text, expected in test_cases:
            result = self.redaction_filter._redact_text(input_text)
            assert result == expected, f"Failed for input: {input_text}"

    def test_multiple_redactions(self):
        """Test multiple types of redaction in one message."""
        input_text = "Processing card 4111111111111111 with CVV: 123, expires 12/25, contact user@example.com"
        expected = "Processing card [PAN_REDACTED] with CVV: [CVV_REDACTED], expires [EXPIRY_REDACTED], contact [EMAIL_REDACTED]"

        result = self.redaction_filter._redact_text(input_text)
        assert result == expected

    def test_log_record_filtering(self):
        """Test that the filter works on log records."""
        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Processing card %s with CVV: %s",
            args=("4111111111111111", "123"),
            exc_info=None,
        )

        # Apply filter
        self.redaction_filter.filter(record)

        # Check that sensitive data is redacted in args (not msg format string)
        assert "[PAN_REDACTED]" in str(record.args)
        # The CVV "123" should be redacted to "[CVV_REDACTED]"
        assert "[CVV_REDACTED]" in str(record.args)


class TestJSONFormatter:
    """Test cases for JSONFormatter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = JSONFormatter()

    def test_basic_formatting(self):
        """Test basic JSON formatting."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_function",
        )

        result = self.formatter.format(record)

        # Parse JSON to verify structure
        import json

        log_entry = json.loads(result)

        assert log_entry["level"] == "INFO"
        assert log_entry["logger"] == "test.logger"
        assert log_entry["message"] == "Test message"
        assert log_entry["module"] == "file"
        assert log_entry["function"] == "test_function"
        assert log_entry["line"] == 42
        assert "timestamp" in log_entry

    def test_trace_id_inclusion(self):
        """Test that trace_id is included when available."""
        # Mock get_current_trace_id to return a test trace ID
        import src.weave.logging_setup as logging_module

        original_get_trace_id = logging_module.get_current_trace_id

        def mock_get_trace_id():
            return "test-trace-id-123"

        logging_module.get_current_trace_id = mock_get_trace_id

        try:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="/path/to/file.py",
                lineno=42,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            result = self.formatter.format(record)

            # Parse JSON to verify trace_id is included
            import json

            log_entry = json.loads(result)

            assert log_entry["trace_id"] == "test-trace-id-123"
        finally:
            # Restore original function
            logging_module.get_current_trace_id = original_get_trace_id

    def test_no_trace_id_when_none(self):
        """Test that trace_id is not included when None."""
        # Mock get_current_trace_id to return None
        import src.weave.logging_setup as logging_module

        original_get_trace_id = logging_module.get_current_trace_id

        def mock_get_trace_id():
            return None

        logging_module.get_current_trace_id = mock_get_trace_id

        try:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="/path/to/file.py",
                lineno=42,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            result = self.formatter.format(record)

            # Parse JSON to verify trace_id is not included
            import json

            log_entry = json.loads(result)

            assert "trace_id" not in log_entry
        finally:
            # Restore original function
            logging_module.get_current_trace_id = original_get_trace_id

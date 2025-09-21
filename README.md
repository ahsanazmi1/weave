# weave

Part of the Open Checkout Network (OCN).

## Dev Quickstart
```bash
python -m venv .venv && . .venv/bin/activate
pip install -U pip && pip install -e .[dev]
pytest -q
```


## Structured Logging & Redaction

Weave implements enterprise-grade structured JSON logging with automatic redaction of sensitive data:

### Features
- **JSON Format**: All logs are structured JSON for easy parsing and analysis
- **Trace ID Binding**: Every log automatically includes the current trace ID for correlation
- **Sensitive Data Redaction**: Automatic masking of:
  - PAN (Primary Account Numbers): 13-19 digits → `[PAN_REDACTED]`
  - CVV (Card Verification Values): 3-4 digits near 'cvv' → `[CVV_REDACTED]`
  - Expiry dates: MM/YY format → `[EXPIRY_REDACTED]`
  - Email addresses: user@domain.com → `[EMAIL_REDACTED]`

### Usage
```python
from src.weave.logging_setup import get_traced_logger, setup_logging

# Set up logging (done automatically in app startup)
setup_logging(level='INFO', format_type='json')

# Get logger with automatic trace ID binding
logger = get_traced_logger(__name__)
logger.info("Processing receipt for user@example.com with card ending in 1111")
```

### Example Output
```json
{
  "timestamp": "2024-01-21T12:00:00Z",
  "level": "INFO",
  "logger": "src.weave.subscriber",
  "message": "Processing receipt for [EMAIL_REDACTED] with card ending in [PAN_REDACTED]",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "module": "subscriber",
  "function": "process_receipt",
  "line": 142
}
```

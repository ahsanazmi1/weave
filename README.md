# Weave — The Open Receipt Ledger

[![Contracts Validation](https://github.com/ocn-ai/weave/actions/workflows/contracts.yml/badge.svg)](https://github.com/ocn-ai/weave/actions/workflows/contracts.yml)
[![Security Validation](https://github.com/ocn-ai/weave/actions/workflows/security.yml/badge.svg)](https://github.com/ocn-ai/weave/actions/workflows/security.yml)
[![CI](https://github.com/ocn-ai/weave/actions/workflows/ci.yml/badge.svg)](https://github.com/ocn-ai/weave/actions/workflows/ci.yml)

**Weave** is the **open, transparent receipt ledger** for the [Open Checkout Network (OCN)](https://github.com/ocn-ai/ocn-common).

## Phase 2 — Explainability

🚧 **Currently in development** - Phase 2 focuses on AI-powered explainability and human-readable audit reasoning.

- **Status**: Active development on `phase-2-explainability` branch
- **Features**: LLM integration, explainability API endpoints, decision audit trails
- **Issue Tracker**: [Phase 2 Issues](https://github.com/ahsanazmi1/weave/issues?q=is%3Aopen+is%3Aissue+label%3Aphase-2)
- **Timeline**: Weeks 4-8 of OCN development roadmap

## Purpose

Weave provides immutable receipt storage and retrieval for the OCN ecosystem. Unlike traditional closed receipt systems, Weave offers:

- **Transparent Receipt Storage** - Clear, auditable receipt ledger
- **Structured Logging** - Enterprise-grade JSON logging with automatic redaction
- **Open Architecture** - Integrates seamlessly with OCN protocols
- **MCP Integration** - Model Context Protocol support for agent interactions

## Quickstart (≤ 60s)

```bash
# Clone and setup
git clone https://github.com/ocn-ai/weave.git
cd weave

# Setup development environment
make setup

# Run tests
make test

# Start the service
make run
```

### Available Make Commands

- `make setup` - Create venv, install deps + dev extras, install pre-commit hooks
- `make lint` - Run ruff and black checks
- `make fmt` - Format code with black
- `make test` - Run pytest with coverage
- `make run` - Start FastAPI app with uvicorn
- `make clean` - Remove virtual environment and cache files


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

## Related OCN Repositories

- [Orca](https://github.com/ocn-ai/orca): The Open Checkout Agent
- [Okra](https://github.com/ocn-ai/okra): The Open Credit Agent
- [Onyx](https://github.com/ocn-ai/onyx): The Open Trust Registry
- [Oasis](https://github.com/ocn-ai/oasis): The Open Treasury Agent
- [Orion](https://github.com/ocn-ai/orion): The Open Payout Agent
- [Opal](https://github.com/ocn-ai/opal): The Open Payment Agent
- [Olive](https://github.com/ocn-ai/olive): The Open Loyalty Agent
- [ocn-common](https://github.com/ocn-ai/ocn-common): Common utilities and schemas

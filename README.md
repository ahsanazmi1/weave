# Weave — The Open Receipt Ledger

[![Contracts Validation](https://github.com/ocn-ai/weave/actions/workflows/contracts.yml/badge.svg)](https://github.com/ocn-ai/weave/actions/workflows/contracts.yml)
[![Security Validation](https://github.com/ocn-ai/weave/actions/workflows/security.yml/badge.svg)](https://github.com/ocn-ai/weave/actions/workflows/security.yml)
[![CI](https://github.com/ocn-ai/weave/actions/workflows/ci.yml/badge.svg)](https://github.com/ocn-ai/weave/actions/workflows/ci.yml)

**Weave** is the **open, transparent receipt ledger** for the [Open Checkout Network (OCN)](https://github.com/ocn-ai/ocn-common).

## Phase 4 — Payment Instruction & Visibility

🚧 **Currently in development** - Phase 4 focuses on payment instruction generation, settlement visibility, and comprehensive payment tracking for receipt audit trails.

- **Status**: Active development on `phase-4-instruction` branch
- **Features**: Payment instruction schemas, settlement visibility, payment tracking, instruction validation
- **Issue Tracker**: [Phase 4 Issues](https://github.com/ahsanazmi1/weave/issues?q=is%3Aopen+is%3Aissue+label%3Aphase-4)
- **Timeline**: Weeks 12-16 of OCN development roadmap

See [CHANGELOG.md](CHANGELOG.md) for detailed Phase 4 progress and features.

## Payment Processor Connectors (Phase 8)

Weave includes integrated connectors for major payment processors with deterministic stub responses for development and testing.

### Supported Processors

- **Carat** (`src/weave/connectors/carat.py`) - Specializes in ACH and real-time payments with competitive pricing
- **Stripe** (`src/weave/connectors/stripe.py`) - Global card processing with balanced pricing and comprehensive features  
- **Adyen** (`src/weave/connectors/adyen.py`) - Premium global payments with fast settlement speeds

### Connector Characteristics

| Processor | Focus | Pricing | Settlement | Global Reach |
|-----------|-------|---------|------------|--------------|
| **Carat** | ACH, RTP, FedNow | Lowest fees (25% discount) | Real-time/Next-day | US-focused |
| **Stripe** | Card payments | Market rates (2.9% + $0.30) | 2-day standard | Global |
| **Adyen** | Multi-rail global | Premium rates (10% markup) | Next-day (premium) | Global |

### Using Connectors

```python
from src.weave.connectors import get_carat_connector, get_stripe_connector, get_adyen_connector
from src.weave.enhanced_bid_broadcaster import get_enhanced_bid_broadcaster

# Get connector instances
carat = get_carat_connector()
stripe = get_stripe_connector()
adyen = get_adyen_connector()

# Use enhanced broadcaster for multi-processor auctions
broadcaster = get_enhanced_bid_broadcaster()
bid_responses, metadata = broadcaster.broadcast_bid_requests(bid_requests)
```

### Replacing Stubs with Real APIs

To replace stub responses with real processor APIs:

#### 1. **Carat Integration**

```python
# In src/weave/connectors/carat.py
def _is_api_available(self) -> bool:
    try:
        # Replace with actual Carat health check
        response = requests.get(f"{self.base_url}/health", 
                              headers={"Authorization": f"Bearer {self.api_key}"},
                              timeout=5)
        return response.status_code == 200
    except:
        return False

def _send_real_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    # Replace with actual Carat bid request API
    response = requests.post(
        f"{self.base_url}/v1/bids",
        headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=30
    )
    response.raise_for_status()
    return response.json()
```

#### 2. **Stripe Integration**

```python
# In src.weave/connectors/stripe.py
def _send_real_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    # Replace with actual Stripe payment methods API
    response = requests.post(
        f"{self.base_url}/v1/payment_methods/calculate_fees",
        headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=30
    )
    response.raise_for_status()
    return response.json()
```

#### 3. **Adyen Integration**

```python
# In src/weave/connectors/adyen.py
def _send_real_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    # Replace with actual Adyen payments API
    response = requests.post(
        f"{self.base_url}/v1/payments/estimate",
        headers={
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=30
    )
    response.raise_for_status()
    return response.json()
```

#### 4. **Environment Configuration**

```bash
# Set API keys for production
export CARAT_API_KEY="your_carat_api_key"
export STRIPE_SECRET_KEY="your_stripe_secret_key"
export ADYEN_API_KEY="your_adyen_api_key"

# Initialize connectors with real API keys
carat = get_carat_connector(api_key=os.getenv("CARAT_API_KEY"))
stripe = get_stripe_connector(api_key=os.getenv("STRIPE_SECRET_KEY"))
adyen = get_adyen_connector(api_key=os.getenv("ADYEN_API_KEY"))
```

#### 5. **Testing Real APIs**

```python
# Test connectivity to real processors
broadcaster = get_enhanced_bid_broadcaster()
connectivity_status = broadcaster.test_connector_connectivity()

for processor, status in connectivity_status.items():
    if status["status"] == "connected":
        print(f"✅ {processor}: Connected ({status['response_time_ms']}ms)")
    else:
        print(f"❌ {processor}: {status['error']}")
```

### Connector Testing

Run comprehensive connector tests:

```bash
# Test all connectors
pytest tests/test_connectors_integration.py -v

# Test specific connector
pytest tests/test_connectors_integration.py::TestConnectorIntegration::test_carat_connector_deterministic_bids -v

# Test enhanced broadcaster
pytest tests/test_connectors_integration.py::TestConnectorIntegration::test_enhanced_broadcaster_aggregation -v
```

### CloudEvents Integration

Connectors automatically emit CloudEvents for bid requests and responses:

- `ocn.weave.bid_request.v1` - Bid request events
- `ocn.weave.bid_response.v1` - Bid response events  
- `ocn.weave.auction_completion.v1` - Auction completion events

These events integrate with the OCN event schema system for comprehensive payment tracking and audit trails.

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

## Phase 3 — Negotiation & Live Fee Bidding

Processor auction system with bid broadcast, aggregation, and audit capabilities.

### Phase 3 — Negotiation & Live Fee Bidding
- [x] **Broadcasts bid requests to processors** (Carat, Adyen, Stripe)
- [x] **Aggregates bid responses** (bps, rebates, settlement) into shared trace
- [x] **Logs bidding rounds**; emits bid request/response events
- [x] **Tests for bidding + aggregation workflows**

### Auction Features
- **Processor Connectors**: Stub implementations for Carat, Adyen, Stripe
- **Bid Aggregation**: Automatic winner determination with tie-breaker logic
- **CloudEvent Emission**: Emits `ocn.weave.bid_request.v1` and `ocn.weave.bid_response.v1` events
- **LLM Summaries**: Optional LLM-powered auction result explanations
- **Deterministic Results**: Consistent auction outcomes with configurable seeds

### Auction API Endpoints
- `POST /auction/run` - Run processor auction for pay-ins (checkout)
- `GET /auction/status` - Get auction service status and capabilities
- `GET /auction/sample-request` - Get sample auction request for testing

### MCP Auction Verb
- `runAuction` - Run processor auction via Model Context Protocol

#### Auction Request Example
```bash
curl -X POST http://localhost:8000/auction/run \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "auction-trace-001",
    "cart_summary": {
      "total_amount": 100.0,
      "currency": "USD",
      "item_count": 2,
      "merchant_id": "merchant_001",
      "merchant_category": "general",
      "channel": "online"
    },
    "rail_candidates": [
      {
        "rail_type": "credit",
        "base_cost_bps": 150.0,
        "settlement_days": 1,
        "risk_score": 0.3
      }
    ]
  }'
```

#### Auction Response Example
```json
{
  "trace_id": "auction-trace-001",
  "auction_id": "auction-auction-trace-001-1234567890",
  "winning_processor": "stripe",
  "winning_bid": {
    "processor_id": "stripe",
    "bps": 150.0,
    "rebate_bps": 10.0,
    "effective_cost_bps": 140.0,
    "expected_settlement_days": 1,
    "confidence": 0.9,
    "constraints": {
      "min_amount": 0.50,
      "max_amount": 100000.0,
      "supported_currencies": ["USD", "EUR", "GBP"]
    }
  },
  "all_bids": [...],
  "effective_cost_bps": 140.0,
  "summary": "Stripe won the auction with 140.0 bps effective cost (150.0 bps - 10.0 bps rebate) and 1-day settlement (saving 5.0 bps vs runner-up) from 3 competing processors.",
  "timestamp": "2024-01-15T10:30:00Z",
  "llm_configured": true
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

# Weave CloudEvents Subscriber API

The Weave CloudEvents Subscriber provides a REST API for receiving, validating, and storing CloudEvents as cryptographic receipt hashes.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, authentication is optional and can be enabled via configuration:

```bash
WEAVE_ENABLE_AUTHENTICATION=true
WEAVE_API_KEY=your-api-key-here
```

## Content Types

All endpoints accept and return `application/json` content.

## Error Responses

All error responses follow this format:

```json
{
    "error": "Error message",
    "detail": "Additional error details (optional)",
    "status_code": 400
}
```

## Endpoints

### Root Information

#### GET /

Get API information and available endpoints.

**Response:**
```json
{
    "service": "Weave CloudEvents Subscriber",
    "version": "0.1.0",
    "status": "operational",
    "endpoints": {
        "events": "/events",
        "receipts": "/receipts",
        "health": "/health"
    }
}
```

### Health Check

#### GET /health

Check service health status.

**Response:**
```json
{
    "status": "healthy",
    "service": "weave-subscriber"
}
```

### CloudEvent Submission

#### POST /events

Submit a CloudEvent for receipt storage.

**Request Body:**
```json
{
    "specversion": "1.0",
    "id": "evt_decision_001",
    "source": "https://orca.ocn.ai/v1",
    "type": "ocn.orca.decision.v1",
    "subject": "txn_abc123",
    "time": "2024-01-21T12:34:56Z",
    "datacontenttype": "application/json",
    "dataschema": "https://schemas.ocn.ai/events/v1/orca.decision.v1.schema.json",
    "data": {
        "ap2_version": "0.1.0",
        "intent": { /* intent mandate data */ },
        "cart": { /* cart mandate data */ },
        "payment": { /* payment mandate data */ },
        "decision": { /* decision data */ },
        "signing": { /* signing data */ }
    }
}
```

**Required Fields:**
- `specversion`: CloudEvents specification version (must be "1.0")
- `id`: Unique event identifier
- `source`: Event source URI
- `type`: Event type (must be in allowed types)
- `time`: Event timestamp (ISO 8601 format)

**Optional Fields:**
- `subject`: Event subject (used as trace_id, falls back to `id`)
- `datacontenttype`: Content type of event data
- `dataschema`: Schema URI for event data

**Allowed Event Types:**
- `ocn.orca.decision.v1`
- `ocn.orca.explanation.v1`
- `ocn.weave.audit.v1`

**Response (201 Created):**
```json
{
    "receipt_id": "550e8400-e29b-41d4-a716-446655440000",
    "trace_id": "txn_abc123",
    "event_type": "ocn.orca.decision.v1",
    "event_hash": "sha256:a1b2c3d4e5f6789abcdef...",
    "time": "2024-01-21T12:34:56.789Z",
    "status": "stored"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid event type or malformed request
- `422 Unprocessable Entity`: Validation error in CloudEvent structure
- `500 Internal Server Error`: Server error during processing

### Receipt Retrieval

#### GET /receipts/{receipt_id}

Retrieve a specific receipt by ID.

**Response (200 OK):**
```json
{
    "receipt_id": "550e8400-e29b-41d4-a716-446655440000",
    "trace_id": "txn_abc123",
    "event_type": "ocn.orca.decision.v1",
    "event_hash": "sha256:a1b2c3d4e5f6789abcdef...",
    "time": "2024-01-21T12:34:56.789Z",
    "metadata": {
        "event_id": "evt_decision_001",
        "source": "https://orca.ocn.ai/v1",
        "datacontenttype": "application/json",
        "dataschema": "https://schemas.ocn.ai/events/v1/orca.decision.v1.schema.json",
        "received_at": "2024-01-21T12:34:56.789Z",
        "client_ip": "192.168.1.100"
    }
}
```

**Error Responses:**
- `404 Not Found`: Receipt ID not found

### Receipt Listing

#### GET /receipts

List receipts with optional filtering and pagination.

**Query Parameters:**
- `trace_id` (optional): Filter by trace ID
- `limit` (optional): Maximum number of receipts to return (default: 100, max: 1000)
- `offset` (optional): Number of receipts to skip (default: 0)

**Response (200 OK):**
```json
{
    "receipts": [
        {
            "receipt_id": "550e8400-e29b-41d4-a716-446655440000",
            "trace_id": "txn_abc123",
            "event_type": "ocn.orca.decision.v1",
            "event_hash": "sha256:a1b2c3d4e5f6789abcdef...",
            "time": "2024-01-21T12:34:56.789Z",
            "metadata": { /* metadata object */ }
        }
    ],
    "total": 150,
    "limit": 100,
    "offset": 0
}
```

### Trace Receipts

#### GET /receipts/trace/{trace_id}

Get all receipts for a specific trace ID.

**Response (200 OK):**
```json
[
    {
        "receipt_id": "550e8400-e29b-41d4-a716-446655440000",
        "trace_id": "txn_abc123",
        "event_type": "ocn.orca.decision.v1",
        "event_hash": "sha256:a1b2c3d4e5f6789abcdef...",
        "time": "2024-01-21T12:34:56.789Z",
        "metadata": { /* metadata object */ }
    },
    {
        "receipt_id": "660f9511-f30c-52e5-b827-557766551111",
        "trace_id": "txn_abc123",
        "event_type": "ocn.orca.explanation.v1",
        "event_hash": "sha256:b2c3d4e5f6789abcdef1...",
        "time": "2024-01-21T12:35:00.123Z",
        "metadata": { /* metadata object */ }
    }
]
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WEAVE_DATABASE_URL` | `sqlite:///./weave_receipts.db` | Database connection URL |
| `WEAVE_HOST` | `0.0.0.0` | Server host address |
| `WEAVE_PORT` | `8000` | Server port |
| `WEAVE_DEBUG` | `false` | Enable debug mode |
| `WEAVE_LOG_LEVEL` | `INFO` | Logging level |
| `WEAVE_ENABLE_AUTHENTICATION` | `false` | Enable API key authentication |
| `WEAVE_API_KEY` | `null` | API key for authentication |

### Allowed Event Types

The following CloudEvent types are accepted by default:

- `ocn.orca.decision.v1` - Orca decision events
- `ocn.orca.explanation.v1` - Orca explanation events  
- `ocn.weave.audit.v1` - Weave audit events

## Usage Examples

### Submit a Decision Event

```bash
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "specversion": "1.0",
    "id": "evt_decision_001",
    "source": "https://orca.ocn.ai/v1",
    "type": "ocn.orca.decision.v1",
    "subject": "txn_abc123",
    "time": "2024-01-21T12:34:56Z",
    "data": {
      "ap2_version": "0.1.0",
      "intent": {
        "actor": {"id": "user_123", "type": "user"},
        "channel": "web",
        "geo": {"country": "US"},
        "metadata": {}
      },
      "cart": {
        "amount": "99.99",
        "currency": "USD",
        "items": [],
        "geo": {"country": "US"},
        "metadata": {}
      },
      "payment": {
        "method": "card",
        "modality": {"type": "immediate"},
        "auth_requirements": [],
        "metadata": {}
      },
      "decision": {
        "result": "APPROVE",
        "risk_score": 0.15,
        "reasons": ["low_risk"],
        "actions": ["process"],
        "meta": {}
      },
      "signing": {
        "vc_proof": null,
        "receipt_hash": "sha256:mock"
      }
    }
  }'
```

### Retrieve a Receipt

```bash
curl http://localhost:8000/receipts/550e8400-e29b-41d4-a716-446655440000
```

### List All Receipts

```bash
curl http://localhost:8000/receipts
```

### Get Receipts by Trace ID

```bash
curl http://localhost:8000/receipts/trace/txn_abc123
```

## Rate Limiting

Rate limiting can be configured to prevent abuse:

- Default: No rate limiting
- Configurable per endpoint
- IP-based or API key-based limiting

## CORS Support

CORS is supported for web-based clients:

```bash
curl -H "Origin: https://example.com" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     http://localhost:8000/events
```

## OpenAPI Documentation

Interactive API documentation is available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

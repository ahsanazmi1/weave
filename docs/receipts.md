# Weave Receipt Storage

Weave implements a secure, privacy-preserving receipt storage system that stores only cryptographic hashes of CloudEvents, never the raw event data containing PII or PCI information.

## Privacy & Security Principles

### No PII/PCI Storage
- **Raw event data is never stored** - only cryptographic hashes
- **No personal information** is persisted in the database
- **No payment card data** is retained
- **No sensitive transaction details** are saved

### What IS Stored
- **Receipt ID**: Unique identifier for each receipt
- **Trace ID**: Transaction trace identifier for correlation
- **Event Type**: CloudEvent type (e.g., `ocn.orca.decision.v1`)
- **Event Hash**: SHA-256 hash of the event data
- **Timestamp**: When the receipt was created
- **Metadata**: Non-sensitive metadata (event ID, source, received timestamp)

### What is NOT Stored
- Raw event data payload
- User identifiers from event data
- Payment information
- Transaction amounts
- Personal details
- Any PII or PCI data

## Hash Generation

### SHA-256 Hashing
All event data is hashed using SHA-256 with the following process:

1. **JSON Serialization**: Event data is converted to JSON with sorted keys
2. **UTF-8 Encoding**: JSON string is encoded as UTF-8 bytes
3. **SHA-256 Hash**: Cryptographic hash is computed
4. **Hex Encoding**: Hash is encoded as hexadecimal string
5. **Prefix Addition**: `sha256:` prefix is added for identification

### Example Hash Generation
```python
import json
import hashlib

def hash_payload(payload):
    # Convert to JSON with sorted keys for consistency
    json_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))

    # Generate SHA-256 hash
    hash_obj = hashlib.sha256(json_str.encode('utf-8'))
    hash_hex = hash_obj.hexdigest()

    return f"sha256:{hash_hex}"
```

## Receipt Structure

### Database Schema
```sql
CREATE TABLE receipts (
    receipt_id VARCHAR(36) PRIMARY KEY,
    trace_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_hash VARCHAR(70) NOT NULL,
    time DATETIME NOT NULL,
    metadata TEXT
);
```

### Receipt JSON Structure
```json
{
    "receipt_id": "550e8400-e29b-41d4-a716-446655440000",
    "trace_id": "txn_abc123",
    "event_type": "ocn.orca.decision.v1",
    "event_hash": "sha256:a1b2c3d4e5f6789...",
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

## Verifiable Credentials (Stubs)

Weave includes stub implementations for Verifiable Credential signing and verification:

### Receipt Signing
```python
from weave.crypto import VCStubs

# Sign a receipt with VC proof
signed_receipt = VCStubs.sign_receipt(receipt_data, private_key)
```

### Receipt Verification
```python
# Verify a receipt's VC proof
is_valid = VCStubs.verify_receipt(signed_receipt, public_key)
```

**Note**: Current implementation includes stub functions. Production deployment would integrate with actual VC libraries and key management systems.

## Storage Backends

### In-Memory Storage
- **Use Case**: Testing and development
- **Persistence**: Data lost on restart
- **Performance**: Fast access, no I/O overhead

### SQLite Storage
- **Use Case**: Single-instance deployments
- **Persistence**: Data persisted to file
- **Performance**: Good for moderate loads

### Future Backends
- PostgreSQL for high-availability deployments
- MongoDB for document-based storage
- Cloud storage backends (AWS RDS, Azure SQL)

## API Endpoints

### Submit CloudEvent
```http
POST /events
Content-Type: application/json

{
    "specversion": "1.0",
    "id": "evt_123",
    "source": "https://orca.ocn.ai/v1",
    "type": "ocn.orca.decision.v1",
    "subject": "txn_abc123",
    "time": "2024-01-21T12:00:00Z",
    "data": { /* event data */ }
}
```

### Retrieve Receipt
```http
GET /receipts/{receipt_id}
```

### List Receipts
```http
GET /receipts?limit=100&offset=0
```

### Get Receipts by Trace ID
```http
GET /receipts/trace/{trace_id}
```

## Compliance & Auditing

### Data Retention
- Receipts can be retained indefinitely (no PII/PCI)
- Hash data is safe for long-term storage
- Audit trails maintained through receipt metadata

### Regulatory Compliance
- **GDPR**: No personal data stored, only hashes
- **PCI DSS**: No payment data stored
- **SOX**: Audit trails via receipt metadata
- **HIPAA**: No health information stored

### Audit Capabilities
- Complete receipt history for each trace_id
- Timestamp tracking for all operations
- Source IP logging (configurable)
- Event type filtering and reporting

## Security Considerations

### Hash Integrity
- SHA-256 provides cryptographic integrity
- Collision resistance prevents hash spoofing
- Consistent JSON serialization ensures reproducibility

### Access Control
- API key authentication (configurable)
- Rate limiting for abuse prevention
- Input validation for all endpoints

### Network Security
- HTTPS/TLS for all communications
- Client IP logging for audit trails
- CORS configuration for web clients

## Monitoring & Observability

### Metrics
- Receipt creation rate
- Hash generation performance
- Storage backend health
- API response times

### Logging
- Receipt creation events
- Error conditions
- Authentication failures
- Performance metrics

### Alerting
- Storage backend failures
- High error rates
- Unusual traffic patterns
- Authentication anomalies

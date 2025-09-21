"""
FastAPI CloudEvents subscriber for Weave receipt storage.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ocn_common.trace import ensure_trace_id, inject_trace_id_ce, trace_middleware

from .crypto import hash_payload, VCStubs
from .logging_setup import get_traced_logger, setup_logging
from .settings import settings
from .store import StorageBackend, get_storage
from .trust_registry import get_trust_registry

# Set up structured logging with redaction
setup_logging(level=settings.log_level, format_type='json')
logger = get_traced_logger(__name__)

app = FastAPI(
    title="Weave CloudEvents Subscriber",
    description="Receives and stores CloudEvents as hash receipts",
    version="0.1.0"
)

# Add trace middleware for automatic trace ID propagation
app = trace_middleware(app)

# Pydantic models for request/response
class CloudEvent(BaseModel):
    """CloudEvent model for validation."""
    specversion: str = Field(..., description="CloudEvents specification version")
    id: str = Field(..., description="Unique event identifier")
    source: str = Field(..., description="Event source URI")
    type: str = Field(..., description="Event type")
    subject: Optional[str] = Field(None, description="Event subject (trace_id)")
    time: str = Field(..., description="Event timestamp")
    datacontenttype: Optional[str] = Field(None, description="Data content type")
    dataschema: Optional[str] = Field(None, description="Data schema URI")
    data: Dict[str, Any] = Field(..., description="Event data payload")
    # Trust Registry fields
    provider_id: Optional[str] = Field(None, description="Credential provider identifier")
    extensions: Optional[Dict[str, Any]] = Field(None, description="CloudEvent extensions")


class ReceiptResponse(BaseModel):
    """Response model for receipt creation."""
    receipt_id: str = Field(..., description="Unique receipt identifier")
    trace_id: str = Field(..., description="Transaction trace identifier")
    event_type: str = Field(..., description="CloudEvent type")
    event_hash: str = Field(..., description="SHA-256 hash of event data")
    time: str = Field(..., description="Receipt creation timestamp")
    status: str = Field(default="stored", description="Receipt status")


class ReceiptListResponse(BaseModel):
    """Response model for receipt listing."""
    receipts: List[Dict[str, Any]] = Field(..., description="List of receipts")
    total: int = Field(..., description="Total number of receipts")
    limit: int = Field(..., description="Page limit")
    offset: int = Field(..., description="Page offset")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")


# Dependency injection for storage
def get_storage_backend():
    """Get storage backend instance."""
    return get_storage()


@app.get("/", response_model=Dict[str, Any])
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Weave CloudEvents Subscriber",
        "version": "0.1.0",
        "status": "operational",
        "endpoints": {
            "events": "/events",
            "receipts": "/receipts",
            "health": "/health"
        }
    }


@app.get("/health", response_model=Dict[str, str])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "weave-subscriber"}


@app.post("/events", response_model=ReceiptResponse, status_code=status.HTTP_201_CREATED)
async def receive_cloud_event(
    event: CloudEvent,
    request: Request,
    storage: StorageBackend = Depends(get_storage_backend)
):
    """
    Receive and store a CloudEvent as a hash receipt.

    This endpoint:
    1. Validates the CloudEvent structure
    2. Checks if the event type is allowed
    3. Enforces trust registry for provider_id (if present)
    4. Generates a hash of the event data
    5. Stores only the hash and metadata (no PII/PCI)
    6. Returns a receipt ID for tracking
    """
    try:
        # Use subject as trace_id, fallback to event id
        # For CloudEvents, we preserve the original trace ID even if it's not UUID4 format
        trace_id = event.subject or event.id

        # Trust Registry enforcement
        provider_id = None

        # Check for provider_id in data first, then extensions (data takes precedence)
        if "provider_id" in event.data:
            provider_id = event.data["provider_id"]
        elif event.extensions and "provider_id" in event.extensions:
            provider_id = event.extensions["provider_id"]

        # If provider_id is present and not empty, validate against trust registry
        if provider_id is not None and provider_id != "":  # Check for valid provider_id
            trust_registry = get_trust_registry()
            if not trust_registry.is_allowed(provider_id):
                logger.warning(f"Trust registry denied provider '{provider_id}' for trace_id '{trace_id}'")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Provider '{provider_id}' not in trust registry allowlist"
                )
            logger.info(f"Trust registry allowed provider '{provider_id}' for trace_id '{trace_id}'")

        # Validate event type is allowed
        if event.type not in settings.allowed_event_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Event type '{event.type}' not allowed. Allowed types: {settings.allowed_event_types}"
            )

        # Generate hash of the event data (this is what we store, not the raw data)
        event_hash = hash_payload(event.data)

        # Prepare metadata (non-sensitive information only)
        metadata = {
            "event_id": event.id,
            "source": event.source,
            "datacontenttype": event.datacontenttype,
            "dataschema": event.dataschema,
            "received_at": datetime.utcnow().isoformat(),
            "client_ip": request.client.host if request.client else None,
            "provider_id": provider_id,  # Include provider_id in metadata
            "trust_verified": provider_id is not None  # Track if trust was verified
        }

        # Store receipt (only hash and metadata, no raw event data)
        receipt_id = storage.store_receipt(
            trace_id=trace_id,
            event_type=event.type,
            event_hash=event_hash,
            metadata=metadata
        )

        logger.info(f"Stored receipt {receipt_id} for event {event.id} (type: {event.type})")

        return ReceiptResponse(
            receipt_id=receipt_id,
            trace_id=trace_id,
            event_type=event.type,
            event_hash=event_hash,
            time=datetime.utcnow().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing CloudEvent {event.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/receipts/{receipt_id}", response_model=Dict[str, Any])
async def get_receipt(
    receipt_id: str,
    storage: StorageBackend = Depends(get_storage_backend)
):
    """Retrieve a receipt by ID."""
    receipt = storage.get_receipt(receipt_id)
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Receipt {receipt_id} not found"
        )
    return receipt


@app.get("/receipts", response_model=ReceiptListResponse)
async def list_receipts(
    trace_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    storage: StorageBackend = Depends(get_storage_backend)
):
    """List receipts with optional filtering by trace_id."""
    if limit > 1000:
        limit = 1000  # Cap limit to prevent abuse

    if trace_id:
        receipts = storage.get_receipts_by_trace_id(trace_id)
        total = len(receipts)
        # Apply pagination
        receipts = receipts[offset:offset + limit]
    else:
        receipts = storage.list_receipts(limit=limit, offset=offset)
        # For SQLite, we'd need a separate count query for total
        # For simplicity, we'll use len() which works for in-memory
        total = len(receipts)  # This is approximate for SQLite

    return ReceiptListResponse(
        receipts=receipts,
        total=total,
        limit=limit,
        offset=offset
    )


@app.get("/receipts/trace/{trace_id}", response_model=List[Dict[str, Any]])
async def get_receipts_by_trace_id(
    trace_id: str,
    storage: StorageBackend = Depends(get_storage_backend)
):
    """Get all receipts for a specific trace_id."""
    receipts = storage.get_receipts_by_trace_id(trace_id)
    return receipts


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "subscriber:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

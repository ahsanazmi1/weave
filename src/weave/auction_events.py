"""
CloudEvent emission for auction bid requests and responses in Weave Phase 3.

Emits ocn.weave.bid_request.v1 and ocn.weave.bid_response.v1 events for
processor auction management and audit trails.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from weave.models import BidRequest, BidResponse, CartSummary, RailCandidate

logger = logging.getLogger(__name__)


class BidRequestData(BaseModel):
    """Data payload for bid request CloudEvent."""
    
    # Core bid request data
    trace_id: str = Field(..., description="Trace identifier")
    auction_id: str = Field(..., description="Auction identifier")
    
    # Context information
    merchant_context: Dict[str, Any] = Field(default_factory=dict, description="Merchant context")
    cart_summary: Dict[str, Any] = Field(default_factory=dict, description="Cart summary")
    
    # Rail candidates and scores
    rail_candidates: List[Dict[str, Any]] = Field(default_factory=list, description="Available rail candidates")
    scores: Dict[str, float] = Field(default_factory=dict, description="Auction scores")
    
    # Explanation and metadata
    explanation: str = Field(..., description="Human-readable explanation")
    
    # Timestamps
    generated_at: datetime = Field(default_factory=datetime.now, description="Bid request generation time")
    expires_at: Optional[datetime] = Field(None, description="Bid request expiration time")


class BidResponseData(BaseModel):
    """Data payload for bid response CloudEvent."""
    
    # Core bid response data
    trace_id: str = Field(..., description="Trace identifier")
    auction_id: str = Field(..., description="Auction identifier")
    processor_id: str = Field(..., description="Processor identifier")
    
    # Bid details
    bps: float = Field(..., ge=0.0, description="Cost in basis points")
    rebate_bps: float = Field(..., ge=0.0, description="Rebate in basis points")
    effective_cost_bps: float = Field(..., ge=0.0, description="Effective cost (max(0, bps - rebate_bps))")
    expected_settlement_days: int = Field(..., ge=0, description="Expected settlement days")
    
    # Context information
    merchant_context: Dict[str, Any] = Field(default_factory=dict, description="Merchant context")
    cart_summary: Dict[str, Any] = Field(default_factory=dict, description="Cart summary")
    
    # Rail candidates and scores
    rail_candidates: List[Dict[str, Any]] = Field(default_factory=list, description="Available rail candidates")
    scores: Dict[str, float] = Field(default_factory=dict, description="Bid scores")
    
    # Processor constraints and metadata
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Processor constraints")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Bid confidence")
    
    # Explanation and metadata
    explanation: str = Field(..., description="Human-readable explanation")
    
    # Timestamps
    generated_at: datetime = Field(default_factory=datetime.now, description="Bid response generation time")
    expires_at: Optional[datetime] = Field(None, description="Bid response expiration time")


class BidRequestEvent(BaseModel):
    """CloudEvent for bid request broadcasting."""
    
    # CloudEvent standard fields
    specversion: str = Field("1.0", description="CloudEvents specification version")
    type: str = Field("ocn.weave.bid_request.v1", description="Event type")
    source: str = Field("weave-auction-manager", description="Event source")
    id: str = Field(..., description="Unique event identifier")
    time: datetime = Field(default_factory=datetime.now, description="Event timestamp")
    datacontenttype: str = Field("application/json", description="Content type")
    subject: str = Field(..., description="Event subject (trace_id)")
    
    # Bid request data
    data: BidRequestData = Field(..., description="Bid request data payload")


class BidResponseEvent(BaseModel):
    """CloudEvent for bid response collection."""
    
    # CloudEvent standard fields
    specversion: str = Field("1.0", description="CloudEvents specification version")
    type: str = Field("ocn.weave.bid_response.v1", description="Event type")
    source: str = Field("weave-processor-connector", description="Event source")
    id: str = Field(..., description="Unique event identifier")
    time: datetime = Field(default_factory=datetime.now, description="Event timestamp")
    datacontenttype: str = Field("application/json", description="Content type")
    subject: str = Field(..., description="Event subject (trace_id)")
    
    # Bid response data
    data: BidResponseData = Field(..., description="Bid response data payload")


def create_bid_request_payload(
    bid_request: BidRequest,
    merchant_context: Optional[Dict[str, Any]] = None,
    explanation: str = "Bid request broadcast to processors"
) -> BidRequestData:
    """
    Create bid request data payload for CloudEvent.
    
    Args:
        bid_request: Bid request object
        merchant_context: Merchant context information
        explanation: Human-readable explanation
        
    Returns:
        Bid request data payload
    """
    # Convert rail candidates to dictionaries
    rail_candidates = [
        {
            "rail_type": rail.rail_type,
            "base_cost_bps": rail.base_cost_bps,
            "settlement_days": rail.settlement_days,
            "risk_score": rail.risk_score,
        }
        for rail in bid_request.rail_candidates
    ]
    
    # Create auction scores (example)
    scores = {
        "total_amount": bid_request.cart_summary.total_amount,
        "item_count": bid_request.cart_summary.item_count,
        "auction_priority": 1.0,
    }
    
    return BidRequestData(
        # Core bid request data
        trace_id=bid_request.trace_id,
        auction_id=bid_request.auction_id,
        
        # Context information
        merchant_context=merchant_context or {},
        cart_summary=bid_request.cart_summary.model_dump(),
        
        # Rail candidates and scores
        rail_candidates=rail_candidates,
        scores=scores,
        
        # Explanation and metadata
        explanation=explanation,
    )


def create_bid_response_payload(
    bid_response: BidResponse,
    merchant_context: Optional[Dict[str, Any]] = None,
    cart_summary: Optional[CartSummary] = None,
    rail_candidates: Optional[List[RailCandidate]] = None,
    explanation: str = "Bid response from processor"
) -> BidResponseData:
    """
    Create bid response data payload for CloudEvent.
    
    Args:
        bid_response: Bid response object
        merchant_context: Merchant context information
        cart_summary: Cart summary information
        rail_candidates: Available rail candidates
        explanation: Human-readable explanation
        
    Returns:
        Bid response data payload
    """
    # Convert rail candidates to dictionaries if provided
    if rail_candidates:
        rail_candidates_dict = [
            {
                "rail_type": rail.rail_type,
                "base_cost_bps": rail.base_cost_bps,
                "settlement_days": rail.settlement_days,
                "risk_score": rail.risk_score,
            }
            for rail in rail_candidates
        ]
    else:
        rail_candidates_dict = []
    
    # Create bid scores
    effective_cost = max(0.0, bid_response.bps - bid_response.rebate_bps)
    scores = {
        "effective_cost_bps": effective_cost,
        "settlement_speed": 1.0 / max(1, bid_response.expected_settlement_days),
        "confidence": bid_response.confidence,
    }
    
    return BidResponseData(
        # Core bid response data
        trace_id=bid_response.trace_id,
        auction_id=bid_response.auction_id,
        processor_id=bid_response.processor_id,
        
        # Bid details
        bps=bid_response.bps,
        rebate_bps=bid_response.rebate_bps,
        effective_cost_bps=effective_cost,
        expected_settlement_days=bid_response.expected_settlement_days,
        
        # Context information
        merchant_context=merchant_context or {},
        cart_summary=cart_summary.model_dump() if cart_summary else {},
        
        # Rail candidates and scores
        rail_candidates=rail_candidates_dict,
        scores=scores,
        
        # Processor constraints and metadata
        constraints=bid_response.constraints,
        confidence=bid_response.confidence,
        
        # Explanation and metadata
        explanation=explanation,
    )


def emit_bid_request_event(
    bid_request: BidRequest,
    merchant_context: Optional[Dict[str, Any]] = None,
    explanation: str = "Bid request broadcast to processors"
) -> BidRequestEvent:
    """
    Emit bid request CloudEvent.
    
    Args:
        bid_request: Bid request object
        merchant_context: Merchant context information
        explanation: Human-readable explanation
        
    Returns:
        Bid request CloudEvent
    """
    # Create data payload
    data = create_bid_request_payload(bid_request, merchant_context, explanation)
    
    # Generate unique event ID
    event_id = f"bid-request-{bid_request.auction_id}-{int(datetime.now().timestamp())}"
    
    # Create CloudEvent
    event = BidRequestEvent(
        id=event_id,
        subject=bid_request.trace_id,
        data=data,
    )
    
    # Log the event (in a real implementation, this would be sent to an event broker)
    logger.info(
        f"Bid request event emitted: {event_id} for auction {bid_request.auction_id}",
        extra={
            "event_id": event_id,
            "trace_id": bid_request.trace_id,
            "auction_id": bid_request.auction_id,
            "rail_candidates": len(bid_request.rail_candidates),
        }
    )
    
    return event


def emit_bid_response_event(
    bid_response: BidResponse,
    merchant_context: Optional[Dict[str, Any]] = None,
    cart_summary: Optional[CartSummary] = None,
    rail_candidates: Optional[List[RailCandidate]] = None,
    explanation: str = "Bid response from processor"
) -> BidResponseEvent:
    """
    Emit bid response CloudEvent.
    
    Args:
        bid_response: Bid response object
        merchant_context: Merchant context information
        cart_summary: Cart summary information
        rail_candidates: Available rail candidates
        explanation: Human-readable explanation
        
    Returns:
        Bid response CloudEvent
    """
    # Create data payload
    data = create_bid_response_payload(
        bid_response, merchant_context, cart_summary, rail_candidates, explanation
    )
    
    # Generate unique event ID
    event_id = f"bid-response-{bid_response.processor_id}-{bid_response.auction_id}-{int(datetime.now().timestamp())}"
    
    # Create CloudEvent
    event = BidResponseEvent(
        id=event_id,
        subject=bid_response.trace_id,
        data=data,
    )
    
    # Log the event (in a real implementation, this would be sent to an event broker)
    logger.info(
        f"Bid response event emitted: {event_id} from {bid_response.processor_id}",
        extra={
            "event_id": event_id,
            "trace_id": bid_response.trace_id,
            "auction_id": bid_response.auction_id,
            "processor_id": bid_response.processor_id,
            "effective_cost_bps": bid_response.bps - bid_response.rebate_bps,
        }
    )
    
    return event


def validate_bid_request_event(event: BidRequestEvent) -> bool:
    """
    Validate bid request CloudEvent structure.
    
    Args:
        event: Bid request CloudEvent to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Validate CloudEvent structure
        if not event.specversion or event.specversion != "1.0":
            logger.error("Invalid CloudEvent specversion")
            return False
        
        if not event.type or event.type != "ocn.weave.bid_request.v1":
            logger.error("Invalid CloudEvent type")
            return False
        
        if not event.id or not event.subject:
            logger.error("Missing required CloudEvent fields")
            return False
        
        # Validate data payload
        data = event.data
        if not data.trace_id or not data.auction_id:
            logger.error("Missing required bid request fields")
            return False
        
        logger.debug(f"Bid request event validation passed: {event.id}")
        return True
        
    except Exception as e:
        logger.error(f"Bid request event validation failed: {e}")
        return False


def validate_bid_response_event(event: BidResponseEvent) -> bool:
    """
    Validate bid response CloudEvent structure.
    
    Args:
        event: Bid response CloudEvent to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Validate CloudEvent structure
        if not event.specversion or event.specversion != "1.0":
            logger.error("Invalid CloudEvent specversion")
            return False
        
        if not event.type or event.type != "ocn.weave.bid_response.v1":
            logger.error("Invalid CloudEvent type")
            return False
        
        if not event.id or not event.subject:
            logger.error("Missing required CloudEvent fields")
            return False
        
        # Validate data payload
        data = event.data
        if not data.trace_id or not data.auction_id or not data.processor_id:
            logger.error("Missing required bid response fields")
            return False
        
        if data.bps < 0 or data.rebate_bps < 0:
            logger.error("Invalid bid pricing")
            return False
        
        if not (0.0 <= data.confidence <= 1.0):
            logger.error("Invalid confidence range")
            return False
        
        logger.debug(f"Bid response event validation passed: {event.id}")
        return True
        
    except Exception as e:
        logger.error(f"Bid response event validation failed: {e}")
        return False


def get_bid_request_event_schema() -> Dict[str, Any]:
    """
    Get JSON schema for bid request CloudEvent.
    
    Returns:
        JSON schema for bid request events
    """
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "specversion": {
                "type": "string",
                "const": "1.0"
            },
            "type": {
                "type": "string",
                "const": "ocn.weave.bid_request.v1"
            },
            "source": {
                "type": "string",
                "pattern": "^weave-auction-manager$"
            },
            "id": {
                "type": "string",
                "pattern": "^bid-request-.*$"
            },
            "time": {
                "type": "string",
                "format": "date-time"
            },
            "datacontenttype": {
                "type": "string",
                "const": "application/json"
            },
            "subject": {
                "type": "string"
            },
            "data": {
                "type": "object",
                "properties": {
                    "trace_id": {"type": "string"},
                    "auction_id": {"type": "string"},
                    "explanation": {"type": "string"},
                    "rail_candidates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "rail_type": {"type": "string"},
                                "base_cost_bps": {"type": "number"},
                                "settlement_days": {"type": "integer"},
                                "risk_score": {"type": "number"}
                            }
                        }
                    }
                },
                "required": ["trace_id", "auction_id", "explanation"]
            }
        },
        "required": [
            "specversion", "type", "source", "id", "time", 
            "datacontenttype", "subject", "data"
        ]
    }


def get_bid_response_event_schema() -> Dict[str, Any]:
    """
    Get JSON schema for bid response CloudEvent.
    
    Returns:
        JSON schema for bid response events
    """
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "specversion": {
                "type": "string",
                "const": "1.0"
            },
            "type": {
                "type": "string",
                "const": "ocn.weave.bid_response.v1"
            },
            "source": {
                "type": "string",
                "pattern": "^weave-processor-connector$"
            },
            "id": {
                "type": "string",
                "pattern": "^bid-response-.*$"
            },
            "time": {
                "type": "string",
                "format": "date-time"
            },
            "datacontenttype": {
                "type": "string",
                "const": "application/json"
            },
            "subject": {
                "type": "string"
            },
            "data": {
                "type": "object",
                "properties": {
                    "trace_id": {"type": "string"},
                    "auction_id": {"type": "string"},
                    "processor_id": {"type": "string"},
                    "bps": {"type": "number", "minimum": 0.0},
                    "rebate_bps": {"type": "number", "minimum": 0.0},
                    "effective_cost_bps": {"type": "number", "minimum": 0.0},
                    "expected_settlement_days": {"type": "integer", "minimum": 0},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "explanation": {"type": "string"},
                    "constraints": {"type": "object"}
                },
                "required": [
                    "trace_id", "auction_id", "processor_id", "bps", "rebate_bps",
                    "effective_cost_bps", "expected_settlement_days", "confidence", "explanation"
                ]
            }
        },
        "required": [
            "specversion", "type", "source", "id", "time", 
            "datacontenttype", "subject", "data"
        ]
    }

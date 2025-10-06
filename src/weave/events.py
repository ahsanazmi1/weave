"""
CloudEvents emission functions for Weave Phase 8.

Provides standardized CloudEvent emission for bid requests and responses,
integrating with the OCN event schema system.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.weave.models import BidRequest, BidResponse

logger = logging.getLogger(__name__)


def emit_bid_request_event(
    bid_request: BidRequest,
    source: str = "https://weave.ocn.ai/bid-request"
) -> Dict[str, Any]:
    """
    Emit a CloudEvent for bid request.
    
    Args:
        bid_request: Bid request to emit as event
        source: Event source URI
        
    Returns:
        CloudEvent dictionary
    """
    try:
        # Prepare bid request data
        bid_request_data = {
            "trace_id": bid_request.trace_id,
            "auction_id": bid_request.auction_id,
            "cart_summary": {
                "total_amount": bid_request.cart_summary.total_amount,
                "currency": bid_request.cart_summary.currency,
                "item_count": bid_request.cart_summary.item_count,
                "merchant_id": bid_request.cart_summary.merchant_id,
                "merchant_category": bid_request.cart_summary.merchant_category,
                "channel": bid_request.cart_summary.channel
            },
            "rail_candidates": [
                {
                    "rail_type": candidate.rail_type,
                    "instrument_type": candidate.instrument_type,
                    "base_cost_bps": candidate.base_cost_bps,
                    "settlement_days": candidate.settlement_days,
                    "risk_score": candidate.risk_score,
                    "is_real_time": candidate.is_real_time,
                    "is_cross_border": candidate.is_cross_border,
                    "max_amount": candidate.max_amount,
                    "min_amount": candidate.min_amount
                }
                for candidate in bid_request.rail_candidates
            ],
            "timestamp": bid_request.timestamp.isoformat()
        }
        
        # Create CloudEvent
        cloud_event = {
            "specversion": "1.0",
            "type": "ocn.weave.bid_request.v1",
            "source": source,
            "id": str(uuid.uuid4()),
            "time": datetime.now().isoformat() + "Z",
            "datacontenttype": "application/json",
            "data": bid_request_data,
            "subject": f"auction/{bid_request.auction_id}",
            "ocn": {
                "trace_id": bid_request.trace_id,
                "auction_id": bid_request.auction_id,
                "merchant_id": bid_request.cart_summary.merchant_id,
                "total_amount": bid_request.cart_summary.total_amount,
                "currency": bid_request.cart_summary.currency,
                "rail_candidates_count": len(bid_request.rail_candidates)
            }
        }
        
        # Emit event (in production, this would send to event stream)
        logger.info(f"Emitted bid request event for trace {bid_request.trace_id}, auction {bid_request.auction_id}")
        
        return cloud_event
        
    except Exception as e:
        logger.error(f"Failed to emit bid request event: {str(e)}")
        raise


def emit_bid_response_event(
    bid_response: BidResponse,
    raw_response: Optional[Dict[str, Any]] = None,
    source: str = "https://weave.ocn.ai/bid-response"
) -> Dict[str, Any]:
    """
    Emit a CloudEvent for bid response.
    
    Args:
        bid_response: Bid response to emit as event
        raw_response: Raw response from processor (optional)
        source: Event source URI
        
    Returns:
        CloudEvent dictionary
    """
    try:
        # Prepare bid response data
        bid_response_data = {
            "trace_id": bid_response.trace_id,
            "processor_id": bid_response.processor_id,
            "auction_id": bid_response.auction_id,
            "bps": bid_response.bps,
            "rebate_bps": bid_response.rebate_bps,
            "expected_settlement_days": bid_response.expected_settlement_days,
            "constraints": bid_response.constraints,
            "timestamp": bid_response.timestamp.isoformat(),
            "raw_response": raw_response
        }
        
        # Create CloudEvent
        cloud_event = {
            "specversion": "1.0",
            "type": "ocn.weave.bid_response.v1",
            "source": source,
            "id": str(uuid.uuid4()),
            "time": datetime.now().isoformat() + "Z",
            "datacontenttype": "application/json",
            "data": bid_response_data,
            "subject": f"auction/{bid_response.auction_id}/processor/{bid_response.processor_id}",
            "ocn": {
                "trace_id": bid_response.trace_id,
                "auction_id": bid_response.auction_id,
                "processor_id": bid_response.processor_id,
                "bps": bid_response.bps,
                "rebate_bps": bid_response.rebate_bps,
                "settlement_days": bid_response.expected_settlement_days,
                "rail_type": bid_response.constraints.get("rail_type"),
                "instrument_type": bid_response.constraints.get("instrument_type")
            }
        }
        
        # Emit event (in production, this would send to event stream)
        logger.info(f"Emitted bid response event for trace {bid_response.trace_id}, processor {bid_response.processor_id}")
        
        return cloud_event
        
    except Exception as e:
        logger.error(f"Failed to emit bid response event: {str(e)}")
        raise


def emit_auction_completion_event(
    auction_result: Dict[str, Any],
    source: str = "https://weave.ocn.ai/auction-completion"
) -> Dict[str, Any]:
    """
    Emit a CloudEvent for auction completion.
    
    Args:
        auction_result: Auction result data
        source: Event source URI
        
    Returns:
        CloudEvent dictionary
    """
    try:
        # Create CloudEvent
        cloud_event = {
            "specversion": "1.0",
            "type": "ocn.weave.auction_completion.v1",
            "source": source,
            "id": str(uuid.uuid4()),
            "time": datetime.now().isoformat() + "Z",
            "datacontenttype": "application/json",
            "data": auction_result,
            "subject": f"auction/{auction_result.get('auction_id', 'unknown')}",
            "ocn": {
                "trace_id": auction_result.get("trace_id"),
                "auction_id": auction_result.get("auction_id"),
                "winner_processor": auction_result.get("winner", {}).get("processor_id"),
                "total_participants": auction_result.get("total_participants"),
                "total_bids": len(auction_result.get("all_bids", []))
            }
        }
        
        # Emit event (in production, this would send to event stream)
        logger.info(f"Emitted auction completion event for auction {auction_result.get('auction_id')}")
        
        return cloud_event
        
    except Exception as e:
        logger.error(f"Failed to emit auction completion event: {str(e)}")
        raise


def emit_processor_integration_event(
    processor_id: str,
    event_type: str,
    event_data: Dict[str, Any],
    source: str = "https://weave.ocn.ai/processor-integration"
) -> Dict[str, Any]:
    """
    Emit a CloudEvent for processor integration events.
    
    Args:
        processor_id: Processor identifier
        event_type: Type of integration event
        event_data: Event-specific data
        source: Event source URI
        
    Returns:
        CloudEvent dictionary
    """
    try:
        # Create CloudEvent
        cloud_event = {
            "specversion": "1.0",
            "type": f"ocn.weave.processor_{event_type}.v1",
            "source": source,
            "id": str(uuid.uuid4()),
            "time": datetime.now().isoformat() + "Z",
            "datacontenttype": "application/json",
            "data": {
                "processor_id": processor_id,
                "event_type": event_type,
                **event_data
            },
            "subject": f"processor/{processor_id}/{event_type}",
            "ocn": {
                "processor_id": processor_id,
                "event_type": event_type,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Emit event (in production, this would send to event stream)
        logger.info(f"Emitted processor {event_type} event for processor {processor_id}")
        
        return cloud_event
        
    except Exception as e:
        logger.error(f"Failed to emit processor integration event: {str(e)}")
        raise









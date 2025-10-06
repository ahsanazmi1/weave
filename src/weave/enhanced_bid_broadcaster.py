"""
Enhanced bid broadcaster for Weave Phase 8.

Integrates with Carat, Stripe, and Adyen connectors to broadcast bid requests
and aggregate responses into shared traces.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.weave.connectors import (
    get_carat_connector,
    get_stripe_connector, 
    get_adyen_connector
)
from src.weave.models import (
    BidRequest, BidResponse, CartSummary, RailCandidate
)
from src.weave.events import (
    emit_bid_request_event,
    emit_bid_response_event
)

logger = logging.getLogger(__name__)


class EnhancedBidBroadcaster:
    """
    Enhanced bid broadcaster that integrates with real payment processor connectors.
    
    Broadcasts bid requests to Carat, Stripe, and Adyen connectors simultaneously
    and aggregates responses into a shared trace for comprehensive auction management.
    """
    
    def __init__(self, max_workers: int = 10):
        """
        Initialize enhanced bid broadcaster.
        
        Args:
            max_workers: Maximum number of worker threads for concurrent processing
        """
        self.max_workers = max_workers
        self.connectors = {
            "carat": get_carat_connector(),
            "stripe": get_stripe_connector(),
            "adyen": get_adyen_connector()
        }
        logger.info(f"Enhanced bid broadcaster initialized with {len(self.connectors)} connectors")
    
    def broadcast_bid_requests(
        self,
        bid_requests: List[BidRequest],
        emit_events: bool = True
    ) -> Tuple[List[BidResponse], Dict[str, Any]]:
        """
        Broadcast bid requests to all connectors and aggregate responses.
        
        Args:
            bid_requests: List of bid requests to broadcast
            emit_events: Whether to emit CloudEvents for bid requests and responses
            
        Returns:
            Tuple of (aggregated_bid_responses, broadcast_metadata)
        """
        all_bid_responses = []
        broadcast_metadata = {
            "total_requests": len(bid_requests),
            "connectors_contacted": [],
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Emit bid request events if requested
        if emit_events:
            for bid_request in bid_requests:
                try:
                    emit_bid_request_event(bid_request)
                except Exception as e:
                    logger.warning(f"Failed to emit bid request event: {str(e)}")
        
        # Process each bid request concurrently
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all connector requests
            future_to_connector = {}
            
            for bid_request in bid_requests:
                for connector_name, connector in self.connectors.items():
                    future = executor.submit(
                        self._process_connector_request,
                        connector_name,
                        connector,
                        bid_request
                    )
                    future_to_connector[future] = (connector_name, bid_request.trace_id)
            
            # Collect results as they complete
            for future in as_completed(future_to_connector):
                connector_name, trace_id = future_to_connector[future]
                
                try:
                    start_time = datetime.now()
                    result = future.result()
                    response_time = (datetime.now() - start_time).total_seconds() * 1000
                    
                    broadcast_metadata["response_times"][connector_name] = response_time
                    
                    if result["success"]:
                        broadcast_metadata["successful_requests"] += 1
                        
                        # Parse connector response
                        connector_responses = result["connector"].parse_bid_response(result["response"])
                        all_bid_responses.extend(connector_responses)
                        
                        # Emit bid response events if requested
                        if emit_events:
                            for bid_response in connector_responses:
                                try:
                                    emit_bid_response_event(bid_response, result["response"])
                                except Exception as e:
                                    logger.warning(f"Failed to emit bid response event: {str(e)}")
                        
                        logger.info(f"Successfully processed {connector_name} request for trace {trace_id}")
                    else:
                        broadcast_metadata["failed_requests"] += 1
                        logger.warning(f"Failed to process {connector_name} request for trace {trace_id}: {result['error']}")
                    
                    if connector_name not in broadcast_metadata["connectors_contacted"]:
                        broadcast_metadata["connectors_contacted"].append(connector_name)
                        
                except Exception as e:
                    broadcast_metadata["failed_requests"] += 1
                    logger.error(f"Exception processing {connector_name} request for trace {trace_id}: {str(e)}")
        
        logger.info(f"Broadcast completed: {len(all_bid_responses)} total responses from {len(broadcast_metadata['connectors_contacted'])} connectors")
        return all_bid_responses, broadcast_metadata
    
    def _process_connector_request(
        self,
        connector_name: str,
        connector: Any,
        bid_request: BidRequest
    ) -> Dict[str, Any]:
        """
        Process a single connector request.
        
        Args:
            connector_name: Name of the connector
            connector: Connector instance
            bid_request: Bid request to process
            
        Returns:
            Dictionary containing success status and response data
        """
        try:
            # Send bid request to connector
            response = connector.send_bid_request(bid_request)
            
            return {
                "success": True,
                "connector": connector,
                "response": response,
                "connector_name": connector_name,
                "trace_id": bid_request.trace_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "connector_name": connector_name,
                "trace_id": bid_request.trace_id
            }
    
    def get_connector_summary(self) -> Dict[str, Any]:
        """Get summary of available connectors and their capabilities."""
        summary = {}
        
        for connector_name, connector in self.connectors.items():
            summary[connector_name] = {
                "connector_id": connector.connector_id,
                "supported_rails": connector.supported_rails,
                "supported_instruments": connector.supported_instruments,
                "base_url": connector.base_url,
                "has_api_key": connector.api_key is not None
            }
        
        return summary
    
    def test_connector_connectivity(self) -> Dict[str, Dict[str, Any]]:
        """
        Test connectivity to all connectors.
        
        Returns:
            Dictionary with connectivity status for each connector
        """
        connectivity_status = {}
        
        for connector_name, connector in self.connectors.items():
            try:
                # Create a test bid request
                test_cart = CartSummary(
                    total_amount=100.0,
                    currency="USD",
                    item_count=1,
                    merchant_id="test_merchant",
                    merchant_category="test",
                    channel="test"
                )
                
                test_candidates = [
                    RailCandidate(
                        rail_type="Card",
                        instrument_type="credit_card",
                        base_cost_bps=200.0,
                        settlement_days=2,
                        risk_score=0.4,
                        is_real_time=True,
                        is_cross_border=True,
                        max_amount=1000.0,
                        min_amount=1.0
                    )
                ]
                
                test_request = BidRequest(
                    trace_id="test_connectivity",
                    cart_summary=test_cart,
                    rail_candidates=test_candidates,
                    auction_id="test_auction",
                    timestamp=datetime.now()
                )
                
                # Test the connector
                response = connector.send_bid_request(test_request)
                
                connectivity_status[connector_name] = {
                    "status": "connected" if response.get("success", False) else "error",
                    "response_time_ms": response.get("response_time_ms", 0),
                    "error": response.get("error") if not response.get("success", False) else None,
                    "supports_test_rail": True
                }
                
            except Exception as e:
                connectivity_status[connector_name] = {
                    "status": "error",
                    "response_time_ms": 0,
                    "error": str(e),
                    "supports_test_rail": False
                }
        
        return connectivity_status


# Global instance
_enhanced_bid_broadcaster = None


def get_enhanced_bid_broadcaster(max_workers: int = 10) -> EnhancedBidBroadcaster:
    """Get global enhanced bid broadcaster instance."""
    global _enhanced_bid_broadcaster
    if _enhanced_bid_broadcaster is None:
        _enhanced_bid_broadcaster = EnhancedBidBroadcaster(max_workers)
    return _enhanced_bid_broadcaster









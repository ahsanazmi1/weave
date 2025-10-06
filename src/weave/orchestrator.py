"""
Enhanced auction orchestrator for Weave Phase 4.

Provides comprehensive bid broadcasting, response aggregation, and audit logging
for payment processor auctions with complete trace linking.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from weave.models import (
    CartSummary, 
    RailCandidate, 
    BidRequest, 
    BidResponse, 
    AuctionResult,
    PaymentInstruction,
    ProcessorAuthResult
)
from weave.auction_events import emit_bid_request_event, emit_bid_response_event
from weave.connectors.connector_registry import get_connector_registry
from weave.signing import get_audit_logger, get_receipt_signer

logger = logging.getLogger(__name__)


class BidBroadcaster:
    """
    Bid broadcasting service for processor auctions.
    
    Broadcasts bid requests to all available processors and aggregates
    responses into a shared trace for comprehensive audit trails.
    """
    
    def __init__(self):
        """Initialize bid broadcaster."""
        self.registry = get_connector_registry()
        self.audit_logger = get_audit_logger()
        logger.info("Bid broadcaster initialized")
    
    def broadcast_bid_requests(
        self,
        trace_id: str,
        cart_summary: CartSummary,
        rail_candidates: List[RailCandidate]
    ) -> List[BidRequest]:
        """
        Broadcast bid requests to all available processors.
        
        Args:
            trace_id: Unique transaction trace ID
            cart_summary: Cart summary for auction
            rail_candidates: Available rail candidates
            
        Returns:
            List of bid requests sent to processors
        """
        auction_id = str(uuid.uuid4())
        bid_requests = []
        
        # Get all available processors
        available_processors = self.registry.get_available_processors()
        logger.info(f"Broadcasting bid requests to {len(available_processors)} processors: {available_processors}")
        
        # Create bid requests for each processor
        for processor_id in available_processors:
            bid_request = BidRequest(
                trace_id=trace_id,
                cart_summary=cart_summary,
                rail_candidates=rail_candidates,
                auction_id=auction_id,
                timestamp=datetime.now()
            )
            
            bid_requests.append(bid_request)
            
            # Emit bid request event
            try:
                event = emit_bid_request_event(
                    bid_request=bid_request,
                    processor_id=processor_id,
                    source="https://weave.ocn.ai/bid-broadcast"
                )
                logger.info(f"Emitted bid request event for processor {processor_id}")
            except Exception as e:
                logger.error(f"Failed to emit bid request event for {processor_id}: {e}")
        
        # Log bid broadcast
        self.audit_logger.log_bid_broadcast(bid_requests)
        
        logger.info(f"Broadcast {len(bid_requests)} bid requests for auction {auction_id}")
        return bid_requests
    
    def collect_bid_responses(
        self,
        bid_requests: List[BidRequest],
        timeout_seconds: int = 30
    ) -> List[BidResponse]:
        """
        Collect bid responses from processors.
        
        Args:
            bid_requests: Bid requests sent to processors
            timeout_seconds: Timeout for response collection
            
        Returns:
            List of bid responses received
        """
        bid_responses = []
        
        for bid_request in bid_requests:
            try:
                # Get processor connector
                processor_id = self._extract_processor_id_from_trace(bid_request.trace_id)
                connector = self.registry.get_connector(processor_id)
                
                if connector:
                    # Generate bid response
                    bid_response = connector.generate_bid(bid_request)
                    bid_responses.append(bid_response)
                    
                    # Emit bid response event
                    try:
                        event = emit_bid_response_event(
                            bid_response=bid_response,
                            source="https://weave.ocn.ai/bid-response"
                        )
                        logger.info(f"Emitted bid response event for processor {processor_id}")
                    except Exception as e:
                        logger.error(f"Failed to emit bid response event for {processor_id}: {e}")
                else:
                    logger.warning(f"No connector found for processor {processor_id}")
                    
            except Exception as e:
                logger.error(f"Failed to collect bid response for request {bid_request.auction_id}: {e}")
        
        logger.info(f"Collected {len(bid_responses)} bid responses from {len(bid_requests)} requests")
        return bid_responses
    
    def _extract_processor_id_from_trace(self, trace_id: str) -> str:
        """Extract processor ID from trace ID (placeholder implementation)."""
        # In a real implementation, this would parse the trace ID to determine
        # which processor the request was intended for
        # For now, we'll use a simple mapping based on available processors
        available_processors = self.registry.get_available_processors()
        # Use a simple hash-based distribution
        processor_index = hash(trace_id) % len(available_processors)
        return available_processors[processor_index]


class ResponseAggregator:
    """
    Response aggregation service for auction results.
    
    Aggregates bid responses into shared traces and determines auction winners
    with comprehensive audit logging.
    """
    
    def __init__(self):
        """Initialize response aggregator."""
        self.audit_logger = get_audit_logger()
        logger.info("Response aggregator initialized")
    
    def aggregate_responses(
        self,
        bid_requests: List[BidRequest],
        bid_responses: List[BidResponse]
    ) -> AuctionResult:
        """
        Aggregate bid responses and determine auction winner.
        
        Args:
            bid_requests: Original bid requests sent
            bid_responses: Bid responses received from processors
            
        Returns:
            Final auction result with winner and explanations
        """
        if not bid_responses:
            raise ValueError("No bid responses to aggregate")
        
        # Determine winner based on effective cost
        winner = min(bid_responses, key=lambda r: r.effective_cost_bps or (r.bps - r.rebate_bps))
        
        # Calculate effective cost
        effective_cost_bps = winner.effective_cost_bps or (winner.bps - winner.rebate_bps)
        
        # Generate auction summary
        summary = self._generate_auction_summary(bid_responses, winner)
        
        # Create auction result
        auction_result = AuctionResult(
            trace_id=winner.trace_id,
            auction_id=winner.auction_id,
            winning_processor=winner.processor_id,
            winning_bid=winner,
            all_bids=bid_responses,
            effective_cost_bps=effective_cost_bps,
            summary=summary,
            timestamp=datetime.now()
        )
        
        # Log auction result
        self.audit_logger.log_auction_result(auction_result)
        
        logger.info(f"Auction {winner.auction_id} completed with winner {winner.processor_id}")
        return auction_result
    
    def _generate_auction_summary(
        self,
        bid_responses: List[BidResponse],
        winner: BidResponse
    ) -> str:
        """Generate human-readable auction summary."""
        total_bids = len(bid_responses)
        winner_cost = winner.effective_cost_bps or (winner.bps - winner.rebate_bps)
        
        summary = f"Auction completed with {total_bids} bids. "
        summary += f"Winner: {winner.processor_id} with effective cost {winner_cost:.2f} bps. "
        summary += f"Winner confidence: {winner.confidence:.2f}. "
        summary += f"Expected settlement: {winner.expected_settlement_days} days."
        
        return summary


class PaymentInstructionProcessor:
    """
    Payment instruction processing service.
    
    Processes final payment instructions from Orca and coordinates with
    processor connectors for transaction execution.
    """
    
    def __init__(self):
        """Initialize payment instruction processor."""
        self.registry = get_connector_registry()
        self.audit_logger = get_audit_logger()
        logger.info("Payment instruction processor initialized")
    
    def process_payment_instruction(
        self,
        payment_instruction: PaymentInstruction
    ) -> ProcessorAuthResult:
        """
        Process payment instruction through selected processor.
        
        Args:
            payment_instruction: Payment instruction from Orca
            
        Returns:
            Processor authorization result
        """
        # Log payment instruction
        self.audit_logger.log_payment_instruction(payment_instruction)
        
        # Get processor connector
        processor_id = payment_instruction.selected_processor
        connector = self.registry.get_connector(processor_id)
        
        if not connector:
            raise ValueError(f"No connector found for processor {processor_id}")
        
        # Simulate processor authorization
        auth_result = self._simulate_processor_auth(payment_instruction, connector)
        
        # Log processor auth result
        self.audit_logger.log_processor_auth_result(auth_result)
        
        logger.info(f"Processed payment instruction {payment_instruction.instruction_id} through {processor_id}")
        return auth_result
    
    def _simulate_processor_auth(
        self,
        payment_instruction: PaymentInstruction,
        connector
    ) -> ProcessorAuthResult:
        """Simulate processor authorization (placeholder implementation)."""
        # In a real implementation, this would call the actual processor API
        # For now, we'll simulate based on the connector's characteristics
        
        # Simulate approval/decline based on amount and processor
        if payment_instruction.amount > 10000:  # High value transaction
            status = "declined"
            decline_reason = "Transaction amount exceeds processor limit"
        else:
            status = "approved"
            decline_reason = None
        
        # Generate auth code if approved
        auth_code = f"AUTH_{uuid.uuid4().hex[:8].upper()}" if status == "approved" else None
        
        # Calculate processor fee based on instruction
        processor_fee = payment_instruction.effective_cost * payment_instruction.amount / 10000
        
        return ProcessorAuthResult(
            auth_id=str(uuid.uuid4()),
            processor_id=payment_instruction.selected_processor,
            status=status,
            auth_code=auth_code,
            decline_reason=decline_reason,
            processor_fee=processor_fee,
            settlement_time_actual=payment_instruction.settlement_time_hours,
            processor_metadata={
                "instruction_id": payment_instruction.instruction_id,
                "rail_type": payment_instruction.selected_rail,
                "instrument": payment_instruction.selected_instrument
            }
        )


class WeaveOrchestrator:
    """
    Main Weave orchestrator for Phase 4.
    
    Coordinates bid broadcasting, response aggregation, payment instruction
    processing, and receipt signing with comprehensive audit logging.
    """
    
    def __init__(self):
        """Initialize Weave orchestrator."""
        self.bid_broadcaster = BidBroadcaster()
        self.response_aggregator = ResponseAggregator()
        self.instruction_processor = PaymentInstructionProcessor()
        self.receipt_signer = get_receipt_signer()
        logger.info("Weave orchestrator initialized")
    
    def run_complete_auction_flow(
        self,
        trace_id: str,
        cart_summary: CartSummary,
        rail_candidates: List[RailCandidate]
    ) -> Dict[str, Any]:
        """
        Run complete auction flow from bid broadcasting to receipt signing.
        
        Args:
            trace_id: Unique transaction trace ID
            cart_summary: Cart summary for auction
            rail_candidates: Available rail candidates
            
        Returns:
            Complete auction flow results with signed receipt
        """
        logger.info(f"Starting complete auction flow for trace {trace_id}")
        
        # Step 1: Broadcast bid requests
        bid_requests = self.bid_broadcaster.broadcast_bid_requests(
            trace_id, cart_summary, rail_candidates
        )
        
        # Step 2: Collect bid responses
        bid_responses = self.bid_broadcaster.collect_bid_responses(bid_requests)
        
        # Step 3: Aggregate responses and determine winner
        auction_result = self.response_aggregator.aggregate_responses(
            bid_requests, bid_responses
        )
        
        # Step 4: Create payment instruction (simulated from Orca)
        payment_instruction = self._create_payment_instruction_from_auction(
            auction_result, cart_summary
        )
        
        # Step 5: Process payment instruction
        processor_auth_result = self.instruction_processor.process_payment_instruction(
            payment_instruction
        )
        
        # Step 6: Create signed receipt
        signed_receipt = self.receipt_signer.create_signed_receipt(
            payment_instruction=payment_instruction,
            processor_auth_result=processor_auth_result,
            auction_result=auction_result,
            bid_requests=bid_requests,
            bid_responses=bid_responses
        )
        
        # Return complete flow results
        return {
            "trace_id": trace_id,
            "auction_result": auction_result,
            "payment_instruction": payment_instruction,
            "processor_auth_result": processor_auth_result,
            "signed_receipt": signed_receipt,
            "bid_requests": bid_requests,
            "bid_responses": bid_responses,
            "flow_completed_at": datetime.now()
        }
    
    def _create_payment_instruction_from_auction(
        self,
        auction_result: AuctionResult,
        cart_summary: CartSummary
    ) -> PaymentInstruction:
        """Create payment instruction from auction result (simulated Orca output)."""
        return PaymentInstruction(
            instruction_id=str(uuid.uuid4()),
            trace_id=auction_result.trace_id,
            selected_rail="ACH",  # Simplified for demo
            selected_processor=auction_result.winning_processor,
            selected_instrument="bank_transfer",
            amount=cart_summary.total_amount,
            currency=cart_summary.currency,
            effective_cost=auction_result.effective_cost_bps,
            settlement_time_hours=auction_result.winning_bid.expected_settlement_days * 24,
            confidence=auction_result.winning_bid.confidence,
            explanation=f"Selected {auction_result.winning_processor} based on auction result",
            alternatives=[
                {
                    "processor": bid.processor_id,
                    "cost": bid.effective_cost_bps or (bid.bps - bid.rebate_bps),
                    "confidence": bid.confidence
                }
                for bid in auction_result.all_bids
                if bid.processor_id != auction_result.winning_processor
            ],
            constraints_applied=[
                {"type": "auction_winner", "processor": auction_result.winning_processor}
            ],
            metadata={
                "auction_id": auction_result.auction_id,
                "merchant_id": cart_summary.merchant_id
            }
        )


# Global instances
_orchestrator = None


def get_orchestrator() -> WeaveOrchestrator:
    """Get global Weave orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = WeaveOrchestrator()
    return _orchestrator


"""
Processor auction system for Weave Phase 3.

Implements bid request broadcasting, response aggregation, and auction management
for payment processor selection (Carat, Adyen, Stripe).
"""

import json
import logging
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from weave.models import CartSummary, RailCandidate, BidRequest, BidResponse, AuctionResult
from weave.auction_events import emit_bid_request_event, emit_bid_response_event
from weave.llm.explain import explain_auction_result_llm, is_auction_llm_configured

logger = logging.getLogger(__name__)


class ProcessorConnector:
    """Base class for processor connectors."""
    
    def __init__(self, processor_id: str, deterministic_seed: int = 42):
        """Initialize processor connector."""
        self.processor_id = processor_id
        self.deterministic_seed = deterministic_seed
        random.seed(deterministic_seed)
        np.random.seed(deterministic_seed)
        
        logger.info(f"Processor connector initialized: {processor_id}")
    
    def generate_bid(self, bid_request: BidRequest) -> BidResponse:
        """
        Generate deterministic bid response.
        
        Args:
            bid_request: Bid request from auction
            
        Returns:
            Bid response with pricing and constraints
        """
        # Processor-specific pricing logic (stub implementation)
        if self.processor_id == "stripe":
            return self._generate_stripe_bid(bid_request)
        elif self.processor_id == "adyen":
            return self._generate_adyen_bid(bid_request)
        elif self.processor_id == "carat":
            return self._generate_carat_bid(bid_request)
        else:
            return self._generate_generic_bid(bid_request)
    
    def _generate_stripe_bid(self, bid_request: BidRequest) -> BidResponse:
        """Generate Stripe-specific bid."""
        # Stripe typically has competitive pricing with good rebates
        base_bps = 150.0  # 1.5% base rate
        rebate_bps = random.uniform(5.0, 15.0)  # 5-15 bps rebate
        settlement_days = 1  # Next day settlement
        
        # Add some deterministic variation based on cart
        cart_factor = min(1.2, bid_request.cart_summary.total_amount / 1000.0)
        bps = base_bps * cart_factor
        
        return BidResponse(
            trace_id=bid_request.trace_id,
            processor_id="stripe",
            auction_id=bid_request.auction_id,
            bps=bps,
            rebate_bps=rebate_bps,
            expected_settlement_days=settlement_days,
            constraints={
                "min_amount": 0.50,
                "max_amount": 100000.0,
                "supported_currencies": ["USD", "EUR", "GBP"],
                "risk_tolerance": "medium"
            },
            confidence=0.9
        )
    
    def _generate_adyen_bid(self, bid_request: BidRequest) -> BidResponse:
        """Generate Adyen-specific bid."""
        # Adyen has competitive rates with good international support
        base_bps = 145.0  # 1.45% base rate
        rebate_bps = random.uniform(3.0, 12.0)  # 3-12 bps rebate
        settlement_days = 2  # 2-day settlement
        
        # Volume-based pricing
        volume_factor = min(1.1, bid_request.cart_summary.total_amount / 2000.0)
        bps = base_bps * volume_factor
        
        return BidResponse(
            trace_id=bid_request.trace_id,
            processor_id="adyen",
            auction_id=bid_request.auction_id,
            bps=bps,
            rebate_bps=rebate_bps,
            expected_settlement_days=settlement_days,
            constraints={
                "min_amount": 1.0,
                "max_amount": 500000.0,
                "supported_currencies": ["USD", "EUR", "GBP", "CAD", "AUD"],
                "risk_tolerance": "high"
            },
            confidence=0.85
        )
    
    def _generate_carat_bid(self, bid_request: BidRequest) -> BidResponse:
        """Generate Carat-specific bid."""
        # Carat focuses on enterprise with volume discounts
        base_bps = 140.0  # 1.4% base rate
        rebate_bps = random.uniform(8.0, 20.0)  # 8-20 bps rebate
        settlement_days = 1  # Next day settlement
        
        # Enterprise volume pricing
        enterprise_factor = min(0.95, bid_request.cart_summary.total_amount / 5000.0)
        bps = base_bps * enterprise_factor
        
        return BidResponse(
            trace_id=bid_request.trace_id,
            processor_id="carat",
            auction_id=bid_request.auction_id,
            bps=bps,
            rebate_bps=rebate_bps,
            expected_settlement_days=settlement_days,
            constraints={
                "min_amount": 10.0,
                "max_amount": 1000000.0,
                "supported_currencies": ["USD", "EUR"],
                "risk_tolerance": "low"
            },
            confidence=0.95
        )
    
    def _generate_generic_bid(self, bid_request: BidRequest) -> BidResponse:
        """Generate generic bid for unknown processors."""
        base_bps = 160.0  # 1.6% base rate
        rebate_bps = random.uniform(2.0, 8.0)  # 2-8 bps rebate
        settlement_days = 3  # 3-day settlement
        
        return BidResponse(
            trace_id=bid_request.trace_id,
            processor_id=self.processor_id,
            auction_id=bid_request.auction_id,
            bps=base_bps,
            rebate_bps=rebate_bps,
            expected_settlement_days=settlement_days,
            constraints={
                "min_amount": 1.0,
                "max_amount": 10000.0,
                "supported_currencies": ["USD"],
                "risk_tolerance": "medium"
            },
            confidence=0.7
        )


class AuctionManager:
    """Manages processor auctions and bid aggregation."""
    
    def __init__(self, deterministic_seed: int = 42):
        """Initialize auction manager."""
        self.deterministic_seed = deterministic_seed
        random.seed(deterministic_seed)
        np.random.seed(deterministic_seed)
        
        # Initialize processor connectors
        self.processors = {
            "stripe": ProcessorConnector("stripe", deterministic_seed),
            "adyen": ProcessorConnector("adyen", deterministic_seed),
            "carat": ProcessorConnector("carat", deterministic_seed),
        }
        
        logger.info(f"Auction manager initialized with {len(self.processors)} processors")
    
    def run_auction(
        self,
        trace_id: str,
        cart_summary: CartSummary,
        rail_candidates: List[RailCandidate],
        deterministic_seed: Optional[int] = None
    ) -> AuctionResult:
        """
        Run processor auction for pay-ins.
        
        Args:
            trace_id: Trace identifier
            cart_summary: Cart summary information
            rail_candidates: Available rail candidates
            deterministic_seed: Seed for deterministic results
            
        Returns:
            Auction result with winning processor and aggregated bids
        """
        # Set deterministic seed
        if deterministic_seed is not None:
            random.seed(deterministic_seed)
            np.random.seed(deterministic_seed)
        
        # Generate auction ID
        auction_id = f"auction-{trace_id}-{int(datetime.now().timestamp())}"
        
        # Create bid request
        bid_request = BidRequest(
            trace_id=trace_id,
            cart_summary=cart_summary,
            rail_candidates=rail_candidates,
            auction_id=auction_id
        )
        
        logger.info(f"Starting auction {auction_id} for trace {trace_id}")
        
        # Emit bid request CloudEvent
        try:
            bid_request_event = emit_bid_request_event(
                bid_request=bid_request,
                merchant_context={"merchant_id": cart_summary.merchant_id},
                explanation=f"Bid request broadcast to {len(self.processors)} processors"
            )
            logger.debug(f"Bid request event emitted: {bid_request_event.id}")
        except Exception as e:
            logger.error(f"Failed to emit bid request event: {e}")
        
        # Broadcast bid requests to all processors
        all_bids = []
        for processor_id, connector in self.processors.items():
            try:
                bid_response = connector.generate_bid(bid_request)
                all_bids.append(bid_response)
                
                # Emit bid response CloudEvent
                try:
                    bid_response_event = emit_bid_response_event(
                        bid_response=bid_response,
                        merchant_context={"merchant_id": cart_summary.merchant_id},
                        cart_summary=cart_summary,
                        rail_candidates=rail_candidates,
                        explanation=f"Bid response from {processor_id}"
                    )
                    logger.debug(f"Bid response event emitted: {bid_response_event.id}")
                except Exception as e:
                    logger.error(f"Failed to emit bid response event for {processor_id}: {e}")
                
                logger.debug(f"Received bid from {processor_id}: {bid_response.bps} bps, {bid_response.rebate_bps} rebate")
            except Exception as e:
                logger.error(f"Failed to get bid from {processor_id}: {e}")
        
        if not all_bids:
            raise ValueError("No bids received from any processor")
        
        # Aggregate responses and determine winner
        winning_bid = self._determine_winner(all_bids)
        effective_cost_bps = winning_bid.effective_cost_bps
        
        # Generate LLM summary
        if is_auction_llm_configured():
            try:
                llm_response = explain_auction_result_llm(
                    auction_result=AuctionResult(
                        trace_id=trace_id,
                        auction_id=auction_id,
                        winning_processor=winning_bid.processor_id,
                        winning_bid=winning_bid,
                        all_bids=all_bids,
                        effective_cost_bps=effective_cost_bps,
                        summary="",  # Will be set below
                    ),
                    cart_summary=cart_summary,
                    merchant_context={"merchant_id": cart_summary.merchant_id}
                )
                if llm_response:
                    summary = llm_response.summary
                else:
                    summary = self._generate_auction_summary(winning_bid, all_bids, cart_summary)
            except Exception as e:
                logger.error(f"LLM explanation failed: {e}")
                summary = self._generate_auction_summary(winning_bid, all_bids, cart_summary)
        else:
            summary = self._generate_auction_summary(winning_bid, all_bids, cart_summary)
        
        # Create auction result
        result = AuctionResult(
            trace_id=trace_id,
            auction_id=auction_id,
            winning_processor=winning_bid.processor_id,
            winning_bid=winning_bid,
            all_bids=all_bids,
            effective_cost_bps=effective_cost_bps,
            summary=summary
        )
        
        logger.info(
            f"Auction {auction_id} completed: {winning_bid.processor_id} won with "
            f"{effective_cost_bps:.1f} bps effective cost"
        )
        
        return result
    
    def _determine_winner(self, bids: List[BidResponse]) -> BidResponse:
        """
        Determine winning bid based on effective cost and tie-breakers.
        
        Args:
            bids: List of all received bids
            
        Returns:
            Winning bid response
        """
        # Calculate effective cost for each bid (ensure it's never negative)
        for bid in bids:
            effective_cost = max(0.0, bid.bps - bid.rebate_bps)
            bid.effective_cost_bps = effective_cost
        
        # Sort by effective cost (ascending), then by settlement days (ascending), then by confidence (descending)
        sorted_bids = sorted(
            bids,
            key=lambda b: (b.effective_cost_bps, b.expected_settlement_days, -b.confidence)
        )
        
        winner = sorted_bids[0]
        
        # Log tie-breaker information if applicable
        if len(sorted_bids) > 1:
            second_place = sorted_bids[1]
            if abs(winner.effective_cost_bps - second_place.effective_cost_bps) < 0.1:
                logger.info(
                    f"Tie-breaker applied: {winner.processor_id} vs {second_place.processor_id} "
                    f"(settlement: {winner.expected_settlement_days} vs {second_place.expected_settlement_days} days)"
                )
        
        return winner
    
    def _generate_auction_summary(
        self,
        winning_bid: BidResponse,
        all_bids: List[BidResponse],
        cart_summary: CartSummary
    ) -> str:
        """
        Generate LLM summary of auction results.
        
        Args:
            winning_bid: Winning bid response
            all_bids: All received bids
            cart_summary: Cart summary information
            
        Returns:
            Human-readable auction summary
        """
        effective_cost = winning_bid.bps - winning_bid.rebate_bps
        
        # Find runner-up for comparison
        other_bids = [b for b in all_bids if b.processor_id != winning_bid.processor_id]
        if other_bids:
            runner_up = min(other_bids, key=lambda b: b.bps - b.rebate_bps)
            runner_up_cost = runner_up.bps - runner_up.rebate_bps
            cost_advantage = runner_up_cost - effective_cost
        else:
            cost_advantage = 0.0
        
        # Generate summary
        summary_parts = [
            f"{winning_bid.processor_id.title()} won the auction with {effective_cost:.1f} bps effective cost"
        ]
        
        if winning_bid.rebate_bps > 0:
            summary_parts.append(f"({winning_bid.bps:.1f} bps - {winning_bid.rebate_bps:.1f} bps rebate)")
        
        if winning_bid.expected_settlement_days == 1:
            summary_parts.append("and 1-day settlement")
        else:
            summary_parts.append(f"and {winning_bid.expected_settlement_days}-day settlement")
        
        if cost_advantage > 0.1:
            summary_parts.append(f"(saving {cost_advantage:.1f} bps vs runner-up)")
        
        # Add processor count
        summary_parts.append(f"from {len(all_bids)} competing processors")
        
        return " ".join(summary_parts) + "."


def run_auction(
    trace_id: str,
    cart_summary: CartSummary,
    rail_candidates: List[RailCandidate],
    deterministic_seed: int = 42
) -> AuctionResult:
    """
    Run processor auction for pay-ins (checkout).
    
    Args:
        trace_id: Trace identifier
        cart_summary: Cart summary information
        rail_candidates: Available rail candidates
        deterministic_seed: Seed for deterministic results
        
    Returns:
        Auction result with winning processor and aggregated bids
    """
    auction_manager = AuctionManager(deterministic_seed)
    return auction_manager.run_auction(trace_id, cart_summary, rail_candidates, deterministic_seed)

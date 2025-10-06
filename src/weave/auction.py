"""
Processor auction system for Weave Phase 3.

Implements bid request broadcasting, response aggregation, and auction management
for payment processor selection (Carat, Adyen, Stripe) using the connector registry.
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
from weave.connectors.connector_registry import get_connector_registry

logger = logging.getLogger(__name__)


class AuctionManager:
    """
    Manages processor auctions using the connector registry.
    
    Orchestrates bid requests, response collection, and winner determination
    for payment processor selection.
    """
    
    def __init__(self, deterministic_seed: int = 42):
        """Initialize auction manager."""
        self.deterministic_seed = deterministic_seed
        self.registry = get_connector_registry()
        random.seed(deterministic_seed)
        np.random.seed(deterministic_seed)
        
        logger.info(f"Auction manager initialized with seed: {deterministic_seed}")
    
    def get_available_processors(self) -> List[str]:
        """Get list of available processors."""
        return self.registry.get_available_processors()
    
    def run_auction(self, trace_id: str, cart_summary: CartSummary, rail_candidates: List[RailCandidate]) -> AuctionResult:
        """
        Run a processor auction for the given cart and rail candidates.
        
        Args:
            trace_id: Unique trace identifier
            cart_summary: Cart information
            rail_candidates: Available payment rails
            
        Returns:
            Auction result with winning processor and all bids
        """
        # Generate auction ID
        auction_id = f"auction_{trace_id}_{int(datetime.now().timestamp())}"
        
        # Create bid request
        bid_request = BidRequest(
            trace_id=trace_id,
            cart_summary=cart_summary,
            rail_candidates=rail_candidates,
            auction_id=auction_id
        )
        
        # Emit bid request CloudEvent
        try:
            bid_request_event = emit_bid_request_event(
                bid_request=bid_request,
                merchant_context={"merchant_id": cart_summary.merchant_id},
                explanation=f"Bid request broadcast to {len(self.get_available_processors())} processors"
            )
            logger.debug(f"Bid request event emitted: {bid_request_event.id}")
        except Exception as e:
            logger.error(f"Failed to emit bid request event: {e}")
        
        # Collect bids from all processors
        all_bids = []
        for processor_id in self.get_available_processors():
            try:
                connector = self.registry.get_connector(processor_id, self.deterministic_seed)
                if connector:
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
                else:
                    logger.warning(f"Could not get connector for processor: {processor_id}")
            except Exception as e:
                logger.error(f"Failed to get bid from {processor_id}: {e}")
        
        if not all_bids:
            raise ValueError("No bids received from any processor")
        
        # Determine winner
        winning_bid = self._determine_winner(all_bids)
        
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
                        effective_cost_bps=winning_bid.effective_cost_bps,
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
        
        return AuctionResult(
            trace_id=trace_id,
            auction_id=auction_id,
            winning_processor=winning_bid.processor_id,
            winning_bid=winning_bid,
            all_bids=all_bids,
            effective_cost_bps=winning_bid.effective_cost_bps,
            summary=summary
        )
    
    def _determine_winner(self, all_bids: List[BidResponse]) -> BidResponse:
        """
        Determine the winning bid based on effective cost and other factors.
        
        Args:
            all_bids: List of all bid responses
            
        Returns:
            Winning bid response
        """
        if not all_bids:
            raise ValueError("No bids to evaluate")
        
        # Calculate effective cost for each bid
        for bid in all_bids:
            bid.effective_cost_bps = max(0.0, bid.bps - bid.rebate_bps)
        
        # Sort by effective cost (ascending), then settlement days (ascending), then confidence (descending)
        sorted_bids = sorted(
            all_bids,
            key=lambda b: (b.effective_cost_bps, b.expected_settlement_days, -b.confidence)
        )
        
        winner = sorted_bids[0]
        logger.info(f"Winner determined: {winner.processor_id} with {winner.effective_cost_bps:.1f} bps effective cost")
        
        return winner
    
    def _generate_auction_summary(self, winning_bid: BidResponse, all_bids: List[BidResponse], cart_summary: CartSummary) -> str:
        """
        Generate a summary of the auction results.
        
        Args:
            winning_bid: The winning bid
            all_bids: All bids received
            cart_summary: Cart information
            
        Returns:
            Summary string
        """
        total_bids = len(all_bids)
        effective_cost = winning_bid.effective_cost_bps
        settlement_days = winning_bid.expected_settlement_days
        
        # Find the second-best bid for comparison
        sorted_bids = sorted(all_bids, key=lambda b: b.effective_cost_bps)
        second_best = sorted_bids[1] if len(sorted_bids) > 1 else None
        
        summary = f"{winning_bid.processor_id.upper()} won the auction with {effective_cost:.1f} bps effective cost"
        summary += f" and {settlement_days} day settlement"
        
        if second_best:
            savings = second_best.effective_cost_bps - effective_cost
            summary += f", saving {savings:.1f} bps over {second_best.processor_id.upper()}"
        
        summary += f" for a ${cart_summary.total_amount:.2f} {cart_summary.currency} transaction"
        
        return summary


def run_auction(
    trace_id: str,
    cart_summary: CartSummary,
    rail_candidates: List[RailCandidate],
    deterministic_seed: int = 42
) -> AuctionResult:
    """
    Run a processor auction with the given parameters.
    
    Args:
        trace_id: Unique trace identifier
        cart_summary: Cart information
        rail_candidates: Available payment rails
        deterministic_seed: Seed for deterministic results
        
    Returns:
        Auction result with winning processor and all bids
    """
    manager = AuctionManager(deterministic_seed)
    return manager.run_auction(trace_id, cart_summary, rail_candidates)
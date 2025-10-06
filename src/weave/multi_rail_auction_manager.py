"""
Multi-rail auction manager for Weave Phase 7.

Provides comprehensive auction management across multiple payment rails
and instruments, including ACH, RTP, FedNow, SEPA, and various payment
instruments like debit, prepaid, and stablecoin.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.weave.models import (
    RailType, InstrumentType, CartSummary, RailCandidate, BidRequest, BidResponse,
    AuctionResult, PaymentInstruction, ProcessorAuthResult
)
from src.weave.enhanced_bid_broadcaster import get_enhanced_bid_broadcaster
from src.weave.events import emit_auction_completion_event

logger = logging.getLogger(__name__)


class MultiRailAuctionRegistry:
    """
    Registry for multi-rail and multi-instrument auction capabilities.
    
    Manages available rails, instruments, and their combinations for
    comprehensive auction orchestration.
    """
    
    def __init__(self):
        """Initialize the auction registry."""
        self.rail_capabilities = {}
        self.instrument_capabilities = {}
        self.processor_capabilities = {}
        self._initialize_capabilities()
        logger.info("Multi-rail auction registry initialized")
    
    def _initialize_capabilities(self) -> None:
        """Initialize rail and instrument capabilities."""
        # Rail capabilities
        self.rail_capabilities = {
            "ACH": {
                "base_cost_bps": 15.0,
                "settlement_hours": 24,
                "is_real_time": False,
                "is_cross_border": False,
                "max_amount": 1000000.0,
                "min_amount": 1.0,
                "risk_score": 0.3,
                "supported_instruments": ["debit_card", "bank_transfer"],
                "jurisdictions": ["US"]
            },
            "RTP": {
                "base_cost_bps": 25.0,
                "settlement_hours": 0,  # Real-time
                "is_real_time": True,
                "is_cross_border": False,
                "max_amount": 1000000.0,
                "min_amount": 1.0,
                "risk_score": 0.2,
                "supported_instruments": ["debit_card", "bank_transfer"],
                "jurisdictions": ["US"]
            },
            "FedNow": {
                "base_cost_bps": 20.0,
                "settlement_hours": 0,  # Real-time
                "is_real_time": True,
                "is_cross_border": False,
                "max_amount": 500000.0,
                "min_amount": 1.0,
                "risk_score": 0.1,
                "supported_instruments": ["debit_card", "bank_transfer"],
                "jurisdictions": ["US"]
            },
            "SEPA": {
                "base_cost_bps": 10.0,
                "settlement_hours": 24,
                "is_real_time": False,
                "is_cross_border": True,
                "max_amount": 50000.0,
                "min_amount": 0.01,
                "risk_score": 0.4,
                "supported_instruments": ["bank_transfer", "debit_card"],
                "jurisdictions": ["EU", "EEA"]
            },
            "Wire": {
                "base_cost_bps": 50.0,
                "settlement_hours": 4,
                "is_real_time": False,
                "is_cross_border": True,
                "max_amount": 10000000.0,
                "min_amount": 1000.0,
                "risk_score": 0.2,
                "supported_instruments": ["bank_transfer"],
                "jurisdictions": ["US", "EU", "Global"]
            },
            "Crypto": {
                "base_cost_bps": 5.0,
                "settlement_hours": 1,
                "is_real_time": True,
                "is_cross_border": True,
                "max_amount": 1000000.0,
                "min_amount": 1.0,
                "risk_score": 0.5,
                "supported_instruments": ["stablecoin"],
                "jurisdictions": ["Global"]
            },
            "Card": {
                "base_cost_bps": 200.0,
                "settlement_hours": 48,
                "is_real_time": True,
                "is_cross_border": True,
                "max_amount": 100000.0,
                "min_amount": 0.01,
                "risk_score": 0.4,
                "supported_instruments": ["credit_card", "debit_card", "prepaid_card"],
                "jurisdictions": ["Global"]
            }
        }
        
        # Instrument capabilities
        self.instrument_capabilities = {
            "credit_card": {
                "cost_modifier": 1.0,
                "risk_modifier": 1.2,
                "supported_rails": ["Card"],
                "max_amount": 100000.0,
                "min_amount": 0.01
            },
            "debit_card": {
                "cost_modifier": 0.8,
                "risk_modifier": 0.8,
                "supported_rails": ["Card", "ACH", "RTP", "FedNow", "SEPA"],
                "max_amount": 10000.0,
                "min_amount": 0.01
            },
            "prepaid_card": {
                "cost_modifier": 0.9,
                "risk_modifier": 1.1,
                "supported_rails": ["Card"],
                "max_amount": 5000.0,
                "min_amount": 1.0
            },
            "bank_transfer": {
                "cost_modifier": 0.7,
                "risk_modifier": 0.6,
                "supported_rails": ["ACH", "RTP", "FedNow", "SEPA", "Wire"],
                "max_amount": 1000000.0,
                "min_amount": 1.0
            },
            "stablecoin": {
                "cost_modifier": 0.3,
                "risk_modifier": 1.5,
                "supported_rails": ["Crypto"],
                "max_amount": 1000000.0,
                "min_amount": 1.0
            },
            "digital_wallet": {
                "cost_modifier": 0.6,
                "risk_modifier": 0.9,
                "supported_rails": ["Card", "ACH"],
                "max_amount": 50000.0,
                "min_amount": 0.01
            },
            "bnpl": {
                "cost_modifier": 1.5,
                "risk_modifier": 2.0,
                "supported_rails": ["Card", "ACH"],
                "max_amount": 25000.0,
                "min_amount": 100.0
            },
            "cash": {
                "cost_modifier": 2.0,
                "risk_modifier": 1.8,
                "supported_rails": ["Card"],
                "max_amount": 5000.0,
                "min_amount": 1.0
            }
        }
        
        # Processor capabilities (simplified for demo)
        self.processor_capabilities = {
            "stripe": {
                "supported_rails": ["Card"],
                "supported_instruments": ["credit_card", "debit_card", "prepaid_card"],
                "base_rebate_bps": 5.0,
                "reliability": 0.99
            },
            "adyen": {
                "supported_rails": ["Card", "ACH", "SEPA"],
                "supported_instruments": ["credit_card", "debit_card", "bank_transfer"],
                "base_rebate_bps": 8.0,
                "reliability": 0.98
            },
            "carat": {
                "supported_rails": ["ACH", "RTP", "FedNow"],
                "supported_instruments": ["debit_card", "bank_transfer"],
                "base_rebate_bps": 12.0,
                "reliability": 0.97
            },
            "coinbase": {
                "supported_rails": ["Crypto"],
                "supported_instruments": ["stablecoin"],
                "base_rebate_bps": 2.0,
                "reliability": 0.95
            },
            "wise": {
                "supported_rails": ["Wire", "SEPA"],
                "supported_instruments": ["bank_transfer"],
                "base_rebate_bps": 15.0,
                "reliability": 0.96
            }
        }
    
    def get_valid_combinations(self) -> List[Tuple[RailType, InstrumentType]]:
        """Get all valid rail-instrument combinations."""
        combinations = []
        for rail_type, rail_info in self.rail_capabilities.items():
            for instrument in rail_info["supported_instruments"]:
                if instrument in self.instrument_capabilities:
                    combinations.append((rail_type, instrument))
        return combinations
    
    def get_rail_capability(self, rail_type: RailType) -> Optional[Dict[str, Any]]:
        """Get capability information for a rail."""
        return self.rail_capabilities.get(rail_type)
    
    def get_instrument_capability(self, instrument_type: InstrumentType) -> Optional[Dict[str, Any]]:
        """Get capability information for an instrument."""
        return self.instrument_capabilities.get(instrument_type)
    
    def get_processors_for_combination(
        self,
        rail_type: RailType,
        instrument_type: InstrumentType
    ) -> List[str]:
        """Get processors that support a specific rail-instrument combination."""
        supported_processors = []
        for processor_id, processor_info in self.processor_capabilities.items():
            if (rail_type in processor_info["supported_rails"] and
                instrument_type in processor_info["supported_instruments"]):
                supported_processors.append(processor_id)
        return supported_processors


class MultiRailAuctionGenerator:
    """
    Generator for multi-rail auction candidates.
    
    Creates comprehensive rail candidates across all available
    combinations for auction participation.
    """
    
    def __init__(self):
        """Initialize the auction generator."""
        self.registry = MultiRailAuctionRegistry()
        logger.info("Multi-rail auction generator initialized")
    
    def generate_rail_candidates(
        self,
        cart_summary: CartSummary,
        constraints: Optional[Dict[str, Any]] = None
    ) -> List[RailCandidate]:
        """
        Generate rail candidates for auction.
        
        Args:
            cart_summary: Cart information for candidate generation
            constraints: Optional constraints for filtering candidates
            
        Returns:
            List of rail candidates for auction
        """
        candidates = []
        valid_combinations = self.registry.get_valid_combinations()
        
        for rail_type, instrument_type in valid_combinations:
            candidate = self._create_rail_candidate(
                rail_type, instrument_type, cart_summary, constraints
            )
            if candidate:
                candidates.append(candidate)
        
        # Sort by cost efficiency
        candidates.sort(key=lambda c: c.base_cost_bps)
        
        logger.info(f"Generated {len(candidates)} rail candidates for auction")
        return candidates
    
    def _create_rail_candidate(
        self,
        rail_type: RailType,
        instrument_type: InstrumentType,
        cart_summary: CartSummary,
        constraints: Optional[Dict[str, Any]]
    ) -> Optional[RailCandidate]:
        """Create a rail candidate for a specific combination."""
        # Get capabilities
        rail_cap = self.registry.get_rail_capability(rail_type)
        instrument_cap = self.registry.get_instrument_capability(instrument_type)
        
        if not rail_cap or not instrument_cap:
            return None
        
        # Check amount constraints
        if (cart_summary.total_amount > rail_cap["max_amount"] or
            cart_summary.total_amount < rail_cap["min_amount"]):
            return None
        
        if (cart_summary.total_amount > instrument_cap["max_amount"] or
            cart_summary.total_amount < instrument_cap["min_amount"]):
            return None
        
        # Apply constraints
        if constraints:
            if not self._meets_constraints(rail_cap, instrument_cap, constraints):
                return None
        
        # Calculate combined metrics
        base_cost_bps = rail_cap["base_cost_bps"] * instrument_cap["cost_modifier"]
        risk_score = min(1.0, rail_cap["risk_score"] * instrument_cap["risk_modifier"])
        settlement_days = max(0, rail_cap["settlement_hours"] // 24)
        
        return RailCandidate(
            rail_type=rail_type,
            instrument_type=instrument_type,
            base_cost_bps=base_cost_bps,
            settlement_days=settlement_days,
            risk_score=risk_score,
            is_real_time=rail_cap["is_real_time"],
            is_cross_border=rail_cap["is_cross_border"],
            max_amount=min(rail_cap["max_amount"], instrument_cap["max_amount"]),
            min_amount=max(rail_cap["min_amount"], instrument_cap["min_amount"])
        )
    
    def _meets_constraints(
        self,
        rail_cap: Dict[str, Any],
        instrument_cap: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> bool:
        """Check if combination meets specified constraints."""
        # Real-time requirement
        if constraints.get("require_real_time", False) and not rail_cap["is_real_time"]:
            return False
        
        # Cross-border requirement
        if constraints.get("cross_border", False) and not rail_cap["is_cross_border"]:
            return False
        
        # Max cost constraint
        max_cost_bps = constraints.get("max_cost_bps", 1000.0)
        total_cost_bps = rail_cap["base_cost_bps"] * instrument_cap["cost_modifier"]
        if total_cost_bps > max_cost_bps:
            return False
        
        # Max risk constraint
        max_risk = constraints.get("max_risk", 1.0)
        total_risk = rail_cap["risk_score"] * instrument_cap["risk_modifier"]
        if total_risk > max_risk:
            return False
        
        return True


class MultiRailBidBroadcaster:
    """
    Bid broadcaster for multi-rail auctions.
    
    Sends bid requests to appropriate processors based on
    rail and instrument capabilities.
    """
    
    def __init__(self):
        """Initialize the bid broadcaster."""
        self.registry = MultiRailAuctionRegistry()
        logger.info("Multi-rail bid broadcaster initialized")
    
    def broadcast_bid_requests(
        self,
        rail_candidates: List[RailCandidate],
        cart_summary: CartSummary,
        trace_id: str
    ) -> List[BidRequest]:
        """
        Broadcast bid requests for all rail candidates.
        
        Args:
            rail_candidates: List of rail candidates
            cart_summary: Cart information
            trace_id: Transaction trace ID
            
        Returns:
            List of bid requests sent to processors
        """
        bid_requests = []
        auction_id = f"auction_{trace_id}_{uuid.uuid4().hex[:8]}"
        
        for candidate in rail_candidates:
            # Get processors that support this combination
            processors = self.registry.get_processors_for_combination(
                candidate.rail_type, candidate.instrument_type
            )
            
            # Create bid request for each processor
            for processor_id in processors:
                bid_request = BidRequest(
                    trace_id=trace_id,
                    cart_summary=cart_summary,
                    rail_candidates=[candidate],
                    auction_id=auction_id,
                    timestamp=datetime.now()
                )
                bid_requests.append(bid_request)
                
                logger.debug(f"Broadcasting bid request to {processor_id} for {candidate.rail_type}/{candidate.instrument_type}")
        
        logger.info(f"Broadcast {len(bid_requests)} bid requests for {len(rail_candidates)} rail candidates")
        return bid_requests
    
    def simulate_bid_responses(
        self,
        bid_requests: List[BidRequest]
    ) -> List[BidResponse]:
        """
        Simulate bid responses from processors.
        
        This is a demo implementation that simulates processor responses.
        In production, this would be replaced with actual processor API calls.
        """
        responses = []
        
        for request in bid_requests:
            for candidate in request.rail_candidates:
                processors = self.registry.get_processors_for_combination(
                    candidate.rail_type, candidate.instrument_type
                )
                
                for processor_id in processors:
                    processor_info = self.registry.processor_capabilities[processor_id]
                    
                    # Simulate bid response
                    response = self._simulate_processor_response(
                        request, candidate, processor_id, processor_info
                    )
                    responses.append(response)
        
        logger.info(f"Generated {len(responses)} simulated bid responses")
        return responses
    
    def _simulate_processor_response(
        self,
        request: BidRequest,
        candidate: RailCandidate,
        processor_id: str,
        processor_info: Dict[str, Any]
    ) -> BidResponse:
        """Simulate a processor bid response."""
        # Base bid from processor capability
        base_bps = candidate.base_cost_bps
        
        # Add processor-specific adjustments
        rebate_bps = processor_info["base_rebate_bps"]
        reliability_factor = processor_info["reliability"]
        
        # Simulate competitive bidding with some randomness
        competitive_adjustment = np.random.normal(1.0, 0.1)  # ±10% variation
        final_bps = max(5.0, base_bps * competitive_adjustment)  # Minimum 5 bps
        
        # Settlement time based on rail capability
        settlement_days = candidate.settlement_days
        if candidate.is_real_time:
            settlement_days = 0
        
        return BidResponse(
            trace_id=request.trace_id,
            processor_id=processor_id,
            auction_id=request.auction_id,
            bps=final_bps,
            rebate_bps=rebate_bps,
            expected_settlement_days=settlement_days,
            constraints={
                "min_amount": candidate.min_amount,
                "max_amount": candidate.max_amount,
                "risk_score": candidate.risk_score,
                "is_real_time": candidate.is_real_time,
                "is_cross_border": candidate.is_cross_border,
                "reliability": reliability_factor
            },
            timestamp=datetime.now()
        )


class MultiRailAuctionManager:
    """
    Main auction manager for multi-rail and multi-instrument support.
    
    Orchestrates the complete auction process across all available
    rails and instruments, from candidate generation to winner selection.
    """
    
    def __init__(self):
        """Initialize the auction manager."""
        self.generator = MultiRailAuctionGenerator()
        self.broadcaster = MultiRailBidBroadcaster()
        self.enhanced_broadcaster = get_enhanced_bid_broadcaster()
        logger.info("Multi-rail auction manager initialized with enhanced bid broadcaster")
    
    def run_multi_rail_auction(
        self,
        cart_summary: CartSummary,
        constraints: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None
    ) -> AuctionResult:
        """
        Run a comprehensive multi-rail auction.
        
        Args:
            cart_summary: Cart information for the auction
            constraints: Optional constraints for filtering candidates
            trace_id: Transaction trace ID
            
        Returns:
            Comprehensive auction result
        """
        if not trace_id:
            trace_id = f"trace_{uuid.uuid4().hex[:8]}"
        
        # Generate rail candidates
        rail_candidates = self.generator.generate_rail_candidates(cart_summary, constraints)
        
        if not rail_candidates:
            raise ValueError("No valid rail candidates found for the auction")
        
        # Create bid requests for enhanced broadcaster
        bid_requests = []
        for candidate in rail_candidates:
            bid_request = BidRequest(
                trace_id=trace_id,
                cart_summary=cart_summary,
                rail_candidates=[candidate],
                auction_id=f"auction_{trace_id}_{uuid.uuid4().hex[:8]}",
                timestamp=datetime.now()
            )
            bid_requests.append(bid_request)
        
        # Broadcast bid requests using enhanced broadcaster with real connectors
        bid_responses, broadcast_metadata = self.enhanced_broadcaster.broadcast_bid_requests(bid_requests)
        
        # Select winner
        winner = self._select_auction_winner(bid_responses, cart_summary)
        
        # Create auction result
        result = AuctionResult(
            trace_id=trace_id,
            auction_id=bid_requests[0].auction_id if bid_requests else f"auction_{trace_id}",
            winner=winner,
            all_bids=bid_responses,
            total_participants=len(set(r.processor_id for r in bid_responses)),
            total_rail_combinations=len(rail_candidates),
            auction_metadata={
                "rail_candidates": [c.dict() for c in rail_candidates],
                "bid_requests": [r.dict() for r in bid_requests],
                "constraints": constraints or {},
                "multi_rail_enabled": True,
                "enhanced_broadcaster_used": True,
                "connectors_contacted": broadcast_metadata.get("connectors_contacted", []),
                "broadcast_metadata": broadcast_metadata
            }
        )
        
        # Emit auction completion event
        try:
            emit_auction_completion_event({
                "trace_id": trace_id,
                "auction_id": result.auction_id,
                "winner": winner.dict() if winner else None,
                "total_participants": result.total_participants,
                "total_bids": len(bid_responses),
                "total_rail_combinations": result.total_rail_combinations,
                "broadcast_metadata": broadcast_metadata
            })
        except Exception as e:
            logger.warning(f"Failed to emit auction completion event: {str(e)}")
        
        logger.info(f"Completed multi-rail auction with {len(bid_responses)} bids from {result.total_participants} participants")
        return result
    
    def _select_auction_winner(
        self,
        bid_responses: List[BidResponse],
        cart_summary: CartSummary
    ) -> BidResponse:
        """Select the winning bid from all responses."""
        if not bid_responses:
            raise ValueError("No bid responses to evaluate")
        
        # Score each bid based on cost, speed, and reliability
        scored_bids = []
        for bid in bid_responses:
            score = self._calculate_bid_score(bid, cart_summary)
            scored_bids.append((score, bid))
        
        # Sort by score (higher is better)
        scored_bids.sort(key=lambda x: x[0], reverse=True)
        
        winner = scored_bids[0][1]
        logger.info(f"Selected winner: {winner.processor_id} with {winner.rail_type}/{winner.instrument_type} "
                   f"at {winner.bps} bps (score: {scored_bids[0][0]:.3f})")
        
        return winner
    
    def _calculate_bid_score(
        self,
        bid: BidResponse,
        cart_summary: CartSummary
    ) -> float:
        """Calculate comprehensive bid score."""
        # Cost score (lower cost = higher score)
        cost_score = max(0.0, 1.0 - (bid.bps / 1000.0))  # Normalize to 0-1
        
        # Speed score (faster = higher score)
        speed_score = max(0.0, 1.0 - (bid.expected_settlement_days / 7.0))  # 7 days max
        
        # Reliability score
        reliability = bid.constraints.get("reliability", 0.95)
        
        # Rebate bonus
        rebate_score = min(1.0, bid.rebate_bps / 50.0)  # 50 bps rebate = max score
        
        # Weighted combination
        total_score = (
            cost_score * 0.4 +        # 40% cost
            speed_score * 0.3 +       # 30% speed
            reliability * 0.2 +       # 20% reliability
            rebate_score * 0.1        # 10% rebate
        )
        
        return total_score


# Global instances
_auction_registry = None
_auction_generator = None
_bid_broadcaster = None
_auction_manager = None


def get_multi_rail_auction_registry() -> MultiRailAuctionRegistry:
    """Get global auction registry instance."""
    global _auction_registry
    if _auction_registry is None:
        _auction_registry = MultiRailAuctionRegistry()
    return _auction_registry


def get_multi_rail_auction_generator() -> MultiRailAuctionGenerator:
    """Get global auction generator instance."""
    global _auction_generator
    if _auction_generator is None:
        _auction_generator = MultiRailAuctionGenerator()
    return _auction_generator


def get_multi_rail_bid_broadcaster() -> MultiRailBidBroadcaster:
    """Get global bid broadcaster instance."""
    global _bid_broadcaster
    if _bid_broadcaster is None:
        _bid_broadcaster = MultiRailBidBroadcaster()
    return _bid_broadcaster


def get_multi_rail_auction_manager() -> MultiRailAuctionManager:
    """Get global auction manager instance."""
    global _auction_manager
    if _auction_manager is None:
        _auction_manager = MultiRailAuctionManager()
    return _auction_manager

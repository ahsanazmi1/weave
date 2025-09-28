"""
Stripe Processor Connector.

Implements Stripe-specific bid generation with deterministic pricing
and constraints for the Weave auction system.
"""

import random
from typing import Any, Dict, List
import numpy as np

from .base_connector import BaseProcessorConnector
from weave.models import BidRequest, BidResponse

class StripeConnector(BaseProcessorConnector):
    """
    Stripe processor connector with competitive pricing and good rebates.
    
    Stripe typically offers:
    - Competitive base rates (1.5% + 30¢)
    - Good rebates for volume
    - Fast settlement (1 day)
    - Strong international support
    """
    
    def __init__(self, deterministic_seed: int = 42):
        """Initialize Stripe connector."""
        super().__init__("stripe", deterministic_seed)
        
        # Set deterministic seed for reproducible results
        random.seed(deterministic_seed)
        np.random.seed(deterministic_seed)
    
    def generate_bid(self, bid_request: BidRequest) -> BidResponse:
        """
        Generate Stripe-specific bid response.
        
        Stripe's pricing strategy:
        - Base rate: 1.5% (150 bps)
        - Volume discounts for larger amounts
        - Competitive rebates
        - Fast settlement
        """
        if not self.validate_bid_request(bid_request):
            raise ValueError(f"Invalid bid request for {self.processor_id}")
        
        # Base pricing
        base_bps = 150.0  # 1.5% base rate
        
        # Calculate adjustments
        risk_adjustment = self.calculate_risk_adjustment(bid_request)
        volume_discount = self.calculate_volume_discount(bid_request)
        
        # Apply adjustments
        adjusted_bps = base_bps * risk_adjustment * volume_discount
        
        # Generate deterministic rebate based on cart characteristics
        rebate_bps = self._calculate_rebate(bid_request)
        
        # Settlement time (Stripe is fast)
        settlement_days = 1
        
        # Confidence based on cart characteristics
        confidence = self._calculate_confidence(bid_request)
        
        return BidResponse(
            trace_id=bid_request.trace_id,
            processor_id=self.processor_id,
            auction_id=bid_request.auction_id,
            bps=adjusted_bps,
            rebate_bps=rebate_bps,
            expected_settlement_days=settlement_days,
            constraints=self._get_constraints(),
            confidence=confidence
        )
    
    def _calculate_rebate(self, bid_request: BidRequest) -> float:
        """Calculate deterministic rebate based on cart characteristics."""
        # Use deterministic seed for consistent rebates
        random.seed(self.deterministic_seed + hash(bid_request.cart_summary.total_amount))
        
        # Base rebate
        base_rebate = 8.0  # 8 bps base rebate
        
        # Volume-based rebate increase
        amount = bid_request.cart_summary.total_amount
        if amount >= 10000:
            volume_bonus = random.uniform(5.0, 12.0)  # 5-12 bps bonus
        elif amount >= 5000:
            volume_bonus = random.uniform(3.0, 8.0)   # 3-8 bps bonus
        elif amount >= 1000:
            volume_bonus = random.uniform(1.0, 4.0)   # 1-4 bps bonus
        else:
            volume_bonus = 0.0
        
        # Category-based rebate
        category = bid_request.cart_summary.merchant_category
        category_bonus = {
            'electronics': random.uniform(2.0, 5.0),
            'clothing': random.uniform(1.0, 3.0),
            'general': random.uniform(0.0, 2.0),
            'high_risk': 0.0,
            'low_risk': random.uniform(3.0, 6.0)
        }.get(category, 0.0)
        
        total_rebate = base_rebate + volume_bonus + category_bonus
        return min(25.0, total_rebate)  # Cap at 25 bps
    
    def _calculate_confidence(self, bid_request: BidRequest) -> float:
        """Calculate confidence score based on cart characteristics."""
        confidence = 0.9  # Base confidence
        
        # Adjust based on amount
        amount = bid_request.cart_summary.total_amount
        if amount > 50000:
            confidence -= 0.1  # Lower confidence for very large amounts
        elif amount < 10:
            confidence -= 0.05  # Lower confidence for very small amounts
        
        # Adjust based on risk
        avg_risk = sum(rail.risk_score for rail in bid_request.rail_candidates) / len(bid_request.rail_candidates)
        if avg_risk > 0.7:
            confidence -= 0.1
        elif avg_risk < 0.3:
            confidence += 0.05
        
        return max(0.5, min(1.0, confidence))
    
    def _get_constraints(self) -> Dict[str, Any]:
        """Get Stripe-specific constraints."""
        return {
            "min_amount": 0.50,
            "max_amount": 100000.0,
            "supported_currencies": self.get_supported_currencies(),
            "risk_tolerance": self.get_risk_tolerance(),
            "settlement_speed": "fast",
            "international_support": True,
            "chargeback_protection": True
        }
    
    def get_processor_info(self) -> Dict[str, Any]:
        """Get Stripe processor information."""
        return {
            "processor_id": self.processor_id,
            "name": "Stripe",
            "description": "Global payment processing platform with competitive rates",
            "strengths": [
                "Fast settlement",
                "Strong international support", 
                "Good developer experience",
                "Competitive rebates"
            ],
            "pricing_model": "percentage_plus_fixed",
            "base_rate_bps": 150.0,
            "fixed_fee_cents": 30
        }
    
    def get_supported_currencies(self) -> List[str]:
        """Get supported currencies."""
        return ["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF", "SEK", "NOK", "DKK"]
    
    def get_risk_tolerance(self) -> str:
        """Get risk tolerance level."""
        return "medium"
    
    def get_amount_constraints(self) -> Dict[str, float]:
        """Get amount constraints."""
        return {
            'min_amount': 0.50,
            'max_amount': 100000.0
        }

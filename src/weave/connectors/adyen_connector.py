"""
Adyen Processor Connector.

Implements Adyen-specific bid generation with deterministic pricing
and constraints for the Weave auction system.
"""

import random
from typing import Any, Dict, List
import numpy as np

from .base_connector import BaseProcessorConnector
from weave.models import BidRequest, BidResponse

class AdyenConnector(BaseProcessorConnector):
    """
    Adyen processor connector with strong international support and competitive rates.
    
    Adyen typically offers:
    - Competitive base rates (1.45% + 25¢)
    - Excellent international support
    - Good volume discounts
    - 2-day settlement
    """
    
    def __init__(self, deterministic_seed: int = 42):
        """Initialize Adyen connector."""
        super().__init__("adyen", deterministic_seed)
        
        # Set deterministic seed for reproducible results
        random.seed(deterministic_seed)
        np.random.seed(deterministic_seed)
    
    def generate_bid(self, bid_request: BidRequest) -> BidResponse:
        """
        Generate Adyen-specific bid response.
        
        Adyen's pricing strategy:
        - Base rate: 1.45% (145 bps)
        - Strong international support
        - Good volume discounts
        - 2-day settlement
        """
        if not self.validate_bid_request(bid_request):
            raise ValueError(f"Invalid bid request for {self.processor_id}")
        
        # Base pricing
        base_bps = 145.0  # 1.45% base rate
        
        # Calculate adjustments
        risk_adjustment = self.calculate_risk_adjustment(bid_request)
        volume_discount = self.calculate_volume_discount(bid_request)
        
        # Apply adjustments
        adjusted_bps = base_bps * risk_adjustment * volume_discount
        
        # Generate deterministic rebate based on cart characteristics
        rebate_bps = self._calculate_rebate(bid_request)
        
        # Settlement time (Adyen is 2 days)
        settlement_days = 2
        
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
        base_rebate = 6.0  # 6 bps base rebate
        
        # Volume-based rebate increase
        amount = bid_request.cart_summary.total_amount
        if amount >= 10000:
            volume_bonus = random.uniform(4.0, 10.0)  # 4-10 bps bonus
        elif amount >= 5000:
            volume_bonus = random.uniform(2.0, 6.0)   # 2-6 bps bonus
        elif amount >= 1000:
            volume_bonus = random.uniform(1.0, 3.0)   # 1-3 bps bonus
        else:
            volume_bonus = 0.0
        
        # International bonus (Adyen's strength)
        currency = bid_request.cart_summary.currency
        international_bonus = 0.0
        if currency in ["EUR", "GBP", "CAD", "AUD", "JPY"]:
            international_bonus = random.uniform(1.0, 3.0)
        
        # Category-based rebate
        category = bid_request.cart_summary.merchant_category
        category_bonus = {
            'electronics': random.uniform(1.0, 4.0),
            'clothing': random.uniform(0.5, 2.0),
            'general': random.uniform(0.0, 1.5),
            'high_risk': 0.0,
            'low_risk': random.uniform(2.0, 4.0)
        }.get(category, 0.0)
        
        total_rebate = base_rebate + volume_bonus + international_bonus + category_bonus
        return min(20.0, total_rebate)  # Cap at 20 bps
    
    def _calculate_confidence(self, bid_request: BidRequest) -> float:
        """Calculate confidence score based on cart characteristics."""
        confidence = 0.85  # Base confidence
        
        # Adjust based on amount
        amount = bid_request.cart_summary.total_amount
        if amount > 100000:
            confidence -= 0.1  # Lower confidence for very large amounts
        elif amount < 5:
            confidence -= 0.05  # Lower confidence for very small amounts
        
        # Adjust based on risk
        avg_risk = sum(rail.risk_score for rail in bid_request.rail_candidates) / len(bid_request.rail_candidates)
        if avg_risk > 0.8:
            confidence -= 0.15
        elif avg_risk < 0.3:
            confidence += 0.05
        
        # International confidence boost
        currency = bid_request.cart_summary.currency
        if currency in ["EUR", "GBP", "CAD", "AUD", "JPY"]:
            confidence += 0.05
        
        return max(0.5, min(1.0, confidence))
    
    def _get_constraints(self) -> Dict[str, Any]:
        """Get Adyen-specific constraints."""
        return {
            "min_amount": 1.0,
            "max_amount": 500000.0,
            "supported_currencies": self.get_supported_currencies(),
            "risk_tolerance": self.get_risk_tolerance(),
            "settlement_speed": "medium",
            "international_support": True,
            "chargeback_protection": True,
            "fraud_detection": "advanced"
        }
    
    def get_processor_info(self) -> Dict[str, Any]:
        """Get Adyen processor information."""
        return {
            "processor_id": self.processor_id,
            "name": "Adyen",
            "description": "Global payment platform with strong international presence",
            "strengths": [
                "Excellent international support",
                "Advanced fraud detection",
                "Good volume discounts",
                "Strong enterprise features"
            ],
            "pricing_model": "percentage_plus_fixed",
            "base_rate_bps": 145.0,
            "fixed_fee_cents": 25
        }
    
    def get_supported_currencies(self) -> List[str]:
        """Get supported currencies."""
        return ["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF", "SEK", "NOK", "DKK", "PLN", "CZK", "HUF"]
    
    def get_risk_tolerance(self) -> str:
        """Get risk tolerance level."""
        return "high"
    
    def get_amount_constraints(self) -> Dict[str, float]:
        """Get amount constraints."""
        return {
            'min_amount': 1.0,
            'max_amount': 500000.0
        }


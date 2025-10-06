"""
Base Processor Connector Interface.

Defines the interface that all payment processor connectors must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

from weave.models import BidRequest, BidResponse

logger = logging.getLogger(__name__)


class BaseProcessorConnector(ABC):
    """
    Abstract base class for payment processor connectors.
    
    All processor connectors must implement this interface to participate
    in the Weave auction system.
    """
    
    def __init__(self, processor_id: str, deterministic_seed: int = 42):
        """
        Initialize the processor connector.
        
        Args:
            processor_id: Unique identifier for the processor
            deterministic_seed: Seed for deterministic bid generation
        """
        self.processor_id = processor_id
        self.deterministic_seed = deterministic_seed
        self.logger = logging.getLogger(f"weave.connector.{processor_id}")
        
        self.logger.info(f"Processor connector initialized: {processor_id}")
    
    @abstractmethod
    def generate_bid(self, bid_request: BidRequest) -> BidResponse:
        """
        Generate a bid response for the given bid request.
        
        Args:
            bid_request: The bid request containing cart and context information
            
        Returns:
            Bid response with pricing, constraints, and confidence
        """
        pass
    
    @abstractmethod
    def get_processor_info(self) -> Dict[str, Any]:
        """
        Get processor-specific information and capabilities.
        
        Returns:
            Dictionary containing processor information
        """
        pass
    
    @abstractmethod
    def get_supported_currencies(self) -> List[str]:
        """
        Get list of supported currencies.
        
        Returns:
            List of currency codes (e.g., ['USD', 'EUR', 'GBP'])
        """
        pass
    
    @abstractmethod
    def get_risk_tolerance(self) -> str:
        """
        Get processor's risk tolerance level.
        
        Returns:
            Risk tolerance level ('low', 'medium', 'high')
        """
        pass
    
    def validate_bid_request(self, bid_request: BidRequest) -> bool:
        """
        Validate if the bid request meets processor requirements.
        
        Args:
            bid_request: The bid request to validate
            
        Returns:
            True if request is valid, False otherwise
        """
        try:
            # Check currency support
            if bid_request.cart_summary.currency not in self.get_supported_currencies():
                self.logger.warning(f"Unsupported currency: {bid_request.cart_summary.currency}")
                return False
            
            # Check amount constraints
            amount = bid_request.cart_summary.total_amount
            constraints = self.get_amount_constraints()
            
            if amount < constraints.get('min_amount', 0):
                self.logger.warning(f"Amount too low: {amount} < {constraints.get('min_amount')}")
                return False
            
            if amount > constraints.get('max_amount', float('inf')):
                self.logger.warning(f"Amount too high: {amount} > {constraints.get('max_amount')}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Bid request validation failed: {e}")
            return False
    
    def get_amount_constraints(self) -> Dict[str, float]:
        """
        Get amount constraints for this processor.
        
        Returns:
            Dictionary with 'min_amount' and 'max_amount' keys
        """
        return {
            'min_amount': 0.0,
            'max_amount': float('inf')
        }
    
    def calculate_risk_adjustment(self, bid_request: BidRequest) -> float:
        """
        Calculate risk adjustment factor based on cart and context.
        
        Args:
            bid_request: The bid request containing risk information
            
        Returns:
            Risk adjustment factor (1.0 = no adjustment, >1.0 = higher risk)
        """
        try:
            # Base risk from rail candidates
            avg_risk = sum(rail.risk_score for rail in bid_request.rail_candidates) / len(bid_request.rail_candidates)
            
            # Cart size risk adjustment
            amount = bid_request.cart_summary.total_amount
            if amount > 10000:
                amount_risk = 1.1  # Higher risk for large amounts
            elif amount < 100:
                amount_risk = 1.05  # Slightly higher risk for small amounts
            else:
                amount_risk = 1.0
            
            # Merchant category risk
            category = bid_request.cart_summary.merchant_category
            category_risk = {
                'electronics': 1.0,
                'clothing': 1.0,
                'general': 1.0,
                'high_risk': 1.3,
                'low_risk': 0.9
            }.get(category, 1.0)
            
            # Combine risk factors
            total_risk = avg_risk * amount_risk * category_risk
            
            return min(2.0, max(0.5, total_risk))  # Clamp between 0.5 and 2.0
            
        except Exception as e:
            self.logger.error(f"Risk adjustment calculation failed: {e}")
            return 1.0
    
    def calculate_volume_discount(self, bid_request: BidRequest) -> float:
        """
        Calculate volume discount factor based on cart amount.
        
        Args:
            bid_request: The bid request containing cart information
            
        Returns:
            Volume discount factor (1.0 = no discount, <1.0 = discount)
        """
        try:
            amount = bid_request.cart_summary.total_amount
            
            # Volume discount tiers
            if amount >= 10000:
                return 0.85  # 15% discount for large volumes
            elif amount >= 5000:
                return 0.90  # 10% discount for medium volumes
            elif amount >= 1000:
                return 0.95  # 5% discount for small volumes
            else:
                return 1.0   # No discount for small amounts
                
        except Exception as e:
            self.logger.error(f"Volume discount calculation failed: {e}")
            return 1.0


"""
Carat payment processor connector for Weave Phase 8.

Provides integration with Carat's payment processing capabilities,
focusing on ACH and real-time payment rails with competitive pricing.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from src.weave.models import (
    BidRequest, BidResponse, PaymentInstruction, ProcessorAuthResult,
    RailType, InstrumentType
)

logger = logging.getLogger(__name__)


class CaratConnector:
    """
    Carat payment processor connector.
    
    Carat specializes in ACH and real-time payment processing with
    competitive fees and fast settlement times. This connector provides
    deterministic stub responses for development and testing.
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.carat.com"):
        """
        Initialize Carat connector.
        
        Args:
            api_key: Carat API key (optional for stub mode)
            base_url: Carat API base URL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.connector_id = "carat"
        self.supported_rails = ["ACH", "RTP", "FedNow"]
        self.supported_instruments = ["debit_card", "bank_transfer"]
        logger.info(f"Carat connector initialized with base_url: {base_url}")
    
    def send_bid_request(self, bid_request: BidRequest) -> Dict[str, Any]:
        """
        Send bid request to Carat processor.
        
        Args:
            bid_request: Bid request containing rail candidates and cart information
            
        Returns:
            Dictionary containing bid response or error information
        """
        try:
            # Check if we have valid rail candidates for Carat
            carat_candidates = self._filter_carat_candidates(bid_request.rail_candidates)
            
            if not carat_candidates:
                return {
                    "success": False,
                    "error": "No supported rail candidates for Carat",
                    "processor_id": self.connector_id
                }
            
            # Prepare request payload
            payload = self._prepare_carat_payload(bid_request, carat_candidates)
            
            # Send request (stub implementation)
            if self.api_key and self._is_api_available():
                response = self._send_real_request(payload)
            else:
                response = self._generate_stub_response(payload)
            
            logger.info(f"Carat bid request completed for trace_id: {bid_request.trace_id}")
            return response
            
        except Exception as e:
            logger.error(f"Carat bid request failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processor_id": self.connector_id
            }
    
    def parse_bid_response(self, response_data: Dict[str, Any]) -> List[BidResponse]:
        """
        Parse Carat bid response into standardized format.
        
        Args:
            response_data: Raw response from Carat API or stub
            
        Returns:
            List of standardized bid responses
        """
        try:
            if not response_data.get("success", False):
                logger.warning(f"Carat response indicates failure: {response_data.get('error', 'Unknown error')}")
                return []
            
            bid_responses = []
            bids = response_data.get("bids", [])
            
            for bid in bids:
                bid_response = BidResponse(
                    trace_id=response_data.get("trace_id", ""),
                    processor_id=self.connector_id,
                    auction_id=response_data.get("auction_id", ""),
                    bps=bid.get("bps", 0.0),
                    rebate_bps=bid.get("rebate_bps", 0.0),
                    expected_settlement_days=bid.get("settlement_days", 1),
                    constraints={
                        "min_amount": bid.get("min_amount", 1.0),
                        "max_amount": bid.get("max_amount", 1000000.0),
                        "risk_score": bid.get("risk_score", 0.3),
                        "is_real_time": bid.get("is_real_time", False),
                        "is_cross_border": bid.get("is_cross_border", False),
                        "reliability": bid.get("reliability", 0.97),
                        "rail_type": bid.get("rail_type"),
                        "instrument_type": bid.get("instrument_type"),
                        "carat_features": bid.get("features", {})
                    },
                    timestamp=datetime.now()
                )
                bid_responses.append(bid_response)
            
            logger.info(f"Parsed {len(bid_responses)} Carat bid responses")
            return bid_responses
            
        except Exception as e:
            logger.error(f"Failed to parse Carat response: {str(e)}")
            return []
    
    def submit_payment_instruction(self, payment_instruction: PaymentInstruction) -> ProcessorAuthResult:
        """
        Submit payment instruction to Carat for processing.
        
        Args:
            payment_instruction: Payment instruction from Orca
            
        Returns:
            Processor authorization result
        """
        try:
            # Prepare payment payload
            payload = {
                "instruction_id": payment_instruction.instruction_id,
                "trace_id": payment_instruction.trace_id,
                "amount": payment_instruction.amount,
                "currency": payment_instruction.currency,
                "rail_type": payment_instruction.selected_rail,
                "instrument_type": payment_instruction.selected_instrument,
                "processor": payment_instruction.selected_processor,
                "merchant_id": payment_instruction.metadata.get("merchant_id", ""),
                "customer_data": payment_instruction.metadata.get("customer_data", {})
            }
            
            # Submit payment (stub implementation)
            if self.api_key and self._is_api_available():
                auth_result = self._submit_real_payment(payload)
            else:
                auth_result = self._generate_stub_auth_result(payload)
            
            logger.info(f"Carat payment instruction submitted for trace_id: {payment_instruction.trace_id}")
            return auth_result
            
        except Exception as e:
            logger.error(f"Carat payment submission failed: {str(e)}")
            return ProcessorAuthResult(
                auth_id=f"carat_auth_{payment_instruction.trace_id}",
                processor_id=self.connector_id,
                status="declined",
                decline_reason=f"Processing error: {str(e)}",
                processor_fee=0.0,
                settlement_time_actual=0,
                processor_metadata={"error": str(e)},
                timestamp=datetime.now()
            )
    
    def _filter_carat_candidates(self, rail_candidates: List) -> List:
        """Filter rail candidates to only those supported by Carat."""
        return [
            candidate for candidate in rail_candidates
            if candidate.rail_type in self.supported_rails and
            candidate.instrument_type in self.supported_instruments
        ]
    
    def _prepare_carat_payload(self, bid_request: BidRequest, candidates: List) -> Dict[str, Any]:
        """Prepare payload for Carat API request."""
        return {
            "trace_id": bid_request.trace_id,
            "auction_id": bid_request.auction_id,
            "amount": bid_request.cart_summary.total_amount,
            "currency": bid_request.cart_summary.currency,
            "merchant_id": bid_request.cart_summary.merchant_id,
            "merchant_category": bid_request.cart_summary.merchant_category,
            "channel": bid_request.cart_summary.channel,
            "rail_candidates": [
                {
                    "rail_type": c.rail_type,
                    "instrument_type": c.instrument_type,
                    "base_cost_bps": c.base_cost_bps,
                    "settlement_days": c.settlement_days,
                    "risk_score": c.risk_score,
                    "is_real_time": c.is_real_time,
                    "is_cross_border": c.is_cross_border
                }
                for c in candidates
            ],
            "timestamp": bid_request.timestamp.isoformat()
        }
    
    def _is_api_available(self) -> bool:
        """Check if Carat API is available (stub implementation)."""
        try:
            # In production, this would make a health check request
            # For now, return False to use stub responses
            return False
        except:
            return False
    
    def _send_real_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send real request to Carat API (placeholder for production)."""
        # This would be implemented with actual Carat API calls
        # For now, fall back to stub
        logger.warning("Real Carat API not implemented, using stub response")
        return self._generate_stub_response(payload)
    
    def _generate_stub_response(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate deterministic stub response for Carat."""
        bids = []
        
        for candidate in payload["rail_candidates"]:
            # Carat's competitive advantage: lowest fees
            base_bps = candidate["base_cost_bps"]
            
            # Carat typically offers 15-25% lower fees than competitors
            carat_bps = base_bps * 0.75  # 25% discount
            
            # Generate rebate (Carat offers good rebates)
            rebate_bps = min(15.0, carat_bps * 0.2)  # Up to 15 bps rebate
            
            # Settlement time (Carat is fast)
            if candidate["rail_type"] in ["RTP", "FedNow"]:
                settlement_days = 0  # Real-time
            else:
                settlement_days = 1  # Next day
            
            bid = {
                "rail_type": candidate["rail_type"],
                "instrument_type": candidate["instrument_type"],
                "bps": round(carat_bps, 2),
                "rebate_bps": round(rebate_bps, 2),
                "settlement_days": settlement_days,
                "min_amount": candidate.get("min_amount", 1.0),
                "max_amount": candidate.get("max_amount", 1000000.0),
                "risk_score": candidate["risk_score"],
                "is_real_time": candidate["rail_type"] in ["RTP", "FedNow"],
                "is_cross_border": False,  # Carat focuses on US
                "reliability": 0.97,  # High reliability
                "features": {
                    "early_funding": True,
                    "fraud_protection": True,
                    "real_time_monitoring": True,
                    "api_integration": "rest"
                }
            }
            bids.append(bid)
        
        return {
            "success": True,
            "trace_id": payload["trace_id"],
            "auction_id": payload["auction_id"],
            "processor_id": self.connector_id,
            "bids": bids,
            "response_time_ms": 45,  # Fast response time
            "timestamp": datetime.now().isoformat()
        }
    
    def _submit_real_payment(self, payload: Dict[str, Any]) -> ProcessorAuthResult:
        """Submit real payment to Carat API (placeholder for production)."""
        # This would be implemented with actual Carat payment API calls
        logger.warning("Real Carat payment API not implemented, using stub response")
        return self._generate_stub_auth_result(payload)
    
    def _generate_stub_auth_result(self, payload: Dict[str, Any]) -> ProcessorAuthResult:
        """Generate deterministic stub authorization result."""
        # Carat has high approval rates for supported rails
        amount = payload["amount"]
        rail_type = payload["rail_type"]
        
        # Simulate approval logic
        if amount <= 10000 and rail_type in self.supported_rails:
            status = "approved"
            auth_code = f"CARAT_{int(time.time())}"
            decline_reason = None
            processor_fee = (amount * 0.0075) / 100  # 0.75% fee
        else:
            status = "declined"
            auth_code = None
            decline_reason = "Amount exceeds limit or unsupported rail"
            processor_fee = 0.0
        
        # Settlement time based on rail
        if rail_type in ["RTP", "FedNow"]:
            settlement_time = 0  # Real-time
        else:
            settlement_time = 24  # Next day
        
        return ProcessorAuthResult(
            auth_id=f"carat_auth_{payload['instruction_id']}",
            processor_id=self.connector_id,
            status=status,
            auth_code=auth_code,
            decline_reason=decline_reason,
            processor_fee=processor_fee,
            settlement_time_actual=settlement_time,
            processor_metadata={
                "carat_transaction_id": f"TXN_{int(time.time())}",
                "approval_score": 0.95 if status == "approved" else 0.3,
                "fraud_check": "passed" if status == "approved" else "failed",
                "rail_type": rail_type,
                "instrument_type": payload["instrument_type"]
            },
            timestamp=datetime.now()
        )


# Global instance
_carat_connector = None


def get_carat_connector(api_key: Optional[str] = None) -> CaratConnector:
    """Get global Carat connector instance."""
    global _carat_connector
    if _carat_connector is None:
        _carat_connector = CaratConnector(api_key)
    return _carat_connector









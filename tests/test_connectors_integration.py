"""
Integration tests for payment processor connectors in Weave Phase 8.

Tests Carat, Stripe, and Adyen connectors for deterministic bids,
fallback behavior, and aggregation correctness.
"""

import json
import pytest
from datetime import datetime
from pathlib import Path

from src.weave.connectors import (
    get_carat_connector,
    get_stripe_connector,
    get_adyen_connector
)
from src.weave.enhanced_bid_broadcaster import get_enhanced_bid_broadcaster
from src.weave.models import (
    BidRequest, BidResponse, CartSummary, RailCandidate
)


class TestConnectorIntegration:
    """Integration tests for payment processor connectors."""
    
    @pytest.fixture
    def carat_connector(self):
        """Get Carat connector instance."""
        return get_carat_connector()
    
    @pytest.fixture
    def stripe_connector(self):
        """Get Stripe connector instance."""
        return get_stripe_connector()
    
    @pytest.fixture
    def adyen_connector(self):
        """Get Adyen connector instance."""
        return get_adyen_connector()
    
    @pytest.fixture
    def enhanced_broadcaster(self):
        """Get enhanced bid broadcaster instance."""
        return get_enhanced_bid_broadcaster()
    
    @pytest.fixture
    def test_bid_request(self):
        """Create test bid request."""
        cart_summary = CartSummary(
            total_amount=2500.0,
            currency="USD",
            item_count=2,
            merchant_id="test_merchant_001",
            merchant_category="retail",
            channel="online"
        )
        
        rail_candidates = [
            RailCandidate(
                rail_type="ACH",
                instrument_type="bank_transfer",
                base_cost_bps=15.0,
                settlement_days=1,
                risk_score=0.3,
                is_real_time=False,
                is_cross_border=False,
                max_amount=1000000.0,
                min_amount=1.0
            ),
            RailCandidate(
                rail_type="Card",
                instrument_type="credit_card",
                base_cost_bps=200.0,
                settlement_days=2,
                risk_score=0.4,
                is_real_time=True,
                is_cross_border=True,
                max_amount=100000.0,
                min_amount=0.01
            )
        ]
        
        return BidRequest(
            trace_id="test_connector_trace_001",
            cart_summary=cart_summary,
            rail_candidates=rail_candidates,
            auction_id="test_auction_001",
            timestamp=datetime.now()
        )
    
    def test_carat_connector_deterministic_bids(self, carat_connector, test_bid_request):
        """Test that Carat connector returns deterministic bids with lowest fees."""
        # Send bid request
        response = carat_connector.send_bid_request(test_bid_request)
        
        assert response["success"] == True
        assert response["processor_id"] == "carat"
        assert "bids" in response
        
        # Parse bid responses
        bid_responses = carat_connector.parse_bid_response(response)
        
        assert len(bid_responses) > 0
        
        # Verify Carat's competitive advantage: lowest fees
        for bid_response in bid_responses:
            assert bid_response.processor_id == "carat"
            assert bid_response.bps < 200.0  # Should be competitive
            assert bid_response.rebate_bps >= 0  # Should offer rebates
            
            # Verify supported rails
            assert bid_response.constraints["rail_type"] in ["ACH", "RTP", "FedNow"]
            assert bid_response.constraints["instrument_type"] in ["debit_card", "bank_transfer"]
            
            # Verify Carat features
            carat_features = bid_response.constraints.get("carat_features", {})
            assert carat_features.get("early_funding") == True
            assert carat_features.get("fraud_protection") == True
            assert carat_features.get("real_time_monitoring") == True
    
    def test_stripe_connector_balanced_bids(self, stripe_connector, test_bid_request):
        """Test that Stripe connector returns balanced bids with global reach."""
        # Send bid request
        response = stripe_connector.send_bid_request(test_bid_request)
        
        assert response["success"] == True
        assert response["processor_id"] == "stripe"
        assert "bids" in response
        
        # Parse bid responses
        bid_responses = stripe_connector.parse_bid_response(response)
        
        assert len(bid_responses) > 0
        
        # Verify Stripe's balanced approach
        for bid_response in bid_responses:
            assert bid_response.processor_id == "stripe"
            assert 100.0 <= bid_response.bps <= 300.0  # Balanced pricing
            assert bid_response.rebate_bps >= 0
            
            # Verify supported rails (cards only)
            assert bid_response.constraints["rail_type"] == "Card"
            assert bid_response.constraints["instrument_type"] in ["credit_card", "debit_card", "prepaid_card", "digital_wallet"]
            
            # Verify Stripe features
            stripe_features = bid_response.constraints.get("stripe_features", {})
            assert stripe_features.get("global_reach") == True
            assert stripe_features.get("fraud_protection") == True
            assert stripe_features.get("chargeback_protection") == True
            assert stripe_features.get("webhook_support") == True
            assert stripe_features.get("mobile_sdk") == True
    
    def test_adyen_connector_premium_speed(self, adyen_connector, test_bid_request):
        """Test that Adyen connector returns premium bids with fast settlement."""
        # Send bid request
        response = adyen_connector.send_bid_request(test_bid_request)
        
        assert response["success"] == True
        assert response["processor_id"] == "adyen"
        assert "bids" in response
        
        # Parse bid responses
        bid_responses = adyen_connector.parse_bid_response(response)
        
        assert len(bid_responses) > 0
        
        # Verify Adyen's premium approach
        for bid_response in bid_responses:
            assert bid_response.processor_id == "adyen"
            assert bid_response.bps >= 200.0  # Premium pricing
            assert bid_response.rebate_bps >= 0
            assert bid_response.expected_settlement_days <= 1  # Fast settlement
            
            # Verify supported rails
            assert bid_response.constraints["rail_type"] in ["Card", "ACH", "SEPA"]
            assert bid_response.constraints["instrument_type"] in ["credit_card", "debit_card", "bank_transfer"]
            
            # Verify Adyen features
            adyen_features = bid_response.constraints.get("adyen_features", {})
            assert adyen_features.get("next_day_settlement") == True
            assert adyen_features.get("global_coverage") == True
            assert adyen_features.get("local_acquiring") == True
            assert adyen_features.get("multi_currency") == True
    
    def test_connector_fallback_behavior(self, carat_connector, test_bid_request):
        """Test that connectors fall back to stub when API is unreachable."""
        # Test with unsupported rail candidates
        unsupported_request = BidRequest(
            trace_id="test_unsupported_001",
            cart_summary=test_bid_request.cart_summary,
            rail_candidates=[
                RailCandidate(
                    rail_type="Wire",  # Carat doesn't support Wire
                    instrument_type="bank_transfer",
                    base_cost_bps=50.0,
                    settlement_days=1,
                    risk_score=0.2,
                    is_real_time=False,
                    is_cross_border=True,
                    max_amount=1000000.0,
                    min_amount=1000.0
                )
            ],
            auction_id="test_unsupported_auction",
            timestamp=datetime.now()
        )
        
        response = carat_connector.send_bid_request(unsupported_request)
        
        # Should fail gracefully
        assert response["success"] == False
        assert "error" in response
        assert "No supported rail candidates for Carat" in response["error"]
    
    def test_enhanced_broadcaster_aggregation(self, enhanced_broadcaster, test_bid_request):
        """Test that enhanced broadcaster aggregates responses correctly."""
        bid_requests = [test_bid_request]
        
        # Broadcast to all connectors
        bid_responses, broadcast_metadata = enhanced_broadcaster.broadcast_bid_requests(bid_requests)
        
        # Verify aggregation
        assert len(bid_responses) > 0
        assert broadcast_metadata["total_requests"] == 1
        assert broadcast_metadata["successful_requests"] > 0
        assert len(broadcast_metadata["connectors_contacted"]) > 0
        
        # Verify we got responses from multiple processors
        processor_ids = set(response.processor_id for response in bid_responses)
        assert len(processor_ids) > 1  # Should have multiple processors
        
        # Verify each processor provided appropriate responses
        for processor_id in processor_ids:
            processor_responses = [r for r in bid_responses if r.processor_id == processor_id]
            assert len(processor_responses) > 0
            
            # Verify processor-specific characteristics
            if processor_id == "carat":
                assert all(r.bps < 200.0 for r in processor_responses)  # Low fees
            elif processor_id == "stripe":
                assert all(100.0 <= r.bps <= 300.0 for r in processor_responses)  # Balanced
            elif processor_id == "adyen":
                assert all(r.bps >= 200.0 for r in processor_responses)  # Premium
    
    def test_connector_deterministic_behavior(self, carat_connector, test_bid_request):
        """Test that connectors return deterministic results."""
        # Send same request multiple times
        response1 = carat_connector.send_bid_request(test_bid_request)
        response2 = carat_connector.send_bid_request(test_bid_request)
        
        # Responses should be identical
        assert response1["success"] == response2["success"]
        assert response1["processor_id"] == response2["processor_id"]
        
        if response1["success"] and response2["success"]:
            bids1 = response1["bids"]
            bids2 = response2["bids"]
            
            assert len(bids1) == len(bids2)
            
            for bid1, bid2 in zip(bids1, bids2):
                assert bid1["bps"] == bid2["bps"]
                assert bid1["rebate_bps"] == bid2["rebate_bps"]
                assert bid1["settlement_days"] == bid2["settlement_days"]
    
    def test_connector_connectivity_test(self, enhanced_broadcaster):
        """Test connector connectivity testing functionality."""
        connectivity_status = enhanced_broadcaster.test_connector_connectivity()
        
        # Should have status for all connectors
        assert "carat" in connectivity_status
        assert "stripe" in connectivity_status
        assert "adyen" in connectivity_status
        
        # Each connector should have status information
        for connector_name, status in connectivity_status.items():
            assert "status" in status
            assert "response_time_ms" in status
            assert "error" in status
            assert "supports_test_rail" in status
            
            # Should be connected (using stubs)
            assert status["status"] in ["connected", "error"]
    
    def test_connector_summary(self, enhanced_broadcaster):
        """Test connector summary functionality."""
        summary = enhanced_broadcaster.get_connector_summary()
        
        # Should have summary for all connectors
        assert "carat" in summary
        assert "stripe" in summary
        assert "adyen" in summary
        
        # Verify connector capabilities
        carat_info = summary["carat"]
        assert carat_info["connector_id"] == "carat"
        assert "ACH" in carat_info["supported_rails"]
        assert "RTP" in carat_info["supported_rails"]
        assert "debit_card" in carat_info["supported_instruments"]
        assert carat_info["has_api_key"] == False  # Using stub mode
        
        stripe_info = summary["stripe"]
        assert stripe_info["connector_id"] == "stripe"
        assert "Card" in stripe_info["supported_rails"]
        assert "credit_card" in stripe_info["supported_instruments"]
        
        adyen_info = summary["adyen"]
        assert adyen_info["connector_id"] == "adyen"
        assert "Card" in adyen_info["supported_rails"]
        assert "ACH" in adyen_info["supported_rails"]
        assert "SEPA" in adyen_info["supported_rails"]
    
    def test_payment_instruction_submission(self, carat_connector):
        """Test payment instruction submission to connectors."""
        from src.weave.models import PaymentInstruction
        
        # Create test payment instruction
        payment_instruction = PaymentInstruction(
            instruction_id="test_instruction_001",
            trace_id="test_payment_trace_001",
            selected_rail="ACH",
            selected_processor="carat",
            selected_instrument="bank_transfer",
            amount=1000.0,
            currency="USD",
            effective_cost=15.0,
            settlement_time_hours=24,
            confidence=0.95,
            explanation="Test payment instruction",
            alternatives=[],
            constraints_applied=[],
            metadata={
                "merchant_id": "test_merchant",
                "customer_data": {"customer_id": "test_customer"}
            }
        )
        
        # Submit payment instruction
        auth_result = carat_connector.submit_payment_instruction(payment_instruction)
        
        # Verify authorization result
        assert auth_result.processor_id == "carat"
        assert auth_result.status in ["approved", "declined"]
        assert auth_result.auth_id.startswith("carat_auth_")
        
        if auth_result.status == "approved":
            assert auth_result.auth_code is not None
            assert auth_result.processor_fee > 0
            assert "carat_transaction_id" in auth_result.processor_metadata
        else:
            assert auth_result.decline_reason is not None
    
    def test_multi_rail_connector_coverage(self, enhanced_broadcaster):
        """Test that connectors cover multiple rail types appropriately."""
        # Create requests for different rail types
        rail_types = ["ACH", "Card", "SEPA", "RTP", "FedNow", "Crypto"]
        supported_combinations = []
        
        for rail_type in rail_types:
            cart_summary = CartSummary(
                total_amount=1000.0,
                currency="USD",
                item_count=1,
                merchant_id="test_merchant",
                merchant_category="general",
                channel="online"
            )
            
            # Create appropriate instrument type for each rail
            if rail_type == "Card":
                instrument_type = "credit_card"
            elif rail_type in ["ACH", "RTP", "FedNow"]:
                instrument_type = "bank_transfer"
            elif rail_type == "SEPA":
                instrument_type = "bank_transfer"
            elif rail_type == "Crypto":
                instrument_type = "stablecoin"
            else:
                instrument_type = "bank_transfer"
            
            rail_candidates = [
                RailCandidate(
                    rail_type=rail_type,
                    instrument_type=instrument_type,
                    base_cost_bps=100.0,
                    settlement_days=1,
                    risk_score=0.3,
                    is_real_time=rail_type in ["RTP", "FedNow", "Crypto"],
                    is_cross_border=rail_type in ["Card", "SEPA", "Crypto"],
                    max_amount=1000000.0,
                    min_amount=1.0
                )
            ]
            
            bid_request = BidRequest(
                trace_id=f"test_coverage_{rail_type}",
                cart_summary=cart_summary,
                rail_candidates=rail_candidates,
                auction_id=f"test_coverage_auction_{rail_type}",
                timestamp=datetime.now()
            )
            
            # Broadcast request
            bid_responses, _ = enhanced_broadcaster.broadcast_bid_requests([bid_request])
            
            if bid_responses:
                supported_combinations.append((rail_type, instrument_type))
        
        # Verify good coverage
        assert len(supported_combinations) >= 3, f"Only {len(supported_combinations)} rail types supported"
        
        # Verify specific important combinations are covered
        important_combinations = [("ACH", "bank_transfer"), ("Card", "credit_card")]
        found_important = sum(1 for combo in important_combinations if combo in supported_combinations)
        assert found_important >= 2, f"Only found {found_important}/2 important combinations"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])









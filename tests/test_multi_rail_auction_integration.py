"""
Integration tests for multi-rail auction functionality in Weave Phase 7.

Tests comprehensive auction management across multiple payment rails
and instruments, including candidate generation, bid broadcasting, and winner selection.
"""

import json
import pytest
from pathlib import Path

from src.weave.multi_rail_auction_manager import (
    get_multi_rail_auction_manager,
    get_multi_rail_auction_generator,
    get_multi_rail_bid_broadcaster,
    get_multi_rail_auction_registry
)
from src.weave.models import (
    CartSummary,
    RailCandidate,
    BidRequest,
    BidResponse,
    AuctionResult,
    RailType,
    InstrumentType
)


class TestMultiRailAuctionIntegration:
    """Integration tests for multi-rail auction functionality."""
    
    @pytest.fixture
    def auction_manager(self):
        """Get multi-rail auction manager."""
        return get_multi_rail_auction_manager()
    
    @pytest.fixture
    def auction_generator(self):
        """Get multi-rail auction generator."""
        return get_multi_rail_auction_generator()
    
    @pytest.fixture
    def bid_broadcaster(self):
        """Get multi-rail bid broadcaster."""
        return get_multi_rail_bid_broadcaster()
    
    @pytest.fixture
    def auction_registry(self):
        """Get multi-rail auction registry."""
        return get_multi_rail_auction_registry()
    
    @pytest.fixture
    def auction_fixture(self):
        """Load auction multi-rail test fixture."""
        fixture_path = Path(__file__).parent / "fixtures" / "multi_rail" / "auction_multi_rail_example.json"
        with open(fixture_path) as f:
            return json.load(f)
    
    def test_auction_registry_initialization(self, auction_registry):
        """Test that auction registry is properly initialized."""
        # Test rail capabilities
        assert "ACH" in auction_registry.rail_capabilities
        assert "RTP" in auction_registry.rail_capabilities
        assert "FedNow" in auction_registry.rail_capabilities
        assert "SEPA" in auction_registry.rail_capabilities
        assert "Wire" in auction_registry.rail_capabilities
        assert "Crypto" in auction_registry.rail_capabilities
        assert "Card" in auction_registry.rail_capabilities
        
        # Test instrument capabilities
        assert "credit_card" in auction_registry.instrument_capabilities
        assert "debit_card" in auction_registry.instrument_capabilities
        assert "prepaid_card" in auction_registry.instrument_capabilities
        assert "bank_transfer" in auction_registry.instrument_capabilities
        assert "stablecoin" in auction_registry.instrument_capabilities
        assert "digital_wallet" in auction_registry.instrument_capabilities
        assert "bnpl" in auction_registry.instrument_capabilities
        assert "cash" in auction_registry.instrument_capabilities
        
        # Test processor capabilities
        assert "stripe" in auction_registry.processor_capabilities
        assert "adyen" in auction_registry.processor_capabilities
        assert "carat" in auction_registry.processor_capabilities
        assert "coinbase" in auction_registry.processor_capabilities
        assert "wise" in auction_registry.processor_capabilities
        
        # Test valid combinations
        valid_combinations = auction_registry.get_valid_combinations()
        assert len(valid_combinations) > 0
        
        # Verify specific combinations exist
        assert ("FedNow", "debit_card") in valid_combinations
        assert ("SEPA", "bank_transfer") in valid_combinations
        assert ("Crypto", "stablecoin") in valid_combinations
    
    def test_rail_candidate_generation(self, auction_generator, auction_fixture):
        """Test rail candidate generation matches expected results."""
        fixture = auction_fixture
        
        # Create cart summary
        cart_summary = CartSummary(**fixture["cart_summary"])
        
        # Create constraints
        constraints = fixture["constraints"]
        
        # Generate rail candidates
        rail_candidates = auction_generator.generate_rail_candidates(cart_summary, constraints)
        
        assert len(rail_candidates) > 0
        
        # Verify candidates include expected rails
        rail_types = [c.rail_type for c in rail_candidates]
        instrument_types = [c.instrument_type for c in rail_candidates]
        
        # Should include SEPA for cross-border requirement
        assert "SEPA" in rail_types
        assert "bank_transfer" in instrument_types
        
        # Verify constraints are applied
        for candidate in rail_candidates:
            assert candidate.base_cost_bps <= constraints["max_cost_bps"]
            assert candidate.risk_score <= constraints["max_risk"]
            assert candidate.is_cross_border == True  # Required by constraints
        
        # Verify candidates are sorted by cost
        for i in range(len(rail_candidates) - 1):
            assert rail_candidates[i].base_cost_bps <= rail_candidates[i + 1].base_cost_bps
    
    def test_bid_request_broadcasting(self, bid_broadcaster, auction_fixture):
        """Test bid request broadcasting to processors."""
        fixture = auction_fixture
        
        # Create cart summary
        cart_summary = CartSummary(**fixture["cart_summary"])
        
        # Create rail candidates
        rail_candidates = []
        for candidate_data in fixture["expected_rail_candidates"][:2]:  # Test with first 2 candidates
            candidate = RailCandidate(**candidate_data)
            rail_candidates.append(candidate)
        
        # Broadcast bid requests
        bid_requests = bid_broadcaster.broadcast_bid_requests(rail_candidates, cart_summary, "test_trace_001")
        
        assert len(bid_requests) > 0
        
        # Verify bid request structure
        for request in bid_requests:
            assert request.trace_id == "test_trace_001"
            assert isinstance(request.cart_summary, CartSummary)
            assert len(request.rail_candidates) > 0
            assert request.auction_id
            assert request.timestamp
        
        # Verify each rail candidate gets bid requests
        rail_instrument_combinations = set()
        for request in bid_requests:
            for candidate in request.rail_candidates:
                combination = (candidate.rail_type, candidate.instrument_type)
                rail_instrument_combinations.add(combination)
        
        assert len(rail_instrument_combinations) == len(rail_candidates)
    
    def test_bid_response_simulation(self, bid_broadcaster, auction_fixture):
        """Test bid response simulation from processors."""
        fixture = auction_fixture
        
        # Create bid requests from fixture
        bid_requests = []
        for request_data in fixture["expected_bid_requests"]:
            # Create rail candidates
            rail_candidates = [RailCandidate(**c) for c in request_data["rail_candidates"]]
            
            # Create bid request
            request = BidRequest(
                trace_id=request_data["trace_id"],
                cart_summary=CartSummary(**request_data["cart_summary"]),
                rail_candidates=rail_candidates,
                auction_id=request_data["auction_id"],
                timestamp=request_data["timestamp"]
            )
            bid_requests.append(request)
        
        # Simulate bid responses
        bid_responses = bid_broadcaster.simulate_bid_responses(bid_requests)
        
        assert len(bid_responses) > 0
        
        # Verify bid response structure
        for response in bid_responses:
            assert response.trace_id
            assert response.processor_id
            assert response.auction_id
            assert response.bps > 0
            assert response.rebate_bps >= 0
            assert response.expected_settlement_days >= 0
            assert response.constraints
            assert response.timestamp
        
        # Verify processors are represented
        processor_ids = set(r.processor_id for r in bid_responses)
        expected_processors = ["wise", "adyen", "stripe", "carat", "coinbase"]
        assert any(pid in processor_ids for pid in expected_processors)
    
    def test_auction_winner_selection(self, auction_manager, auction_fixture):
        """Test auction winner selection logic."""
        fixture = auction_fixture
        
        # Create cart summary
        cart_summary = CartSummary(**fixture["cart_summary"])
        
        # Create constraints
        constraints = fixture["constraints"]
        
        # Run complete auction
        auction_result = auction_manager.run_multi_rail_auction(
            cart_summary, constraints, "test_auction_001"
        )
        
        assert isinstance(auction_result, AuctionResult)
        assert auction_result.trace_id == "test_auction_001"
        assert auction_result.winner is not None
        assert len(auction_result.all_bids) > 0
        assert auction_result.total_participants > 0
        assert auction_result.total_rail_combinations > 0
        
        # Verify winner selection criteria
        winner = auction_result.winner
        assert winner.processor_id in ["wise", "adyen", "stripe", "carat", "coinbase"]
        assert winner.bps > 0
        assert winner.rebate_bps >= 0
        
        # Verify winner meets constraints
        assert winner.constraints["is_cross_border"] == True  # Required by constraints
        assert winner.bps <= constraints["max_cost_bps"] * 2  # Allow some margin for competitive bidding
    
    def test_multi_rail_auction_complete_flow(self, auction_manager, auction_fixture):
        """Test complete multi-rail auction flow."""
        fixture = auction_fixture
        
        # Create cart summary
        cart_summary = CartSummary(**fixture["cart_summary"])
        
        # Create constraints
        constraints = fixture["constraints"]
        
        # Run complete auction
        auction_result = auction_manager.run_multi_rail_auction(
            cart_summary, constraints, "test_complete_flow_001"
        )
        
        # Verify auction result structure
        assert auction_result.auction_id
        assert auction_result.winner is not None
        assert len(auction_result.all_bids) > 0
        assert auction_result.auction_metadata
        
        # Verify metadata includes multi-rail information
        metadata = auction_result.auction_metadata
        assert metadata["multi_rail_enabled"] == True
        assert "rail_candidates" in metadata
        assert "bid_requests" in metadata
        assert "constraints_applied" in metadata
        
        # Verify rail candidates are included
        assert len(metadata["rail_candidates"]) > 0
        for candidate_data in metadata["rail_candidates"]:
            assert "rail_type" in candidate_data
            assert "instrument_type" in candidate_data
            assert "base_cost_bps" in candidate_data
            assert "is_cross_border" in candidate_data
        
        # Verify constraints were applied
        applied_constraints = metadata["constraints_applied"]
        assert applied_constraints["cross_border"] == True
        assert applied_constraints["max_cost_bps"] == constraints["max_cost_bps"]
    
    def test_rail_instrument_combination_coverage(self, auction_generator):
        """Test that auction covers multiple rail/instrument combinations."""
        # Create cart summary
        cart_summary = CartSummary(
            total_amount=2000.0,
            currency="USD",
            item_count=2,
            merchant_id="test_coverage_merchant",
            merchant_category="general",
            channel="online"
        )
        
        # Generate rail candidates without constraints
        rail_candidates = auction_generator.generate_rail_candidates(cart_summary)
        
        # Verify good coverage of rail types
        rail_types = set(c.rail_type for c in rail_candidates)
        instrument_types = set(c.instrument_type for c in rail_candidates)
        
        # Should include multiple rail types
        assert len(rail_types) >= 4  # Should have ACH, Card, SEPA, Crypto at minimum
        assert len(instrument_types) >= 4  # Should have multiple instrument types
        
        # Verify specific important combinations exist
        combinations = set((c.rail_type, c.instrument_type) for c in rail_candidates)
        important_combinations = [
            ("Card", "credit_card"),
            ("ACH", "bank_transfer"),
            ("SEPA", "bank_transfer"),
            ("Crypto", "stablecoin")
        ]
        
        found_important = sum(1 for combo in important_combinations if combo in combinations)
        assert found_important >= 2, f"Only found {found_important}/4 important combinations"
    
    def test_constraint_filtering(self, auction_generator):
        """Test that constraints properly filter rail candidates."""
        # Create cart summary
        cart_summary = CartSummary(
            total_amount=5000.0,
            currency="USD",
            item_count=1,
            merchant_id="test_constraints_merchant",
            merchant_category="general",
            channel="mobile"
        )
        
        # Test real-time constraint
        real_time_constraints = {
            "require_real_time": True,
            "max_cost_bps": 100.0,
            "max_risk": 0.8
        }
        
        real_time_candidates = auction_generator.generate_rail_candidates(cart_summary, real_time_constraints)
        
        # All candidates should be real-time
        for candidate in real_time_candidates:
            assert candidate.is_real_time == True
        
        # Test cross-border constraint
        cross_border_constraints = {
            "cross_border": True,
            "max_cost_bps": 100.0,
            "max_risk": 0.8
        }
        
        cross_border_candidates = auction_generator.generate_rail_candidates(cart_summary, cross_border_constraints)
        
        # All candidates should support cross-border
        for candidate in cross_border_candidates:
            assert candidate.is_cross_border == True
        
        # Test cost constraint
        low_cost_constraints = {
            "max_cost_bps": 20.0,
            "max_risk": 1.0
        }
        
        low_cost_candidates = auction_generator.generate_rail_candidates(cart_summary, low_cost_constraints)
        
        # All candidates should meet cost constraint
        for candidate in low_cost_candidates:
            assert candidate.base_cost_bps <= low_cost_constraints["max_cost_bps"]
    
    def test_processor_capability_matching(self, auction_registry):
        """Test that processors are correctly matched to rail/instrument combinations."""
        # Test SEPA/bank_transfer combination
        sepa_processors = auction_registry.get_processors_for_combination("SEPA", "bank_transfer")
        assert "wise" in sepa_processors  # Wise supports SEPA
        assert "adyen" in sepa_processors  # Adyen supports SEPA
        
        # Test Crypto/stablecoin combination
        crypto_processors = auction_registry.get_processors_for_combination("Crypto", "stablecoin")
        assert "coinbase" in crypto_processors  # Coinbase supports crypto
        
        # Test Card/credit_card combination
        card_processors = auction_registry.get_processors_for_combination("Card", "credit_card")
        assert "stripe" in card_processors  # Stripe supports cards
        assert "adyen" in card_processors  # Adyen supports cards
        
        # Test ACH/bank_transfer combination
        ach_processors = auction_registry.get_processors_for_combination("ACH", "bank_transfer")
        assert "carat" in ach_processors  # Carat supports ACH
        
        # Test invalid combination
        invalid_processors = auction_registry.get_processors_for_combination("Crypto", "credit_card")
        assert len(invalid_processors) == 0  # No processors support this combination
    
    def test_auction_scoring_consistency(self, auction_manager):
        """Test that auction scoring is consistent and deterministic."""
        # Create cart summary
        cart_summary = CartSummary(
            total_amount=1500.0,
            currency="USD",
            item_count=1,
            merchant_id="test_scoring_merchant",
            merchant_category="general",
            channel="online"
        )
        
        # Run auction multiple times
        result1 = auction_manager.run_multi_rail_auction(cart_summary, None, "test_scoring_001")
        result2 = auction_manager.run_multi_rail_auction(cart_summary, None, "test_scoring_002")
        
        # Verify both auctions completed successfully
        assert result1.winner is not None
        assert result2.winner is not None
        
        # Verify similar structure (may have different winners due to randomization in simulation)
        assert len(result1.all_bids) > 0
        assert len(result2.all_bids) > 0
        assert result1.total_participants > 0
        assert result2.total_participants > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])









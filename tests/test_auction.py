"""
Tests for Weave auction functionality.

Tests processor auction, bid aggregation, CloudEvent emission, and LLM explanations.
"""

import json
import pytest
from datetime import datetime
from typing import Dict, Any

from weave.models import (
    CartSummary, RailCandidate, BidRequest, BidResponse, AuctionResult
)
from weave.auction import (
    ProcessorConnector, AuctionManager, run_auction
)
from weave.auction_events import (
    BidRequestData, BidResponseData, BidRequestEvent, BidResponseEvent,
    create_bid_request_payload, create_bid_response_payload,
    emit_bid_request_event, emit_bid_response_event,
    validate_bid_request_event, validate_bid_response_event,
    get_bid_request_event_schema, get_bid_response_event_schema
)
from weave.llm.explain import (
    AuctionLLMExplainer, AuctionExplanationRequest, AuctionExplanationResponse,
    is_auction_llm_configured, explain_auction_result_llm
)


class TestProcessorConnector:
    """Test processor connector functionality."""
    
    def test_processor_connector_initialization(self):
        """Test processor connector initialization."""
        connector = ProcessorConnector("stripe", deterministic_seed=42)
        
        assert connector.processor_id == "stripe"
        assert connector.deterministic_seed == 42
    
    def test_stripe_bid_generation(self):
        """Test Stripe bid generation."""
        connector = ProcessorConnector("stripe", deterministic_seed=42)
        
        cart_summary = CartSummary(
            total_amount=100.0,
            currency="USD",
            item_count=2,
            merchant_id="merchant_001"
        )
        
        rail_candidates = [
            RailCandidate(
                rail_type="credit",
                base_cost_bps=150.0,
                settlement_days=1,
                risk_score=0.3
            )
        ]
        
        bid_request = BidRequest(
            trace_id="test-trace-001",
            cart_summary=cart_summary,
            rail_candidates=rail_candidates,
            auction_id="auction-001"
        )
        
        bid_response = connector.generate_bid(bid_request)
        
        assert isinstance(bid_response, BidResponse)
        assert bid_response.processor_id == "stripe"
        assert bid_response.trace_id == "test-trace-001"
        assert bid_response.auction_id == "auction-001"
        assert bid_response.bps > 0
        assert bid_response.rebate_bps >= 0
        assert bid_response.expected_settlement_days == 1
        assert 0.0 <= bid_response.confidence <= 1.0
        assert "min_amount" in bid_response.constraints
    
    def test_adyen_bid_generation(self):
        """Test Adyen bid generation."""
        connector = ProcessorConnector("adyen", deterministic_seed=42)
        
        cart_summary = CartSummary(
            total_amount=500.0,
            currency="USD",
            item_count=1,
            merchant_id="merchant_002"
        )
        
        rail_candidates = [
            RailCandidate(
                rail_type="debit",
                base_cost_bps=100.0,
                settlement_days=2,
                risk_score=0.2
            )
        ]
        
        bid_request = BidRequest(
            trace_id="test-trace-002",
            cart_summary=cart_summary,
            rail_candidates=rail_candidates,
            auction_id="auction-002"
        )
        
        bid_response = connector.generate_bid(bid_request)
        
        assert isinstance(bid_response, BidResponse)
        assert bid_response.processor_id == "adyen"
        assert bid_response.expected_settlement_days == 2
        assert "supported_currencies" in bid_response.constraints
    
    def test_carat_bid_generation(self):
        """Test Carat bid generation."""
        connector = ProcessorConnector("carat", deterministic_seed=42)
        
        cart_summary = CartSummary(
            total_amount=1000.0,
            currency="USD",
            item_count=5,
            merchant_id="merchant_003"
        )
        
        rail_candidates = [
            RailCandidate(
                rail_type="ACH",
                base_cost_bps=50.0,
                settlement_days=1,
                risk_score=0.1
            )
        ]
        
        bid_request = BidRequest(
            trace_id="test-trace-003",
            cart_summary=cart_summary,
            rail_candidates=rail_candidates,
            auction_id="auction-003"
        )
        
        bid_response = connector.generate_bid(bid_request)
        
        assert isinstance(bid_response, BidResponse)
        assert bid_response.processor_id == "carat"
        assert bid_response.expected_settlement_days == 1
        assert bid_response.constraints["risk_tolerance"] == "low"


class TestAuctionManager:
    """Test auction manager functionality."""
    
    def test_auction_manager_initialization(self):
        """Test auction manager initialization."""
        manager = AuctionManager(deterministic_seed=42)
        
        assert len(manager.processors) == 3
        assert "stripe" in manager.processors
        assert "adyen" in manager.processors
        assert "carat" in manager.processors
    
    def test_auction_execution(self):
        """Test complete auction execution."""
        manager = AuctionManager(deterministic_seed=42)
        
        cart_summary = CartSummary(
            total_amount=250.0,
            currency="USD",
            item_count=3,
            merchant_id="merchant_004"
        )
        
        rail_candidates = [
            RailCandidate(
                rail_type="credit",
                base_cost_bps=150.0,
                settlement_days=1,
                risk_score=0.3
            ),
            RailCandidate(
                rail_type="debit",
                base_cost_bps=100.0,
                settlement_days=2,
                risk_score=0.2
            )
        ]
        
        result = manager.run_auction(
            trace_id="test-trace-004",
            cart_summary=cart_summary,
            rail_candidates=rail_candidates
        )
        
        assert isinstance(result, AuctionResult)
        assert result.trace_id == "test-trace-004"
        assert result.winning_processor in ["stripe", "adyen", "carat"]
        assert len(result.all_bids) == 3
        assert result.effective_cost_bps >= 0  # Allow 0.0 when rebate >= bps
        assert isinstance(result.summary, str)
        assert len(result.summary) > 0
    
    def test_winner_determination(self):
        """Test winner determination logic."""
        manager = AuctionManager(deterministic_seed=42)
        
        # Create mock bids with different effective costs
        bids = [
            BidResponse(
                trace_id="test-trace-005",
                processor_id="stripe",
                auction_id="auction-005",
                bps=150.0,
                rebate_bps=10.0,
                expected_settlement_days=1,
                constraints={},
                confidence=0.9
            ),
            BidResponse(
                trace_id="test-trace-005",
                processor_id="adyen",
                auction_id="auction-005",
                bps=145.0,
                rebate_bps=5.0,
                expected_settlement_days=2,
                constraints={},
                confidence=0.85
            ),
            BidResponse(
                trace_id="test-trace-005",
                processor_id="carat",
                auction_id="auction-005",
                bps=140.0,
                rebate_bps=15.0,
                expected_settlement_days=1,
                constraints={},
                confidence=0.95
            )
        ]
        
        winner = manager._determine_winner(bids)
        
        # Carat should win (140 - 15 = 125 bps effective cost)
        assert winner.processor_id == "carat"
        assert winner.bps == 140.0
        assert winner.rebate_bps == 15.0
    
    def test_tie_breaker_logic(self):
        """Test tie-breaker logic for identical effective costs."""
        manager = AuctionManager(deterministic_seed=42)
        
        # Create bids with identical effective costs but different settlement days
        bids = [
            BidResponse(
                trace_id="test-trace-006",
                processor_id="stripe",
                auction_id="auction-006",
                bps=150.0,
                rebate_bps=10.0,
                expected_settlement_days=2,  # Slower settlement
                constraints={},
                confidence=0.9
            ),
            BidResponse(
                trace_id="test-trace-006",
                processor_id="adyen",
                auction_id="auction-006",
                bps=145.0,
                rebate_bps=5.0,
                expected_settlement_days=1,  # Faster settlement
                constraints={},
                confidence=0.85
            )
        ]
        
        winner = manager._determine_winner(bids)
        
        # Adyen should win due to faster settlement (tie-breaker)
        assert winner.processor_id == "adyen"
        assert winner.expected_settlement_days == 1


class TestAuctionAggregation:
    """Test auction aggregation and math."""
    
    def test_effective_cost_calculation(self):
        """Test effective cost calculation."""
        cart_summary = CartSummary(
            total_amount=100.0,
            currency="USD",
            item_count=1,
            merchant_id="merchant_007"
        )
        
        rail_candidates = [
            RailCandidate(
                rail_type="credit",
                base_cost_bps=150.0,
                settlement_days=1,
                risk_score=0.3
            )
        ]
        
        result = run_auction(
            trace_id="test-trace-007",
            cart_summary=cart_summary,
            rail_candidates=rail_candidates,
            deterministic_seed=42
        )
        
        # Verify effective cost calculation
        expected_effective_cost = max(0.0, result.winning_bid.bps - result.winning_bid.rebate_bps)
        assert result.effective_cost_bps == expected_effective_cost
        assert result.effective_cost_bps >= 0
    
    def test_aggregation_math(self):
        """Test aggregation math with multiple bids."""
        cart_summary = CartSummary(
            total_amount=500.0,
            currency="USD",
            item_count=2,
            merchant_id="merchant_008"
        )
        
        rail_candidates = [
            RailCandidate(
                rail_type="credit",
                base_cost_bps=150.0,
                settlement_days=1,
                risk_score=0.3
            )
        ]
        
        result = run_auction(
            trace_id="test-trace-008",
            cart_summary=cart_summary,
            rail_candidates=rail_candidates,
            deterministic_seed=42
        )
        
        # Verify all bids are collected
        assert len(result.all_bids) == 3
        
        # Verify effective costs are calculated correctly for all bids
        for bid in result.all_bids:
            effective_cost = max(0.0, bid.bps - bid.rebate_bps)
            assert effective_cost >= 0
            assert effective_cost == bid.effective_cost_bps
        
        # Verify winner has the best (lowest) effective cost
        winner_effective_cost = result.winning_bid.effective_cost_bps
        for bid in result.all_bids:
            bid_effective_cost = bid.effective_cost_bps
            assert winner_effective_cost <= bid_effective_cost
    
    def test_deterministic_snapshots(self):
        """Test deterministic auction results."""
        cart_summary = CartSummary(
            total_amount=300.0,
            currency="USD",
            item_count=2,
            merchant_id="merchant_009"
        )
        
        rail_candidates = [
            RailCandidate(
                rail_type="debit",
                base_cost_bps=100.0,
                settlement_days=2,
                risk_score=0.2
            )
        ]
        
        # Run auction multiple times with same seed
        results = []
        for i in range(3):
            result = run_auction(
                trace_id=f"test-trace-009-{i}",
                cart_summary=cart_summary,
                rail_candidates=rail_candidates,
                deterministic_seed=42
            )
            results.append(result)
        
        # All results should be identical
        for i in range(1, len(results)):
            assert results[i].winning_processor == results[0].winning_processor
            assert results[i].effective_cost_bps == results[0].effective_cost_bps
            assert results[i].summary == results[0].summary


class TestAuctionCloudEvents:
    """Test CloudEvent emission for auction."""
    
    def test_bid_request_data_creation(self):
        """Test bid request data payload creation."""
        cart_summary = CartSummary(
            total_amount=150.0,
            currency="USD",
            item_count=2,
            merchant_id="merchant_010"
        )
        
        rail_candidates = [
            RailCandidate(
                rail_type="credit",
                base_cost_bps=150.0,
                settlement_days=1,
                risk_score=0.3
            )
        ]
        
        bid_request = BidRequest(
            trace_id="test-trace-010",
            cart_summary=cart_summary,
            rail_candidates=rail_candidates,
            auction_id="auction-010"
        )
        
        data = create_bid_request_payload(
            bid_request=bid_request,
            merchant_context={"merchant_id": "merchant_010"},
            explanation="Test bid request"
        )
        
        assert isinstance(data, BidRequestData)
        assert data.trace_id == "test-trace-010"
        assert data.auction_id == "auction-010"
        assert data.merchant_context["merchant_id"] == "merchant_010"
        assert len(data.rail_candidates) == 1
        assert data.rail_candidates[0]["rail_type"] == "credit"
    
    def test_bid_response_data_creation(self):
        """Test bid response data payload creation."""
        bid_response = BidResponse(
            trace_id="test-trace-011",
            processor_id="stripe",
            auction_id="auction-011",
            bps=150.0,
            rebate_bps=10.0,
            expected_settlement_days=1,
            constraints={"min_amount": 0.50},
            confidence=0.9
        )
        
        cart_summary = CartSummary(
            total_amount=200.0,
            currency="USD",
            item_count=1,
            merchant_id="merchant_011"
        )
        
        data = create_bid_response_payload(
            bid_response=bid_response,
            merchant_context={"merchant_id": "merchant_011"},
            cart_summary=cart_summary,
            explanation="Test bid response"
        )
        
        assert isinstance(data, BidResponseData)
        assert data.trace_id == "test-trace-011"
        assert data.processor_id == "stripe"
        assert data.bps == 150.0
        assert data.rebate_bps == 10.0
        assert data.effective_cost_bps == 140.0
        assert data.confidence == 0.9
    
    def test_bid_request_event_emission(self):
        """Test bid request CloudEvent emission."""
        cart_summary = CartSummary(
            total_amount=100.0,
            currency="USD",
            item_count=1,
            merchant_id="merchant_012"
        )
        
        rail_candidates = [
            RailCandidate(
                rail_type="credit",
                base_cost_bps=150.0,
                settlement_days=1,
                risk_score=0.3
            )
        ]
        
        bid_request = BidRequest(
            trace_id="test-trace-012",
            cart_summary=cart_summary,
            rail_candidates=rail_candidates,
            auction_id="auction-012"
        )
        
        event = emit_bid_request_event(
            bid_request=bid_request,
            merchant_context={"merchant_id": "merchant_012"},
            explanation="Test bid request event"
        )
        
        assert isinstance(event, BidRequestEvent)
        assert event.specversion == "1.0"
        assert event.type == "ocn.weave.bid_request.v1"
        assert event.source == "weave-auction-manager"
        assert event.subject == "test-trace-012"
        assert event.data.trace_id == "test-trace-012"
    
    def test_bid_response_event_emission(self):
        """Test bid response CloudEvent emission."""
        bid_response = BidResponse(
            trace_id="test-trace-013",
            processor_id="adyen",
            auction_id="auction-013",
            bps=145.0,
            rebate_bps=8.0,
            expected_settlement_days=2,
            constraints={"min_amount": 1.0},
            confidence=0.85
        )
        
        event = emit_bid_response_event(
            bid_response=bid_response,
            merchant_context={"merchant_id": "merchant_013"},
            explanation="Test bid response event"
        )
        
        assert isinstance(event, BidResponseEvent)
        assert event.specversion == "1.0"
        assert event.type == "ocn.weave.bid_response.v1"
        assert event.source == "weave-processor-connector"
        assert event.subject == "test-trace-013"
        assert event.data.processor_id == "adyen"
    
    def test_bid_request_event_validation(self):
        """Test bid request CloudEvent validation."""
        cart_summary = CartSummary(
            total_amount=100.0,
            currency="USD",
            item_count=1,
            merchant_id="merchant_014"
        )
        
        rail_candidates = [
            RailCandidate(
                rail_type="credit",
                base_cost_bps=150.0,
                settlement_days=1,
                risk_score=0.3
            )
        ]
        
        bid_request = BidRequest(
            trace_id="test-trace-014",
            cart_summary=cart_summary,
            rail_candidates=rail_candidates,
            auction_id="auction-014"
        )
        
        event = emit_bid_request_event(
            bid_request=bid_request,
            explanation="Test validation"
        )
        
        # Validate event
        assert validate_bid_request_event(event) is True
        
        # Test invalid event
        event.specversion = "2.0"  # Invalid version
        assert validate_bid_request_event(event) is False
    
    def test_bid_response_event_validation(self):
        """Test bid response CloudEvent validation."""
        bid_response = BidResponse(
            trace_id="test-trace-015",
            processor_id="carat",
            auction_id="auction-015",
            bps=140.0,
            rebate_bps=12.0,
            expected_settlement_days=1,
            constraints={"min_amount": 10.0},
            confidence=0.95
        )
        
        event = emit_bid_response_event(
            bid_response=bid_response,
            explanation="Test validation"
        )
        
        # Validate event
        assert validate_bid_response_event(event) is True
        
        # Test invalid event
        event.data.bps = -10.0  # Invalid pricing
        assert validate_bid_response_event(event) is False
    
    def test_bid_event_schemas(self):
        """Test bid event JSON schemas."""
        request_schema = get_bid_request_event_schema()
        response_schema = get_bid_response_event_schema()
        
        assert isinstance(request_schema, dict)
        assert request_schema["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert request_schema["type"] == "object"
        assert "properties" in request_schema
        assert "specversion" in request_schema["properties"]
        assert "type" in request_schema["properties"]
        assert "data" in request_schema["properties"]
        
        assert isinstance(response_schema, dict)
        assert response_schema["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert response_schema["type"] == "object"
        assert "properties" in response_schema
        assert "specversion" in response_schema["properties"]
        assert "type" in response_schema["properties"]
        assert "data" in response_schema["properties"]


class TestAuctionLLMExplainer:
    """Test LLM explanation functionality."""
    
    def test_llm_explainer_initialization(self):
        """Test LLM explainer initialization."""
        explainer = AuctionLLMExplainer()
        
        config = explainer.get_configuration_status()
        assert isinstance(config, dict)
        assert "configured" in config
        assert "endpoint" in config
        assert "api_key" in config
        assert "deployment" in config
    
    def test_llm_explanation_request_creation(self):
        """Test LLM explanation request creation."""
        # Create mock auction result
        winning_bid = BidResponse(
            trace_id="test-trace-016",
            processor_id="stripe",
            auction_id="auction-016",
            bps=150.0,
            rebate_bps=10.0,
            expected_settlement_days=1,
            constraints={},
            confidence=0.9
        )
        
        all_bids = [
            winning_bid,
            BidResponse(
                trace_id="test-trace-016",
                processor_id="adyen",
                auction_id="auction-016",
                bps=145.0,
                rebate_bps=5.0,
                expected_settlement_days=2,
                constraints={},
                confidence=0.85
            )
        ]
        
        auction_result = AuctionResult(
            trace_id="test-trace-016",
            auction_id="auction-016",
            winning_processor="stripe",
            winning_bid=winning_bid,
            all_bids=all_bids,
            effective_cost_bps=140.0,
            summary="Test summary"
        )
        
        cart_summary = CartSummary(
            total_amount=100.0,
            currency="USD",
            item_count=1,
            merchant_id="merchant_016"
        )
        
        request = AuctionExplanationRequest(
            auction_result=auction_result,
            cart_summary=cart_summary,
            merchant_context={"merchant_id": "merchant_016"}
        )
        
        assert isinstance(request, AuctionExplanationRequest)
        assert request.auction_result.winning_processor == "stripe"
        assert request.cart_summary.total_amount == 100.0
    
    def test_llm_explanation_generation(self):
        """Test LLM explanation generation (stub implementation)."""
        explainer = AuctionLLMExplainer()
        
        # Create mock auction result
        winning_bid = BidResponse(
            trace_id="test-trace-017",
            processor_id="carat",
            auction_id="auction-017",
            bps=140.0,
            rebate_bps=15.0,
            expected_settlement_days=1,
            constraints={},
            confidence=0.95
        )
        
        all_bids = [
            winning_bid,
            BidResponse(
                trace_id="test-trace-017",
                processor_id="stripe",
                auction_id="auction-017",
                bps=150.0,
                rebate_bps=10.0,
                expected_settlement_days=1,
                constraints={},
                confidence=0.9
            )
        ]
        
        auction_result = AuctionResult(
            trace_id="test-trace-017",
            auction_id="auction-017",
            winning_processor="carat",
            winning_bid=winning_bid,
            all_bids=all_bids,
            effective_cost_bps=125.0,
            summary="Test summary"
        )
        
        cart_summary = CartSummary(
            total_amount=500.0,
            currency="USD",
            item_count=2,
            merchant_id="merchant_017"
        )
        
        request = AuctionExplanationRequest(
            auction_result=auction_result,
            cart_summary=cart_summary
        )
        
        # Test stub explanation generation
        response = explainer.explain_auction_result(request)
        
        if response:  # Only if LLM is configured
            assert isinstance(response, AuctionExplanationResponse)
            assert isinstance(response.summary, str)
            assert isinstance(response.key_factors, list)
            assert isinstance(response.processor_comparison, dict)
            assert 0.0 <= response.confidence <= 1.0
            assert isinstance(response.model_used, str)
    
    def test_auction_llm_configuration_check(self):
        """Test auction LLM configuration check."""
        configured = is_auction_llm_configured()
        assert isinstance(configured, bool)


class TestAuctionIntegration:
    """Test integration scenarios for auction system."""
    
    def test_complete_auction_workflow(self):
        """Test complete auction workflow from start to finish."""
        cart_summary = CartSummary(
            total_amount=1000.0,
            currency="USD",
            item_count=5,
            merchant_id="merchant_018"
        )
        
        rail_candidates = [
            RailCandidate(
                rail_type="credit",
                base_cost_bps=150.0,
                settlement_days=1,
                risk_score=0.3
            ),
            RailCandidate(
                rail_type="debit",
                base_cost_bps=100.0,
                settlement_days=2,
                risk_score=0.2
            ),
            RailCandidate(
                rail_type="ACH",
                base_cost_bps=50.0,
                settlement_days=1,
                risk_score=0.1
            )
        ]
        
        result = run_auction(
            trace_id="test-trace-018",
            cart_summary=cart_summary,
            rail_candidates=rail_candidates,
            deterministic_seed=42
        )
        
        # Verify complete workflow
        assert isinstance(result, AuctionResult)
        assert result.trace_id == "test-trace-018"
        assert result.winning_processor in ["stripe", "adyen", "carat"]
        assert len(result.all_bids) == 3
        assert result.effective_cost_bps >= 0
        assert isinstance(result.summary, str)
        assert len(result.summary) > 0
        
        # Verify all processors participated
        processor_ids = {bid.processor_id for bid in result.all_bids}
        assert processor_ids == {"stripe", "adyen", "carat"}
        
        # Verify winner has best effective cost
        winner_effective_cost = result.winning_bid.bps - result.winning_bid.rebate_bps
        for bid in result.all_bids:
            bid_effective_cost = bid.bps - bid.rebate_bps
            assert winner_effective_cost <= bid_effective_cost
    
    def test_auction_with_large_cart(self):
        """Test auction with large cart amount."""
        cart_summary = CartSummary(
            total_amount=10000.0,
            currency="USD",
            item_count=20,
            merchant_id="merchant_019"
        )
        
        rail_candidates = [
            RailCandidate(
                rail_type="credit",
                base_cost_bps=150.0,
                settlement_days=1,
                risk_score=0.3
            )
        ]
        
        result = run_auction(
            trace_id="test-trace-019",
            cart_summary=cart_summary,
            rail_candidates=rail_candidates,
            deterministic_seed=42
        )
        
        # Verify auction completed successfully
        assert isinstance(result, AuctionResult)
        assert result.winning_processor in ["stripe", "adyen", "carat"]
        assert result.effective_cost_bps >= 0
        
        # Verify all bids were received
        assert len(result.all_bids) == 3
    
    def test_auction_with_small_cart(self):
        """Test auction with small cart amount."""
        cart_summary = CartSummary(
            total_amount=5.0,
            currency="USD",
            item_count=1,
            merchant_id="merchant_020"
        )
        
        rail_candidates = [
            RailCandidate(
                rail_type="debit",
                base_cost_bps=100.0,
                settlement_days=2,
                risk_score=0.2
            )
        ]
        
        result = run_auction(
            trace_id="test-trace-020",
            cart_summary=cart_summary,
            rail_candidates=rail_candidates,
            deterministic_seed=42
        )
        
        # Verify auction completed successfully
        assert isinstance(result, AuctionResult)
        assert result.winning_processor in ["stripe", "adyen", "carat"]
        assert result.effective_cost_bps >= 0
        
        # Verify all bids were received
        assert len(result.all_bids) == 3

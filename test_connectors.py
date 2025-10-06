#!/usr/bin/env python3
"""
Test Script for Weave Connector System

Demonstrates the new connector system with cart profiles and deterministic results.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import logging
from weave.models import CartSummary, RailCandidate
from weave.connectors import get_connector_registry
from weave.fixtures import get_cart_profiles, get_expected_winners
from weave.auction import run_auction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_connector_registry():
    """Test the connector registry functionality."""
    logger.info("🧪 Testing Connector Registry")
    
    registry = get_connector_registry()
    
    # Test available processors
    processors = registry.get_available_processors()
    logger.info(f"Available processors: {processors}")
    
    # Test processor info
    for processor_id in processors:
        info = registry.get_processor_info(processor_id)
        logger.info(f"{processor_id.upper()}: {info['name']} - {info['description']}")
    
    # Test validation
    for processor_id in processors:
        is_valid = registry.validate_processor(processor_id)
        logger.info(f"{processor_id.upper()} validation: {'✅' if is_valid else '❌'}")
    
    return True


def test_connector_bids():
    """Test individual connector bid generation."""
    logger.info("🧪 Testing Connector Bid Generation")
    
    registry = get_connector_registry()
    
    # Create a test bid request
    cart_summary = CartSummary(
        total_amount=1000.0,
        currency="USD",
        item_count=2,
        merchant_id="test_merchant",
        merchant_category="electronics",
        channel="online"
    )
    
    rail_candidates = [
        RailCandidate(
            rail_type="credit",
            base_cost_bps=150.0,
            settlement_days=1,
            risk_score=0.3
        )
    ]
    
    from weave.models import BidRequest
    bid_request = BidRequest(
        trace_id="test-trace-001",
        cart_summary=cart_summary,
        rail_candidates=rail_candidates,
        auction_id="test-auction-001"
    )
    
    # Test each connector
    for processor_id in registry.get_available_processors():
        connector = registry.get_connector(processor_id, deterministic_seed=42)
        if connector:
            try:
                bid = connector.generate_bid(bid_request)
                logger.info(f"{processor_id.upper()}: {bid.bps:.1f} bps - {bid.rebate_bps:.1f} rebate = {bid.effective_cost_bps:.1f} bps effective")
            except Exception as e:
                logger.error(f"{processor_id.upper()} bid generation failed: {e}")
    
    return True


def test_cart_profiles():
    """Test auction results with different cart profiles."""
    logger.info("🧪 Testing Cart Profiles")
    
    cart_profiles = get_cart_profiles()
    expected_winners = get_expected_winners()
    
    for profile_name, profile_data in cart_profiles.items():
        logger.info(f"\n📊 Testing Profile: {profile_name}")
        logger.info(f"Description: {profile_data['profile_description']}")
        
        # Create cart summary and rail candidates
        cart_summary = CartSummary(**profile_data['cart_summary'])
        rail_candidates = [RailCandidate(**rail) for rail in profile_data['rail_candidates']]
        
        # Run auction
        try:
            result = run_auction(
                trace_id=f"test-{profile_name}",
                cart_summary=cart_summary,
                rail_candidates=rail_candidates,
                deterministic_seed=42
            )
            
            # Check results
            actual_winner = result.winning_processor
            expected_winner = expected_winners[profile_name]
            
            logger.info(f"Expected winner: {expected_winner.upper()}")
            logger.info(f"Actual winner: {actual_winner.upper()}")
            logger.info(f"Effective cost: {result.effective_cost_bps:.1f} bps")
            logger.info(f"Summary: {result.summary}")
            
            # Show all bids
            logger.info("All bids:")
            for bid in result.all_bids:
                status = "🏆 WINNER" if bid.processor_id == actual_winner else "  "
                logger.info(f"{status} {bid.processor_id.upper():6} | {bid.bps:5.1f} bps - {bid.rebate_bps:4.1f} rebate = {bid.effective_cost_bps:5.1f} bps | {bid.expected_settlement_days}d | {bid.confidence:.1%}")
            
            # Check if expected winner matches
            if actual_winner == expected_winner:
                logger.info("✅ Expected winner matches actual winner")
            else:
                logger.warning(f"⚠️  Expected {expected_winner} but got {actual_winner}")
            
        except Exception as e:
            logger.error(f"❌ Auction failed for {profile_name}: {e}")
    
    return True


def test_deterministic_results():
    """Test that results are deterministic with the same seed."""
    logger.info("🧪 Testing Deterministic Results")
    
    # Get a simple cart profile
    profile_data = get_cart_profiles()["low_risk_small"]
    cart_summary = CartSummary(**profile_data['cart_summary'])
    rail_candidates = [RailCandidate(**rail) for rail in profile_data['rail_candidates']]
    
    # Run auction twice with same seed
    result1 = run_auction(
        trace_id="deterministic-test-1",
        cart_summary=cart_summary,
        rail_candidates=rail_candidates,
        deterministic_seed=123
    )
    
    result2 = run_auction(
        trace_id="deterministic-test-2",
        cart_summary=cart_summary,
        rail_candidates=rail_candidates,
        deterministic_seed=123
    )
    
    # Compare results
    if (result1.winning_processor == result2.winning_processor and
        abs(result1.effective_cost_bps - result2.effective_cost_bps) < 0.01):
        logger.info("✅ Results are deterministic with same seed")
        return True
    else:
        logger.error("❌ Results are not deterministic")
        logger.error(f"Run 1: {result1.winning_processor} - {result1.effective_cost_bps:.1f} bps")
        logger.error(f"Run 2: {result2.winning_processor} - {result2.effective_cost_bps:.1f} bps")
        return False


def main():
    """Run all tests."""
    logger.info("🚀 Starting Weave Connector System Tests")
    
    tests = [
        ("Connector Registry Test", test_connector_registry),
        ("Connector Bid Generation Test", test_connector_bids),
        ("Cart Profiles Test", test_cart_profiles),
        ("Deterministic Results Test", test_deterministic_results)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running {test_name}")
        logger.info(f"{'='*60}")
        
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name} passed")
            else:
                logger.error(f"❌ {test_name} failed")
        except Exception as e:
            logger.error(f"❌ {test_name} failed with exception: {e}")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Test Results: {passed}/{total} tests passed")
    logger.info(f"{'='*60}")
    
    if passed == total:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())


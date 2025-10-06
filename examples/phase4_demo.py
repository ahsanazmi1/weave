#!/usr/bin/env python3
"""
Weave Phase 4 Demo Script

Demonstrates comprehensive audit, orchestration, and guardrail capabilities
including bid broadcasting, response aggregation, receipt signing, and drift detection.
"""

import json
import sys
import os
from datetime import datetime, timedelta
from typing import List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from weave.models import (
    CartSummary, RailCandidate, BidRequest, BidResponse, AuctionResult,
    PaymentInstruction, ProcessorAuthResult, SignedReceipt, RewardVariant
)
from weave.orchestrator import WeaveOrchestrator
from weave.signing import get_digital_signer, get_receipt_signer, get_audit_logger
from weave.nightly_jobs import get_reward_aggregator, get_scorecard_generator
from weave.guardrails import get_guardrail_manager, get_drift_detector


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_subsection(title: str):
    """Print a formatted subsection header."""
    print(f"\n{'-'*40}")
    print(f"  {title}")
    print(f"{'-'*40}")


def demo_digital_signing():
    """Demonstrate digital signing and verification."""
    print_section("DIGITAL SIGNING & AUDIT LOGGING")
    
    signer = get_digital_signer()
    audit_logger = get_audit_logger()
    
    print(f"✅ Digital signer initialized with key: {signer.key_id}")
    
    # Test data signing
    test_data = {
        "trace_id": "demo-trace-123",
        "amount": 1000.0,
        "processor": "stripe",
        "timestamp": datetime.now().isoformat()
    }
    
    signature = signer.sign_data(test_data)
    is_valid = signer.verify_signature(test_data, signature)
    
    print(f"✅ Data signed and verified: {is_valid}")
    print(f"   Signature: {signature[:20]}...")
    
    # Test audit logging
    payment_instruction = PaymentInstruction(
        instruction_id="demo-inst-123",
        trace_id="demo-trace-123",
        selected_rail="ACH",
        selected_processor="stripe",
        selected_instrument="bank_transfer",
        amount=1000.0,
        currency="USD",
        effective_cost=25.0,
        settlement_time_hours=24,
        confidence=0.95,
        explanation="Demo payment instruction"
    )
    
    audit_log = audit_logger.log_payment_instruction(payment_instruction)
    print(f"✅ Audit log created: {audit_log.log_id}")
    print(f"   Event type: {audit_log.event_type}")
    print(f"   Trace ID: {audit_log.trace_id}")


def demo_bid_broadcasting():
    """Demonstrate bid broadcasting and response aggregation."""
    print_section("BID BROADCASTING & AGGREGATION")
    
    orchestrator = WeaveOrchestrator()
    
    # Create test cart and rail candidates
    cart_summary = CartSummary(
        total_amount=750.50,
        currency="USD",
        item_count=4,
        merchant_id="demo-merchant-123",
        merchant_category="retail",
        channel="online"
    )
    
    rail_candidates = [
        RailCandidate(
            rail_type="ACH",
            base_cost_bps=15.0,
            settlement_days=1,
            risk_score=0.1
        ),
        RailCandidate(
            rail_type="debit",
            base_cost_bps=25.0,
            settlement_days=1,
            risk_score=0.2
        ),
        RailCandidate(
            rail_type="credit",
            base_cost_bps=35.0,
            settlement_days=2,
            risk_score=0.3
        )
    ]
    
    print(f"✅ Cart summary created: ${cart_summary.total_amount}")
    print(f"✅ Rail candidates: {len(rail_candidates)} options")
    
    # Run complete auction flow
    trace_id = f"demo-auction-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    print(f"🚀 Running auction flow for trace: {trace_id}")
    
    try:
        results = orchestrator.run_complete_auction_flow(
            trace_id, cart_summary, rail_candidates
        )
        
        print(f"✅ Auction completed successfully!")
        print(f"   Winner: {results['auction_result'].winning_processor}")
        print(f"   Effective cost: {results['auction_result'].effective_cost_bps} bps")
        print(f"   Bid responses: {len(results['bid_responses'])}")
        
        # Show receipt signing
        receipt = results['signed_receipt']
        print(f"✅ Signed receipt created: {receipt.receipt_id}")
        print(f"   Verified: {receipt.verified}")
        print(f"   Hash: {receipt.receipt_hash[:20]}...")
        
    except Exception as e:
        print(f"❌ Auction flow failed: {e}")


def demo_nightly_jobs():
    """Demonstrate nightly job functionality."""
    print_section("NIGHTLY JOBS & SCORECARD GENERATION")
    
    aggregator = get_reward_aggregator()
    generator = get_scorecard_generator()
    
    # Create sample receipts for aggregation
    print("📊 Creating sample receipts for aggregation...")
    
    receipts = []
    for i in range(50):
        receipt = SignedReceipt(
            receipt_id=f"demo-receipt-{i}",
            trace_id=f"demo-trace-{i}",
            payment_instruction=PaymentInstruction(
                instruction_id=f"demo-inst-{i}",
                trace_id=f"demo-trace-{i}",
                selected_rail="ACH",
                selected_processor="stripe" if i % 2 == 0 else "adyen",
                selected_instrument="bank_transfer",
                amount=100.0 + i * 10,
                currency="USD",
                effective_cost=25.0,
                settlement_time_hours=24,
                confidence=0.95,
                explanation="Demo instruction"
            ),
            processor_auth_result=ProcessorAuthResult(
                auth_id=f"demo-auth-{i}",
                processor_id="stripe" if i % 2 == 0 else "adyen",
                status="approved" if i < 45 else "declined",
                processor_fee=2.50 if i % 3 == 0 else -1.00,
                settlement_time_actual=24
            ),
            auction_result=AuctionResult(
                trace_id=f"demo-trace-{i}",
                auction_id=f"demo-auction-{i}",
                winning_processor="stripe" if i % 2 == 0 else "adyen",
                winning_bid=BidResponse(
                    trace_id=f"demo-trace-{i}",
                    processor_id="stripe" if i % 2 == 0 else "adyen",
                    auction_id=f"demo-auction-{i}",
                    bps=25.0,
                    rebate_bps=0.0,
                    expected_settlement_days=1,
                    confidence=0.95
                ),
                all_bids=[],
                effective_cost_bps=25.0,
                summary="Demo auction"
            ),
            bid_requests=[],
            bid_responses=[],
            receipt_hash="demo-hash",
            signature="demo-signature",
            signing_key_id="demo-key"
        )
        receipts.append(receipt)
    
    print(f"✅ Created {len(receipts)} sample receipts")
    
    # Aggregate rewards by variant
    variants = aggregator.aggregate_rewards_by_variant(receipts, datetime.now())
    print(f"✅ Aggregated {len(variants)} reward variants")
    
    for variant in variants:
        print(f"   - {variant.processor_id}: {variant.transaction_count} transactions, "
              f"{variant.success_rate:.1%} success rate")
    
    # Generate scorecard
    scorecard = generator.generate_scorecard(variants, datetime.now())
    print(f"✅ Scorecard generated: {scorecard.scorecard_id}")
    print(f"   Total transactions: {scorecard.total_transactions}")
    print(f"   Average success rate: {scorecard.avg_success_rate:.1%}")
    print(f"   Top processor: {scorecard.top_processor}")
    
    # Show markdown preview
    markdown_preview = scorecard.markdown_report.split('\n')[:10]
    print(f"📄 Markdown preview:")
    for line in markdown_preview:
        print(f"   {line}")


def demo_guardrails():
    """Demonstrate guardrail functionality."""
    print_section("GUARDRAILS & DRIFT DETECTION")
    
    drift_detector = get_drift_detector()
    guardrail_manager = get_guardrail_manager()
    
    # Test drift detection
    print_subsection("Drift Detection")
    
    baseline_data = [1.0, 2.0, 3.0, 4.0, 5.0] * 1000
    current_data = [2.0, 3.0, 4.0, 5.0, 6.0] * 1000  # Shifted distribution
    
    psi = drift_detector.calculate_psi(baseline_data, current_data)
    ks_stat, p_value = drift_detector.calculate_ks_statistic(baseline_data, current_data)
    
    print(f"✅ PSI calculation: {psi:.3f}")
    print(f"✅ KS statistic: {ks_stat:.3f} (p-value: {p_value:.3f})")
    
    # Test comprehensive drift detection
    metrics = drift_detector.detect_drift(baseline_data, current_data, "test_metric", 0.1)
    print(f"✅ Drift detected: {metrics.drift_detected}")
    print(f"   Severity: {metrics.severity}")
    print(f"   Drift score: {metrics.drift_score:.3f}")
    
    # Test guardrail enforcement
    print_subsection("Guardrail Enforcement")
    
    # Create test receipts with problematic metrics
    receipts = []
    for i in range(100):
        status = "approved" if i < 75 else "declined"  # 75% approval rate
        receipt = SignedReceipt(
            receipt_id=f"guardrail-receipt-{i}",
            trace_id=f"guardrail-trace-{i}",
            payment_instruction=PaymentInstruction(
                instruction_id=f"guardrail-inst-{i}",
                trace_id=f"guardrail-trace-{i}",
                selected_rail="ACH",
                selected_processor="stripe",
                selected_instrument="bank_transfer",
                amount=100.0,
                currency="USD",
                effective_cost=25.0,
                settlement_time_hours=24,
                confidence=0.95,
                explanation="Guardrail test"
            ),
            processor_auth_result=ProcessorAuthResult(
                auth_id=f"guardrail-auth-{i}",
                processor_id="stripe",
                status=status,
                processor_fee=2.50,
                settlement_time_actual=120  # Long settlement time
            ),
            auction_result=AuctionResult(
                trace_id=f"guardrail-trace-{i}",
                auction_id=f"guardrail-auction-{i}",
                winning_processor="stripe",
                winning_bid=BidResponse(
                    trace_id=f"guardrail-trace-{i}",
                    processor_id="stripe",
                    auction_id=f"guardrail-auction-{i}",
                    bps=25.0,
                    rebate_bps=0.0,
                    expected_settlement_days=5,
                    confidence=0.95
                ),
                all_bids=[],
                effective_cost_bps=25.0,
                summary="Guardrail test"
            ),
            bid_requests=[],
            bid_responses=[],
            receipt_hash="guardrail-hash",
            signature="guardrail-signature",
            signing_key_id="guardrail-key"
        )
        receipts.append(receipt)
    
    # Create test variants with cost drift
    variants = [
        RewardVariant(
            variant_id="stripe_ach_problematic",
            processor_id="stripe",
            rail_type="ACH",
            reward_type="standard",
            reward_value=250.0,  # High cost
            transaction_count=100,
            total_amount=10000.0,
            success_rate=0.75,  # Low success rate
            avg_settlement_time=120.0  # Long settlement
        )
    ]
    
    print(f"✅ Created {len(receipts)} test receipts with problematic metrics")
    print(f"   Approval rate: 75% (below 95% threshold)")
    print(f"   Settlement time: 120 hours (above 72 hour threshold)")
    
    # Run guardrail checks
    breaches = guardrail_manager.run_guardrail_checks(receipts, variants)
    print(f"✅ Guardrail checks completed: {len(breaches)} breaches detected")
    
    for breach in breaches:
        print(f"   🚨 {breach.guardrail_type}: {breach.breach_severity}")
        print(f"      Description: {breach.breach_description}")
        print(f"      Rollback triggered: {breach.rollback_triggered}")
        if breach.rollback_pr_url:
            print(f"      Rollback PR: {breach.rollback_pr_url}")
    
    # Show guardrail status
    status = guardrail_manager.get_guardrail_status()
    print(f"✅ Guardrail status:")
    print(f"   Active: {status['guardrails_active']}")
    print(f"   Drift detection: {status['drift_detection_enabled']}")
    print(f"   Auto rollback: {status['auto_rollback_enabled']}")


def main():
    """Run the complete Weave Phase 4 demo."""
    print("🚀 Weave Phase 4 Demo - Audit, Orchestration & Guardrails")
    print(f"   Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Run all demo sections
        demo_digital_signing()
        demo_bid_broadcasting()
        demo_nightly_jobs()
        demo_guardrails()
        
        print_section("DEMO COMPLETED SUCCESSFULLY")
        print("✅ All Weave Phase 4 features demonstrated successfully!")
        print("   - Digital signing and audit logging")
        print("   - Bid broadcasting and response aggregation")
        print("   - Nightly jobs and scorecard generation")
        print("   - Guardrails and drift detection")
        print("   - Automatic rollback capabilities")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()









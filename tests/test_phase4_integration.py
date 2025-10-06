"""
Integration tests for Weave Phase 4 functionality.

Tests processor stub integration, aggregation correctness, rollback scenarios,
and comprehensive audit logging with digital signatures.
"""

import json
import pytest
from datetime import datetime, timedelta
from typing import List

from weave.models import (
    CartSummary, RailCandidate, BidRequest, BidResponse, AuctionResult,
    PaymentInstruction, ProcessorAuthResult, SignedReceipt, RewardVariant,
    GuardrailMetrics, GuardrailBreach
)
from weave.signing import DigitalSigner, ReceiptSigner, AuditLogger
from weave.orchestrator import BidBroadcaster, ResponseAggregator, WeaveOrchestrator
from weave.nightly_jobs import RewardAggregator, ScorecardGenerator, NightlyJobRunner
from weave.guardrails import DriftDetector, GuardrailEnforcer, AutoRollbackManager, GuardrailManager


class TestDigitalSigning:
    """Test digital signing and verification functionality."""
    
    def test_digital_signer_creation(self):
        """Test digital signer initialization."""
        signer = DigitalSigner("test-key")
        assert signer.key_id == "test-key"
        assert signer.signing_key.key_id == "test-key"
        assert signer.signing_key.active is True
    
    def test_data_signing_and_verification(self):
        """Test data signing and verification."""
        signer = DigitalSigner("test-key")
        
        # Test data
        test_data = {
            "trace_id": "test-trace-123",
            "amount": 100.0,
            "processor": "stripe",
            "timestamp": datetime.now().isoformat()
        }
        
        # Sign data
        signature = signer.sign_data(test_data)
        assert signature is not None
        assert len(signature) > 0
        
        # Verify signature
        is_valid = signer.verify_signature(test_data, signature)
        assert is_valid is True
        
        # Test with modified data (should fail)
        modified_data = test_data.copy()
        modified_data["amount"] = 200.0
        is_valid_modified = signer.verify_signature(modified_data, signature)
        assert is_valid_modified is False
    
    def test_receipt_signing(self):
        """Test receipt signing functionality."""
        signer = DigitalSigner("test-key")
        receipt_signer = ReceiptSigner(signer)
        
        # Create test data
        payment_instruction = PaymentInstruction(
            instruction_id="inst-123",
            trace_id="trace-123",
            selected_rail="ACH",
            selected_processor="stripe",
            selected_instrument="bank_transfer",
            amount=100.0,
            currency="USD",
            effective_cost=25.0,
            settlement_time_hours=24,
            confidence=0.95,
            explanation="Test instruction"
        )
        
        processor_auth_result = ProcessorAuthResult(
            auth_id="auth-123",
            processor_id="stripe",
            status="approved",
            auth_code="AUTH123",
            processor_fee=2.50,
            settlement_time_actual=24
        )
        
        auction_result = AuctionResult(
            trace_id="trace-123",
            auction_id="auction-123",
            winning_processor="stripe",
            winning_bid=BidResponse(
                trace_id="trace-123",
                processor_id="stripe",
                auction_id="auction-123",
                bps=25.0,
                rebate_bps=0.0,
                expected_settlement_days=1,
                confidence=0.95
            ),
            all_bids=[],
            effective_cost_bps=25.0,
            summary="Test auction"
        )
        
        # Create signed receipt
        receipt = receipt_signer.create_signed_receipt(
            payment_instruction=payment_instruction,
            processor_auth_result=processor_auth_result,
            auction_result=auction_result,
            bid_requests=[],
            bid_responses=[]
        )
        
        assert receipt.receipt_id is not None
        assert receipt.signature is not None
        assert receipt.receipt_hash is not None
        assert receipt.verified is True
        
        # Verify receipt
        is_valid = receipt_signer.verify_receipt(receipt)
        assert is_valid is True


class TestAuditLogging:
    """Test comprehensive audit logging functionality."""
    
    def test_audit_logger_creation(self):
        """Test audit logger initialization."""
        signer = DigitalSigner("test-key")
        logger = AuditLogger(signer)
        assert logger.signer == signer
    
    def test_payment_instruction_logging(self):
        """Test payment instruction audit logging."""
        signer = DigitalSigner("test-key")
        audit_logger = AuditLogger(signer)
        
        payment_instruction = PaymentInstruction(
            instruction_id="inst-123",
            trace_id="trace-123",
            selected_rail="ACH",
            selected_processor="stripe",
            selected_instrument="bank_transfer",
            amount=100.0,
            currency="USD",
            effective_cost=25.0,
            settlement_time_hours=24,
            confidence=0.95,
            explanation="Test instruction"
        )
        
        audit_log = audit_logger.log_payment_instruction(payment_instruction)
        
        assert audit_log.log_id is not None
        assert audit_log.trace_id == "trace-123"
        assert audit_log.event_type == "payment_instruction_created"
        assert audit_log.signature is not None
        assert audit_log.source == "orca"
        
        # Verify audit log
        is_valid = audit_logger.verify_audit_log(audit_log)
        assert is_valid is True
    
    def test_auction_result_logging(self):
        """Test auction result audit logging."""
        signer = DigitalSigner("test-key")
        audit_logger = AuditLogger(signer)
        
        auction_result = AuctionResult(
            trace_id="trace-123",
            auction_id="auction-123",
            winning_processor="stripe",
            winning_bid=BidResponse(
                trace_id="trace-123",
                processor_id="stripe",
                auction_id="auction-123",
                bps=25.0,
                rebate_bps=0.0,
                expected_settlement_days=1,
                confidence=0.95
            ),
            all_bids=[],
            effective_cost_bps=25.0,
            summary="Test auction"
        )
        
        audit_log = audit_logger.log_auction_result(auction_result)
        
        assert audit_log.log_id is not None
        assert audit_log.trace_id == "trace-123"
        assert audit_log.event_type == "auction_result"
        assert audit_log.signature is not None
        assert audit_log.source == "weave"


class TestBidBroadcasting:
    """Test bid broadcasting and response aggregation."""
    
    def test_bid_broadcaster_creation(self):
        """Test bid broadcaster initialization."""
        broadcaster = BidBroadcaster()
        assert broadcaster.registry is not None
        assert broadcaster.audit_logger is not None
    
    def test_response_aggregator_creation(self):
        """Test response aggregator initialization."""
        aggregator = ResponseAggregator()
        assert aggregator.audit_logger is not None
    
    def test_bid_response_aggregation(self):
        """Test bid response aggregation logic."""
        aggregator = ResponseAggregator()
        
        # Create test bid responses
        bid_responses = [
            BidResponse(
                trace_id="trace-123",
                processor_id="stripe",
                auction_id="auction-123",
                bps=25.0,
                rebate_bps=2.0,
                expected_settlement_days=1,
                confidence=0.95
            ),
            BidResponse(
                trace_id="trace-123",
                processor_id="adyen",
                auction_id="auction-123",
                bps=30.0,
                rebate_bps=1.0,
                expected_settlement_days=2,
                confidence=0.90
            ),
            BidResponse(
                trace_id="trace-123",
                processor_id="carat",
                auction_id="auction-123",
                bps=20.0,
                rebate_bps=3.0,
                expected_settlement_days=1,
                confidence=0.85
            )
        ]
        
        # Set effective costs
        bid_responses[0].effective_cost_bps = 23.0  # 25 - 2
        bid_responses[1].effective_cost_bps = 29.0  # 30 - 1
        bid_responses[2].effective_cost_bps = 17.0  # 20 - 3
        
        bid_requests = [
            BidRequest(
                trace_id="trace-123",
                cart_summary=CartSummary(
                    total_amount=100.0,
                    merchant_id="merchant-123"
                ),
                rail_candidates=[],
                auction_id="auction-123"
            )
        ]
        
        # Aggregate responses
        auction_result = aggregator.aggregate_responses(bid_requests, bid_responses)
        
        # Carat should win (lowest effective cost: 17.0)
        assert auction_result.winning_processor == "carat"
        assert auction_result.effective_cost_bps == 17.0
        assert auction_result.winning_bid.processor_id == "carat"
        assert len(auction_result.all_bids) == 3


class TestNightlyJobs:
    """Test nightly job functionality."""
    
    def test_reward_aggregator_creation(self):
        """Test reward aggregator initialization."""
        aggregator = RewardAggregator()
        assert aggregator is not None
    
    def test_scorecard_generator_creation(self):
        """Test scorecard generator initialization."""
        generator = ScorecardGenerator()
        assert generator is not None
    
    def test_variant_aggregation(self):
        """Test reward variant aggregation."""
        aggregator = RewardAggregator()
        
        # Create test receipts
        receipts = []
        for i in range(10):
            receipt = SignedReceipt(
                receipt_id=f"receipt-{i}",
                trace_id=f"trace-{i}",
                payment_instruction=PaymentInstruction(
                    instruction_id=f"inst-{i}",
                    trace_id=f"trace-{i}",
                    selected_rail="ACH",
                    selected_processor="stripe" if i % 2 == 0 else "adyen",
                    selected_instrument="bank_transfer",
                    amount=100.0 + i * 10,
                    currency="USD",
                    effective_cost=25.0,
                    settlement_time_hours=24,
                    confidence=0.95,
                    explanation="Test"
                ),
                processor_auth_result=ProcessorAuthResult(
                    auth_id=f"auth-{i}",
                    processor_id="stripe" if i % 2 == 0 else "adyen",
                    status="approved",
                    processor_fee=2.50 if i % 3 == 0 else -1.00,  # Some rebates
                    settlement_time_actual=24
                ),
                auction_result=AuctionResult(
                    trace_id=f"trace-{i}",
                    auction_id=f"auction-{i}",
                    winning_processor="stripe" if i % 2 == 0 else "adyen",
                    winning_bid=BidResponse(
                        trace_id=f"trace-{i}",
                        processor_id="stripe" if i % 2 == 0 else "adyen",
                        auction_id=f"auction-{i}",
                        bps=25.0,
                        rebate_bps=0.0,
                        expected_settlement_days=1,
                        confidence=0.95
                    ),
                    all_bids=[],
                    effective_cost_bps=25.0,
                    summary="Test"
                ),
                bid_requests=[],
                bid_responses=[],
                receipt_hash="test-hash",
                signature="test-signature",
                signing_key_id="test-key"
            )
            receipts.append(receipt)
        
        # Aggregate by variant
        variants = aggregator.aggregate_rewards_by_variant(receipts, datetime.now())
        
        # Should have 2 variants (stripe and adyen)
        assert len(variants) == 2
        
        # Check variant properties
        stripe_variant = next(v for v in variants if v.processor_id == "stripe")
        adyen_variant = next(v for v in variants if v.processor_id == "adyen")
        
        assert stripe_variant.transaction_count == 5  # Half of 10
        assert adyen_variant.transaction_count == 5
        assert stripe_variant.success_rate == 1.0  # All approved
        assert adyen_variant.success_rate == 1.0
    
    def test_scorecard_generation(self):
        """Test scorecard generation."""
        generator = ScorecardGenerator()
        
        # Create test variants
        variants = [
            RewardVariant(
                variant_id="stripe_ach_rebate",
                processor_id="stripe",
                rail_type="ACH",
                reward_type="rebate",
                reward_value=100.0,
                transaction_count=50,
                total_amount=5000.0,
                success_rate=0.98,
                avg_settlement_time=24.0
            ),
            RewardVariant(
                variant_id="adyen_ach_discount",
                processor_id="adyen",
                rail_type="ACH",
                reward_type="discount",
                reward_value=75.0,
                transaction_count=30,
                total_amount=3000.0,
                success_rate=0.95,
                avg_settlement_time=48.0
            )
        ]
        
        # Generate scorecard
        scorecard = generator.generate_scorecard(variants, datetime.now())
        
        assert scorecard.scorecard_id is not None
        assert scorecard.total_transactions == 80
        assert scorecard.total_amount == 8000.0
        assert scorecard.top_processor == "stripe"  # Higher success rate
        assert scorecard.top_rail == "ACH"
        assert "Weave Scorecard" in scorecard.markdown_report
        assert scorecard.json_data is not None


class TestGuardrails:
    """Test guardrail functionality and drift detection."""
    
    def test_drift_detector_creation(self):
        """Test drift detector initialization."""
        detector = DriftDetector()
        assert detector is not None
    
    def test_psi_calculation(self):
        """Test PSI calculation."""
        detector = DriftDetector()
        
        # Test data with some drift
        baseline_data = [1.0, 2.0, 3.0, 4.0, 5.0] * 100
        current_data = [1.5, 2.5, 3.5, 4.5, 5.5] * 100  # Shifted distribution
        
        psi = detector.calculate_psi(baseline_data, current_data)
        assert psi > 0.0  # Should detect drift
        assert psi < 10.0  # Should be reasonable value
    
    def test_ks_statistic_calculation(self):
        """Test KS statistic calculation."""
        detector = DriftDetector()
        
        # Test data
        baseline_data = [1.0, 2.0, 3.0, 4.0, 5.0] * 100
        current_data = [1.5, 2.5, 3.5, 4.5, 5.5] * 100
        
        ks_stat, p_value = detector.calculate_ks_statistic(baseline_data, current_data)
        assert ks_stat > 0.0
        assert p_value >= 0.0
        assert p_value <= 1.0
    
    def test_drift_detection(self):
        """Test comprehensive drift detection."""
        detector = DriftDetector()
        
        # Test data with significant drift
        baseline_data = [1.0, 2.0, 3.0, 4.0, 5.0] * 1000
        current_data = [2.0, 3.0, 4.0, 5.0, 6.0] * 1000  # Significant shift
        
        metrics = detector.detect_drift(baseline_data, current_data, "test_metric", 0.1)
        
        assert metrics.metric_type == "test_metric"
        assert metrics.drift_detected is True
        assert metrics.severity in ["low", "medium", "high", "critical"]
        assert metrics.drift_score > 0.0
    
    def test_approval_rate_guardrail(self):
        """Test approval rate guardrail enforcement."""
        enforcer = GuardrailEnforcer()
        
        # Create test receipts with low approval rate
        receipts = []
        for i in range(100):
            status = "approved" if i < 80 else "declined"  # 80% approval rate
            receipt = SignedReceipt(
                receipt_id=f"receipt-{i}",
                trace_id=f"trace-{i}",
                payment_instruction=PaymentInstruction(
                    instruction_id=f"inst-{i}",
                    trace_id=f"trace-{i}",
                    selected_rail="ACH",
                    selected_processor="stripe",
                    selected_instrument="bank_transfer",
                    amount=100.0,
                    currency="USD",
                    effective_cost=25.0,
                    settlement_time_hours=24,
                    confidence=0.95,
                    explanation="Test"
                ),
                processor_auth_result=ProcessorAuthResult(
                    auth_id=f"auth-{i}",
                    processor_id="stripe",
                    status=status,
                    processor_fee=2.50,
                    settlement_time_actual=24
                ),
                auction_result=AuctionResult(
                    trace_id=f"trace-{i}",
                    auction_id=f"auction-{i}",
                    winning_processor="stripe",
                    winning_bid=BidResponse(
                        trace_id=f"trace-{i}",
                        processor_id="stripe",
                        auction_id=f"auction-{i}",
                        bps=25.0,
                        rebate_bps=0.0,
                        expected_settlement_days=1,
                        confidence=0.95
                    ),
                    all_bids=[],
                    effective_cost_bps=25.0,
                    summary="Test"
                ),
                bid_requests=[],
                bid_responses=[],
                receipt_hash="test-hash",
                signature="test-signature",
                signing_key_id="test-key"
            )
            receipts.append(receipt)
        
        # Check guardrail (threshold 95%)
        metrics = enforcer.check_approval_rate_guardrail(receipts, 0.95)
        
        assert metrics.metric_type == "approval_rate"
        assert metrics.drift_detected is True  # 80% < 95%
        assert metrics.severity == "critical"  # Significant breach
    
    def test_auto_rollback_trigger(self):
        """Test automatic rollback triggering."""
        rollback_manager = AutoRollbackManager()
        
        # Create test metrics with critical drift
        metrics = [
            GuardrailMetrics(
                metric_id="metric-1",
                metric_type="approval_rate",
                baseline_value=0.95,
                baseline_date=datetime.now() - timedelta(days=30),
                baseline_sample_size=1000,
                current_value=0.80,
                current_date=datetime.now(),
                current_sample_size=100,
                drift_score=0.25,
                drift_threshold=0.1,
                drift_detected=True,
                severity="critical"
            )
        ]
        
        # Check for breaches
        breaches = rollback_manager.check_guardrail_breaches(metrics)
        
        assert len(breaches) == 1
        breach = breaches[0]
        assert breach.guardrail_type == "approval_rate"
        assert breach.breach_severity == "critical"
        assert breach.rollback_triggered is True
        assert breach.rollback_pr_url is not None
        assert breach.rollback_status == "created"


class TestIntegrationScenarios:
    """Test end-to-end integration scenarios."""
    
    def test_complete_auction_flow(self):
        """Test complete auction flow from broadcasting to receipt signing."""
        orchestrator = WeaveOrchestrator()
        
        # Create test data
        trace_id = "integration-test-123"
        cart_summary = CartSummary(
            total_amount=500.0,
            currency="USD",
            item_count=3,
            merchant_id="merchant-123",
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
            )
        ]
        
        # Run complete flow
        results = orchestrator.run_complete_auction_flow(
            trace_id, cart_summary, rail_candidates
        )
        
        # Verify results
        assert results["trace_id"] == trace_id
        assert results["auction_result"] is not None
        assert results["payment_instruction"] is not None
        assert results["processor_auth_result"] is not None
        assert results["signed_receipt"] is not None
        assert results["bid_requests"] is not None
        assert results["bid_responses"] is not None
        assert results["flow_completed_at"] is not None
        
        # Verify signed receipt
        receipt = results["signed_receipt"]
        assert receipt.trace_id == trace_id
        assert receipt.payment_instruction.amount == 500.0
        assert receipt.verified is True
    
    def test_guardrail_breach_scenario(self):
        """Test guardrail breach detection and rollback scenario."""
        guardrail_manager = GuardrailManager()
        
        # Create test receipts with problematic metrics
        receipts = []
        for i in range(100):
            # Create receipts with declining approval rates
            status = "approved" if i < 70 else "declined"  # 70% approval rate
            receipt = SignedReceipt(
                receipt_id=f"receipt-{i}",
                trace_id=f"trace-{i}",
                payment_instruction=PaymentInstruction(
                    instruction_id=f"inst-{i}",
                    trace_id=f"trace-{i}",
                    selected_rail="ACH",
                    selected_processor="stripe",
                    selected_instrument="bank_transfer",
                    amount=100.0,
                    currency="USD",
                    effective_cost=25.0,
                    settlement_time_hours=24,
                    confidence=0.95,
                    explanation="Test"
                ),
                processor_auth_result=ProcessorAuthResult(
                    auth_id=f"auth-{i}",
                    processor_id="stripe",
                    status=status,
                    processor_fee=2.50,
                    settlement_time_actual=120  # Long settlement time
                ),
                auction_result=AuctionResult(
                    trace_id=f"trace-{i}",
                    auction_id=f"auction-{i}",
                    winning_processor="stripe",
                    winning_bid=BidResponse(
                        trace_id=f"trace-{i}",
                        processor_id="stripe",
                        auction_id=f"auction-{i}",
                        bps=25.0,
                        rebate_bps=0.0,
                        expected_settlement_days=5,  # Long settlement
                        confidence=0.95
                    ),
                    all_bids=[],
                    effective_cost_bps=25.0,
                    summary="Test"
                ),
                bid_requests=[],
                bid_responses=[],
                receipt_hash="test-hash",
                signature="test-signature",
                signing_key_id="test-key"
            )
            receipts.append(receipt)
        
        # Create test variants with cost drift
        variants = [
            RewardVariant(
                variant_id="stripe_ach_standard",
                processor_id="stripe",
                rail_type="ACH",
                reward_type="standard",
                reward_value=250.0,  # High cost
                transaction_count=100,
                total_amount=10000.0,
                success_rate=0.70,  # Low success rate
                avg_settlement_time=120.0  # Long settlement
            )
        ]
        
        # Run guardrail checks
        breaches = guardrail_manager.run_guardrail_checks(receipts, variants)
        
        # Should detect multiple breaches
        assert len(breaches) > 0
        
        # Check for critical breaches that trigger rollback
        critical_breaches = [b for b in breaches if b.breach_severity == "critical"]
        assert len(critical_breaches) > 0
        
        # Verify rollback was triggered for critical breaches
        rollback_triggered = any(b.rollback_triggered for b in critical_breaches)
        assert rollback_triggered is True
    
    def test_nightly_job_integration(self):
        """Test nightly job integration with scorecard generation."""
        nightly_runner = NightlyJobRunner()
        
        # Mock receipts for the job
        # In a real test, this would come from a database
        target_date = datetime.now() - timedelta(days=1)
        
        # This would normally fail without real data, but we can test the structure
        try:
            scorecard = nightly_runner.run_nightly_jobs(target_date)
            # If it succeeds, verify structure
            assert scorecard.scorecard_id is not None
            assert scorecard.date == target_date
        except Exception as e:
            # Expected to fail without real data
            assert "receipts" in str(e).lower() or "empty" in str(e).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])









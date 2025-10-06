"""
Integration tests for Weave Learning Loop Phase 9.

Tests outcomes tracking, nightly aggregation, drift detection,
and auto-rollback with comprehensive scenarios.
"""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path

from src.weave.outcomes_tracker import (
    get_outcomes_ingester,
    CohortTracker,
    OutcomesIngester
)
from src.weave.nightly_learning_jobs import (
    get_nightly_learning_jobs,
    RewardAggregator,
    AutoPRPromoter,
    NightlyLearningJobRunner
)
from src.weave.drift_detection import (
    get_drift_detector,
    get_performance_drift_monitor,
    DriftDetector,
    PerformanceDriftMonitor
)
from src.weave.auto_rollback import (
    get_auto_rollback_orchestrator,
    GuardrailBreachDetector,
    AutoRollbackManager,
    AutoRollbackOrchestrator
)
from src.weave.models import (
    PaymentInstruction, ProcessorAuthResult
)


class TestWeaveLearningLoopIntegration:
    """Integration tests for Weave's learning loop components."""
    
    @pytest.fixture
    def outcomes_ingester(self):
        """Get outcomes ingester instance."""
        return get_outcomes_ingester()
    
    @pytest.fixture
    def cohort_tracker(self):
        """Get cohort tracker instance."""
        return CohortTracker()
    
    @pytest.fixture
    def reward_aggregator(self):
        """Get reward aggregator instance."""
        return RewardAggregator()
    
    @pytest.fixture
    def auto_pr_promoter(self):
        """Get auto PR promoter instance."""
        return AutoPRPromoter()
    
    @pytest.fixture
    def nightly_jobs(self):
        """Get nightly learning jobs runner."""
        return get_nightly_learning_jobs()
    
    @pytest.fixture
    def drift_detector(self):
        """Get drift detector instance."""
        return get_drift_detector()
    
    @pytest.fixture
    def performance_drift_monitor(self):
        """Get performance drift monitor instance."""
        return get_performance_drift_monitor()
    
    @pytest.fixture
    def guardrail_breach_detector(self):
        """Get guardrail breach detector instance."""
        return GuardrailBreachDetector()
    
    @pytest.fixture
    def auto_rollback_orchestrator(self):
        """Get auto rollback orchestrator instance."""
        return get_auto_rollback_orchestrator()
    
    @pytest.fixture
    def sample_payment_instruction(self):
        """Create sample payment instruction."""
        return PaymentInstruction(
            instruction_id="test_instruction_001",
            trace_id="test_trace_001",
            selected_rail="ACH",
            selected_processor="carat",
            selected_instrument="bank_transfer",
            amount=1000.0,
            currency="USD",
            effective_cost=15.0,
            settlement_time_hours=24,
            confidence=0.95,
            explanation="Selected ACH rail for optimal cost efficiency",
            alternatives=[],
            constraints_applied=[],
            metadata={
                "merchant_id": "merchant_001",
                "customer_data": {"customer_id": "customer_001"}
            }
        )
    
    @pytest.fixture
    def sample_auth_result(self):
        """Create sample authorization result."""
        return ProcessorAuthResult(
            auth_id="carat_auth_001",
            processor_id="carat",
            status="approved",
            auth_code="AUTH_123456",
            decline_reason=None,
            processor_fee=15.0,
            settlement_time_actual=24,
            processor_metadata={
                "processing_time_ms": 245,
                "fraud_check": "passed",
                "risk_score": 0.25,
                "approval_score": 0.96
            },
            timestamp=datetime.now()
        )
    
    def test_cohort_assignment(self, cohort_tracker, sample_payment_instruction):
        """Test cohort ID assignment based on transaction characteristics."""
        # Test cohort assignment
        cohort_id = cohort_tracker.assign_cohort_id(sample_payment_instruction)
        
        assert cohort_id is not None
        assert isinstance(cohort_id, str)
        assert len(cohort_id) > 0
        
        # Verify cohort components
        assert "1000.0" in cohort_id or "medium" in cohort_id  # Amount range
        assert "ACH" in cohort_id  # Rail type
        assert "bank_transfer" in cohort_id  # Instrument type
        
        # Test with additional context
        additional_context = {
            "merchant_category": "retail",
            "geographic_region": "US"
        }
        
        cohort_id_with_context = cohort_tracker.assign_cohort_id(
            sample_payment_instruction, additional_context
        )
        
        assert cohort_id_with_context != cohort_id  # Should be different
        assert "retail" in cohort_id_with_context
        assert "US" in cohort_id_with_context
    
    def test_outcomes_ingestion(self, outcomes_ingester, sample_payment_instruction, sample_auth_result):
        """Test outcomes ingestion for t0 and tx outcomes."""
        # Test t0 outcome ingestion
        t0_outcome = outcomes_ingester.ingest_t0_outcome(
            sample_payment_instruction,
            sample_auth_result
        )
        
        assert t0_outcome["outcome_type"] == "t0_immediate"
        assert t0_outcome["trace_id"] == sample_payment_instruction.trace_id
        assert t0_outcome["cohort_id"] is not None
        assert "payment_data" in t0_outcome
        assert "auth_result" in t0_outcome
        assert "immediate_metrics" in t0_outcome
        
        # Test tx outcome ingestion
        settlement_data = {
            "settlement_status": "settled",
            "actual_settlement_time_hours": 22,
            "final_cost": 15.0,
            "fees_breakdown": {
                "processor_fee": 15.0,
                "network_fee": 0.0
            },
            "settlement_reference": "ACH_SETTLE_001",
            "success": True,
            "actual_cost": 15.0,
            "chargeback_count": 0,
            "dispute_count": 0,
            "customer_rating": 0.9,
            "merchant_satisfaction": 0.85,
            "risk_events": []
        }
        
        tx_outcome = outcomes_ingester.ingest_tx_outcome(
            sample_payment_instruction,
            settlement_data
        )
        
        assert tx_outcome["outcome_type"] == "tx_settled"
        assert tx_outcome["trace_id"] == sample_payment_instruction.trace_id
        assert tx_outcome["cohort_id"] is not None
        assert "settlement_data" in tx_outcome
        assert "final_metrics" in tx_outcome
    
    def test_cohort_performance_summary(self, outcomes_ingester, sample_payment_instruction, sample_auth_result):
        """Test cohort performance summary generation."""
        # Ingest multiple outcomes for the same cohort
        for i in range(5):
            instruction = PaymentInstruction(
                instruction_id=f"test_instruction_{i:03d}",
                trace_id=f"test_trace_{i:03d}",
                selected_rail="ACH",
                selected_processor="carat",
                selected_instrument="bank_transfer",
                amount=100.0 + i * 50,
                currency="USD",
                effective_cost=15.0,
                settlement_time_hours=24,
                confidence=0.95,
                explanation=f"Test instruction {i}",
                alternatives=[],
                constraints_applied=[],
                metadata={"merchant_id": f"merchant_{i:03d}"}
            )
            
            auth_result = ProcessorAuthResult(
                auth_id=f"auth_{i:03d}",
                processor_id="carat",
                status="approved" if i < 4 else "declined",
                auth_code=f"AUTH_{i:03d}",
                decline_reason=None if i < 4 else "Insufficient funds",
                processor_fee=15.0,
                settlement_time_actual=24,
                processor_metadata={
                    "processing_time_ms": 245 + i * 10,
                    "fraud_check": "passed",
                    "risk_score": 0.25 + i * 0.05,
                    "approval_score": 0.96 - i * 0.02
                },
                timestamp=datetime.now()
            )
            
            outcomes_ingester.ingest_t0_outcome(instruction, auth_result)
        
        # Get cohort performance summary
        cohort_id = outcomes_ingester.cohort_tracker.assign_cohort_id(sample_payment_instruction)
        performance_summary = outcomes_ingester.get_cohort_performance_summary(cohort_id)
        
        assert performance_summary["cohort_id"] == cohort_id
        assert performance_summary["total_transactions"] == 5
        assert performance_summary["approval_rate"] == 0.8  # 4 out of 5 approved
        assert performance_summary["avg_processing_time_ms"] > 0
        assert performance_summary["avg_cost"] > 0
    
    def test_reward_aggregation(self, reward_aggregator):
        """Test reward aggregation for daily analysis."""
        # Test daily reward aggregation
        yesterday = datetime.now() - timedelta(days=1)
        aggregation_result = reward_aggregator.aggregate_daily_rewards(yesterday)
        
        assert "aggregation_date" in aggregation_result
        assert "total_transactions" in aggregation_result
        assert "total_variants" in aggregation_result
        assert "variant_performance" in aggregation_result
        assert "promotion_candidates" in aggregation_result
        
        # Verify aggregation metadata
        assert aggregation_result["aggregation_metadata"]["processed_at"] is not None
        assert aggregation_result["aggregation_metadata"]["aggregation_version"] == "1.0"
    
    def test_auto_pr_promotion(self, auto_pr_promoter):
        """Test automatic PR creation for variant promotion."""
        # Create promotion candidate
        promotion_candidate = {
            "variant_id": "test_variant_001",
            "performance": {
                "variant_id": "test_variant_001",
                "transaction_count": 25,
                "approval_rate": 0.95,
                "avg_cost": 18.5,
                "avg_settlement_time_hours": 20.0,
                "chargeback_rate": 0.01,
                "customer_satisfaction": 0.88,
                "risk_score": 0.25,
                "total_reward": 0.85,
                "confidence_score": 0.9
            },
            "promotion_reason": "Meets all promotion criteria",
            "promotion_priority": 0.92
        }
        
        # Create promotion PR
        pr_result = auto_pr_promoter.create_promotion_pr(
            promotion_candidate,
            datetime.now().isoformat()
        )
        
        assert pr_result["success"] == True
        assert "pr_number" in pr_result
        assert "pr_title" in pr_result
        assert "config_changes" in pr_result
        assert "rollback_metadata" in pr_result["config_changes"]
    
    def test_nightly_learning_jobs(self, nightly_jobs):
        """Test complete nightly learning jobs execution."""
        # Run nightly jobs
        yesterday = datetime.now() - timedelta(days=1)
        nightly_result = nightly_jobs.run_nightly_jobs(yesterday)
        
        assert nightly_result["date"] == yesterday.isoformat()
        assert "aggregation_result" in nightly_result
        assert "promotion_results" in nightly_result
        assert "nightly_report" in nightly_result
        assert nightly_result["success"] == True
        
        # Verify nightly report structure
        nightly_report = nightly_result["nightly_report"]
        assert "summary" in nightly_report
        assert "top_performers" in nightly_report
        assert "recommendations" in nightly_report
    
    def test_drift_detection(self, drift_detector):
        """Test PSI and KS drift detection."""
        # Test PSI drift detection
        baseline_data = [0.95, 0.96, 0.94, 0.97, 0.95, 0.96, 0.93, 0.95, 0.96, 0.94]
        current_data = [0.85, 0.87, 0.83, 0.89, 0.86, 0.88, 0.84, 0.87, 0.85, 0.86]
        
        psi_result = drift_detector.detect_psi_drift(
            baseline_data, current_data, "approval_rate"
        )
        
        assert psi_result["feature_name"] == "approval_rate"
        assert psi_result["drift_type"] == "psi"
        assert psi_result["psi_score"] > 0.0
        assert psi_result["drift_severity"] in ["minor_drift", "major_drift", "critical_drift"]
        assert psi_result["baseline_samples"] == len(baseline_data)
        assert psi_result["current_samples"] == len(current_data)
        
        # Test KS drift detection
        ks_result = drift_detector.detect_ks_drift(
            baseline_data, current_data, "approval_rate"
        )
        
        assert ks_result["feature_name"] == "approval_rate"
        assert ks_result["drift_type"] == "ks"
        assert ks_result["ks_statistic"] > 0.0
        assert ks_result["p_value"] >= 0.0
        assert ks_result["drift_severity"] in ["minor_drift", "major_drift", "critical_drift"]
    
    def test_multivariate_drift_detection(self, drift_detector):
        """Test multivariate drift detection across multiple features."""
        baseline_features = {
            "approval_rate": [0.95, 0.96, 0.94, 0.97, 0.95],
            "avg_cost": [25.0, 26.5, 24.8, 27.2, 25.5],
            "settlement_time": [24.0, 25.5, 23.8, 26.2, 24.5]
        }
        
        current_features = {
            "approval_rate": [0.85, 0.87, 0.83, 0.89, 0.86],
            "avg_cost": [35.0, 37.5, 34.8, 38.2, 36.5],
            "settlement_time": [48.0, 50.5, 47.8, 52.2, 49.5]
        }
        
        multivariate_result = drift_detector.detect_multivariate_drift(
            baseline_features, current_features
        )
        
        assert multivariate_result["drift_type"] == "multivariate"
        assert multivariate_result["overall_drift_severity"] in ["minor_drift", "major_drift", "critical_drift"]
        assert multivariate_result["total_features"] == 3
        assert multivariate_result["features_with_drift"] > 0
        
        # Verify feature results
        for feature_name in baseline_features.keys():
            assert feature_name in multivariate_result["feature_results"]
            feature_result = multivariate_result["feature_results"][feature_name]
            assert "psi" in feature_result
            assert "ks" in feature_result
    
    def test_performance_drift_monitoring(self, performance_drift_monitor):
        """Test performance drift monitoring."""
        # Test performance drift monitoring
        performance_data = {
            "approval_rate": 0.82,
            "avg_cost": 45.0,
            "avg_settlement_time": 52.0,
            "chargeback_rate": 0.03,
            "customer_satisfaction": 0.72
        }
        
        drift_result = performance_drift_monitor.monitor_performance_drift(
            performance_data, "daily"
        )
        
        assert drift_result["time_window"] == "daily"
        assert "overall_drift_severity" in drift_result
        assert "metric_results" in drift_result
        
        # Verify metric results
        for metric in performance_data.keys():
            assert metric in drift_result["metric_results"]
    
    def test_guardrail_breach_detection(self, guardrail_breach_detector):
        """Test guardrail breach detection."""
        # Test with breach scenario
        breach_performance_data = {
            "approval_rate": 0.78,
            "avg_cost": 85.0,
            "avg_settlement_time": 72.0,
            "chargeback_rate": 0.08,
            "customer_satisfaction": 0.65
        }
        
        breach_result = guardrail_breach_detector.check_guardrail_breaches(
            breach_performance_data, "daily"
        )
        
        assert breach_result["overall_status"] == "breach"
        assert len(breach_result["breaches_detected"]) > 0
        assert len(breach_result["critical_alerts"]) >= 0
        assert len(breach_result["warnings_detected"]) >= 0
        
        # Test with healthy scenario
        healthy_performance_data = {
            "approval_rate": 0.96,
            "avg_cost": 35.0,
            "avg_settlement_time": 36.0,
            "chargeback_rate": 0.015,
            "customer_satisfaction": 0.85
        }
        
        healthy_result = guardrail_breach_detector.check_guardrail_breaches(
            healthy_performance_data, "daily"
        )
        
        assert healthy_result["overall_status"] == "healthy"
        assert len(healthy_result["breaches_detected"]) == 0
    
    def test_auto_rollback_orchestration(self, auto_rollback_orchestrator):
        """Test complete auto-rollback orchestration."""
        # Test with breach scenario
        breach_performance_data = {
            "approval_rate": 0.78,
            "avg_cost": 85.0,
            "avg_settlement_time": 72.0,
            "chargeback_rate": 0.08,
            "customer_satisfaction": 0.65
        }
        
        rollback_result = auto_rollback_orchestrator.monitor_and_rollback(
            breach_performance_data, "daily"
        )
        
        assert rollback_result["monitoring_timestamp"] is not None
        assert "breach_detection" in rollback_result
        assert "rollback_execution" in rollback_result
        assert rollback_result["action_taken"] in ["rollback_triggered", "monitoring_only"]
        
        # Test system health status
        health_status = auto_rollback_orchestrator.get_system_health_status()
        
        assert "overall_health" in health_status
        assert "recent_breaches" in health_status
        assert "breach_counts" in health_status
        assert health_status["overall_health"] in ["healthy", "warning", "degraded", "critical"]
    
    def test_learning_loop_with_fixtures(self, outcomes_ingester, drift_detector, guardrail_breach_detector):
        """Test learning loop components with golden fixtures."""
        # Load outcomes fixture
        outcomes_fixture_path = Path(__file__).parent / "fixtures" / "learning_loop" / "outcomes_example.json"
        with open(outcomes_fixture_path) as f:
            outcomes_fixture = json.load(f)
        
        # Test t0 outcome ingestion with fixture
        t0_outcome_data = outcomes_fixture["t0_outcome_example"]
        payment_instruction = PaymentInstruction(**t0_outcome_data["payment_data"])
        auth_result = ProcessorAuthResult(**t0_outcome_data["auth_result"])
        
        t0_result = outcomes_ingester.ingest_t0_outcome(payment_instruction, auth_result)
        
        assert t0_result["outcome_type"] == "t0_immediate"
        assert t0_result["trace_id"] == t0_outcome_data["trace_id"]
        assert t0_result["cohort_id"] is not None
        
        # Load drift detection fixture
        drift_fixture_path = Path(__file__).parent / "fixtures" / "learning_loop" / "drift_detection_example.json"
        with open(drift_fixture_path) as f:
            drift_fixture = json.load(f)
        
        # Test PSI drift detection with fixture
        psi_fixture = drift_fixture["psi_drift_example"]
        psi_result = drift_detector.detect_psi_drift(
            psi_fixture["baseline_data"],
            psi_fixture["current_data"],
            psi_fixture["feature_name"]
        )
        
        assert psi_result["drift_severity"] == psi_fixture["expected_drift_severity"]
        assert psi_fixture["expected_psi_score_range"][0] <= psi_result["psi_score"] <= psi_fixture["expected_psi_score_range"][1]
        
        # Load guardrail breach fixture
        breach_fixture_path = Path(__file__).parent / "fixtures" / "learning_loop" / "guardrail_breach_example.json"
        with open(breach_fixture_path) as f:
            breach_fixture = json.load(f)
        
        # Test guardrail breach detection with fixture
        breach_data = breach_fixture["performance_data_breach"]
        breach_result = guardrail_breach_detector.check_guardrail_breaches(breach_data, "daily")
        
        assert breach_result["overall_status"] == "breach"
        assert len(breach_result["breaches_detected"]) > 0
    
    def test_learning_loop_deterministic_behavior(self, outcomes_ingester, drift_detector):
        """Test that learning loop components produce deterministic results."""
        # Test outcomes ingestion determinism
        payment_instruction = PaymentInstruction(
            instruction_id="deterministic_test",
            trace_id="deterministic_trace",
            selected_rail="ACH",
            selected_processor="carat",
            selected_instrument="bank_transfer",
            amount=1000.0,
            currency="USD",
            effective_cost=15.0,
            settlement_time_hours=24,
            confidence=0.95,
            explanation="Deterministic test",
            alternatives=[],
            constraints_applied=[],
            metadata={"merchant_id": "test_merchant"}
        )
        
        auth_result = ProcessorAuthResult(
            auth_id="deterministic_auth",
            processor_id="carat",
            status="approved",
            auth_code="DETERMINISTIC_AUTH",
            decline_reason=None,
            processor_fee=15.0,
            settlement_time_actual=24,
            processor_metadata={"processing_time_ms": 245},
            timestamp=datetime.now()
        )
        
        # Run multiple times
        results = []
        for _ in range(3):
            result = outcomes_ingester.ingest_t0_outcome(payment_instruction, auth_result)
            results.append(result)
        
        # Results should be identical
        assert all(r["trace_id"] == results[0]["trace_id"] for r in results)
        assert all(r["cohort_id"] == results[0]["cohort_id"] for r in results)
        
        # Test drift detection determinism
        baseline_data = [0.95, 0.96, 0.94, 0.97, 0.95]
        current_data = [0.85, 0.87, 0.83, 0.89, 0.86]
        
        drift_results = []
        for _ in range(3):
            result = drift_detector.detect_psi_drift(baseline_data, current_data, "test_feature")
            drift_results.append(result)
        
        # Results should be identical
        assert all(r["psi_score"] == drift_results[0]["psi_score"] for r in drift_results)
        assert all(r["drift_severity"] == drift_results[0]["drift_severity"] for r in drift_results)
    
    def test_learning_loop_error_handling(self, outcomes_ingester, drift_detector):
        """Test learning loop error handling."""
        # Test outcomes ingestion with invalid data
        invalid_instruction = PaymentInstruction(
            instruction_id="invalid",
            trace_id="invalid",
            selected_rail="INVALID_RAIL",
            selected_processor="invalid",
            selected_instrument="invalid",
            amount=-100.0,
            currency="INVALID",
            effective_cost=-10.0,
            settlement_time_hours=-1,
            confidence=2.0,
            explanation="",
            alternatives=[],
            constraints_applied=[],
            metadata={}
        )
        
        invalid_auth_result = ProcessorAuthResult(
            auth_id="invalid",
            processor_id="invalid",
            status="invalid",
            auth_code=None,
            decline_reason="Invalid",
            processor_fee=-5.0,
            settlement_time_actual=-1,
            processor_metadata={},
            timestamp=datetime.now()
        )
        
        # Should handle gracefully
        result = outcomes_ingester.ingest_t0_outcome(invalid_instruction, invalid_auth_result)
        assert "error" in result or "trace_id" in result
        
        # Test drift detection with empty data
        empty_result = drift_detector.detect_psi_drift([], [], "empty_feature")
        assert "error" in empty_result
        
        # Test drift detection with insufficient data
        single_result = drift_detector.detect_psi_drift([0.95], [0.85], "single_feature")
        assert single_result["drift_severity"] == "insufficient_data"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])









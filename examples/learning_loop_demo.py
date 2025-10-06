#!/usr/bin/env python3
"""
Weave Learning Loop Demo for Phase 9

Demonstrates Weave's learning loop functionality including:
- Outcomes tracking with cohort assignment
- Nightly rewards aggregation and PR promotion
- PSI/KS drift detection
- Guardrail breach detection and auto-rollback
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from weave.outcomes_tracker import (
    get_outcomes_ingester,
    CohortTracker
)
from weave.nightly_learning_jobs import (
    get_nightly_learning_jobs,
    RewardAggregator,
    AutoPRPromoter
)
from weave.drift_detection import (
    get_drift_detector,
    get_performance_drift_monitor
)
from weave.auto_rollback import (
    get_auto_rollback_orchestrator,
    GuardrailBreachDetector
)
from weave.models import (
    PaymentInstruction, ProcessorAuthResult
)


def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'-'*40}")
    print(f"  {title}")
    print(f"{'-'*40}")


def demo_outcomes_tracking():
    """Demonstrate outcomes tracking with cohort assignment."""
    print_header("Outcomes Tracking Demo")
    
    outcomes_ingester = get_outcomes_ingester()
    cohort_tracker = CohortTracker()
    
    # Create sample payment instruction
    payment_instruction = PaymentInstruction(
        instruction_id="demo_instruction_001",
        trace_id="demo_trace_001",
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
            "merchant_category": "retail",
            "geographic_region": "US"
        }
    )
    
    print_section("Cohort Assignment")
    cohort_id = cohort_tracker.assign_cohort_id(
        payment_instruction,
        {"merchant_category": "retail", "geographic_region": "US"}
    )
    
    print(f"Transaction: ${payment_instruction.amount:.2f} {payment_instruction.selected_rail}")
    print(f"Assigned Cohort: {cohort_id}")
    
    # Create sample authorization result
    auth_result = ProcessorAuthResult(
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
    
    print_section("T0 Outcome Ingestion")
    t0_outcome = outcomes_ingester.ingest_t0_outcome(
        payment_instruction,
        auth_result
    )
    
    print(f"Outcome Type: {t0_outcome['outcome_type']}")
    print(f"Cohort ID: {t0_outcome['cohort_id']}")
    print(f"Approval Status: {t0_outcome['auth_result']['status']}")
    print(f"Processing Time: {t0_outcome['immediate_metrics']['processing_time_ms']}ms")
    print(f"Risk Score: {t0_outcome['immediate_metrics']['risk_score']}")
    
    # Create settlement data for tx outcome
    settlement_data = {
        "settlement_status": "settled",
        "actual_settlement_time_hours": 22,
        "final_cost": 15.0,
        "fees_breakdown": {
            "processor_fee": 15.0,
            "network_fee": 0.0,
            "additional_fees": 0.0
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
    
    print_section("TX Outcome Ingestion")
    tx_outcome = outcomes_ingester.ingest_tx_outcome(
        payment_instruction,
        settlement_data
    )
    
    print(f"Outcome Type: {tx_outcome['outcome_type']}")
    print(f"Settlement Status: {tx_outcome['settlement_data']['settlement_status']}")
    print(f"Final Cost: ${tx_outcome['final_metrics']['actual_cost']:.2f}")
    print(f"Settlement Time: {tx_outcome['final_metrics']['settlement_time_hours']:.1f} hours")
    print(f"Customer Rating: {tx_outcome['final_metrics']['customer_rating']:.2f}")
    
    print_section("Cohort Performance Summary")
    performance_summary = outcomes_ingester.get_cohort_performance_summary(cohort_id)
    
    print(f"Cohort: {performance_summary['cohort_id']}")
    print(f"Total Transactions: {performance_summary['total_transactions']}")
    print(f"Settled Transactions: {performance_summary['settled_transactions']}")
    print(f"Approval Rate: {performance_summary['approval_rate']:.2%}")
    print(f"Average Cost: ${performance_summary['avg_cost']:.2f}")
    print(f"Average Settlement Time: {performance_summary['avg_settlement_time_hours']:.1f} hours")
    print(f"Chargeback Rate: {performance_summary['chargeback_rate']:.2%}")
    print(f"Customer Satisfaction: {performance_summary['customer_satisfaction']:.2f}")


def demo_reward_aggregation():
    """Demonstrate reward aggregation and PR promotion."""
    print_header("Reward Aggregation Demo")
    
    reward_aggregator = RewardAggregator()
    auto_pr_promoter = AutoPRPromoter()
    
    print_section("Daily Reward Aggregation")
    yesterday = datetime.now() - timedelta(days=1)
    aggregation_result = reward_aggregator.aggregate_daily_rewards(yesterday)
    
    print(f"Aggregation Date: {aggregation_result['aggregation_date']}")
    print(f"Total Transactions: {aggregation_result['total_transactions']}")
    print(f"Total Variants: {aggregation_result['total_variants']}")
    print(f"Promotion Candidates: {len(aggregation_result['promotion_candidates'])}")
    
    if aggregation_result['promotion_candidates']:
        print("\nTop Promotion Candidates:")
        for i, candidate in enumerate(aggregation_result['promotion_candidates'][:3], 1):
            perf = candidate['performance']
            print(f"  {i}. {candidate['variant_id']}")
            print(f"     Transactions: {perf['transaction_count']}")
            print(f"     Approval Rate: {perf['approval_rate']:.2%}")
            print(f"     Avg Cost: ${perf['avg_cost']:.2f}")
            print(f"     Priority: {candidate['promotion_priority']:.3f}")
    
    print_section("Auto PR Promotion")
    if aggregation_result['promotion_candidates']:
        # Create PR for top candidate
        top_candidate = aggregation_result['promotion_candidates'][0]
        pr_result = auto_pr_promoter.create_promotion_pr(
            top_candidate,
            yesterday.isoformat()
        )
        
        if pr_result['success']:
            print(f"PR Created: {pr_result['pr_number']}")
            print(f"Branch: {pr_result['branch_name']}")
            print(f"Title: {pr_result['pr_title']}")
        else:
            print(f"PR Creation Failed: {pr_result.get('error', 'Unknown error')}")
    else:
        print("No promotion candidates available for PR creation")


def demo_drift_detection():
    """Demonstrate PSI/KS drift detection."""
    print_header("Drift Detection Demo")
    
    drift_detector = get_drift_detector()
    performance_drift_monitor = get_performance_drift_monitor()
    
    print_section("PSI Drift Detection")
    # Simulate baseline vs current data for approval rates
    baseline_approval_rates = [0.95, 0.96, 0.94, 0.97, 0.95, 0.96, 0.93, 0.95, 0.96, 0.94]
    current_approval_rates = [0.85, 0.87, 0.83, 0.89, 0.86, 0.88, 0.84, 0.87, 0.85, 0.86]
    
    psi_result = drift_detector.detect_psi_drift(
        baseline_approval_rates,
        current_approval_rates,
        "approval_rate"
    )
    
    print(f"Feature: {psi_result['feature_name']}")
    print(f"PSI Score: {psi_result['psi_score']:.4f}")
    print(f"Drift Severity: {psi_result['drift_severity']}")
    print(f"Baseline Samples: {psi_result['baseline_samples']}")
    print(f"Current Samples: {psi_result['current_samples']}")
    
    print_section("KS Drift Detection")
    # Simulate baseline vs current data for costs
    baseline_costs = [25.0, 26.5, 24.8, 27.2, 25.5, 26.0, 24.5, 25.8, 26.2, 25.0]
    current_costs = [35.0, 37.5, 34.8, 38.2, 36.5, 37.0, 35.5, 36.8, 37.2, 36.0]
    
    ks_result = drift_detector.detect_ks_drift(
        baseline_costs,
        current_costs,
        "avg_cost"
    )
    
    print(f"Feature: {ks_result['feature_name']}")
    print(f"KS Statistic: {ks_result['ks_statistic']:.4f}")
    print(f"P-value: {ks_result['p_value']:.4f}")
    print(f"Drift Severity: {ks_result['drift_severity']}")
    
    print_section("Multivariate Drift Detection")
    baseline_features = {
        "approval_rate": baseline_approval_rates,
        "avg_cost": baseline_costs,
        "settlement_time": [24.0, 25.5, 23.8, 26.2, 24.5, 25.0, 23.5, 24.8, 25.2, 24.0]
    }
    
    current_features = {
        "approval_rate": current_approval_rates,
        "avg_cost": current_costs,
        "settlement_time": [48.0, 50.5, 47.8, 52.2, 49.5, 50.0, 47.5, 49.8, 50.2, 48.0]
    }
    
    multivariate_result = drift_detector.detect_multivariate_drift(
        baseline_features,
        current_features
    )
    
    print(f"Overall Drift Severity: {multivariate_result['overall_drift_severity']}")
    print(f"Features with Drift: {multivariate_result['features_with_drift']}")
    print(f"Total Features: {multivariate_result['total_features']}")
    
    print("\nFeature-specific Results:")
    for feature_name, feature_result in multivariate_result['feature_results'].items():
        psi_severity = feature_result['psi']['drift_severity']
        ks_severity = feature_result['ks']['drift_severity']
        print(f"  {feature_name}: PSI={psi_severity}, KS={ks_severity}")
    
    print_section("Performance Drift Monitoring")
    performance_data = {
        "approval_rate": 0.82,
        "avg_cost": 45.0,
        "avg_settlement_time": 52.0,
        "chargeback_rate": 0.03,
        "customer_satisfaction": 0.72
    }
    
    performance_drift_result = performance_drift_monitor.monitor_performance_drift(
        performance_data,
        "daily"
    )
    
    print(f"Overall Drift Severity: {performance_drift_result['overall_drift_severity']}")
    print("\nMetric-specific Drift Results:")
    for metric, result in performance_drift_result['metric_results'].items():
        print(f"  {metric}: {result['drift_severity']}")


def demo_guardrail_breach_detection():
    """Demonstrate guardrail breach detection and auto-rollback."""
    print_header("Guardrail Breach Detection Demo")
    
    guardrail_breach_detector = GuardrailBreachDetector()
    auto_rollback_orchestrator = get_auto_rollback_orchestrator()
    
    print_section("Healthy Performance Scenario")
    healthy_performance = {
        "approval_rate": 0.96,
        "avg_cost": 35.0,
        "avg_settlement_time": 36.0,
        "chargeback_rate": 0.015,
        "customer_satisfaction": 0.85
    }
    
    healthy_result = guardrail_breach_detector.check_guardrail_breaches(
        healthy_performance,
        "daily"
    )
    
    print(f"Overall Status: {healthy_result['overall_status']}")
    print(f"Breaches Detected: {len(healthy_result['breaches_detected'])}")
    print(f"Critical Alerts: {len(healthy_result['critical_alerts'])}")
    print(f"Warnings: {len(healthy_result['warnings_detected'])}")
    
    print_section("Warning Performance Scenario")
    warning_performance = {
        "approval_rate": 0.91,
        "avg_cost": 55.0,
        "avg_settlement_time": 50.0,
        "chargeback_rate": 0.025,
        "customer_satisfaction": 0.78
    }
    
    warning_result = guardrail_breach_detector.check_guardrail_breaches(
        warning_performance,
        "daily"
    )
    
    print(f"Overall Status: {warning_result['overall_status']}")
    print(f"Breaches Detected: {len(warning_result['breaches_detected'])}")
    print(f"Critical Alerts: {len(warning_result['critical_alerts'])}")
    print(f"Warnings: {len(warning_result['warnings_detected'])}")
    
    if warning_result['warnings_detected']:
        print("\nWarning Details:")
        for warning in warning_result['warnings_detected']:
            print(f"  {warning['metric']}: {warning['current_value']} (threshold: {warning['threshold']})")
    
    print_section("Critical Performance Scenario")
    critical_performance = {
        "approval_rate": 0.87,
        "avg_cost": 65.0,
        "avg_settlement_time": 60.0,
        "chargeback_rate": 0.04,
        "customer_satisfaction": 0.75
    }
    
    critical_result = guardrail_breach_detector.check_guardrail_breaches(
        critical_performance,
        "daily"
    )
    
    print(f"Overall Status: {critical_result['overall_status']}")
    print(f"Breaches Detected: {len(critical_result['breaches_detected'])}")
    print(f"Critical Alerts: {len(critical_result['critical_alerts'])}")
    print(f"Warnings: {len(critical_result['warnings_detected'])}")
    
    if critical_result['critical_alerts']:
        print("\nCritical Alert Details:")
        for alert in critical_result['critical_alerts']:
            print(f"  {alert['metric']}: {alert['current_value']} (threshold: {alert['threshold']})")
    
    print_section("Breach Performance Scenario")
    breach_performance = {
        "approval_rate": 0.78,
        "avg_cost": 85.0,
        "avg_settlement_time": 72.0,
        "chargeback_rate": 0.08,
        "customer_satisfaction": 0.65
    }
    
    breach_result = guardrail_breach_detector.check_guardrail_breaches(
        breach_performance,
        "daily"
    )
    
    print(f"Overall Status: {breach_result['overall_status']}")
    print(f"Breaches Detected: {len(breach_result['breaches_detected'])}")
    
    if breach_result['breaches_detected']:
        print("\nBreach Details:")
        for breach in breach_result['breaches_detected']:
            print(f"  {breach['metric']}: {breach['current_value']} (threshold: {breach['threshold']})")
            print(f"    Action Required: {breach['action_required']}")
    
    print_section("Auto-Rollback Orchestration")
    # Test auto-rollback with breach scenario
    rollback_result = auto_rollback_orchestrator.monitor_and_rollback(
        breach_performance,
        "daily"
    )
    
    print(f"Action Taken: {rollback_result['action_taken']}")
    print(f"Breach Status: {rollback_result['breach_detection']['overall_status']}")
    
    if rollback_result['rollback_execution']:
        rollback_config = rollback_result['rollback_execution'].get('rollback_config', {})
        print(f"Rollback Scope: {rollback_config.get('rollback_scope', {}).get('scope_type', 'unknown')}")
        
        pr_result = rollback_result['rollback_execution'].get('pr_result', {})
        if pr_result.get('success'):
            print(f"Rollback PR Created: {pr_result.get('pr_number', 'unknown')}")
    
    print_section("System Health Status")
    health_status = auto_rollback_orchestrator.get_system_health_status()
    
    print(f"Overall Health: {health_status['overall_health']}")
    print(f"Recent Breaches (7 days): {len(health_status['recent_breaches'])}")
    print("Breach Counts by Severity:")
    for severity, count in health_status['breach_counts'].items():
        print(f"  {severity}: {count}")


def demo_nightly_learning_jobs():
    """Demonstrate complete nightly learning jobs."""
    print_header("Nightly Learning Jobs Demo")
    
    nightly_jobs = get_nightly_learning_jobs()
    
    print_section("Running Nightly Jobs")
    yesterday = datetime.now() - timedelta(days=1)
    nightly_result = nightly_jobs.run_nightly_jobs(yesterday)
    
    print(f"Date: {nightly_result['date']}")
    print(f"Success: {nightly_result['success']}")
    print(f"Completed At: {nightly_result['completed_at']}")
    
    if nightly_result['success']:
        aggregation_result = nightly_result['aggregation_result']
        print(f"\nAggregation Results:")
        print(f"  Total Transactions: {aggregation_result['total_transactions']}")
        print(f"  Total Variants: {aggregation_result['total_variants']}")
        print(f"  Promotion Candidates: {len(aggregation_result['promotion_candidates'])}")
        
        promotion_results = nightly_result['promotion_results']
        print(f"\nPromotion Results:")
        print(f"  PRs Created: {len(promotion_results)}")
        for i, pr_result in enumerate(promotion_results, 1):
            if pr_result.get('success'):
                print(f"  PR {i}: {pr_result.get('pr_number', 'unknown')}")
            else:
                print(f"  PR {i}: Failed - {pr_result.get('error', 'unknown error')}")
        
        nightly_report = nightly_result['nightly_report']
        print(f"\nNightly Report Summary:")
        print(f"  Top Performers: {len(nightly_report['summary']['top_performers'])}")
        print(f"  Recommendations: {len(nightly_report['recommendations'])}")
        
        if nightly_report['recommendations']:
            print("\nRecommendations:")
            for i, recommendation in enumerate(nightly_report['recommendations'], 1):
                print(f"  {i}. {recommendation}")
    else:
        print(f"Nightly Jobs Failed: {nightly_result.get('error', 'Unknown error')}")


def main():
    """Run the complete Weave learning loop demo."""
    print("🌊 Weave Learning Loop Phase 9 Demo")
    print("=" * 60)
    
    try:
        # Run individual demos
        demo_outcomes_tracking()
        demo_reward_aggregation()
        demo_drift_detection()
        demo_guardrail_breach_detection()
        demo_nightly_learning_jobs()
        
        print_header("Demo Complete! ✅")
        print("Weave's learning loop is now operational with:")
        print("• Outcomes tracking with cohort assignment")
        print("• Reward aggregation and auto PR promotion")
        print("• PSI/KS drift detection")
        print("• Guardrail breach detection")
        print("• Auto-rollback procedures")
        print("• Complete nightly learning jobs")
        print("\nNext steps:")
        print("• Integrate with Orca for reward updates")
        print("• Set up CloudEvent emission")
        print("• Configure real-time monitoring")
        print("• Deploy to production environment")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())









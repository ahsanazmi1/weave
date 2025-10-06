"""
Guardrails and drift detection for Weave Phase 4.

Provides comprehensive guardrails with PSI/KS drift detection, approval/decline
thresholds, and automatic rollback capabilities for payment processor policies.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

from weave.models import GuardrailMetrics, GuardrailBreach, SignedReceipt, RewardVariant

logger = logging.getLogger(__name__)


class DriftDetector:
    """
    Statistical drift detection service.
    
    Implements Population Stability Index (PSI) and Kolmogorov-Smirnov (KS) tests
    for detecting distribution drift in payment processor metrics.
    """
    
    def __init__(self):
        """Initialize drift detector."""
        logger.info("Drift detector initialized")
    
    def calculate_psi(
        self,
        baseline_data: List[float],
        current_data: List[float],
        bins: int = 10
    ) -> float:
        """
        Calculate Population Stability Index (PSI) between baseline and current data.
        
        Args:
            baseline_data: Baseline distribution data
            current_data: Current distribution data
            bins: Number of bins for histogram
            
        Returns:
            PSI value (higher values indicate more drift)
        """
        if not baseline_data or not current_data:
            return 0.0
        
        # Create bins based on baseline data
        baseline_array = np.array(baseline_data)
        current_array = np.array(current_data)
        
        # Define bin edges
        min_val = min(baseline_array.min(), current_array.min())
        max_val = max(baseline_array.max(), current_array.max())
        
        if min_val == max_val:
            return 0.0
        
        bin_edges = np.linspace(min_val, max_val, bins + 1)
        
        # Calculate histograms
        baseline_hist, _ = np.histogram(baseline_array, bins=bin_edges)
        current_hist, _ = np.histogram(current_array, bins=bin_edges)
        
        # Normalize to probabilities
        baseline_prob = baseline_hist / len(baseline_data)
        current_prob = current_hist / len(current_data)
        
        # Add small epsilon to avoid log(0)
        epsilon = 1e-6
        baseline_prob = baseline_prob + epsilon
        current_prob = current_prob + epsilon
        
        # Calculate PSI
        psi = np.sum((current_prob - baseline_prob) * np.log(current_prob / baseline_prob))
        
        return float(psi)
    
    def calculate_ks_statistic(
        self,
        baseline_data: List[float],
        current_data: List[float]
    ) -> Tuple[float, float]:
        """
        Calculate Kolmogorov-Smirnov statistic between baseline and current data.
        
        Args:
            baseline_data: Baseline distribution data
            current_data: Current distribution data
            
        Returns:
            Tuple of (KS statistic, p-value)
        """
        if not baseline_data or not current_data:
            return 0.0, 1.0
        
        baseline_array = np.array(baseline_data)
        current_array = np.array(current_data)
        
        # Perform KS test
        ks_statistic, p_value = stats.ks_2samp(baseline_array, current_array)
        
        return float(ks_statistic), float(p_value)
    
    def detect_drift(
        self,
        baseline_data: List[float],
        current_data: List[float],
        metric_type: str,
        threshold: float = 0.2
    ) -> GuardrailMetrics:
        """
        Detect drift between baseline and current data.
        
        Args:
            baseline_data: Baseline distribution data
            current_data: Current distribution data
            metric_type: Type of metric being analyzed
            threshold: Drift threshold for alerting
            
        Returns:
            Guardrail metrics with drift analysis
        """
        # Calculate PSI
        psi = self.calculate_psi(baseline_data, current_data)
        
        # Calculate KS statistic
        ks_statistic, p_value = self.calculate_ks_statistic(baseline_data, current_data)
        
        # Determine drift severity
        if psi > 0.25 or ks_statistic > 0.3:
            severity = "critical"
            drift_detected = True
        elif psi > 0.15 or ks_statistic > 0.2:
            severity = "high"
            drift_detected = True
        elif psi > threshold or ks_statistic > 0.1:
            severity = "medium"
            drift_detected = True
        elif psi > threshold * 0.5 or ks_statistic > 0.05:
            severity = "low"
            drift_detected = True
        else:
            severity = "low"
            drift_detected = False
        
        # Calculate current value (mean for simplicity)
        current_value = np.mean(current_data) if current_data else 0.0
        baseline_value = np.mean(baseline_data) if baseline_data else 0.0
        
        return GuardrailMetrics(
            metric_id=str(uuid.uuid4()),
            metric_type=metric_type,
            baseline_value=baseline_value,
            baseline_date=datetime.now() - timedelta(days=30),  # Simulated baseline date
            baseline_sample_size=len(baseline_data),
            current_value=current_value,
            current_date=datetime.now(),
            current_sample_size=len(current_data),
            drift_score=psi,  # Use PSI as primary drift score
            drift_threshold=threshold,
            drift_detected=drift_detected,
            severity=severity
        )


class GuardrailEnforcer:
    """
    Guardrail enforcement service.
    
    Enforces approval/decline thresholds and triggers automatic rollbacks
    when guardrails are breached.
    """
    
    def __init__(self):
        """Initialize guardrail enforcer."""
        self.drift_detector = DriftDetector()
        logger.info("Guardrail enforcer initialized")
    
    def check_approval_rate_guardrail(
        self,
        receipts: List[SignedReceipt],
        threshold: float = 0.95
    ) -> GuardrailMetrics:
        """
        Check approval rate guardrail.
        
        Args:
            receipts: Receipts to analyze
            threshold: Minimum approval rate threshold
            
        Returns:
            Guardrail metrics for approval rate
        """
        if not receipts:
            return GuardrailMetrics(
                metric_id=str(uuid.uuid4()),
                metric_type="approval_rate",
                baseline_value=threshold,
                baseline_date=datetime.now() - timedelta(days=30),
                baseline_sample_size=1000,
                current_value=0.0,
                current_date=datetime.now(),
                current_sample_size=0,
                drift_score=0.0,
                drift_threshold=0.1,
                drift_detected=True,
                severity="critical"
            )
        
        # Calculate current approval rate
        approved_count = sum(
            1 for receipt in receipts 
            if receipt.processor_auth_result.status == "approved"
        )
        current_approval_rate = approved_count / len(receipts)
        
        # Simulate baseline data
        baseline_approval_rates = [threshold] * 1000  # Simulated baseline
        current_approval_rates = [current_approval_rate] * len(receipts)
        
        # Detect drift
        metrics = self.drift_detector.detect_drift(
            baseline_approval_rates,
            current_approval_rates,
            "approval_rate",
            threshold=0.1
        )
        
        # Override drift detection based on threshold
        if current_approval_rate < threshold:
            metrics.drift_detected = True
            metrics.severity = "critical" if current_approval_rate < threshold * 0.9 else "high"
        
        return metrics
    
    def check_settlement_time_guardrail(
        self,
        receipts: List[SignedReceipt],
        max_settlement_hours: float = 72.0
    ) -> GuardrailMetrics:
        """
        Check settlement time guardrail.
        
        Args:
            receipts: Receipts to analyze
            max_settlement_hours: Maximum acceptable settlement time
            
        Returns:
            Guardrail metrics for settlement time
        """
        if not receipts:
            return GuardrailMetrics(
                metric_id=str(uuid.uuid4()),
                metric_type="settlement_time",
                baseline_value=max_settlement_hours,
                baseline_date=datetime.now() - timedelta(days=30),
                baseline_sample_size=1000,
                current_value=0.0,
                current_date=datetime.now(),
                current_sample_size=0,
                drift_score=0.0,
                drift_threshold=0.2,
                drift_detected=False,
                severity="low"
            )
        
        # Calculate current settlement times
        settlement_times = [
            receipt.processor_auth_result.settlement_time_actual
            for receipt in receipts
        ]
        current_avg_settlement = np.mean(settlement_times)
        
        # Simulate baseline data
        baseline_settlement_times = [max_settlement_hours * 0.8] * 1000  # Simulated baseline
        current_settlement_times = settlement_times
        
        # Detect drift
        metrics = self.drift_detector.detect_drift(
            baseline_settlement_times,
            current_settlement_times,
            "settlement_time",
            threshold=0.2
        )
        
        # Override drift detection based on threshold
        if current_avg_settlement > max_settlement_hours:
            metrics.drift_detected = True
            metrics.severity = "critical" if current_avg_settlement > max_settlement_hours * 1.5 else "high"
        
        return metrics
    
    def check_cost_drift_guardrail(
        self,
        variants: List[RewardVariant],
        max_cost_increase_pct: float = 0.1
    ) -> GuardrailMetrics:
        """
        Check cost drift guardrail.
        
        Args:
            variants: Reward variants to analyze
            max_cost_increase_pct: Maximum acceptable cost increase percentage
            
        Returns:
            Guardrail metrics for cost drift
        """
        if not variants:
            return GuardrailMetrics(
                metric_id=str(uuid.uuid4()),
                metric_type="cost_drift",
                baseline_value=0.0,
                baseline_date=datetime.now() - timedelta(days=30),
                baseline_sample_size=1000,
                current_value=0.0,
                current_date=datetime.now(),
                current_sample_size=0,
                drift_score=0.0,
                drift_threshold=max_cost_increase_pct,
                drift_detected=False,
                severity="low"
            )
        
        # Calculate current average cost
        total_amount = sum(v.total_amount for v in variants)
        total_reward_value = sum(v.reward_value for v in variants)
        current_cost_rate = total_reward_value / total_amount if total_amount > 0 else 0.0
        
        # Simulate baseline data
        baseline_cost_rate = current_cost_rate * 0.9  # Simulated baseline
        baseline_costs = [baseline_cost_rate] * 1000
        current_costs = [current_cost_rate] * len(variants)
        
        # Detect drift
        metrics = self.drift_detector.detect_drift(
            baseline_costs,
            current_costs,
            "cost_drift",
            threshold=max_cost_increase_pct
        )
        
        # Override drift detection based on threshold
        cost_increase = (current_cost_rate - baseline_cost_rate) / baseline_cost_rate if baseline_cost_rate > 0 else 0
        if cost_increase > max_cost_increase_pct:
            metrics.drift_detected = True
            metrics.severity = "critical" if cost_increase > max_cost_increase_pct * 2 else "high"
        
        return metrics


class AutoRollbackManager:
    """
    Automatic rollback manager for guardrail breaches.
    
    Triggers automatic rollbacks by opening PRs to reset DEFAULT_POLICY
    when critical guardrails are breached.
    """
    
    def __init__(self):
        """Initialize auto rollback manager."""
        logger.info("Auto rollback manager initialized")
    
    def check_guardrail_breaches(
        self,
        metrics: List[GuardrailMetrics]
    ) -> List[GuardrailBreach]:
        """
        Check for guardrail breaches and create breach events.
        
        Args:
            metrics: Guardrail metrics to check
            
        Returns:
            List of guardrail breaches detected
        """
        breaches = []
        
        for metric in metrics:
            if metric.drift_detected and metric.severity in ["high", "critical"]:
                breach = GuardrailBreach(
                    breach_id=str(uuid.uuid4()),
                    trace_id="system",  # System-wide breach
                    guardrail_type=metric.metric_type,
                    metric=metric,
                    breach_severity=metric.severity,
                    breach_description=f"{metric.metric_type} guardrail breached: {metric.drift_score:.3f} > {metric.drift_threshold:.3f}",
                    rollback_triggered=False,
                    rollback_status="pending"
                )
                
                # Trigger rollback for critical breaches
                if metric.severity == "critical":
                    breach.rollback_triggered = True
                    breach.rollback_pr_url = self._create_rollback_pr(metric)
                    breach.rollback_status = "created"
                
                breaches.append(breach)
                
                logger.warning(f"Guardrail breach detected: {breach.breach_description}")
        
        return breaches
    
    def _create_rollback_pr(self, metric: GuardrailMetrics) -> str:
        """
        Create rollback PR to reset DEFAULT_POLICY (placeholder implementation).
        
        Args:
            metric: Guardrail metric that triggered rollback
            
        Returns:
            PR URL (placeholder)
        """
        # In a real implementation, this would:
        # 1. Create a new branch
        # 2. Reset DEFAULT_POLICY to previous known good state
        # 3. Open a PR to main branch
        # 4. Return the PR URL
        
        pr_url = f"https://github.com/ocn-demo/orca/pull/rollback-{uuid.uuid4().hex[:8]}"
        
        logger.info(f"Created rollback PR: {pr_url} for metric {metric.metric_type}")
        return pr_url
    
    def resolve_breach(
        self,
        breach: GuardrailBreach,
        resolution_notes: str
    ) -> GuardrailBreach:
        """
        Resolve a guardrail breach.
        
        Args:
            breach: Breach to resolve
            resolution_notes: Notes about the resolution
            
        Returns:
            Updated breach with resolution information
        """
        breach.resolved = True
        breach.resolution_notes = resolution_notes
        breach.resolved_at = datetime.now()
        
        logger.info(f"Resolved breach {breach.breach_id}: {resolution_notes}")
        return breach


class GuardrailManager:
    """
    Main guardrail manager for Weave Phase 4.
    
    Coordinates drift detection, guardrail enforcement, and automatic rollbacks
    for comprehensive payment processor monitoring and safety.
    """
    
    def __init__(self):
        """Initialize guardrail manager."""
        self.enforcer = GuardrailEnforcer()
        self.rollback_manager = AutoRollbackManager()
        logger.info("Guardrail manager initialized")
    
    def run_guardrail_checks(
        self,
        receipts: List[SignedReceipt],
        variants: List[RewardVariant]
    ) -> List[GuardrailBreach]:
        """
        Run comprehensive guardrail checks.
        
        Args:
            receipts: Receipts to analyze
            variants: Reward variants to analyze
            
        Returns:
            List of guardrail breaches detected
        """
        logger.info("Running comprehensive guardrail checks")
        
        # Collect all metrics
        metrics = []
        
        # Check approval rate guardrail
        approval_metrics = self.enforcer.check_approval_rate_guardrail(receipts)
        metrics.append(approval_metrics)
        
        # Check settlement time guardrail
        settlement_metrics = self.enforcer.check_settlement_time_guardrail(receipts)
        metrics.append(settlement_metrics)
        
        # Check cost drift guardrail
        cost_metrics = self.enforcer.check_cost_drift_guardrail(variants)
        metrics.append(cost_metrics)
        
        # Check for breaches
        breaches = self.rollback_manager.check_guardrail_breaches(metrics)
        
        logger.info(f"Guardrail checks completed: {len(metrics)} metrics, {len(breaches)} breaches")
        return breaches
    
    def get_guardrail_status(self) -> Dict[str, Any]:
        """
        Get current guardrail status summary.
        
        Returns:
            Guardrail status summary
        """
        return {
            "guardrails_active": True,
            "drift_detection_enabled": True,
            "auto_rollback_enabled": True,
            "last_check": datetime.now().isoformat(),
            "supported_metrics": [
                "approval_rate",
                "settlement_time", 
                "cost_drift",
                "psi_drift",
                "ks_drift"
            ]
        }


# Global instances
_drift_detector = None
_guardrail_enforcer = None
_auto_rollback_manager = None
_guardrail_manager = None


def get_drift_detector() -> DriftDetector:
    """Get global drift detector instance."""
    global _drift_detector
    if _drift_detector is None:
        _drift_detector = DriftDetector()
    return _drift_detector


def get_guardrail_enforcer() -> GuardrailEnforcer:
    """Get global guardrail enforcer instance."""
    global _guardrail_enforcer
    if _guardrail_enforcer is None:
        _guardrail_enforcer = GuardrailEnforcer()
    return _guardrail_enforcer


def get_auto_rollback_manager() -> AutoRollbackManager:
    """Get global auto rollback manager instance."""
    global _auto_rollback_manager
    if _auto_rollback_manager is None:
        _auto_rollback_manager = AutoRollbackManager()
    return _auto_rollback_manager


def get_guardrail_manager() -> GuardrailManager:
    """Get global guardrail manager instance."""
    global _guardrail_manager
    if _guardrail_manager is None:
        _guardrail_manager = GuardrailManager()
    return _guardrail_manager









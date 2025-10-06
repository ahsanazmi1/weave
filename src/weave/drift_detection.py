"""
Drift Detection for Weave Phase 9.

Implements PSI (Population Stability Index) and KS (Kolmogorov-Smirnov) 
drift detection with CloudEvent emission for model monitoring.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

from src.weave.events import emit_processor_integration_event

logger = logging.getLogger(__name__)


class DriftDetector:
    """
    Detects drift in model performance and data distributions.
    
    Implements PSI and KS tests to identify when model performance
    or input data distributions have shifted significantly.
    """
    
    def __init__(self):
        """Initialize the drift detector."""
        self.drift_thresholds = {
            "psi": {
                "no_drift": 0.1,
                "minor_drift": 0.2,
                "major_drift": 0.25
            },
            "ks": {
                "no_drift": 0.05,
                "minor_drift": 0.1,
                "major_drift": 0.15
            }
        }
        self.baseline_distributions = {}  # Store baseline distributions
        logger.info("Drift detector initialized")
    
    def detect_psi_drift(
        self,
        baseline_data: List[float],
        current_data: List[float],
        feature_name: str,
        bins: int = 10
    ) -> Dict[str, Any]:
        """
        Detect drift using Population Stability Index (PSI).
        
        Args:
            baseline_data: Baseline data distribution
            current_data: Current data distribution
            feature_name: Name of the feature being analyzed
            bins: Number of bins for histogram
            
        Returns:
            Dictionary containing PSI drift detection results
        """
        try:
            if len(baseline_data) == 0 or len(current_data) == 0:
                return {
                    "feature_name": feature_name,
                    "drift_type": "psi",
                    "psi_score": 0.0,
                    "drift_severity": "insufficient_data",
                    "error": "Insufficient data for PSI calculation"
                }
            
            # Create bins based on baseline data
            baseline_min = min(baseline_data)
            baseline_max = max(baseline_data)
            
            # Handle edge case where all values are the same
            if baseline_min == baseline_max:
                bin_edges = [baseline_min - 0.1, baseline_min, baseline_min + 0.1]
            else:
                bin_edges = np.linspace(baseline_min, baseline_max, bins + 1)
            
            # Calculate histograms
            baseline_hist, _ = np.histogram(baseline_data, bins=bin_edges)
            current_hist, _ = np.histogram(current_data, bins=bin_edges)
            
            # Normalize to probabilities
            baseline_prob = baseline_hist / len(baseline_data)
            current_prob = current_hist / len(current_data)
            
            # Avoid division by zero
            epsilon = 1e-10
            baseline_prob = np.maximum(baseline_prob, epsilon)
            current_prob = np.maximum(current_prob, epsilon)
            
            # Calculate PSI
            psi_score = np.sum((current_prob - baseline_prob) * np.log(current_prob / baseline_prob))
            
            # Determine drift severity
            drift_severity = self._classify_psi_drift(psi_score)
            
            psi_result = {
                "feature_name": feature_name,
                "drift_type": "psi",
                "psi_score": float(psi_score),
                "drift_severity": drift_severity,
                "baseline_samples": len(baseline_data),
                "current_samples": len(current_data),
                "bins_used": len(bin_edges) - 1,
                "detected_at": datetime.now().isoformat()
            }
            
            # Emit drift detection event if drift detected
            if drift_severity != "no_drift":
                self._emit_drift_event(psi_result)
            
            logger.info(f"PSI drift detection for {feature_name}: {psi_score:.4f} ({drift_severity})")
            return psi_result
            
        except Exception as e:
            logger.error(f"PSI drift detection failed for {feature_name}: {str(e)}")
            return {
                "feature_name": feature_name,
                "drift_type": "psi",
                "error": str(e),
                "detected_at": datetime.now().isoformat()
            }
    
    def detect_ks_drift(
        self,
        baseline_data: List[float],
        current_data: List[float],
        feature_name: str,
        significance_level: float = 0.05
    ) -> Dict[str, Any]:
        """
        Detect drift using Kolmogorov-Smirnov (KS) test.
        
        Args:
            baseline_data: Baseline data distribution
            current_data: Current data distribution
            feature_name: Name of the feature being analyzed
            significance_level: Statistical significance level
            
        Returns:
            Dictionary containing KS drift detection results
        """
        try:
            if len(baseline_data) == 0 or len(current_data) == 0:
                return {
                    "feature_name": feature_name,
                    "drift_type": "ks",
                    "ks_statistic": 0.0,
                    "p_value": 1.0,
                    "drift_severity": "insufficient_data",
                    "error": "Insufficient data for KS test"
                }
            
            # Perform KS test
            ks_statistic, p_value = stats.ks_2samp(baseline_data, current_data)
            
            # Determine drift severity
            drift_severity = self._classify_ks_drift(ks_statistic, p_value, significance_level)
            
            ks_result = {
                "feature_name": feature_name,
                "drift_type": "ks",
                "ks_statistic": float(ks_statistic),
                "p_value": float(p_value),
                "significance_level": significance_level,
                "drift_severity": drift_severity,
                "baseline_samples": len(baseline_data),
                "current_samples": len(current_data),
                "detected_at": datetime.now().isoformat()
            }
            
            # Emit drift detection event if drift detected
            if drift_severity != "no_drift":
                self._emit_drift_event(ks_result)
            
            logger.info(f"KS drift detection for {feature_name}: statistic={ks_statistic:.4f}, p-value={p_value:.4f} ({drift_severity})")
            return ks_result
            
        except Exception as e:
            logger.error(f"KS drift detection failed for {feature_name}: {str(e)}")
            return {
                "feature_name": feature_name,
                "drift_type": "ks",
                "error": str(e),
                "detected_at": datetime.now().isoformat()
            }
    
    def detect_multivariate_drift(
        self,
        baseline_features: Dict[str, List[float]],
        current_features: Dict[str, List[float]]
    ) -> Dict[str, Any]:
        """
        Detect drift across multiple features.
        
        Args:
            baseline_features: Dictionary of baseline feature distributions
            current_features: Dictionary of current feature distributions
            
        Returns:
            Dictionary containing multivariate drift detection results
        """
        try:
            drift_results = {}
            overall_drift_severity = "no_drift"
            drift_count = 0
            
            # Check each feature
            for feature_name in baseline_features.keys():
                if feature_name not in current_features:
                    continue
                
                baseline_data = baseline_features[feature_name]
                current_data = current_features[feature_name]
                
                # Perform both PSI and KS tests
                psi_result = self.detect_psi_drift(baseline_data, current_data, feature_name)
                ks_result = self.detect_ks_drift(baseline_data, current_data, feature_name)
                
                drift_results[feature_name] = {
                    "psi": psi_result,
                    "ks": ks_result
                }
                
                # Track overall drift severity
                feature_drift = max(
                    self._drift_severity_to_score(psi_result.get("drift_severity", "no_drift")),
                    self._drift_severity_to_score(ks_result.get("drift_severity", "no_drift"))
                )
                
                if feature_drift > 0:
                    drift_count += 1
                    overall_drift_severity = self._score_to_drift_severity(
                        max(self._drift_severity_to_score(overall_drift_severity), feature_drift)
                    )
            
            multivariate_result = {
                "drift_type": "multivariate",
                "overall_drift_severity": overall_drift_severity,
                "features_with_drift": drift_count,
                "total_features": len(drift_results),
                "feature_results": drift_results,
                "detected_at": datetime.now().isoformat()
            }
            
            # Emit multivariate drift event if any drift detected
            if overall_drift_severity != "no_drift":
                self._emit_drift_event(multivariate_result)
            
            logger.info(f"Multivariate drift detection: {drift_count}/{len(drift_results)} features with drift ({overall_drift_severity})")
            return multivariate_result
            
        except Exception as e:
            logger.error(f"Multivariate drift detection failed: {str(e)}")
            return {
                "drift_type": "multivariate",
                "error": str(e),
                "detected_at": datetime.now().isoformat()
            }
    
    def update_baseline(
        self,
        feature_name: str,
        baseline_data: List[float]
    ) -> None:
        """
        Update baseline distribution for a feature.
        
        Args:
            feature_name: Name of the feature
            baseline_data: New baseline data
        """
        try:
            self.baseline_distributions[feature_name] = baseline_data.copy()
            logger.info(f"Updated baseline for feature {feature_name} with {len(baseline_data)} samples")
        except Exception as e:
            logger.error(f"Failed to update baseline for {feature_name}: {str(e)}")
    
    def _classify_psi_drift(self, psi_score: float) -> str:
        """Classify PSI drift severity."""
        thresholds = self.drift_thresholds["psi"]
        
        if psi_score < thresholds["no_drift"]:
            return "no_drift"
        elif psi_score < thresholds["minor_drift"]:
            return "minor_drift"
        elif psi_score < thresholds["major_drift"]:
            return "major_drift"
        else:
            return "critical_drift"
    
    def _classify_ks_drift(self, ks_statistic: float, p_value: float, significance_level: float) -> str:
        """Classify KS drift severity."""
        thresholds = self.drift_thresholds["ks"]
        
        # Check statistical significance
        if p_value > significance_level:
            return "no_drift"
        
        # Check magnitude of statistic
        if ks_statistic < thresholds["no_drift"]:
            return "minor_drift"
        elif ks_statistic < thresholds["minor_drift"]:
            return "major_drift"
        else:
            return "critical_drift"
    
    def _drift_severity_to_score(self, severity: str) -> int:
        """Convert drift severity to numeric score."""
        severity_scores = {
            "no_drift": 0,
            "minor_drift": 1,
            "major_drift": 2,
            "critical_drift": 3
        }
        return severity_scores.get(severity, 0)
    
    def _score_to_drift_severity(self, score: int) -> str:
        """Convert numeric score to drift severity."""
        score_to_severity = {
            0: "no_drift",
            1: "minor_drift",
            2: "major_drift",
            3: "critical_drift"
        }
        return score_to_severity.get(score, "no_drift")
    
    def _emit_drift_event(self, drift_result: Dict[str, Any]) -> None:
        """Emit CloudEvent for drift detection."""
        try:
            emit_processor_integration_event(
                "drift_detector",
                "drift_detected",
                {
                    "drift_type": drift_result.get("drift_type"),
                    "drift_severity": drift_result.get("drift_severity", drift_result.get("overall_drift_severity")),
                    "feature_name": drift_result.get("feature_name"),
                    "detection_details": drift_result,
                    "detected_at": drift_result.get("detected_at")
                }
            )
            logger.debug(f"Emitted drift detection event for {drift_result.get('feature_name', 'multivariate')}")
        except Exception as e:
            logger.error(f"Failed to emit drift event: {str(e)}")


class PerformanceDriftMonitor:
    """
    Monitors performance drift across payment processing metrics.
    
    Tracks key performance indicators and detects drift in
    approval rates, costs, settlement times, and other metrics.
    """
    
    def __init__(self):
        """Initialize the performance drift monitor."""
        self.drift_detector = DriftDetector()
        self.performance_baselines = {}
        logger.info("Performance drift monitor initialized")
    
    def monitor_performance_drift(
        self,
        performance_data: Dict[str, Any],
        time_window: str = "daily"
    ) -> Dict[str, Any]:
        """
        Monitor performance drift for payment processing.
        
        Args:
            performance_data: Current performance data
            time_window: Time window for drift detection (daily, weekly, monthly)
            
        Returns:
            Dictionary containing performance drift analysis
        """
        try:
            drift_results = {}
            
            # Monitor key performance metrics
            metrics_to_monitor = [
                "approval_rate",
                "avg_cost",
                "avg_settlement_time",
                "chargeback_rate",
                "customer_satisfaction"
            ]
            
            for metric in metrics_to_monitor:
                if metric in performance_data:
                    current_values = performance_data[metric]
                    
                    # Get baseline for this metric
                    baseline_key = f"{metric}_{time_window}"
                    baseline_values = self.performance_baselines.get(baseline_key, [])
                    
                    if baseline_values:
                        # Detect drift
                        drift_result = self.drift_detector.detect_psi_drift(
                            baseline_values, [current_values], metric
                        )
                        drift_results[metric] = drift_result
                    else:
                        # No baseline yet, store current value
                        drift_results[metric] = {
                            "feature_name": metric,
                            "drift_type": "psi",
                            "drift_severity": "no_baseline",
                            "message": "No baseline data available"
                        }
            
            # Determine overall performance drift
            overall_drift = self._assess_overall_performance_drift(drift_results)
            
            performance_drift_result = {
                "time_window": time_window,
                "monitoring_timestamp": datetime.now().isoformat(),
                "overall_drift_severity": overall_drift,
                "metric_results": drift_results,
                "performance_data": performance_data
            }
            
            logger.info(f"Performance drift monitoring completed: {overall_drift}")
            return performance_drift_result
            
        except Exception as e:
            logger.error(f"Performance drift monitoring failed: {str(e)}")
            return {
                "error": str(e),
                "time_window": time_window,
                "monitoring_timestamp": datetime.now().isoformat()
            }
    
    def update_performance_baseline(
        self,
        performance_data: Dict[str, Any],
        time_window: str = "daily"
    ) -> None:
        """
        Update performance baselines with new data.
        
        Args:
            performance_data: Performance data to add to baseline
            time_window: Time window for baseline (daily, weekly, monthly)
        """
        try:
            metrics_to_update = [
                "approval_rate",
                "avg_cost",
                "avg_settlement_time",
                "chargeback_rate",
                "customer_satisfaction"
            ]
            
            for metric in metrics_to_update:
                if metric in performance_data:
                    baseline_key = f"{metric}_{time_window}"
                    
                    if baseline_key not in self.performance_baselines:
                        self.performance_baselines[baseline_key] = []
                    
                    # Add current value to baseline
                    self.performance_baselines[baseline_key].append(performance_data[metric])
                    
                    # Keep only recent data (e.g., last 30 days for daily baseline)
                    max_baseline_size = 30 if time_window == "daily" else 12 if time_window == "weekly" else 12
                    if len(self.performance_baselines[baseline_key]) > max_baseline_size:
                        self.performance_baselines[baseline_key] = self.performance_baselines[baseline_key][-max_baseline_size:]
            
            logger.debug(f"Updated performance baselines for {time_window} window")
            
        except Exception as e:
            logger.error(f"Failed to update performance baseline: {str(e)}")
    
    def _assess_overall_performance_drift(self, drift_results: Dict[str, Any]) -> str:
        """Assess overall performance drift severity."""
        severity_scores = []
        
        for metric, result in drift_results.items():
            severity = result.get("drift_severity", "no_drift")
            severity_score = {
                "no_drift": 0,
                "no_baseline": 0,
                "minor_drift": 1,
                "major_drift": 2,
                "critical_drift": 3
            }.get(severity, 0)
            
            severity_scores.append(severity_score)
        
        if not severity_scores:
            return "no_drift"
        
        max_severity_score = max(severity_scores)
        
        severity_map = {
            0: "no_drift",
            1: "minor_drift",
            2: "major_drift",
            3: "critical_drift"
        }
        
        return severity_map.get(max_severity_score, "no_drift")


# Global instances
_drift_detector = None
_performance_drift_monitor = None


def get_drift_detector() -> DriftDetector:
    """Get global drift detector instance."""
    global _drift_detector
    if _drift_detector is None:
        _drift_detector = DriftDetector()
    return _drift_detector


def get_performance_drift_monitor() -> PerformanceDriftMonitor:
    """Get global performance drift monitor instance."""
    global _performance_drift_monitor
    if _performance_drift_monitor is None:
        _performance_drift_monitor = PerformanceDriftMonitor()
    return _performance_drift_monitor









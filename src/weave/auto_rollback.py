"""
Auto-Rollback System for Weave Phase 9.

Implements automated rollback when guardrails are breached,
creating PRs to Orca to reset DEFAULT_POLICY when performance
thresholds are violated.
"""

import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.weave.drift_detection import get_performance_drift_monitor
from src.weave.events import emit_processor_integration_event

logger = logging.getLogger(__name__)


class GuardrailBreachDetector:
    """
    Detects guardrail breaches in payment processing performance.
    
    Monitors key performance indicators and identifies when
    performance thresholds are violated, triggering rollback procedures.
    """
    
    def __init__(self):
        """Initialize the guardrail breach detector."""
        self.performance_drift_monitor = get_performance_drift_monitor()
        self.guardrail_thresholds = {
            "approval_rate": {
                "warning": 0.90,
                "critical": 0.85,
                "breach": 0.80
            },
            "avg_cost": {
                "warning": 50.0,  # $50
                "critical": 75.0,  # $75
                "breach": 100.0   # $100
            },
            "chargeback_rate": {
                "warning": 0.02,  # 2%
                "critical": 0.05,  # 5%
                "breach": 0.10    # 10%
            },
            "settlement_time": {
                "warning": 48.0,  # 48 hours
                "critical": 72.0,  # 72 hours
                "breach": 96.0    # 96 hours
            },
            "customer_satisfaction": {
                "warning": 0.7,   # 70%
                "critical": 0.6,   # 60%
                "breach": 0.5     # 50%
            }
        }
        self.breach_history = []
        logger.info("Guardrail breach detector initialized")
    
    def check_guardrail_breaches(
        self,
        performance_data: Dict[str, Any],
        time_window: str = "daily"
    ) -> Dict[str, Any]:
        """
        Check for guardrail breaches in performance data.
        
        Args:
            performance_data: Current performance data
            time_window: Time window for breach detection
            
        Returns:
            Dictionary containing breach detection results
        """
        try:
            breaches_detected = []
            warnings_detected = []
            critical_alerts = []
            
            # Check each guardrail metric
            for metric, thresholds in self.guardrail_thresholds.items():
                if metric not in performance_data:
                    continue
                
                current_value = performance_data[metric]
                
                # Check breach levels
                if current_value <= thresholds["breach"] if metric in ["approval_rate", "customer_satisfaction"] else current_value >= thresholds["breach"]:
                    breaches_detected.append({
                        "metric": metric,
                        "current_value": current_value,
                        "threshold": thresholds["breach"],
                        "severity": "breach",
                        "action_required": "immediate_rollback"
                    })
                elif current_value <= thresholds["critical"] if metric in ["approval_rate", "customer_satisfaction"] else current_value >= thresholds["critical"]:
                    critical_alerts.append({
                        "metric": metric,
                        "current_value": current_value,
                        "threshold": thresholds["critical"],
                        "severity": "critical",
                        "action_required": "rollback_preparation"
                    })
                elif current_value <= thresholds["warning"] if metric in ["approval_rate", "customer_satisfaction"] else current_value >= thresholds["warning"]:
                    warnings_detected.append({
                        "metric": metric,
                        "current_value": current_value,
                        "threshold": thresholds["warning"],
                        "severity": "warning",
                        "action_required": "monitor_closely"
                    })
            
            # Determine overall breach status
            overall_status = self._determine_overall_status(breaches_detected, critical_alerts, warnings_detected)
            
            breach_result = {
                "time_window": time_window,
                "check_timestamp": datetime.now().isoformat(),
                "overall_status": overall_status,
                "breaches_detected": breaches_detected,
                "critical_alerts": critical_alerts,
                "warnings_detected": warnings_detected,
                "performance_data": performance_data,
                "thresholds_used": self.guardrail_thresholds
            }
            
            # Store breach history
            self._store_breach_record(breach_result)
            
            # Emit breach detection event
            if overall_status in ["breach", "critical"]:
                self._emit_breach_event(breach_result)
            
            logger.info(f"Guardrail check completed: {overall_status} ({len(breaches_detected)} breaches, {len(critical_alerts)} critical, {len(warnings_detected)} warnings)")
            return breach_result
            
        except Exception as e:
            logger.error(f"Guardrail breach detection failed: {str(e)}")
            return {
                "error": str(e),
                "time_window": time_window,
                "check_timestamp": datetime.now().isoformat(),
                "overall_status": "error"
            }
    
    def _determine_overall_status(
        self,
        breaches: List[Dict[str, Any]],
        critical_alerts: List[Dict[str, Any]],
        warnings: List[Dict[str, Any]]
    ) -> str:
        """Determine overall breach status."""
        if breaches:
            return "breach"
        elif critical_alerts:
            return "critical"
        elif warnings:
            return "warning"
        else:
            return "healthy"
    
    def _store_breach_record(self, breach_result: Dict[str, Any]) -> None:
        """Store breach record in history."""
        breach_record = {
            "timestamp": breach_result["check_timestamp"],
            "status": breach_result["overall_status"],
            "breach_count": len(breach_result["breaches_detected"]),
            "critical_count": len(breach_result["critical_alerts"]),
            "warning_count": len(breach_result["warnings_detected"]),
            "performance_summary": {
                "approval_rate": breach_result["performance_data"].get("approval_rate", 0),
                "avg_cost": breach_result["performance_data"].get("avg_cost", 0),
                "chargeback_rate": breach_result["performance_data"].get("chargeback_rate", 0)
            }
        }
        
        self.breach_history.append(breach_record)
        
        # Keep only recent history (last 30 days)
        cutoff_date = datetime.now() - timedelta(days=30)
        self.breach_history = [
            record for record in self.breach_history
            if datetime.fromisoformat(record["timestamp"]) > cutoff_date
        ]
    
    def _emit_breach_event(self, breach_result: Dict[str, Any]) -> None:
        """Emit CloudEvent for guardrail breach."""
        try:
            emit_processor_integration_event(
                "guardrail_breach_detector",
                "guardrail_breach_detected",
                {
                    "overall_status": breach_result["overall_status"],
                    "breach_count": len(breach_result["breaches_detected"]),
                    "critical_count": len(breach_result["critical_alerts"]),
                    "warning_count": len(breach_result["warnings_detected"]),
                    "time_window": breach_result["time_window"],
                    "breach_details": breach_result["breaches_detected"],
                    "detected_at": breach_result["check_timestamp"]
                }
            )
            logger.debug(f"Emitted guardrail breach event: {breach_result['overall_status']}")
        except Exception as e:
            logger.error(f"Failed to emit breach event: {str(e)}")
    
    def get_breach_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent breach history."""
        cutoff_date = datetime.now() - timedelta(days=days)
        return [
            record for record in self.breach_history
            if datetime.fromisoformat(record["timestamp"]) > cutoff_date
        ]


class AutoRollbackManager:
    """
    Manages automated rollback procedures when guardrails are breached.
    
    Creates PRs to Orca to reset DEFAULT_POLICY and restore
    stable configuration when performance thresholds are violated.
    """
    
    def __init__(self, orca_repo_path: str = None):
        """
        Initialize the auto rollback manager.
        
        Args:
            orca_repo_path: Path to Orca repository for PR creation
        """
        self.breach_detector = GuardrailBreachDetector()
        self.orca_repo_path = orca_repo_path or "/path/to/orca"  # Default path
        logger.info("Auto rollback manager initialized")
    
    def trigger_rollback(
        self,
        breach_result: Dict[str, Any],
        rollback_reason: str = "Guardrail breach detected"
    ) -> Dict[str, Any]:
        """
        Trigger automated rollback procedure.
        
        Args:
            breach_result: Result from guardrail breach detection
            rollback_reason: Reason for rollback
            
        Returns:
            Dictionary containing rollback execution results
        """
        try:
            # Determine rollback scope
            rollback_scope = self._determine_rollback_scope(breach_result)
            
            # Generate rollback configuration
            rollback_config = self._generate_rollback_config(breach_result, rollback_scope)
            
            # Create rollback PR
            pr_result = self._create_rollback_pr(rollback_config, rollback_reason)
            
            # Execute immediate rollback if critical
            if breach_result["overall_status"] == "breach":
                immediate_rollback = self._execute_immediate_rollback(rollback_config)
            else:
                immediate_rollback = {"executed": False, "reason": "Not critical breach"}
            
            rollback_result = {
                "rollback_triggered": True,
                "trigger_timestamp": datetime.now().isoformat(),
                "breach_result": breach_result,
                "rollback_scope": rollback_scope,
                "rollback_config": rollback_config,
                "pr_result": pr_result,
                "immediate_rollback": immediate_rollback,
                "rollback_reason": rollback_reason
            }
            
            # Emit rollback event
            self._emit_rollback_event(rollback_result)
            
            logger.info(f"Rollback triggered for {breach_result['overall_status']} breach")
            return rollback_result
            
        except Exception as e:
            logger.error(f"Rollback execution failed: {str(e)}")
            return {
                "rollback_triggered": False,
                "error": str(e),
                "trigger_timestamp": datetime.now().isoformat()
            }
    
    def _determine_rollback_scope(self, breach_result: Dict[str, Any]) -> Dict[str, Any]:
        """Determine the scope of rollback based on breach severity."""
        breaches = breach_result["breaches_detected"]
        critical_alerts = breach_result["critical_alerts"]
        
        # Determine affected metrics
        affected_metrics = set()
        for breach in breaches + critical_alerts:
            affected_metrics.add(breach["metric"])
        
        # Determine rollback scope
        if "approval_rate" in affected_metrics:
            scope = "full_policy_rollback"
            description = "Full policy rollback due to approval rate breach"
        elif "chargeback_rate" in affected_metrics:
            scope = "risk_policy_rollback"
            description = "Risk policy rollback due to chargeback rate breach"
        elif "avg_cost" in affected_metrics:
            scope = "cost_policy_rollback"
            description = "Cost policy rollback due to cost threshold breach"
        else:
            scope = "selective_rollback"
            description = "Selective rollback for specific metrics"
        
        return {
            "scope_type": scope,
            "description": description,
            "affected_metrics": list(affected_metrics),
            "rollback_severity": breach_result["overall_status"]
        }
    
    def _generate_rollback_config(
        self,
        breach_result: Dict[str, Any],
        rollback_scope: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate rollback configuration."""
        return {
            "rollback_id": f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "trigger_reason": "guardrail_breach",
            "breach_details": breach_result,
            "rollback_scope": rollback_scope,
            "target_configuration": self._get_target_configuration(rollback_scope),
            "rollback_steps": self._define_rollback_steps(rollback_scope),
            "validation_criteria": self._define_validation_criteria(breach_result),
            "created_at": datetime.now().isoformat()
        }
    
    def _get_target_configuration(self, rollback_scope: Dict[str, Any]) -> Dict[str, Any]:
        """Get target configuration for rollback."""
        scope_type = rollback_scope["scope_type"]
        
        if scope_type == "full_policy_rollback":
            return {
                "DEFAULT_POLICY": "conservative",
                "approval_threshold": 0.95,
                "cost_threshold": 25.0,
                "risk_threshold": 0.3,
                "settlement_time_limit": 24.0
            }
        elif scope_type == "risk_policy_rollback":
            return {
                "DEFAULT_POLICY": "risk_averse",
                "approval_threshold": 0.98,
                "risk_threshold": 0.2,
                "chargeback_threshold": 0.01
            }
        elif scope_type == "cost_policy_rollback":
            return {
                "DEFAULT_POLICY": "cost_optimized",
                "cost_threshold": 20.0,
                "settlement_time_limit": 48.0
            }
        else:
            return {
                "DEFAULT_POLICY": "stable",
                "conservative_mode": True
            }
    
    def _define_rollback_steps(self, rollback_scope: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Define rollback execution steps."""
        return [
            {
                "step": 1,
                "action": "backup_current_config",
                "description": "Backup current configuration"
            },
            {
                "step": 2,
                "action": "update_default_policy",
                "description": f"Update DEFAULT_POLICY to {rollback_scope['scope_type']}"
            },
            {
                "step": 3,
                "action": "validate_configuration",
                "description": "Validate new configuration"
            },
            {
                "step": 4,
                "action": "deploy_changes",
                "description": "Deploy configuration changes"
            },
            {
                "step": 5,
                "action": "monitor_performance",
                "description": "Monitor performance post-rollback"
            }
        ]
    
    def _define_validation_criteria(self, breach_result: Dict[str, Any]) -> Dict[str, Any]:
        """Define validation criteria for rollback success."""
        return {
            "approval_rate_threshold": 0.90,
            "cost_threshold": 50.0,
            "chargeback_rate_threshold": 0.02,
            "settlement_time_threshold": 48.0,
            "validation_period_hours": 24,
            "success_criteria": "all_metrics_within_thresholds"
        }
    
    def _create_rollback_pr(
        self,
        rollback_config: Dict[str, Any],
        rollback_reason: str
    ) -> Dict[str, Any]:
        """Create PR for rollback configuration changes."""
        try:
            # Generate PR content
            pr_title = f"Auto-Rollback: {rollback_config['rollback_id']}"
            pr_description = self._generate_rollback_pr_description(rollback_config, rollback_reason)
            
            # Create configuration changes
            config_changes = self._generate_config_changes(rollback_config)
            
            # Simulate PR creation (in production, use Git API)
            pr_result = self._simulate_pr_creation(pr_title, pr_description, config_changes)
            
            logger.info(f"Created rollback PR: {pr_result.get('pr_number')}")
            return pr_result
            
        except Exception as e:
            logger.error(f"Failed to create rollback PR: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "created_at": datetime.now().isoformat()
            }
    
    def _generate_rollback_pr_description(
        self,
        rollback_config: Dict[str, Any],
        rollback_reason: str
    ) -> str:
        """Generate PR description for rollback."""
        breach_details = rollback_config["breach_details"]
        rollback_scope = rollback_config["rollback_scope"]
        
        description = f"""## Auto-Rollback: {rollback_config['rollback_id']}

**Automated rollback triggered due to guardrail breach**

### Breach Details
- **Overall Status**: {breach_details['overall_status']}
- **Breaches Detected**: {len(breach_details['breaches_detected'])}
- **Critical Alerts**: {len(breach_details['critical_alerts'])}
- **Warnings**: {len(breach_details['warnings_detected'])}

### Affected Metrics
"""
        
        for breach in breach_details["breaches_detected"]:
            description += f"- **{breach['metric']}**: {breach['current_value']} (threshold: {breach['threshold']})\n"
        
        description += f"""
### Rollback Scope
- **Type**: {rollback_scope['scope_type']}
- **Description**: {rollback_scope['description']}
- **Affected Metrics**: {', '.join(rollback_scope['affected_metrics'])}

### Target Configuration
"""
        
        target_config = rollback_config["target_configuration"]
        for key, value in target_config.items():
            description += f"- **{key}**: {value}\n"
        
        description += f"""
### Rollback Reason
{rollback_reason}

### Validation Criteria
- **Approval Rate**: ≥ {rollback_config['validation_criteria']['approval_rate_threshold']:.0%}
- **Cost Threshold**: ≤ ${rollback_config['validation_criteria']['cost_threshold']}
- **Chargeback Rate**: ≤ {rollback_config['validation_criteria']['chargeback_rate_threshold']:.1%}
- **Settlement Time**: ≤ {rollback_config['validation_criteria']['settlement_time_threshold']} hours
- **Validation Period**: {rollback_config['validation_criteria']['validation_period_hours']} hours

---
*This rollback was automatically triggered by the guardrail breach detection system.*
"""
        
        return description
    
    def _generate_config_changes(self, rollback_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate configuration changes for the PR."""
        return {
            "file_changes": {
                "src/orca_core/config.py": {
                    "DEFAULT_POLICY": rollback_config["target_configuration"]["DEFAULT_POLICY"]
                }
            },
            "rollback_metadata": {
                "rollback_id": rollback_config["rollback_id"],
                "trigger_timestamp": rollback_config["created_at"],
                "breach_details": rollback_config["breach_details"],
                "validation_criteria": rollback_config["validation_criteria"]
            }
        }
    
    def _simulate_pr_creation(
        self,
        pr_title: str,
        pr_description: str,
        config_changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate PR creation (in production, use Git API)."""
        return {
            "success": True,
            "pr_number": f"ROLLBACK-{int(datetime.now().timestamp())}",
            "pr_title": pr_title,
            "pr_url": f"https://github.com/example/orca/pull/{int(datetime.now().timestamp())}",
            "config_changes": config_changes,
            "created_at": datetime.now().isoformat()
        }
    
    def _execute_immediate_rollback(self, rollback_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute immediate rollback for critical breaches."""
        try:
            # In production, this would update configuration immediately
            # For demo, simulate immediate rollback
            return {
                "executed": True,
                "rollback_id": rollback_config["rollback_id"],
                "execution_time": datetime.now().isoformat(),
                "status": "completed",
                "message": "Immediate rollback executed successfully"
            }
        except Exception as e:
            return {
                "executed": False,
                "error": str(e),
                "execution_time": datetime.now().isoformat()
            }
    
    def _emit_rollback_event(self, rollback_result: Dict[str, Any]) -> None:
        """Emit CloudEvent for rollback execution."""
        try:
            emit_processor_integration_event(
                "auto_rollback_manager",
                "rollback_executed",
                {
                    "rollback_id": rollback_result.get("rollback_config", {}).get("rollback_id"),
                    "rollback_scope": rollback_result.get("rollback_scope", {}).get("scope_type"),
                    "breach_status": rollback_result.get("breach_result", {}).get("overall_status"),
                    "pr_number": rollback_result.get("pr_result", {}).get("pr_number"),
                    "immediate_rollback": rollback_result.get("immediate_rollback", {}).get("executed"),
                    "triggered_at": rollback_result.get("trigger_timestamp")
                }
            )
            logger.debug(f"Emitted rollback event for {rollback_result.get('rollback_config', {}).get('rollback_id')}")
        except Exception as e:
            logger.error(f"Failed to emit rollback event: {str(e)}")


class AutoRollbackOrchestrator:
    """
    Orchestrates the complete auto-rollback process.
    
    Coordinates guardrail monitoring, breach detection, and
    automated rollback execution for the learning loop system.
    """
    
    def __init__(self):
        """Initialize the auto rollback orchestrator."""
        self.breach_detector = GuardrailBreachDetector()
        self.rollback_manager = AutoRollbackManager()
        logger.info("Auto rollback orchestrator initialized")
    
    def monitor_and_rollback(
        self,
        performance_data: Dict[str, Any],
        time_window: str = "daily"
    ) -> Dict[str, Any]:
        """
        Monitor performance and trigger rollback if needed.
        
        Args:
            performance_data: Current performance data
            time_window: Time window for monitoring
            
        Returns:
            Dictionary containing monitoring and rollback results
        """
        try:
            # Check for guardrail breaches
            breach_result = self.breach_detector.check_guardrail_breaches(
                performance_data, time_window
            )
            
            # Trigger rollback if breaches detected
            rollback_result = None
            if breach_result["overall_status"] in ["breach", "critical"]:
                rollback_reason = f"Guardrail breach detected: {breach_result['overall_status']}"
                rollback_result = self.rollback_manager.trigger_rollback(
                    breach_result, rollback_reason
                )
            
            monitoring_result = {
                "monitoring_timestamp": datetime.now().isoformat(),
                "time_window": time_window,
                "breach_detection": breach_result,
                "rollback_execution": rollback_result,
                "action_taken": "rollback_triggered" if rollback_result else "monitoring_only"
            }
            
            logger.info(f"Monitoring completed: {monitoring_result['action_taken']}")
            return monitoring_result
            
        except Exception as e:
            logger.error(f"Monitoring and rollback failed: {str(e)}")
            return {
                "error": str(e),
                "monitoring_timestamp": datetime.now().isoformat(),
                "action_taken": "error"
            }
    
    def get_system_health_status(self) -> Dict[str, Any]:
        """Get overall system health status."""
        try:
            recent_breaches = self.breach_detector.get_breach_history(days=7)
            
            # Analyze recent breach patterns
            breach_counts = {"healthy": 0, "warning": 0, "critical": 0, "breach": 0}
            for breach in recent_breaches:
                status = breach["status"]
                if status in breach_counts:
                    breach_counts[status] += 1
            
            # Determine overall health
            if breach_counts["breach"] > 0:
                health_status = "critical"
            elif breach_counts["critical"] > 2:
                health_status = "degraded"
            elif breach_counts["warning"] > 5:
                health_status = "warning"
            else:
                health_status = "healthy"
            
            return {
                "overall_health": health_status,
                "recent_breaches": recent_breaches,
                "breach_counts": breach_counts,
                "last_check": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get system health status: {str(e)}")
            return {
                "overall_health": "error",
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }


# Global instance
_auto_rollback_orchestrator = None


def get_auto_rollback_orchestrator() -> AutoRollbackOrchestrator:
    """Get global auto rollback orchestrator instance."""
    global _auto_rollback_orchestrator
    if _auto_rollback_orchestrator is None:
        _auto_rollback_orchestrator = AutoRollbackOrchestrator()
    return _auto_rollback_orchestrator









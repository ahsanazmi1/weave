"""
Nightly Learning Jobs for Weave Phase 9.

Implements nightly rewards aggregation, auto PR promotion, and
performance scorecard generation for the learning loop.
"""

import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.weave.outcomes_tracker import get_outcomes_ingester
from src.weave.events import emit_processor_integration_event

logger = logging.getLogger(__name__)


class RewardAggregator:
    """
    Aggregates rewards by variant for learning loop optimization.
    
    Processes daily reward data to identify high-performing variants
    and prepare them for promotion via automated PRs.
    """
    
    def __init__(self):
        """Initialize the reward aggregator."""
        self.outcomes_ingester = get_outcomes_ingester()
        logger.info("Reward aggregator initialized")
    
    def aggregate_daily_rewards(
        self,
        date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Aggregate rewards for a specific date.
        
        Args:
            date: Date to aggregate rewards for (defaults to yesterday)
            
        Returns:
            Dictionary containing aggregated reward data
        """
        try:
            if date is None:
                date = datetime.now() - timedelta(days=1)
            
            start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)
            
            # Get all outcomes for the date
            all_outcomes = self._get_outcomes_for_date_range(start_time, end_time)
            
            # Group outcomes by variant (cohort + processor combination)
            variant_rewards = self._group_rewards_by_variant(all_outcomes)
            
            # Calculate variant performance metrics
            variant_performance = self._calculate_variant_performance(variant_rewards)
            
            # Identify promotion candidates
            promotion_candidates = self._identify_promotion_candidates(variant_performance)
            
            aggregation_result = {
                "aggregation_date": date.isoformat(),
                "date_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "total_transactions": len(all_outcomes),
                "total_variants": len(variant_rewards),
                "variant_performance": variant_performance,
                "promotion_candidates": promotion_candidates,
                "aggregation_metadata": {
                    "processed_at": datetime.now().isoformat(),
                    "aggregation_version": "1.0"
                }
            }
            
            logger.info(f"Aggregated rewards for {date.date()}: {len(all_outcomes)} transactions, {len(variant_rewards)} variants")
            return aggregation_result
            
        except Exception as e:
            logger.error(f"Failed to aggregate daily rewards: {str(e)}")
            return {
                "error": str(e),
                "aggregation_date": date.isoformat() if date else None,
                "processed_at": datetime.now().isoformat()
            }
    
    def _get_outcomes_for_date_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """Get all outcomes within a date range."""
        outcomes = []
        
        # This would typically query a database
        # For demo, we'll use the in-memory storage
        for outcome in self.outcomes_ingester.outcome_storage.values():
            outcome_time = datetime.fromisoformat(outcome.get("timestamp", ""))
            if start_time <= outcome_time < end_time:
                outcomes.append(outcome)
        
        return outcomes
    
    def _group_rewards_by_variant(
        self,
        outcomes: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group outcomes by variant (cohort + processor combination)."""
        variant_groups = {}
        
        for outcome in outcomes:
            cohort_id = outcome.get("cohort_id", "unknown")
            processor_id = outcome.get("payment_data", {}).get("processor_id", "unknown")
            variant_id = f"{cohort_id}_{processor_id}"
            
            if variant_id not in variant_groups:
                variant_groups[variant_id] = []
            
            variant_groups[variant_id].append(outcome)
        
        return variant_groups
    
    def _calculate_variant_performance(
        self,
        variant_rewards: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate performance metrics for each variant."""
        variant_performance = {}
        
        for variant_id, outcomes in variant_rewards.items():
            # Separate t0 and tx outcomes
            t0_outcomes = [o for o in outcomes if o.get("outcome_type") == "t0_immediate"]
            tx_outcomes = [o for o in outcomes if o.get("outcome_type") == "tx_settled"]
            
            # Calculate metrics
            performance = {
                "variant_id": variant_id,
                "transaction_count": len(t0_outcomes),
                "settlement_count": len(tx_outcomes),
                "approval_rate": self._calculate_approval_rate(t0_outcomes),
                "avg_processing_time_ms": self._calculate_avg_processing_time(t0_outcomes),
                "avg_settlement_time_hours": self._calculate_avg_settlement_time(tx_outcomes),
                "avg_cost": self._calculate_avg_cost(tx_outcomes),
                "chargeback_rate": self._calculate_chargeback_rate(tx_outcomes),
                "customer_satisfaction": self._calculate_customer_satisfaction(tx_outcomes),
                "risk_score": self._calculate_risk_score(tx_outcomes),
                "total_reward": self._calculate_total_reward(outcomes),
                "confidence_score": self._calculate_confidence_score(outcomes)
            }
            
            variant_performance[variant_id] = performance
        
        return variant_performance
    
    def _identify_promotion_candidates(
        self,
        variant_performance: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify variants that should be promoted to production."""
        promotion_candidates = []
        
        for variant_id, performance in variant_performance.items():
            # Promotion criteria
            if (performance["transaction_count"] >= 10 and  # Minimum sample size
                performance["approval_rate"] >= 0.90 and    # High approval rate
                performance["confidence_score"] >= 0.8 and  # High confidence
                performance["chargeback_rate"] <= 0.02):    # Low chargeback rate
                
                promotion_candidates.append({
                    "variant_id": variant_id,
                    "performance": performance,
                    "promotion_reason": "Meets all promotion criteria",
                    "promotion_priority": self._calculate_promotion_priority(performance)
                })
        
        # Sort by promotion priority
        promotion_candidates.sort(key=lambda x: x["promotion_priority"], reverse=True)
        
        return promotion_candidates
    
    def _calculate_promotion_priority(self, performance: Dict[str, Any]) -> float:
        """Calculate promotion priority score."""
        # Weighted scoring based on key metrics
        score = (
            performance["approval_rate"] * 0.3 +
            (1 - performance["avg_cost"] / 100) * 0.2 +  # Lower cost is better
            (1 - performance["avg_settlement_time_hours"] / 168) * 0.2 +  # Faster is better
            performance["customer_satisfaction"] * 0.2 +
            performance["confidence_score"] * 0.1
        )
        return min(1.0, max(0.0, score))
    
    # Helper methods for calculating metrics
    def _calculate_approval_rate(self, t0_outcomes: List[Dict[str, Any]]) -> float:
        if not t0_outcomes:
            return 0.0
        approved_count = sum(
            1 for outcome in t0_outcomes
            if outcome.get("auth_result", {}).get("status") == "approved"
        )
        return approved_count / len(t0_outcomes)
    
    def _calculate_avg_processing_time(self, t0_outcomes: List[Dict[str, Any]]) -> float:
        if not t0_outcomes:
            return 0.0
        processing_times = [
            outcome.get("immediate_metrics", {}).get("processing_time_ms", 0)
            for outcome in t0_outcomes
        ]
        return sum(processing_times) / len(processing_times) if processing_times else 0.0
    
    def _calculate_avg_settlement_time(self, tx_outcomes: List[Dict[str, Any]]) -> float:
        if not tx_outcomes:
            return 0.0
        settlement_times = [
            outcome.get("final_metrics", {}).get("settlement_time_hours", 0)
            for outcome in tx_outcomes
        ]
        return sum(settlement_times) / len(settlement_times) if settlement_times else 0.0
    
    def _calculate_avg_cost(self, tx_outcomes: List[Dict[str, Any]]) -> float:
        if not tx_outcomes:
            return 0.0
        costs = [
            outcome.get("final_metrics", {}).get("actual_cost", 0.0)
            for outcome in tx_outcomes
        ]
        return sum(costs) / len(costs) if costs else 0.0
    
    def _calculate_chargeback_rate(self, tx_outcomes: List[Dict[str, Any]]) -> float:
        if not tx_outcomes:
            return 0.0
        chargeback_count = sum(
            outcome.get("final_metrics", {}).get("chargeback_count", 0)
            for outcome in tx_outcomes
        )
        return chargeback_count / len(tx_outcomes)
    
    def _calculate_customer_satisfaction(self, tx_outcomes: List[Dict[str, Any]]) -> float:
        if not tx_outcomes:
            return 0.0
        ratings = [
            outcome.get("final_metrics", {}).get("customer_rating")
            for outcome in tx_outcomes
            if outcome.get("final_metrics", {}).get("customer_rating") is not None
        ]
        return sum(ratings) / len(ratings) if ratings else 0.0
    
    def _calculate_risk_score(self, tx_outcomes: List[Dict[str, Any]]) -> float:
        if not tx_outcomes:
            return 0.0
        risk_scores = [
            outcome.get("immediate_metrics", {}).get("risk_score", 0.5)
            for outcome in tx_outcomes
        ]
        return sum(risk_scores) / len(risk_scores) if risk_scores else 0.5
    
    def _calculate_total_reward(self, outcomes: List[Dict[str, Any]]) -> float:
        """Calculate total reward for a variant."""
        # This would integrate with the reward function from Orca
        # For now, use a simplified calculation
        total_reward = 0.0
        for outcome in outcomes:
            if outcome.get("outcome_type") == "tx_settled":
                # Simplified reward calculation
                approval_bonus = 1.0 if outcome.get("final_metrics", {}).get("success", True) else 0.0
                cost_penalty = outcome.get("final_metrics", {}).get("actual_cost", 0.0) / 100.0
                speed_bonus = max(0, 1.0 - outcome.get("final_metrics", {}).get("settlement_time_hours", 24) / 168.0)
                
                reward = approval_bonus - cost_penalty + speed_bonus
                total_reward += max(0.0, reward)
        
        return total_reward
    
    def _calculate_confidence_score(self, outcomes: List[Dict[str, Any]]) -> float:
        """Calculate confidence score based on sample size and consistency."""
        if not outcomes:
            return 0.0
        
        sample_size = len(outcomes)
        consistency_score = 1.0 - self._calculate_variance(outcomes) / sample_size
        
        # Confidence increases with sample size (up to a point)
        sample_confidence = min(1.0, sample_size / 100.0)
        
        return (consistency_score + sample_confidence) / 2.0
    
    def _calculate_variance(self, outcomes: List[Dict[str, Any]]) -> float:
        """Calculate variance in outcomes (simplified)."""
        if len(outcomes) <= 1:
            return 0.0
        
        # Calculate variance in approval rates
        approval_rates = []
        for outcome in outcomes:
            if outcome.get("outcome_type") == "t0_immediate":
                is_approved = outcome.get("auth_result", {}).get("status") == "approved"
                approval_rates.append(1.0 if is_approved else 0.0)
        
        if not approval_rates:
            return 0.0
        
        mean_approval = sum(approval_rates) / len(approval_rates)
        variance = sum((rate - mean_approval) ** 2 for rate in approval_rates) / len(approval_rates)
        
        return variance


class AutoPRPromoter:
    """
    Automatically creates PRs to promote high-performing variants.
    
    Integrates with Git to create pull requests that promote successful
    variants from shadow mode to production configuration.
    """
    
    def __init__(self, repo_path: str = None):
        """
        Initialize the auto PR promoter.
        
        Args:
            repo_path: Path to the Git repository (defaults to current directory)
        """
        self.repo_path = repo_path or os.getcwd()
        logger.info(f"Auto PR promoter initialized for repo: {self.repo_path}")
    
    def create_promotion_pr(
        self,
        promotion_candidate: Dict[str, Any],
        aggregation_date: str
    ) -> Dict[str, Any]:
        """
        Create a PR to promote a high-performing variant.
        
        Args:
            promotion_candidate: Candidate variant to promote
            aggregation_date: Date of the aggregation that identified this candidate
            
        Returns:
            Dictionary containing PR creation results
        """
        try:
            variant_id = promotion_candidate["variant_id"]
            performance = promotion_candidate["performance"]
            
            # Create branch name
            branch_name = f"promote-variant-{variant_id}-{datetime.now().strftime('%Y%m%d')}"
            
            # Create PR content
            pr_title = f"Promote Variant: {variant_id}"
            pr_description = self._generate_pr_description(promotion_candidate, aggregation_date)
            
            # Create configuration changes
            config_changes = self._generate_config_changes(variant_id, performance)
            
            # Create the PR (simulated for demo)
            pr_result = self._simulate_pr_creation(
                branch_name, pr_title, pr_description, config_changes
            )
            
            # Emit integration event
            emit_processor_integration_event(
                "auto_pr_promoter",
                "promotion_pr_created",
                {
                    "variant_id": variant_id,
                    "branch_name": branch_name,
                    "pr_number": pr_result.get("pr_number"),
                    "aggregation_date": aggregation_date
                }
            )
            
            logger.info(f"Created promotion PR for variant {variant_id}: {pr_result.get('pr_number')}")
            return pr_result
            
        except Exception as e:
            logger.error(f"Failed to create promotion PR: {str(e)}")
            return {
                "error": str(e),
                "variant_id": promotion_candidate.get("variant_id"),
                "created_at": datetime.now().isoformat()
            }
    
    def _generate_pr_description(
        self,
        promotion_candidate: Dict[str, Any],
        aggregation_date: str
    ) -> str:
        """Generate PR description for variant promotion."""
        performance = promotion_candidate["performance"]
        
        description = f"""## Variant Promotion: {promotion_candidate['variant_id']}

**Automated promotion based on nightly learning aggregation ({aggregation_date})**

### Performance Metrics
- **Transaction Count**: {performance['transaction_count']}
- **Approval Rate**: {performance['approval_rate']:.2%}
- **Average Cost**: ${performance['avg_cost']:.2f}
- **Settlement Time**: {performance['avg_settlement_time_hours']:.1f} hours
- **Chargeback Rate**: {performance['chargeback_rate']:.2%}
- **Customer Satisfaction**: {performance['customer_satisfaction']:.2f}
- **Confidence Score**: {performance['confidence_score']:.2f}

### Promotion Reason
{promotion_candidate['promotion_reason']}

### Changes
This PR promotes the variant from shadow mode to production configuration based on:
- High approval rate (≥90%)
- Low chargeback rate (≤2%)
- Sufficient sample size (≥10 transactions)
- High confidence score (≥0.8)

### Risk Assessment
- **Risk Score**: {performance['risk_score']:.2f}
- **Promotion Priority**: {promotion_candidate['promotion_priority']:.2f}

---
*This PR was automatically generated by the learning loop system.*
"""
        
        return description
    
    def _generate_config_changes(
        self,
        variant_id: str,
        performance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate configuration changes for variant promotion."""
        return {
            "variant_id": variant_id,
            "promotion_config": {
                "shadow_mode": False,
                "production_weight": 0.1,  # Start with 10% traffic
                "rollback_threshold": 0.85,  # Rollback if approval rate drops below 85%
                "monitoring_enabled": True,
                "promotion_date": datetime.now().isoformat()
            },
            "performance_baseline": {
                "approval_rate": performance["approval_rate"],
                "avg_cost": performance["avg_cost"],
                "avg_settlement_time": performance["avg_settlement_time_hours"],
                "chargeback_rate": performance["chargeback_rate"]
            }
        }
    
    def _simulate_pr_creation(
        self,
        branch_name: str,
        pr_title: str,
        pr_description: str,
        config_changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate PR creation (in production, this would use Git API)."""
        # This would integrate with GitHub/GitLab API
        # For demo, return simulated result
        return {
            "success": True,
            "pr_number": f"PR-{int(datetime.now().timestamp())}",
            "branch_name": branch_name,
            "pr_title": pr_title,
            "pr_url": f"https://github.com/example/repo/pull/{int(datetime.now().timestamp())}",
            "created_at": datetime.now().isoformat(),
            "config_changes": config_changes
        }


class NightlyLearningJobRunner:
    """
    Orchestrates nightly learning jobs including aggregation and promotion.
    
    Runs comprehensive nightly analysis of learning loop performance
    and automatically promotes high-performing variants.
    """
    
    def __init__(self):
        """Initialize the nightly learning job runner."""
        self.reward_aggregator = RewardAggregator()
        self.auto_pr_promoter = AutoPRPromoter()
        logger.info("Nightly learning job runner initialized")
    
    def run_nightly_jobs(
        self,
        date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Run complete nightly learning jobs.
        
        Args:
            date: Date to process (defaults to yesterday)
            
        Returns:
            Dictionary containing nightly job results
        """
        try:
            if date is None:
                date = datetime.now() - timedelta(days=1)
            
            logger.info(f"Starting nightly learning jobs for {date.date()}")
            
            # Step 1: Aggregate daily rewards
            aggregation_result = self.reward_aggregator.aggregate_daily_rewards(date)
            
            if aggregation_result.get("error"):
                logger.error(f"Reward aggregation failed: {aggregation_result['error']}")
                return aggregation_result
            
            # Step 2: Create promotion PRs for high-performing variants
            promotion_results = []
            promotion_candidates = aggregation_result.get("promotion_candidates", [])
            
            for candidate in promotion_candidates[:3]:  # Limit to top 3 candidates
                pr_result = self.auto_pr_promoter.create_promotion_pr(
                    candidate, date.isoformat()
                )
                promotion_results.append(pr_result)
            
            # Step 3: Generate nightly report
            nightly_report = self._generate_nightly_report(
                aggregation_result, promotion_results, date
            )
            
            # Step 4: Emit completion event
            emit_processor_integration_event(
                "nightly_learning_jobs",
                "nightly_jobs_completed",
                {
                    "date": date.isoformat(),
                    "total_variants": aggregation_result.get("total_variants", 0),
                    "promotion_candidates": len(promotion_candidates),
                    "prs_created": len(promotion_results)
                }
            )
            
            nightly_jobs_result = {
                "date": date.isoformat(),
                "aggregation_result": aggregation_result,
                "promotion_results": promotion_results,
                "nightly_report": nightly_report,
                "completed_at": datetime.now().isoformat(),
                "success": True
            }
            
            logger.info(f"Completed nightly learning jobs for {date.date()}")
            return nightly_jobs_result
            
        except Exception as e:
            logger.error(f"Nightly learning jobs failed: {str(e)}")
            return {
                "date": date.isoformat() if date else None,
                "error": str(e),
                "completed_at": datetime.now().isoformat(),
                "success": False
            }
    
    def _generate_nightly_report(
        self,
        aggregation_result: Dict[str, Any],
        promotion_results: List[Dict[str, Any]],
        date: datetime
    ) -> Dict[str, Any]:
        """Generate comprehensive nightly report."""
        return {
            "report_date": date.isoformat(),
            "summary": {
                "total_transactions": aggregation_result.get("total_transactions", 0),
                "total_variants": aggregation_result.get("total_variants", 0),
                "promotion_candidates": len(aggregation_result.get("promotion_candidates", [])),
                "prs_created": len(promotion_results),
                "successful_prs": len([pr for pr in promotion_results if pr.get("success", False)])
            },
            "top_performers": self._get_top_performers(aggregation_result),
            "recommendations": self._generate_recommendations(aggregation_result),
            "generated_at": datetime.now().isoformat()
        }
    
    def _get_top_performers(
        self,
        aggregation_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get top performing variants."""
        variant_performance = aggregation_result.get("variant_performance", {})
        
        # Sort by total reward
        sorted_variants = sorted(
            variant_performance.values(),
            key=lambda x: x.get("total_reward", 0),
            reverse=True
        )
        
        return sorted_variants[:5]  # Top 5 performers
    
    def _generate_recommendations(
        self,
        aggregation_result: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on aggregation results."""
        recommendations = []
        
        variant_performance = aggregation_result.get("variant_performance", {})
        total_transactions = aggregation_result.get("total_transactions", 0)
        
        if total_transactions < 100:
            recommendations.append("Consider increasing transaction volume for better statistical significance")
        
        low_performance_variants = [
            v for v in variant_performance.values()
            if v.get("approval_rate", 0) < 0.85
        ]
        
        if len(low_performance_variants) > 0:
            recommendations.append(f"Review {len(low_performance_variants)} low-performing variants for potential rollback")
        
        high_cost_variants = [
            v for v in variant_performance.values()
            if v.get("avg_cost", 0) > 50.0
        ]
        
        if len(high_cost_variants) > 0:
            recommendations.append(f"Investigate {len(high_cost_variants)} high-cost variants for optimization opportunities")
        
        return recommendations


# Global instance
_nightly_learning_jobs = None


def get_nightly_learning_jobs() -> NightlyLearningJobRunner:
    """Get global nightly learning jobs runner instance."""
    global _nightly_learning_jobs
    if _nightly_learning_jobs is None:
        _nightly_learning_jobs = NightlyLearningJobRunner()
    return _nightly_learning_jobs









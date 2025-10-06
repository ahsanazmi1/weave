"""
Nightly jobs for Weave Phase 4.

Provides automated nightly aggregation of rewards per variant, scorecard generation,
and comprehensive reporting for payment processor performance analysis.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from weave.models import RewardVariant, Scorecard, SignedReceipt

logger = logging.getLogger(__name__)


class RewardAggregator:
    """
    Reward aggregation service for nightly scorecard generation.
    
    Aggregates transaction data by processor, rail type, and reward variant
    to generate comprehensive performance metrics.
    """
    
    def __init__(self):
        """Initialize reward aggregator."""
        logger.info("Reward aggregator initialized")
    
    def aggregate_rewards_by_variant(
        self,
        receipts: List[SignedReceipt],
        date: datetime
    ) -> List[RewardVariant]:
        """
        Aggregate rewards by variant for a specific date.
        
        Args:
            receipts: Signed receipts to aggregate
            date: Date for aggregation
            
        Returns:
            List of reward variants with aggregated metrics
        """
        # Group receipts by variant key (processor + rail + reward_type)
        variant_groups = {}
        
        for receipt in receipts:
            # Extract variant information
            processor_id = receipt.processor_auth_result.processor_id
            rail_type = receipt.payment_instruction.selected_rail
            reward_type = self._determine_reward_type(receipt)
            
            variant_key = f"{processor_id}_{rail_type}_{reward_type}"
            
            if variant_key not in variant_groups:
                variant_groups[variant_key] = {
                    "receipts": [],
                    "processor_id": processor_id,
                    "rail_type": rail_type,
                    "reward_type": reward_type
                }
            
            variant_groups[variant_key]["receipts"].append(receipt)
        
        # Calculate metrics for each variant
        variants = []
        for variant_key, group in variant_groups.items():
            variant = self._calculate_variant_metrics(
                variant_key, group["receipts"], group["processor_id"],
                group["rail_type"], group["reward_type"]
            )
            variants.append(variant)
        
        logger.info(f"Aggregated {len(variants)} reward variants from {len(receipts)} receipts")
        return variants
    
    def _determine_reward_type(self, receipt: SignedReceipt) -> str:
        """Determine reward type from receipt data."""
        # Analyze receipt to determine reward type
        if receipt.processor_auth_result.processor_fee < 0:
            return "rebate"
        elif receipt.payment_instruction.effective_cost < 50:  # Low cost
            return "discount"
        elif receipt.processor_auth_result.settlement_time_actual < 24:  # Fast settlement
            return "speed_bonus"
        else:
            return "standard"
    
    def _calculate_variant_metrics(
        self,
        variant_key: str,
        receipts: List[SignedReceipt],
        processor_id: str,
        rail_type: str,
        reward_type: str
    ) -> RewardVariant:
        """Calculate metrics for a reward variant."""
        # Calculate basic metrics
        transaction_count = len(receipts)
        total_amount = sum(r.payment_instruction.amount for r in receipts)
        
        # Calculate success rate
        successful_transactions = sum(
            1 for r in receipts 
            if r.processor_auth_result.status == "approved"
        )
        success_rate = successful_transactions / transaction_count if transaction_count > 0 else 0.0
        
        # Calculate average settlement time
        avg_settlement_time = sum(
            r.processor_auth_result.settlement_time_actual 
            for r in receipts
        ) / transaction_count if transaction_count > 0 else 0.0
        
        # Calculate reward value (simplified)
        reward_value = sum(
            abs(r.processor_auth_result.processor_fee) 
            for r in receipts if r.processor_auth_result.processor_fee < 0
        )
        
        return RewardVariant(
            variant_id=variant_key,
            processor_id=processor_id,
            rail_type=rail_type,
            reward_type=reward_type,
            reward_value=reward_value,
            transaction_count=transaction_count,
            total_amount=total_amount,
            success_rate=success_rate,
            avg_settlement_time=avg_settlement_time
        )


class ScorecardGenerator:
    """
    Scorecard generation service for nightly reporting.
    
    Generates comprehensive scorecards with performance metrics, top performers,
    and formatted reports in both Markdown and JSON formats.
    """
    
    def __init__(self):
        """Initialize scorecard generator."""
        logger.info("Scorecard generator initialized")
    
    def generate_scorecard(
        self,
        variants: List[RewardVariant],
        date: datetime
    ) -> Scorecard:
        """
        Generate nightly scorecard from reward variants.
        
        Args:
            variants: Aggregated reward variants
            date: Scorecard date
            
        Returns:
            Complete scorecard with metrics and reports
        """
        # Calculate aggregated metrics
        total_transactions = sum(v.transaction_count for v in variants)
        total_amount = sum(v.total_amount for v in variants)
        
        # Calculate average success rate
        if variants:
            avg_success_rate = sum(v.success_rate * v.transaction_count for v in variants) / total_transactions
        else:
            avg_success_rate = 0.0
        
        # Calculate average settlement time
        if variants:
            avg_settlement_time = sum(v.avg_settlement_time * v.transaction_count for v in variants) / total_transactions
        else:
            avg_settlement_time = 0.0
        
        # Determine top performers
        top_processor = self._find_top_performer(variants, "processor_id", "success_rate")
        top_rail = self._find_top_performer(variants, "rail_type", "success_rate")
        best_reward_type = self._find_top_performer(variants, "reward_type", "reward_value")
        
        # Generate markdown report
        markdown_report = self._generate_markdown_report(
            variants, date, total_transactions, total_amount,
            avg_success_rate, avg_settlement_time,
            top_processor, top_rail, best_reward_type
        )
        
        # Generate JSON data
        json_data = self._generate_json_data(variants, date)
        
        # Create scorecard
        scorecard = Scorecard(
            scorecard_id=str(uuid.uuid4()),
            date=date,
            total_transactions=total_transactions,
            total_amount=total_amount,
            avg_success_rate=avg_success_rate,
            avg_settlement_time=avg_settlement_time,
            variants=variants,
            top_processor=top_processor,
            top_rail=top_rail,
            best_reward_type=best_reward_type,
            markdown_report=markdown_report,
            json_data=json_data
        )
        
        logger.info(f"Generated scorecard {scorecard.scorecard_id} for {date.strftime('%Y-%m-%d')}")
        return scorecard
    
    def _find_top_performer(
        self,
        variants: List[RewardVariant],
        field: str,
        metric: str
    ) -> str:
        """Find top performer by field and metric."""
        if not variants:
            return "N/A"
        
        # Group by field and calculate weighted average
        field_groups = {}
        for variant in variants:
            field_value = getattr(variant, field)
            if field_value not in field_groups:
                field_groups[field_value] = []
            field_groups[field_value].append(variant)
        
        # Find best performer
        best_performer = None
        best_score = -1
        
        for field_value, group_variants in field_groups.items():
            if metric == "success_rate":
                # Weight by transaction count
                total_transactions = sum(v.transaction_count for v in group_variants)
                if total_transactions > 0:
                    weighted_score = sum(
                        v.success_rate * v.transaction_count for v in group_variants
                    ) / total_transactions
                else:
                    weighted_score = 0
            elif metric == "reward_value":
                # Sum reward values
                weighted_score = sum(v.reward_value for v in group_variants)
            else:
                weighted_score = 0
            
            if weighted_score > best_score:
                best_score = weighted_score
                best_performer = field_value
        
        return best_performer or "N/A"
    
    def _generate_markdown_report(
        self,
        variants: List[RewardVariant],
        date: datetime,
        total_transactions: int,
        total_amount: float,
        avg_success_rate: float,
        avg_settlement_time: float,
        top_processor: str,
        top_rail: str,
        best_reward_type: str
    ) -> str:
        """Generate markdown formatted scorecard report."""
        report = f"""# Weave Scorecard - {date.strftime('%Y-%m-%d')}

## Executive Summary

- **Total Transactions**: {total_transactions:,}
- **Total Amount**: ${total_amount:,.2f}
- **Average Success Rate**: {avg_success_rate:.2%}
- **Average Settlement Time**: {avg_settlement_time:.1f} hours

## Top Performers

- **Best Processor**: {top_processor}
- **Best Rail Type**: {top_rail}
- **Best Reward Type**: {best_reward_type}

## Variant Performance

| Variant ID | Processor | Rail | Reward Type | Transactions | Amount | Success Rate | Avg Settlement |
|------------|-----------|------|-------------|--------------|--------|--------------|----------------|
"""
        
        # Sort variants by success rate
        sorted_variants = sorted(variants, key=lambda v: v.success_rate, reverse=True)
        
        for variant in sorted_variants:
            report += f"| {variant.variant_id} | {variant.processor_id} | {variant.rail_type} | {variant.reward_type} | {variant.transaction_count:,} | ${variant.total_amount:,.2f} | {variant.success_rate:.2%} | {variant.avg_settlement_time:.1f}h |\n"
        
        # Add insights
        report += "\n## Insights\n\n"
        
        if variants:
            high_performers = [v for v in variants if v.success_rate > avg_success_rate]
            report += f"- {len(high_performers)} variants above average success rate\n"
            
            fast_settlers = [v for v in variants if v.avg_settlement_time < avg_settlement_time]
            report += f"- {len(fast_settlers)} variants with faster settlement than average\n"
            
            high_reward = [v for v in variants if v.reward_value > 0]
            report += f"- {len(high_reward)} variants providing rewards\n"
        
        report += f"\n---\n*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC*"
        
        return report
    
    def _generate_json_data(
        self,
        variants: List[RewardVariant],
        date: datetime
    ) -> Dict[str, Any]:
        """Generate JSON data for scorecard."""
        return {
            "scorecard_date": date.isoformat(),
            "generated_at": datetime.now().isoformat(),
            "variants": [variant.dict() for variant in variants],
            "summary": {
                "total_variants": len(variants),
                "unique_processors": len(set(v.processor_id for v in variants)),
                "unique_rails": len(set(v.rail_type for v in variants)),
                "unique_reward_types": len(set(v.reward_type for v in variants))
            }
        }


class NightlyJobRunner:
    """
    Nightly job runner for automated scorecard generation.
    
    Runs nightly aggregation and scorecard generation jobs with comprehensive
    error handling and logging.
    """
    
    def __init__(self):
        """Initialize nightly job runner."""
        self.reward_aggregator = RewardAggregator()
        self.scorecard_generator = ScorecardGenerator()
        logger.info("Nightly job runner initialized")
    
    def run_nightly_jobs(self, target_date: Optional[datetime] = None) -> Scorecard:
        """
        Run nightly aggregation and scorecard generation.
        
        Args:
            target_date: Date to process (defaults to yesterday)
            
        Returns:
            Generated scorecard
        """
        if target_date is None:
            target_date = datetime.now() - timedelta(days=1)
        
        logger.info(f"Running nightly jobs for {target_date.strftime('%Y-%m-%d')}")
        
        try:
            # Step 1: Get receipts for the target date
            receipts = self._get_receipts_for_date(target_date)
            logger.info(f"Retrieved {len(receipts)} receipts for processing")
            
            # Step 2: Aggregate rewards by variant
            variants = self.reward_aggregator.aggregate_rewards_by_variant(receipts, target_date)
            logger.info(f"Aggregated {len(variants)} reward variants")
            
            # Step 3: Generate scorecard
            scorecard = self.scorecard_generator.generate_scorecard(variants, target_date)
            logger.info(f"Generated scorecard {scorecard.scorecard_id}")
            
            # Step 4: Save scorecard
            self._save_scorecard(scorecard)
            logger.info(f"Saved scorecard to storage")
            
            return scorecard
            
        except Exception as e:
            logger.error(f"Nightly job failed: {e}")
            raise
    
    def _get_receipts_for_date(self, date: datetime) -> List[SignedReceipt]:
        """Get receipts for a specific date (placeholder implementation)."""
        # In a real implementation, this would query the database
        # For now, return empty list as placeholder
        return []
    
    def _save_scorecard(self, scorecard: Scorecard) -> None:
        """Save scorecard to storage (placeholder implementation)."""
        # In a real implementation, this would save to database and/or file system
        logger.info(f"Saving scorecard {scorecard.scorecard_id} to storage")
        
        # Example: Save markdown to file
        filename = f"scorecards/scorecard_{scorecard.date.strftime('%Y-%m-%d')}.md"
        # with open(filename, 'w') as f:
        #     f.write(scorecard.markdown_report)
        
        # Example: Save JSON to file
        json_filename = f"scorecards/scorecard_{scorecard.date.strftime('%Y-%m-%d')}.json"
        # with open(json_filename, 'w') as f:
        #     json.dump(scorecard.json_data, f, indent=2)


# Global instances
_reward_aggregator = None
_scorecard_generator = None
_nightly_job_runner = None


def get_reward_aggregator() -> RewardAggregator:
    """Get global reward aggregator instance."""
    global _reward_aggregator
    if _reward_aggregator is None:
        _reward_aggregator = RewardAggregator()
    return _reward_aggregator


def get_scorecard_generator() -> ScorecardGenerator:
    """Get global scorecard generator instance."""
    global _scorecard_generator
    if _scorecard_generator is None:
        _scorecard_generator = ScorecardGenerator()
    return _scorecard_generator


def get_nightly_job_runner() -> NightlyJobRunner:
    """Get global nightly job runner instance."""
    global _nightly_job_runner
    if _nightly_job_runner is None:
        _nightly_job_runner = NightlyJobRunner()
    return _nightly_job_runner









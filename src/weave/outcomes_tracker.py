"""
Outcomes Tracking for Weave Phase 9.

Implements t0/tx outcomes ingestion with cohort_id tracking for
learning loop optimization and performance monitoring.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.weave.models import (
    PaymentInstruction, ProcessorAuthResult, RewardVariant
)
from src.weave.events import (
    emit_processor_integration_event
)

logger = logging.getLogger(__name__)


class CohortTracker:
    """
    Tracks cohorts for learning loop optimization.
    
    Groups transactions by similar characteristics to enable
    cohort-based analysis and learning optimization.
    """
    
    def __init__(self):
        """Initialize the cohort tracker."""
        self.cohort_definitions = {
            "amount_ranges": [
                (0, 100, "micro"),
                (100, 1000, "small"),
                (1000, 10000, "medium"),
                (10000, 100000, "large"),
                (100000, float('inf'), "enterprise")
            ],
            "merchant_categories": [
                "retail", "services", "marketplace", "saas", "gaming",
                "travel", "healthcare", "finance", "education", "other"
            ],
            "payment_rails": ["ACH", "Card", "RTP", "FedNow", "SEPA", "Crypto"],
            "instruments": ["credit_card", "debit_card", "bank_transfer", "stablecoin"],
            "geographic_regions": ["US", "EU", "APAC", "LATAM", "Other"]
        }
        logger.info("Cohort tracker initialized")
    
    def assign_cohort_id(
        self,
        payment_instruction: PaymentInstruction,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Assign cohort ID based on transaction characteristics.
        
        Args:
            payment_instruction: Payment instruction to assign cohort to
            additional_context: Additional context for cohort assignment
            
        Returns:
            Cohort ID string
        """
        try:
            # Extract transaction characteristics
            amount = payment_instruction.amount
            currency = payment_instruction.currency
            rail_type = payment_instruction.selected_rail
            instrument_type = payment_instruction.selected_instrument
            merchant_id = payment_instruction.metadata.get("merchant_id", "unknown")
            
            # Determine amount range
            amount_range = self._get_amount_range(amount)
            
            # Determine merchant category (from metadata or infer)
            merchant_category = payment_instruction.metadata.get(
                "merchant_category", 
                additional_context.get("merchant_category", "other") if additional_context else "other"
            )
            
            # Determine geographic region (from metadata or infer)
            geographic_region = payment_instruction.metadata.get(
                "geographic_region",
                additional_context.get("geographic_region", "US") if additional_context else "US"
            )
            
            # Generate cohort ID
            cohort_id = f"{amount_range}_{merchant_category}_{rail_type}_{instrument_type}_{geographic_region}"
            
            logger.debug(f"Assigned cohort ID {cohort_id} for transaction {payment_instruction.trace_id}")
            return cohort_id
            
        except Exception as e:
            logger.error(f"Failed to assign cohort ID: {str(e)}")
            return f"error_cohort_{uuid.uuid4().hex[:8]}"
    
    def _get_amount_range(self, amount: float) -> str:
        """Get amount range category for given amount."""
        for min_amt, max_amt, category in self.cohort_definitions["amount_ranges"]:
            if min_amt <= amount < max_amt:
                return category
        return "enterprise"  # Fallback for very large amounts
    
    def get_cohort_statistics(self, cohort_id: str) -> Dict[str, Any]:
        """
        Get statistics for a specific cohort.
        
        Args:
            cohort_id: Cohort identifier
            
        Returns:
            Dictionary containing cohort statistics
        """
        # This would typically query a database
        # For now, return mock statistics
        return {
            "cohort_id": cohort_id,
            "transaction_count": 0,  # Would be populated from database
            "avg_amount": 0.0,
            "avg_cost": 0.0,
            "avg_settlement_time": 0.0,
            "approval_rate": 0.0,
            "risk_score": 0.0,
            "last_updated": datetime.now().isoformat()
        }


class OutcomesIngester:
    """
    Ingests and processes payment outcomes for learning loop.
    
    Handles t0 (immediate) and tx (settled) outcomes with cohort tracking
    for comprehensive performance analysis.
    """
    
    def __init__(self):
        """Initialize the outcomes ingester."""
        self.cohort_tracker = CohortTracker()
        self.outcome_storage = {}  # In-memory storage for demo
        logger.info("Outcomes ingester initialized")
    
    def ingest_t0_outcome(
        self,
        payment_instruction: PaymentInstruction,
        auth_result: ProcessorAuthResult,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ingest t0 (immediate) outcome data.
        
        Args:
            payment_instruction: Original payment instruction
            auth_result: Authorization result from processor
            additional_context: Additional context data
            
        Returns:
            Dictionary containing ingested outcome data
        """
        try:
            # Assign cohort ID
            cohort_id = self.cohort_tracker.assign_cohort_id(
                payment_instruction, additional_context
            )
            
            # Extract t0 outcome data
            t0_outcome = {
                "outcome_type": "t0_immediate",
                "trace_id": payment_instruction.trace_id,
                "instruction_id": payment_instruction.instruction_id,
                "cohort_id": cohort_id,
                "timestamp": datetime.now().isoformat(),
                "payment_data": {
                    "amount": payment_instruction.amount,
                    "currency": payment_instruction.currency,
                    "rail_type": payment_instruction.selected_rail,
                    "instrument_type": payment_instruction.selected_instrument,
                    "processor_id": payment_instruction.selected_processor
                },
                "auth_result": {
                    "status": auth_result.status,
                    "auth_code": auth_result.auth_code,
                    "decline_reason": auth_result.decline_reason,
                    "processor_fee": auth_result.processor_fee,
                    "auth_id": auth_result.auth_id
                },
                "immediate_metrics": {
                    "approval_status": auth_result.status,
                    "processing_time_ms": auth_result.processor_metadata.get("processing_time_ms", 0),
                    "fraud_check": auth_result.processor_metadata.get("fraud_check", "unknown"),
                    "risk_score": auth_result.processor_metadata.get("risk_score", 0.5),
                    "approval_score": auth_result.processor_metadata.get("approval_score", 0.5)
                },
                "additional_context": additional_context or {}
            }
            
            # Store outcome
            self._store_outcome(t0_outcome)
            
            # Emit integration event
            emit_processor_integration_event(
                auth_result.processor_id,
                "t0_outcome_ingested",
                {
                    "trace_id": payment_instruction.trace_id,
                    "cohort_id": cohort_id,
                    "status": auth_result.status,
                    "outcome_type": "t0_immediate"
                }
            )
            
            logger.info(f"Ingested t0 outcome for trace {payment_instruction.trace_id}, cohort {cohort_id}")
            return t0_outcome
            
        except Exception as e:
            logger.error(f"Failed to ingest t0 outcome: {str(e)}")
            return {
                "error": str(e),
                "trace_id": payment_instruction.trace_id,
                "outcome_type": "t0_immediate",
                "timestamp": datetime.now().isoformat()
            }
    
    def ingest_tx_outcome(
        self,
        payment_instruction: PaymentInstruction,
        settlement_data: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ingest tx (settled) outcome data.
        
        Args:
            payment_instruction: Original payment instruction
            settlement_data: Settlement and final outcome data
            additional_context: Additional context data
            
        Returns:
            Dictionary containing ingested outcome data
        """
        try:
            # Assign cohort ID
            cohort_id = self.cohort_tracker.assign_cohort_id(
                payment_instruction, additional_context
            )
            
            # Extract tx outcome data
            tx_outcome = {
                "outcome_type": "tx_settled",
                "trace_id": payment_instruction.trace_id,
                "instruction_id": payment_instruction.instruction_id,
                "cohort_id": cohort_id,
                "timestamp": datetime.now().isoformat(),
                "payment_data": {
                    "amount": payment_instruction.amount,
                    "currency": payment_instruction.currency,
                    "rail_type": payment_instruction.selected_rail,
                    "instrument_type": payment_instruction.selected_instrument,
                    "processor_id": payment_instruction.selected_processor
                },
                "settlement_data": {
                    "settlement_status": settlement_data.get("settlement_status", "settled"),
                    "actual_settlement_time_hours": settlement_data.get("actual_settlement_time_hours", 0),
                    "final_cost": settlement_data.get("final_cost", 0.0),
                    "fees_breakdown": settlement_data.get("fees_breakdown", {}),
                    "settlement_reference": settlement_data.get("settlement_reference", "")
                },
                "final_metrics": {
                    "success": settlement_data.get("success", True),
                    "actual_cost": settlement_data.get("actual_cost", payment_instruction.effective_cost),
                    "settlement_time_hours": settlement_data.get("actual_settlement_time_hours", payment_instruction.settlement_time_hours),
                    "chargeback_count": settlement_data.get("chargeback_count", 0),
                    "dispute_count": settlement_data.get("dispute_count", 0),
                    "customer_rating": settlement_data.get("customer_rating", None),
                    "merchant_satisfaction": settlement_data.get("merchant_satisfaction", None)
                },
                "risk_events": settlement_data.get("risk_events", []),
                "additional_context": additional_context or {}
            }
            
            # Store outcome
            self._store_outcome(tx_outcome)
            
            # Emit integration event
            emit_processor_integration_event(
                payment_instruction.selected_processor,
                "tx_outcome_ingested",
                {
                    "trace_id": payment_instruction.trace_id,
                    "cohort_id": cohort_id,
                    "settlement_status": settlement_data.get("settlement_status", "settled"),
                    "outcome_type": "tx_settled"
                }
            )
            
            logger.info(f"Ingested tx outcome for trace {payment_instruction.trace_id}, cohort {cohort_id}")
            return tx_outcome
            
        except Exception as e:
            logger.error(f"Failed to ingest tx outcome: {str(e)}")
            return {
                "error": str(e),
                "trace_id": payment_instruction.trace_id,
                "outcome_type": "tx_settled",
                "timestamp": datetime.now().isoformat()
            }
    
    def get_outcomes_by_cohort(
        self,
        cohort_id: str,
        outcome_type: Optional[str] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get outcomes for a specific cohort.
        
        Args:
            cohort_id: Cohort identifier
            outcome_type: Filter by outcome type (t0_immediate, tx_settled)
            time_range: Filter by time range
            
        Returns:
            List of outcome data
        """
        try:
            outcomes = []
            
            # Filter outcomes by cohort
            for outcome in self.outcome_storage.values():
                if outcome.get("cohort_id") == cohort_id:
                    # Apply filters
                    if outcome_type and outcome.get("outcome_type") != outcome_type:
                        continue
                    
                    if time_range:
                        outcome_time = datetime.fromisoformat(outcome.get("timestamp", ""))
                        if not (time_range[0] <= outcome_time <= time_range[1]):
                            continue
                    
                    outcomes.append(outcome)
            
            logger.debug(f"Retrieved {len(outcomes)} outcomes for cohort {cohort_id}")
            return outcomes
            
        except Exception as e:
            logger.error(f"Failed to get outcomes by cohort: {str(e)}")
            return []
    
    def get_cohort_performance_summary(self, cohort_id: str) -> Dict[str, Any]:
        """
        Get performance summary for a cohort.
        
        Args:
            cohort_id: Cohort identifier
            
        Returns:
            Dictionary containing cohort performance summary
        """
        try:
            outcomes = self.get_outcomes_by_cohort(cohort_id)
            
            if not outcomes:
                return {
                    "cohort_id": cohort_id,
                    "total_transactions": 0,
                    "error": "No outcomes found for cohort"
                }
            
            # Separate t0 and tx outcomes
            t0_outcomes = [o for o in outcomes if o.get("outcome_type") == "t0_immediate"]
            tx_outcomes = [o for o in outcomes if o.get("outcome_type") == "tx_settled"]
            
            # Calculate performance metrics
            summary = {
                "cohort_id": cohort_id,
                "total_transactions": len(t0_outcomes),
                "settled_transactions": len(tx_outcomes),
                "approval_rate": self._calculate_approval_rate(t0_outcomes),
                "avg_processing_time_ms": self._calculate_avg_processing_time(t0_outcomes),
                "avg_settlement_time_hours": self._calculate_avg_settlement_time(tx_outcomes),
                "avg_cost": self._calculate_avg_cost(tx_outcomes),
                "chargeback_rate": self._calculate_chargeback_rate(tx_outcomes),
                "customer_satisfaction": self._calculate_customer_satisfaction(tx_outcomes),
                "risk_score": self._calculate_risk_score(tx_outcomes),
                "last_updated": datetime.now().isoformat()
            }
            
            logger.info(f"Generated performance summary for cohort {cohort_id}")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate cohort performance summary: {str(e)}")
            return {
                "cohort_id": cohort_id,
                "error": str(e),
                "last_updated": datetime.now().isoformat()
            }
    
    def _store_outcome(self, outcome: Dict[str, Any]) -> None:
        """Store outcome data (in-memory for demo)."""
        outcome_id = f"{outcome['trace_id']}_{outcome['outcome_type']}"
        self.outcome_storage[outcome_id] = outcome
    
    def _calculate_approval_rate(self, t0_outcomes: List[Dict[str, Any]]) -> float:
        """Calculate approval rate from t0 outcomes."""
        if not t0_outcomes:
            return 0.0
        
        approved_count = sum(
            1 for outcome in t0_outcomes
            if outcome.get("auth_result", {}).get("status") == "approved"
        )
        return approved_count / len(t0_outcomes)
    
    def _calculate_avg_processing_time(self, t0_outcomes: List[Dict[str, Any]]) -> float:
        """Calculate average processing time from t0 outcomes."""
        if not t0_outcomes:
            return 0.0
        
        processing_times = [
            outcome.get("immediate_metrics", {}).get("processing_time_ms", 0)
            for outcome in t0_outcomes
        ]
        return sum(processing_times) / len(processing_times) if processing_times else 0.0
    
    def _calculate_avg_settlement_time(self, tx_outcomes: List[Dict[str, Any]]) -> float:
        """Calculate average settlement time from tx outcomes."""
        if not tx_outcomes:
            return 0.0
        
        settlement_times = [
            outcome.get("final_metrics", {}).get("settlement_time_hours", 0)
            for outcome in tx_outcomes
        ]
        return sum(settlement_times) / len(settlement_times) if settlement_times else 0.0
    
    def _calculate_avg_cost(self, tx_outcomes: List[Dict[str, Any]]) -> float:
        """Calculate average cost from tx outcomes."""
        if not tx_outcomes:
            return 0.0
        
        costs = [
            outcome.get("final_metrics", {}).get("actual_cost", 0.0)
            for outcome in tx_outcomes
        ]
        return sum(costs) / len(costs) if costs else 0.0
    
    def _calculate_chargeback_rate(self, tx_outcomes: List[Dict[str, Any]]) -> float:
        """Calculate chargeback rate from tx outcomes."""
        if not tx_outcomes:
            return 0.0
        
        chargeback_count = sum(
            outcome.get("final_metrics", {}).get("chargeback_count", 0)
            for outcome in tx_outcomes
        )
        return chargeback_count / len(tx_outcomes)
    
    def _calculate_customer_satisfaction(self, tx_outcomes: List[Dict[str, Any]]) -> float:
        """Calculate average customer satisfaction from tx outcomes."""
        if not tx_outcomes:
            return 0.0
        
        ratings = [
            outcome.get("final_metrics", {}).get("customer_rating")
            for outcome in tx_outcomes
            if outcome.get("final_metrics", {}).get("customer_rating") is not None
        ]
        return sum(ratings) / len(ratings) if ratings else 0.0
    
    def _calculate_risk_score(self, tx_outcomes: List[Dict[str, Any]]) -> float:
        """Calculate average risk score from tx outcomes."""
        if not tx_outcomes:
            return 0.0
        
        risk_scores = [
            outcome.get("immediate_metrics", {}).get("risk_score", 0.5)
            for outcome in tx_outcomes
        ]
        return sum(risk_scores) / len(risk_scores) if risk_scores else 0.5


# Global instance
_outcomes_ingester = None


def get_outcomes_ingester() -> OutcomesIngester:
    """Get global outcomes ingester instance."""
    global _outcomes_ingester
    if _outcomes_ingester is None:
        _outcomes_ingester = OutcomesIngester()
    return _outcomes_ingester









"""
ML-enhanced auction manager for Weave.
Integrates ML models with traditional auction logic for optimized processor selection.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from weave.auction import AuctionManager, AuctionResult
from weave.models import CartSummary, RailCandidate, BidResponse
from weave.ml.auction_optimization import get_auction_optimizer, AuctionOptimizationFeatures, AuctionOptimizationResult
from weave.ml.bid_prediction import get_bid_predictor, BidPredictionFeatures, BidPredictionResult

logger = logging.getLogger(__name__)


class MLEnhancedAuctionManager(AuctionManager):
    """
    ML-enhanced auction manager that combines traditional auction logic with ML predictions.
    
    Uses ML models to:
    1. Optimize auction parameters and predict winners
    2. Predict processor bid behavior
    3. Enhance winner determination with ML insights
    """

    def __init__(self, deterministic_seed: int = 42, ml_weight: float = 0.7, use_ml: bool = True):
        """Initialize ML-enhanced auction manager."""
        super().__init__(deterministic_seed)
        self.ml_weight = ml_weight
        self.use_ml = use_ml
        self.auction_optimizer = get_auction_optimizer()
        self.bid_predictor = get_bid_predictor()
        logger.info(f"MLEnhancedAuctionManager initialized with ml_weight={self.ml_weight}, use_ml={self.use_ml}")

    def run_auction(self, trace_id: str, cart_summary: CartSummary, rail_candidates: List[RailCandidate]) -> AuctionResult:
        """
        Run an ML-enhanced processor auction.
        
        Args:
            trace_id: Unique trace identifier
            cart_summary: Cart information
            rail_candidates: Available payment rails
            
        Returns:
            Auction result with ML-enhanced winner determination
        """
        if not self.use_ml:
            logger.info("ML is disabled, falling back to traditional auction logic.")
            return super().run_auction(trace_id, cart_summary, rail_candidates)

        start_time = datetime.now()
        logger.info(
            f"Running ML-enhanced auction for merchant {cart_summary.merchant_id}",
            extra={
                "merchant_id": cart_summary.merchant_id,
                "cart_total": cart_summary.total_amount,
                "trace_id": trace_id,
            }
        )

        # 1. Run traditional auction to get baseline results
        traditional_result = super().run_auction(trace_id, cart_summary, rail_candidates)
        
        # 2. Prepare features for ML optimization
        optimization_features = self._prepare_optimization_features(cart_summary, rail_candidates)
        
        # 3. Get ML optimization predictions
        optimization_result = self.auction_optimizer.optimize_auction(optimization_features)
        
        # 4. Predict bids for each processor
        predicted_bids = self._predict_all_bids(cart_summary, rail_candidates)
        
        # 5. Apply ML-enhanced winner determination
        ml_enhanced_winner = self._determine_ml_enhanced_winner(
            traditional_result.all_bids, 
            predicted_bids, 
            optimization_result
        )
        
        # 6. Generate enhanced summary with ML insights
        enhanced_summary = self._generate_ml_enhanced_summary(
            traditional_result, 
            optimization_result, 
            predicted_bids, 
            ml_enhanced_winner
        )

        auction_time = (datetime.now() - start_time).total_seconds() * 1000
        
        logger.info(
            f"ML-enhanced auction completed",
            extra={
                "trace_id": trace_id,
                "traditional_winner": traditional_result.winning_processor,
                "ml_enhanced_winner": ml_enhanced_winner.processor_id,
                "optimization_confidence": optimization_result.confidence_score,
                "auction_time_ms": auction_time,
            }
        )

        return AuctionResult(
            trace_id=trace_id,
            auction_id=traditional_result.auction_id,
            winning_processor=ml_enhanced_winner.processor_id,
            winning_bid=ml_enhanced_winner,
            all_bids=traditional_result.all_bids,
            effective_cost_bps=ml_enhanced_winner.effective_cost_bps,
            summary=enhanced_summary,
            ml_metadata={
                "optimization_result": optimization_result.model_dump(),
                "predicted_bids": [bid.model_dump() for bid in predicted_bids],
                "ml_weight": self.ml_weight,
                "auction_time_ms": auction_time
            }
        )

    def _prepare_optimization_features(self, cart_summary: CartSummary, rail_candidates: List[RailCandidate]) -> AuctionOptimizationFeatures:
        """Prepare features for auction optimization."""
        # Extract rail characteristics
        rail_dict = {rail.rail_type: rail for rail in rail_candidates}
        
        # Helper function to get rail attributes safely
        def get_rail_attr(rail_type: str, attr: str, default: float):
            rail = rail_dict.get(rail_type)
            return getattr(rail, attr, default) if rail else default
        
        return AuctionOptimizationFeatures(
            cart_total_amount=cart_summary.total_amount,
            cart_item_count=cart_summary.item_count,
            merchant_id=cart_summary.merchant_id,
            merchant_category=cart_summary.merchant_category,
            channel=cart_summary.channel,
            currency=cart_summary.currency,
            ach_base_cost_bps=get_rail_attr("ACH", "base_cost_bps", 50.0),
            ach_settlement_days=get_rail_attr("ACH", "settlement_days", 1.0),
            debit_base_cost_bps=get_rail_attr("Card", "base_cost_bps", 100.0),  # Card is used for debit/credit
            debit_settlement_days=get_rail_attr("Card", "settlement_days", 1.0),
            credit_base_cost_bps=get_rail_attr("Card", "base_cost_bps", 200.0),
            credit_settlement_days=get_rail_attr("Card", "settlement_days", 2.0),
            # Placeholder values - in production, these would come from real data sources
            market_volatility=0.3,
            competitor_pressure=0.5,
            processor_capacity_utilization=0.7,
            historical_ach_win_rate=0.4,
            historical_debit_win_rate=0.3,
            historical_credit_win_rate=0.3,
            historical_avg_effective_cost=75.0,
            transaction_risk_score=0.2,
            merchant_risk_score=0.1,
            fraud_likelihood=0.05,
            hour_of_day=datetime.now().hour,
            day_of_week=datetime.now().weekday(),
            is_weekend=datetime.now().weekday() >= 5,
            is_holiday=False,
            is_peak_hours=9 <= datetime.now().hour <= 17,
            customer_segment="standard",
            customer_lifetime_value=1000.0,
            customer_transaction_frequency=2.5,
            customer_preferred_rail="debit",
            network_congestion=0.3,
            processor_maintenance_mode=False,
            regulatory_compliance_required=False
        )

    def _predict_all_bids(self, cart_summary: CartSummary, rail_candidates: List[RailCandidate]) -> List[BidPredictionResult]:
        """Predict bids for all processors and rails."""
        predicted_bids = []
        
        processors = ["stripe", "adyen", "carat"]
        
        for processor_id in processors:
            for rail in rail_candidates:
                features = BidPredictionFeatures(
                    processor_id=processor_id,
                    cart_total_amount=cart_summary.total_amount,
                    cart_item_count=cart_summary.item_count,
                    merchant_id=cart_summary.merchant_id,
                    merchant_category=cart_summary.merchant_category,
                    channel=cart_summary.channel,
                    currency=cart_summary.currency,
                    rail_type=rail.rail_type,
                    base_cost_bps=rail.base_cost_bps,
                    settlement_days=rail.settlement_days,
                    # Placeholder values - in production, these would come from real data sources
                    market_volatility=0.3,
                    competitor_bids_expected=3,
                    processor_utilization=0.7,
                    network_congestion=0.3,
                    processor_historical_win_rate=0.33,
                    processor_historical_avg_bps=rail.base_cost_bps,
                    processor_historical_rebate_rate=0.05,
                    merchant_historical_processor_preference=0.33,
                    transaction_risk_score=0.2,
                    merchant_risk_score=0.1,
                    fraud_likelihood=0.05,
                    chargeback_rate=0.02,
                    hour_of_day=datetime.now().hour,
                    day_of_week=datetime.now().weekday(),
                    is_weekend=datetime.now().weekday() >= 5,
                    is_holiday=False,
                    is_peak_hours=9 <= datetime.now().hour <= 17,
                    customer_segment="standard",
                    customer_lifetime_value=1000.0,
                    customer_transaction_frequency=2.5,
                    customer_preferred_rail="debit",
                    processor_margin_target=0.15,
                    processor_capacity_remaining=0.7,
                    regulatory_compliance_cost=0.0,
                    processor_maintenance_mode=False,
                    last_auction_winner="stripe",
                    competitor_aggressiveness=0.5,
                    market_share_pressure=0.4
                )
                
                prediction = self.bid_predictor.predict_bid(features)
                predicted_bids.append(prediction)
        
        return predicted_bids

    def _determine_ml_enhanced_winner(
        self, 
        actual_bids: List[BidResponse], 
        predicted_bids: List[BidPredictionResult], 
        optimization_result: AuctionOptimizationResult
    ) -> BidResponse:
        """Determine winner using both actual bids and ML predictions."""
        if not actual_bids:
            raise ValueError("No actual bids to evaluate")
        
        # Calculate effective cost for each actual bid
        for bid in actual_bids:
            bid.effective_cost_bps = max(0.0, bid.bps - bid.rebate_bps)
        
        # Get the traditional winner
        traditional_winner = min(actual_bids, key=lambda b: b.effective_cost_bps)
        
        # If ML confidence is high and prediction differs significantly, consider ML recommendation
        if optimization_result.confidence_score > 0.8:
            # Find the bid that matches the ML prediction
            for bid in actual_bids:
                if bid.processor_id == optimization_result.predicted_winner:
                    # Calculate ML-adjusted cost
                    ml_adjustment = optimization_result.predicted_effective_cost * (1 - self.ml_weight)
                    traditional_cost = traditional_winner.effective_cost_bps * self.ml_weight
                    combined_cost = ml_adjustment + traditional_cost
                    
                    # If ML-adjusted cost is significantly better, use ML winner
                    if combined_cost < traditional_winner.effective_cost_bps * 0.95:
                        logger.info(f"ML recommendation overrode traditional winner: {bid.processor_id}")
                        return bid
        
        return traditional_winner

    def _generate_ml_enhanced_summary(
        self, 
        traditional_result: AuctionResult, 
        optimization_result: AuctionOptimizationResult, 
        predicted_bids: List[BidPredictionResult],
        ml_enhanced_winner: BidResponse
    ) -> str:
        """Generate enhanced summary with ML insights."""
        base_summary = traditional_result.summary
        
        # Add ML insights
        ml_insights = []
        
        if optimization_result.confidence_score > 0.7:
            ml_insights.append(f"ML predicted {optimization_result.predicted_winner.upper()} with {optimization_result.confidence_score:.1%} confidence")
        
        # Calculate prediction accuracy for bids
        accurate_predictions = 0
        for pred in predicted_bids:
            for actual_bid in traditional_result.all_bids:
                if pred.predicted_bps and abs(pred.predicted_bps - actual_bid.bps) / actual_bid.bps < 0.15:
                    accurate_predictions += 1
                    break
        
        if predicted_bids:
            prediction_accuracy = accurate_predictions / len(predicted_bids)
            ml_insights.append(f"Bid prediction accuracy: {prediction_accuracy:.1%}")
        
        # Add risk assessment
        if optimization_result.risk_adjusted_score > 0.8:
            ml_insights.append("Low-risk transaction profile")
        elif optimization_result.risk_adjusted_score < 0.5:
            ml_insights.append("Higher-risk transaction, enhanced monitoring recommended")
        
        if ml_insights:
            enhanced_summary = f"{base_summary}. ML Insights: {'; '.join(ml_insights)}."
        else:
            enhanced_summary = base_summary
        
        return enhanced_summary


def get_ml_enhanced_auction_manager(ml_weight: float = 0.7, use_ml: bool = True) -> MLEnhancedAuctionManager:
    """Get an ML-enhanced auction manager instance."""
    return MLEnhancedAuctionManager(ml_weight=ml_weight, use_ml=use_ml)

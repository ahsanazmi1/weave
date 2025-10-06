"""
Training script for Weave ML models.
"""

import os
import sys
from pathlib import Path
import logging
import numpy as np
import pandas as pd

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from weave.ml.auction_optimization import AuctionOptimizationModel
from weave.ml.bid_prediction import BidPredictionModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def train_all_models():
    """Train all ML models for Weave."""
    logger.info("🚀 Starting Weave ML model training...")

    # Train Auction Optimization Model
    logger.info("🔧 Training auction optimization model...")
    auction_optimizer = AuctionOptimizationModel()
    
    # Create synthetic data for auction optimization
    n_samples = 10000
    np.random.seed(42)
    
    data_auction = {
        "cart_total_amount": np.random.uniform(10, 10000, n_samples),
        "cart_item_count": np.random.randint(1, 20, n_samples),
        "ach_base_cost_bps": np.random.uniform(30, 80, n_samples),
        "ach_settlement_days": np.random.uniform(0.5, 3, n_samples),
        "debit_base_cost_bps": np.random.uniform(80, 150, n_samples),
        "debit_settlement_days": np.random.uniform(0.5, 2, n_samples),
        "credit_base_cost_bps": np.random.uniform(150, 300, n_samples),
        "credit_settlement_days": np.random.uniform(1, 3, n_samples),
        "market_volatility": np.random.uniform(0.1, 0.8, n_samples),
        "competitor_pressure": np.random.uniform(0.2, 0.9, n_samples),
        "processor_capacity_utilization": np.random.uniform(0.3, 0.95, n_samples),
        "historical_ach_win_rate": np.random.uniform(0.2, 0.6, n_samples),
        "historical_debit_win_rate": np.random.uniform(0.1, 0.5, n_samples),
        "historical_credit_win_rate": np.random.uniform(0.1, 0.4, n_samples),
        "historical_avg_effective_cost": np.random.uniform(50, 150, n_samples),
        "transaction_risk_score": np.random.uniform(0.05, 0.5, n_samples),
        "merchant_risk_score": np.random.uniform(0.02, 0.3, n_samples),
        "fraud_likelihood": np.random.uniform(0.01, 0.2, n_samples),
        "hour_of_day": np.random.randint(0, 24, n_samples),
        "day_of_week": np.random.randint(0, 7, n_samples),
        "is_weekend": np.random.choice([True, False], n_samples, p=[0.3, 0.7]),
        "is_holiday": np.random.choice([True, False], n_samples, p=[0.1, 0.9]),
        "is_peak_hours": np.random.choice([True, False], n_samples, p=[0.4, 0.6]),
        "customer_lifetime_value": np.random.uniform(100, 10000, n_samples),
        "customer_transaction_frequency": np.random.uniform(0.5, 10, n_samples),
        "network_congestion": np.random.uniform(0.1, 0.8, n_samples),
        "processor_maintenance_mode": np.random.choice([True, False], n_samples, p=[0.05, 0.95]),
        "regulatory_compliance_required": np.random.choice([True, False], n_samples, p=[0.2, 0.8]),
        # One-hot encoded features
        "merchant_category_fashion": np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
        "merchant_category_electronics": np.random.choice([0, 1], n_samples, p=[0.8, 0.2]),
        "channel_online": np.random.choice([0, 1], n_samples, p=[0.3, 0.7]),
        "channel_mobile": np.random.choice([0, 1], n_samples, p=[0.4, 0.6]),
        "customer_segment_premium": np.random.choice([0, 1], n_samples, p=[0.8, 0.2]),
        "customer_preferred_rail_debit": np.random.choice([0, 1], n_samples, p=[0.6, 0.4]),
        "customer_preferred_rail_credit": np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
        "currency_USD": np.random.choice([0, 1], n_samples, p=[0.2, 0.8]),
        "currency_EUR": np.random.choice([0, 1], n_samples, p=[0.9, 0.1]),
    }
    
    df_auction = pd.DataFrame(data_auction)
    
    # Generate synthetic effective cost targets
    # Lower costs for ACH, medium for debit, higher for credit
    # Add market conditions, risk, and other factors
    df_auction['effective_cost_bps'] = (
        df_auction['historical_avg_effective_cost'] * 0.4 +
        (100 - df_auction['market_volatility'] * 50) * 0.2 +
        (100 - df_auction['competitor_pressure'] * 40) * 0.2 +
        (100 - df_auction['transaction_risk_score'] * 30) * 0.1 +
        (100 - df_auction['network_congestion'] * 20) * 0.1 +
        np.random.normal(0, 10, n_samples)
    )
    df_auction['effective_cost_bps'] = np.clip(df_auction['effective_cost_bps'], 20, 300)
    
    auction_optimizer.train_model(df_auction[auction_optimizer.feature_names], df_auction['effective_cost_bps'])
    auction_optimizer.save_model()
    logger.info("✅ Auction optimization model trained and saved")

    # Train Bid Prediction Model
    logger.info("🔧 Training bid prediction model...")
    bid_predictor = BidPredictionModel()
    
    # Create synthetic data for bid prediction
    data_bid = {
        "cart_total_amount": np.random.uniform(10, 10000, n_samples),
        "cart_item_count": np.random.randint(1, 20, n_samples),
        "base_cost_bps": np.random.uniform(50, 300, n_samples),
        "settlement_days": np.random.uniform(0.5, 3, n_samples),
        "market_volatility": np.random.uniform(0.1, 0.8, n_samples),
        "competitor_bids_expected": np.random.randint(1, 4, n_samples),
        "processor_utilization": np.random.uniform(0.3, 0.95, n_samples),
        "network_congestion": np.random.uniform(0.1, 0.8, n_samples),
        "processor_historical_win_rate": np.random.uniform(0.1, 0.8, n_samples),
        "processor_historical_avg_bps": np.random.uniform(60, 250, n_samples),
        "processor_historical_rebate_rate": np.random.uniform(0.02, 0.15, n_samples),
        "merchant_historical_processor_preference": np.random.uniform(0.1, 0.9, n_samples),
        "transaction_risk_score": np.random.uniform(0.05, 0.5, n_samples),
        "merchant_risk_score": np.random.uniform(0.02, 0.3, n_samples),
        "fraud_likelihood": np.random.uniform(0.01, 0.2, n_samples),
        "chargeback_rate": np.random.uniform(0.005, 0.05, n_samples),
        "hour_of_day": np.random.randint(0, 24, n_samples),
        "day_of_week": np.random.randint(0, 7, n_samples),
        "is_weekend": np.random.choice([True, False], n_samples, p=[0.3, 0.7]),
        "is_holiday": np.random.choice([True, False], n_samples, p=[0.1, 0.9]),
        "is_peak_hours": np.random.choice([True, False], n_samples, p=[0.4, 0.6]),
        "customer_lifetime_value": np.random.uniform(100, 10000, n_samples),
        "customer_transaction_frequency": np.random.uniform(0.5, 10, n_samples),
        "processor_margin_target": np.random.uniform(0.1, 0.3, n_samples),
        "processor_capacity_remaining": np.random.uniform(0.1, 0.9, n_samples),
        "regulatory_compliance_cost": np.random.uniform(0, 20, n_samples),
        "processor_maintenance_mode": np.random.choice([True, False], n_samples, p=[0.05, 0.95]),
        "competitor_aggressiveness": np.random.uniform(0.2, 0.9, n_samples),
        "market_share_pressure": np.random.uniform(0.1, 0.8, n_samples),
        # One-hot encoded features
        "processor_id_stripe": np.random.choice([0, 1], n_samples, p=[0.6, 0.4]),
        "processor_id_adyen": np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
        "processor_id_carat": np.random.choice([0, 1], n_samples, p=[0.8, 0.2]),
        "merchant_category_fashion": np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
        "merchant_category_electronics": np.random.choice([0, 1], n_samples, p=[0.8, 0.2]),
        "channel_online": np.random.choice([0, 1], n_samples, p=[0.3, 0.7]),
        "channel_mobile": np.random.choice([0, 1], n_samples, p=[0.4, 0.6]),
        "rail_type_ACH": np.random.choice([0, 1], n_samples, p=[0.6, 0.4]),
        "rail_type_debit": np.random.choice([0, 1], n_samples, p=[0.5, 0.5]),
        "rail_type_credit": np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
        "customer_segment_premium": np.random.choice([0, 1], n_samples, p=[0.8, 0.2]),
        "customer_preferred_rail_debit": np.random.choice([0, 1], n_samples, p=[0.6, 0.4]),
        "customer_preferred_rail_credit": np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
        "currency_USD": np.random.choice([0, 1], n_samples, p=[0.2, 0.8]),
        "currency_EUR": np.random.choice([0, 1], n_samples, p=[0.9, 0.1]),
        "last_auction_winner_stripe": np.random.choice([0, 1], n_samples, p=[0.5, 0.5]),
        "last_auction_winner_adyen": np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
    }
    
    df_bid = pd.DataFrame(data_bid)
    
    # Generate synthetic BPS targets
    # BPS should be close to base cost but adjusted by various factors
    df_bid['bps'] = (
        df_bid['base_cost_bps'] * 0.6 +
        df_bid['processor_historical_avg_bps'] * 0.3 +
        (100 - df_bid['market_volatility'] * 30) * 0.05 +
        (100 - df_bid['competitor_aggressiveness'] * 25) * 0.05 +
        np.random.normal(0, 15, n_samples)
    )
    df_bid['bps'] = np.clip(df_bid['bps'], 30, 400)
    
    # Generate rebate BPS (should be less than BPS)
    df_bid['rebate_bps'] = (
        df_bid['bps'] * df_bid['processor_historical_rebate_rate'] +
        (df_bid['processor_id_stripe'] * 5) +  # Stripe gives better rebates
        (df_bid['processor_id_carat'] * 8) +  # Carat gives best rebates
        (df_bid['customer_segment_premium'] * 3) +  # Premium customers get better rebates
        np.random.normal(0, 2, n_samples)
    )
    df_bid['rebate_bps'] = np.clip(df_bid['rebate_bps'], 0, df_bid['bps'] * 0.2)
    
    # Generate confidence scores
    df_bid['confidence'] = (
        0.7 +  # Base confidence
        df_bid['processor_historical_win_rate'] * 0.2 +
        (1 - df_bid['market_volatility']) * 0.05 +
        (1 - df_bid['network_congestion']) * 0.05 +
        np.random.normal(0, 0.05, n_samples)
    )
    df_bid['confidence'] = np.clip(df_bid['confidence'], 0.1, 0.95)
    
    # Generate settlement days
    df_bid['settlement_days'] = (
        df_bid['settlement_days'] * 0.8 +
        df_bid['network_congestion'] * 0.5 +
        (df_bid['processor_maintenance_mode'] * 1.0) +
        np.random.normal(0, 0.2, n_samples)
    )
    df_bid['settlement_days'] = np.clip(df_bid['settlement_days'], 0.5, 5.0)
    
    bid_predictor.train_model(
        df_bid[bid_predictor.feature_names], 
        df_bid['bps'],
        df_bid['rebate_bps'],
        df_bid['confidence'],
        df_bid['settlement_days']
    )
    bid_predictor.save_model()
    logger.info("✅ Bid prediction model trained and saved")

    logger.info("🎉 All ML models trained successfully!")


if __name__ == "__main__":
    train_all_models()

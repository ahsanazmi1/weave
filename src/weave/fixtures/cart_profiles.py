"""
Cart Profile Fixtures for Weave Auction Testing.

Provides predefined cart profiles to demonstrate different auction outcomes
and processor preferences based on cart characteristics.
"""

from typing import Dict, List, Any
from weave.models import CartSummary, RailCandidate


def get_cart_profiles() -> Dict[str, Dict[str, Any]]:
    """
    Get predefined cart profiles for testing different auction scenarios.
    
    Returns:
        Dictionary mapping profile names to cart configurations
    """
    return {
        "low_risk_small": get_low_risk_small_cart(),
        "low_risk_large": get_low_risk_large_cart(),
        "high_risk_medium": get_high_risk_medium_cart(),
        "loyalty_heavy": get_loyalty_heavy_cart(),
        "enterprise_volume": get_enterprise_volume_cart(),
        "international": get_international_cart()
    }


def get_low_risk_small_cart() -> Dict[str, Any]:
    """
    Low-risk, small amount cart profile.
    
    Expected winner: Stripe (good for small amounts, fast settlement)
    """
    return {
        "cart_summary": {
            "total_amount": 99.99,
            "currency": "USD",
            "item_count": 1,
            "merchant_id": "low_risk_merchant",
            "merchant_category": "low_risk",
            "channel": "online"
        },
        "rail_candidates": [
            {
                "rail_type": "credit",
                "base_cost_bps": 150.0,
                "settlement_days": 1,
                "risk_score": 0.2
            },
            {
                "rail_type": "debit",
                "base_cost_bps": 100.0,
                "settlement_days": 2,
                "risk_score": 0.1
            },
            {
                "rail_type": "ACH",
                "base_cost_bps": 50.0,
                "settlement_days": 1,
                "risk_score": 0.05
            }
        ],
        "expected_winner": "stripe",
        "expected_reason": "Stripe offers competitive rates for small amounts with fast settlement",
        "profile_description": "Low-risk, small amount transaction ideal for Stripe's fast settlement"
    }


def get_low_risk_large_cart() -> Dict[str, Any]:
    """
    Low-risk, large amount cart profile.
    
    Expected winner: Carat (excellent volume discounts for large amounts)
    """
    return {
        "cart_summary": {
            "total_amount": 25000.00,
            "currency": "USD",
            "item_count": 5,
            "merchant_id": "enterprise_merchant",
            "merchant_category": "low_risk",
            "channel": "online"
        },
        "rail_candidates": [
            {
                "rail_type": "credit",
                "base_cost_bps": 150.0,
                "settlement_days": 1,
                "risk_score": 0.15
            },
            {
                "rail_type": "debit",
                "base_cost_bps": 100.0,
                "settlement_days": 2,
                "risk_score": 0.1
            },
            {
                "rail_type": "ACH",
                "base_cost_bps": 50.0,
                "settlement_days": 1,
                "risk_score": 0.05
            }
        ],
        "expected_winner": "carat",
        "expected_reason": "Carat offers the best volume discounts for large enterprise transactions",
        "profile_description": "Large, low-risk transaction that benefits from Carat's volume discounts"
    }


def get_high_risk_medium_cart() -> Dict[str, Any]:
    """
    High-risk, medium amount cart profile.
    
    Expected winner: Adyen (high risk tolerance, good fraud detection)
    """
    return {
        "cart_summary": {
            "total_amount": 2500.00,
            "currency": "USD",
            "item_count": 3,
            "merchant_id": "high_risk_merchant",
            "merchant_category": "high_risk",
            "channel": "online"
        },
        "rail_candidates": [
            {
                "rail_type": "credit",
                "base_cost_bps": 150.0,
                "settlement_days": 1,
                "risk_score": 0.8
            },
            {
                "rail_type": "debit",
                "base_cost_bps": 100.0,
                "settlement_days": 2,
                "risk_score": 0.7
            },
            {
                "rail_type": "ACH",
                "base_cost_bps": 50.0,
                "settlement_days": 1,
                "risk_score": 0.6
            }
        ],
        "expected_winner": "adyen",
        "expected_reason": "Adyen has high risk tolerance and advanced fraud detection capabilities",
        "profile_description": "Medium amount, high-risk transaction requiring robust fraud protection"
    }


def get_loyalty_heavy_cart() -> Dict[str, Any]:
    """
    Loyalty-heavy cart profile with rewards focus.
    
    Expected winner: Stripe (good rebates for loyalty programs)
    """
    return {
        "cart_summary": {
            "total_amount": 1500.00,
            "currency": "USD",
            "item_count": 8,
            "merchant_id": "loyalty_merchant",
            "merchant_category": "electronics",
            "channel": "online"
        },
        "rail_candidates": [
            {
                "rail_type": "credit",
                "base_cost_bps": 150.0,
                "settlement_days": 1,
                "risk_score": 0.3
            },
            {
                "rail_type": "debit",
                "base_cost_bps": 100.0,
                "settlement_days": 2,
                "risk_score": 0.2
            },
            {
                "rail_type": "ACH",
                "base_cost_bps": 50.0,
                "settlement_days": 1,
                "risk_score": 0.1
            }
        ],
        "expected_winner": "stripe",
        "expected_reason": "Stripe offers competitive rebates for electronics and loyalty programs",
        "profile_description": "Electronics purchase with loyalty rewards, benefiting from Stripe's rebates"
    }


def get_enterprise_volume_cart() -> Dict[str, Any]:
    """
    Enterprise volume cart profile.
    
    Expected winner: Carat (enterprise focus, volume discounts)
    """
    return {
        "cart_summary": {
            "total_amount": 50000.00,
            "currency": "USD",
            "item_count": 25,
            "merchant_id": "enterprise_corp",
            "merchant_category": "general",
            "channel": "online"
        },
        "rail_candidates": [
            {
                "rail_type": "credit",
                "base_cost_bps": 150.0,
                "settlement_days": 1,
                "risk_score": 0.2
            },
            {
                "rail_type": "debit",
                "base_cost_bps": 100.0,
                "settlement_days": 2,
                "risk_score": 0.15
            },
            {
                "rail_type": "ACH",
                "base_cost_bps": 50.0,
                "settlement_days": 1,
                "risk_score": 0.1
            }
        ],
        "expected_winner": "carat",
        "expected_reason": "Carat provides the best enterprise volume discounts and features",
        "profile_description": "Large enterprise transaction maximizing Carat's volume discounts"
    }


def get_international_cart() -> Dict[str, Any]:
    """
    International cart profile with EUR currency.
    
    Expected winner: Adyen (strong international support)
    """
    return {
        "cart_summary": {
            "total_amount": 1500.00,
            "currency": "EUR",
            "item_count": 2,
            "merchant_id": "international_merchant",
            "merchant_category": "clothing",
            "channel": "online"
        },
        "rail_candidates": [
            {
                "rail_type": "credit",
                "base_cost_bps": 150.0,
                "settlement_days": 1,
                "risk_score": 0.3
            },
            {
                "rail_type": "debit",
                "base_cost_bps": 100.0,
                "settlement_days": 2,
                "risk_score": 0.25
            },
            {
                "rail_type": "ACH",
                "base_cost_bps": 50.0,
                "settlement_days": 1,
                "risk_score": 0.2
            }
        ],
        "expected_winner": "adyen",
        "expected_reason": "Adyen has excellent international support and EUR processing capabilities",
        "profile_description": "International EUR transaction leveraging Adyen's global presence"
    }


def get_cart_profile_by_name(profile_name: str) -> Dict[str, Any]:
    """
    Get a specific cart profile by name.
    
    Args:
        profile_name: Name of the cart profile
        
    Returns:
        Cart profile configuration
        
    Raises:
        ValueError: If profile name is not found
    """
    profiles = get_cart_profiles()
    if profile_name not in profiles:
        available = ", ".join(profiles.keys())
        raise ValueError(f"Unknown cart profile: {profile_name}. Available: {available}")
    
    return profiles[profile_name]


def get_profile_summary() -> Dict[str, str]:
    """
    Get a summary of all available cart profiles.
    
    Returns:
        Dictionary mapping profile names to descriptions
    """
    profiles = get_cart_profiles()
    return {
        name: profile["profile_description"]
        for name, profile in profiles.items()
    }


def get_expected_winners() -> Dict[str, str]:
    """
    Get expected winners for each cart profile.
    
    Returns:
        Dictionary mapping profile names to expected processor winners
    """
    profiles = get_cart_profiles()
    return {
        name: profile["expected_winner"]
        for name, profile in profiles.items()
    }


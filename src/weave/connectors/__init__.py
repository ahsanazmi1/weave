"""
Payment processor connectors for Weave Phase 8.

Provides integration with major payment processors including Carat, Stripe, and Adyen.
Each connector exposes standardized methods for bid requests, response parsing,
and payment instruction submission.
"""

from .carat import CaratConnector, get_carat_connector
from .stripe import StripeConnector, get_stripe_connector
from .adyen import AdyenConnector, get_adyen_connector


def get_connector_registry():
    """Get the connector registry with all available connectors."""
    return {
        "carat": get_carat_connector(),
        "stripe": get_stripe_connector(),
        "adyen": get_adyen_connector()
    }


__all__ = [
    "CaratConnector",
    "get_carat_connector",
    "StripeConnector", 
    "get_stripe_connector",
    "AdyenConnector",
    "get_adyen_connector",
    "get_connector_registry"
]
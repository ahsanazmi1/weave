"""
Processor Connectors for Weave Auction System.

This module provides interfaces and implementations for payment processor connectors
that respond to bid requests with deterministic pricing and constraints.
"""

from .base_connector import BaseProcessorConnector
from .stripe_connector import StripeConnector
from .adyen_connector import AdyenConnector
from .carat_connector import CaratConnector
from .connector_registry import ConnectorRegistry, get_connector_registry

__all__ = [
    'BaseProcessorConnector',
    'StripeConnector',
    'AdyenConnector', 
    'CaratConnector',
    'ConnectorRegistry',
    'get_connector_registry'
]

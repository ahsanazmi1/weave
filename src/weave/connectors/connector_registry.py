"""
Connector Registry for Processor Management.

Manages registration and retrieval of payment processor connectors
for the Weave auction system.
"""

from typing import Dict, List, Optional, Type
import logging

from .base_connector import BaseProcessorConnector
from .stripe_connector import StripeConnector
from .adyen_connector import AdyenConnector
from .carat_connector import CaratConnector

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """
    Registry for managing payment processor connectors.
    
    Provides centralized management of available processors and their
    connector implementations.
    """
    
    def __init__(self):
        """Initialize the connector registry."""
        self._connectors: Dict[str, Type[BaseProcessorConnector]] = {}
        self._instances: Dict[str, BaseProcessorConnector] = {}
        self.logger = logging.getLogger("weave.connector.registry")
        
        # Register default connectors
        self._register_default_connectors()
    
    def _register_default_connectors(self):
        """Register the default set of processor connectors."""
        self.register_connector("stripe", StripeConnector)
        self.register_connector("adyen", AdyenConnector)
        self.register_connector("carat", CaratConnector)
        
        self.logger.info("Default connectors registered: stripe, adyen, carat")
    
    def register_connector(self, processor_id: str, connector_class: Type[BaseProcessorConnector]):
        """
        Register a new processor connector.
        
        Args:
            processor_id: Unique identifier for the processor
            connector_class: Connector class that implements BaseProcessorConnector
        """
        if not issubclass(connector_class, BaseProcessorConnector):
            raise ValueError(f"Connector class must inherit from BaseProcessorConnector")
        
        self._connectors[processor_id] = connector_class
        self.logger.info(f"Registered connector: {processor_id}")
    
    def unregister_connector(self, processor_id: str):
        """
        Unregister a processor connector.
        
        Args:
            processor_id: Processor identifier to unregister
        """
        if processor_id in self._connectors:
            del self._connectors[processor_id]
            if processor_id in self._instances:
                del self._instances[processor_id]
            self.logger.info(f"Unregistered connector: {processor_id}")
        else:
            self.logger.warning(f"Attempted to unregister unknown connector: {processor_id}")
    
    def get_connector(self, processor_id: str, deterministic_seed: int = 42) -> Optional[BaseProcessorConnector]:
        """
        Get a connector instance for the specified processor.
        
        Args:
            processor_id: Processor identifier
            deterministic_seed: Seed for deterministic bid generation
            
        Returns:
            Connector instance or None if not found
        """
        if processor_id not in self._connectors:
            self.logger.warning(f"Unknown processor: {processor_id}")
            return None
        
        # Create instance if not exists or seed changed
        instance_key = f"{processor_id}_{deterministic_seed}"
        if instance_key not in self._instances:
            connector_class = self._connectors[processor_id]
            self._instances[instance_key] = connector_class(deterministic_seed)
        
        return self._instances[instance_key]
    
    def get_available_processors(self) -> List[str]:
        """
        Get list of available processor IDs.
        
        Returns:
            List of processor identifiers
        """
        return list(self._connectors.keys())
    
    def get_processor_info(self, processor_id: str) -> Optional[Dict]:
        """
        Get processor information.
        
        Args:
            processor_id: Processor identifier
            
        Returns:
            Processor information dictionary or None if not found
        """
        connector = self.get_connector(processor_id)
        if connector:
            return connector.get_processor_info()
        return None
    
    def get_all_processor_info(self) -> Dict[str, Dict]:
        """
        Get information for all registered processors.
        
        Returns:
            Dictionary mapping processor IDs to their information
        """
        info = {}
        for processor_id in self.get_available_processors():
            info[processor_id] = self.get_processor_info(processor_id)
        return info
    
    def validate_processor(self, processor_id: str) -> bool:
        """
        Validate if a processor is available and properly configured.
        
        Args:
            processor_id: Processor identifier
            
        Returns:
            True if processor is valid, False otherwise
        """
        try:
            connector = self.get_connector(processor_id)
            if not connector:
                return False
            
            # Test basic functionality
            info = connector.get_processor_info()
            currencies = connector.get_supported_currencies()
            risk_tolerance = connector.get_risk_tolerance()
            
            return all([
                info is not None,
                isinstance(currencies, list) and len(currencies) > 0,
                risk_tolerance in ['low', 'medium', 'high']
            ])
            
        except Exception as e:
            self.logger.error(f"Processor validation failed for {processor_id}: {e}")
            return False
    
    def get_processors_by_currency(self, currency: str) -> List[str]:
        """
        Get processors that support a specific currency.
        
        Args:
            currency: Currency code (e.g., 'USD', 'EUR')
            
        Returns:
            List of processor IDs that support the currency
        """
        supported_processors = []
        
        for processor_id in self.get_available_processors():
            connector = self.get_connector(processor_id)
            if connector and currency in connector.get_supported_currencies():
                supported_processors.append(processor_id)
        
        return supported_processors
    
    def get_processors_by_risk_tolerance(self, risk_tolerance: str) -> List[str]:
        """
        Get processors with a specific risk tolerance.
        
        Args:
            risk_tolerance: Risk tolerance level ('low', 'medium', 'high')
            
        Returns:
            List of processor IDs with the specified risk tolerance
        """
        matching_processors = []
        
        for processor_id in self.get_available_processors():
            connector = self.get_connector(processor_id)
            if connector and connector.get_risk_tolerance() == risk_tolerance:
                matching_processors.append(processor_id)
        
        return matching_processors
    
    def clear_instances(self):
        """Clear all connector instances (useful for testing)."""
        self._instances.clear()
        self.logger.info("Cleared all connector instances")
    
    def get_registry_stats(self) -> Dict[str, any]:
        """
        Get registry statistics.
        
        Returns:
            Dictionary with registry statistics
        """
        return {
            "total_connectors": len(self._connectors),
            "total_instances": len(self._instances),
            "available_processors": self.get_available_processors(),
            "connector_types": {
                processor_id: connector_class.__name__
                for processor_id, connector_class in self._connectors.items()
            }
        }


# Global registry instance
_global_registry: Optional[ConnectorRegistry] = None


def get_connector_registry() -> ConnectorRegistry:
    """
    Get the global connector registry instance.
    
    Returns:
        Global ConnectorRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ConnectorRegistry()
    return _global_registry


def reset_connector_registry():
    """Reset the global connector registry (useful for testing)."""
    global _global_registry
    _global_registry = None


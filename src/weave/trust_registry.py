"""
Trust Registry for Weave - v0 allowlist of Credential Providers.

This module provides functionality to manage and validate credential providers
against an allowlist to ensure only trusted providers can submit receipts.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Union

from .settings import Settings


class TrustRegistryError(Exception):
    """Raised when trust registry operations fail."""
    pass


class TrustRegistry:
    """
    Trust Registry for managing allowed credential providers.
    
    Provides allowlist functionality to validate credential providers
    before allowing receipt submission.
    """
    
    # Default embedded allowlist (fallback)
    DEFAULT_ALLOWLIST = {
        "providers": [
            {
                "id": "ocn-orca-v1",
                "name": "OCN Orca v1",
                "description": "OCN Orca Decision Engine v1",
                "type": "decision_engine",
                "status": "active",
                "trust_level": "high",
                "version": "1.0.0"
            },
            {
                "id": "ocn-weave-v1",
                "name": "OCN Weave v1", 
                "description": "OCN Weave Receipt Store v1",
                "type": "receipt_store",
                "status": "active",
                "trust_level": "high",
                "version": "1.0.0"
            },
            {
                "id": "ocn-okra-v1",
                "name": "OCN Okra v1",
                "description": "OCN Okra Credit Agent v1",
                "type": "credit_agent",
                "status": "active",
                "trust_level": "medium",
                "version": "1.0.0"
            },
            {
                "id": "ocn-opal-v1",
                "name": "OCN Opal v1",
                "description": "OCN Opal Wallet Agent v1", 
                "type": "wallet_agent",
                "status": "active",
                "trust_level": "medium",
                "version": "1.0.0"
            },
            {
                "id": "test-provider",
                "name": "Test Provider",
                "description": "Test credential provider for development",
                "type": "test",
                "status": "active",
                "trust_level": "low",
                "version": "0.1.0"
            }
        ],
        "metadata": {
            "version": "v0.1.0",
            "created": "2024-01-01T00:00:00Z",
            "description": "OCN Trust Registry v0 - Credential Provider Allowlist",
            "schema_version": "1.0"
        }
    }
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize trust registry.
        
        Args:
            settings: Settings instance for configuration
        """
        self.settings = settings or Settings()
        self._allowlist: Dict = {}
        self._provider_ids: List[str] = []
        self._source: str = "embedded"
        self._load_allowlist()
    
    def _load_allowlist(self) -> None:
        """Load allowlist from configured path or fallback to default."""
        try:
            if self.settings.trust_registry_path:
                allowlist_path = Path(self.settings.trust_registry_path)
                
                if not allowlist_path.exists():
                    raise TrustRegistryError(f"Trust registry file not found: {allowlist_path}")
                
                # Load based on file extension
                if allowlist_path.suffix.lower() in ['.yaml', '.yml']:
                    with open(allowlist_path, 'r', encoding='utf-8') as f:
                        self._allowlist = yaml.safe_load(f)
                elif allowlist_path.suffix.lower() == '.json':
                    with open(allowlist_path, 'r', encoding='utf-8') as f:
                        self._allowlist = json.load(f)
                else:
                    raise TrustRegistryError(f"Unsupported trust registry file format: {allowlist_path.suffix}")
                
                # Validate loaded allowlist
                self._validate_allowlist()
                self._source = "file"
                
            else:
                # Use default embedded allowlist
                self._allowlist = self.DEFAULT_ALLOWLIST.copy()
                self._source = "embedded"
                
        except Exception as e:
            # Fallback to default on any error
            print(f"Warning: Failed to load trust registry from {self.settings.trust_registry_path}: {e}")
            print("Falling back to default embedded allowlist")
            self._allowlist = self.DEFAULT_ALLOWLIST.copy()
            self._source = "embedded"
        
        # Build provider ID list for quick lookup
        self._provider_ids = [
            provider["id"] 
            for provider in self._allowlist.get("providers", [])
            if provider.get("status") == "active"
        ]
    
    def _validate_allowlist(self) -> None:
        """Validate loaded allowlist structure."""
        if not isinstance(self._allowlist, dict):
            raise TrustRegistryError("Trust registry must be a dictionary")
        
        if "providers" not in self._allowlist:
            raise TrustRegistryError("Trust registry must contain 'providers' key")
        
        if not isinstance(self._allowlist["providers"], list):
            raise TrustRegistryError("Providers must be a list")
        
        for i, provider in enumerate(self._allowlist["providers"]):
            if not isinstance(provider, dict):
                raise TrustRegistryError(f"Provider at index {i} must be a dictionary")
            
            required_fields = ["id", "name", "status"]
            for field in required_fields:
                if field not in provider:
                    raise TrustRegistryError(f"Provider at index {i} missing required field: {field}")
            
            if provider["status"] not in ["active", "inactive", "suspended"]:
                raise TrustRegistryError(f"Provider at index {i} has invalid status: {provider['status']}")
    
    def is_allowed(self, provider_id: str) -> bool:
        """
        Check if a provider ID is in the allowlist.
        
        Args:
            provider_id: Provider identifier to check
            
        Returns:
            True if provider is allowed (active), False otherwise
        """
        if not provider_id or not isinstance(provider_id, str):
            return False
        
        # Convert to string in case it's not already
        provider_id = str(provider_id)
        
        return provider_id in self._provider_ids
    
    def list_providers(self) -> List[str]:
        """
        Get list of all allowed provider IDs.
        
        Returns:
            List of active provider IDs
        """
        return self._provider_ids.copy()
    
    def get_provider_info(self, provider_id: str) -> Optional[Dict]:
        """
        Get detailed information about a provider.
        
        Args:
            provider_id: Provider identifier
            
        Returns:
            Provider information dictionary or None if not found
        """
        for provider in self._allowlist.get("providers", []):
            if provider["id"] == provider_id:
                return provider.copy()
        return None
    
    def get_registry_metadata(self) -> Dict:
        """
        Get trust registry metadata.
        
        Returns:
            Registry metadata dictionary
        """
        return self._allowlist.get("metadata", {}).copy()
    
    def reload(self) -> None:
        """Reload allowlist from configured path."""
        self._load_allowlist()
    
    def get_stats(self) -> Dict[str, Union[int, str]]:
        """
        Get trust registry statistics.
        
        Returns:
            Dictionary with registry statistics
        """
        providers = self._allowlist.get("providers", [])
        
        stats = {
            "total_providers": len(providers),
            "active_providers": len(self._provider_ids),
            "inactive_providers": len([
                p for p in providers 
                if p.get("status") == "inactive"
            ]),
            "suspended_providers": len([
                p for p in providers 
                if p.get("status") == "suspended"
            ]),
            "registry_version": self._allowlist.get("metadata", {}).get("version", "unknown"),
            "source": self._source
        }
        
        return stats


# Global trust registry instance
_trust_registry: Optional[TrustRegistry] = None


def get_trust_registry() -> TrustRegistry:
    """
    Get global trust registry instance.
    
    Returns:
        Trust registry instance
    """
    global _trust_registry
    
    if _trust_registry is None:
        _trust_registry = TrustRegistry()
    
    return _trust_registry


def reset_trust_registry() -> None:
    """Reset global trust registry instance (for testing)."""
    global _trust_registry
    _trust_registry = None

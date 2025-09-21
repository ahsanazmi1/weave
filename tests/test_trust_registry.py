"""
Tests for trust registry functionality.
"""

import json
import os
import tempfile

import yaml

from weave.trust_registry import TrustRegistry, get_trust_registry, reset_trust_registry
from weave.settings import Settings


class TestTrustRegistry:
    """Test TrustRegistry class."""

    def test_default_allowlist_loaded(self):
        """Test that default allowlist is loaded when no config file."""
        settings = Settings(trust_registry_path=None)
        registry = TrustRegistry(settings)
        
        # Should have default providers
        assert len(registry.list_providers()) > 0
        assert "ocn-orca-v1" in registry.list_providers()
        assert "ocn-weave-v1" in registry.list_providers()
        assert "test-provider" in registry.list_providers()
        
    def test_is_allowed_valid_provider(self):
        """Test is_allowed with valid provider."""
        registry = TrustRegistry()
        
        # Test with default providers
        assert registry.is_allowed("ocn-orca-v1") is True
        assert registry.is_allowed("ocn-weave-v1") is True
        assert registry.is_allowed("test-provider") is True
        
    def test_is_allowed_invalid_provider(self):
        """Test is_allowed with invalid provider."""
        registry = TrustRegistry()
        
        assert registry.is_allowed("nonexistent-provider") is False
        assert registry.is_allowed("") is False
        assert registry.is_allowed(None) is False
        
    def test_list_providers(self):
        """Test list_providers returns active providers."""
        registry = TrustRegistry()
        providers = registry.list_providers()
        
        assert isinstance(providers, list)
        assert len(providers) > 0
        assert "ocn-orca-v1" in providers
        assert "ocn-weave-v1" in providers
        
    def test_get_provider_info(self):
        """Test get_provider_info returns provider details."""
        registry = TrustRegistry()
        
        info = registry.get_provider_info("ocn-orca-v1")
        assert info is not None
        assert info["id"] == "ocn-orca-v1"
        assert info["name"] == "OCN Orca v1"
        assert info["status"] == "active"
        
        # Test nonexistent provider
        info = registry.get_provider_info("nonexistent")
        assert info is None
        
    def test_get_registry_metadata(self):
        """Test get_registry_metadata returns metadata."""
        registry = TrustRegistry()
        metadata = registry.get_registry_metadata()
        
        assert isinstance(metadata, dict)
        assert "version" in metadata
        
    def test_get_stats(self):
        """Test get_stats returns registry statistics."""
        registry = TrustRegistry()
        stats = registry.get_stats()
        
        assert isinstance(stats, dict)
        assert "total_providers" in stats
        assert "active_providers" in stats
        assert "registry_version" in stats
        assert "source" in stats
        
        assert stats["total_providers"] > 0
        assert stats["active_providers"] > 0
        assert stats["source"] == "embedded"  # Using default


class TestTrustRegistryFileLoading:
    """Test trust registry file loading functionality."""

    def test_load_yaml_file(self):
        """Test loading trust registry from YAML file."""
        # Create temporary YAML file
        yaml_data = {
            "metadata": {
                "version": "v0.1.0",
                "description": "Test registry"
            },
            "providers": [
                {
                    "id": "test-provider-1",
                    "name": "Test Provider 1",
                    "status": "active"
                },
                {
                    "id": "test-provider-2", 
                    "name": "Test Provider 2",
                    "status": "inactive"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_data, f)
            temp_path = f.name
        
        try:
            settings = Settings(trust_registry_path=temp_path)
            registry = TrustRegistry(settings)
            
            # Should have test providers
            providers = registry.list_providers()
            assert "test-provider-1" in providers
            assert "test-provider-2" not in providers  # inactive
            
            # Test stats
            stats = registry.get_stats()
            assert stats["total_providers"] == 2
            assert stats["active_providers"] == 1
            assert stats["source"] == "file"
            
        finally:
            os.unlink(temp_path)
            
    def test_load_json_file(self):
        """Test loading trust registry from JSON file."""
        # Create temporary JSON file
        json_data = {
            "metadata": {
                "version": "v0.1.0",
                "description": "Test registry"
            },
            "providers": [
                {
                    "id": "json-provider-1",
                    "name": "JSON Provider 1",
                    "status": "active"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_data, f)
            temp_path = f.name
        
        try:
            settings = Settings(trust_registry_path=temp_path)
            registry = TrustRegistry(settings)
            
            providers = registry.list_providers()
            assert "json-provider-1" in providers
            
        finally:
            os.unlink(temp_path)
            
    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file falls back to default."""
        settings = Settings(trust_registry_path="/nonexistent/path.yaml")
        registry = TrustRegistry(settings)
        
        # Should fall back to default
        assert "ocn-orca-v1" in registry.list_providers()
        stats = registry.get_stats()
        assert stats["source"] == "embedded"
        
    def test_load_invalid_yaml(self):
        """Test loading invalid YAML falls back to default."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name
        
        try:
            settings = Settings(trust_registry_path=temp_path)
            registry = TrustRegistry(settings)
            
            # Should fall back to default
            assert "ocn-orca-v1" in registry.list_providers()
            
        finally:
            os.unlink(temp_path)
            
    def test_load_invalid_structure(self):
        """Test loading file with invalid structure falls back to default."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({"invalid": "structure"}, f)
            temp_path = f.name
        
        try:
            settings = Settings(trust_registry_path=temp_path)
            registry = TrustRegistry(settings)
            
            # Should fall back to default
            assert "ocn-orca-v1" in registry.list_providers()
            
        finally:
            os.unlink(temp_path)
            
    def test_load_unsupported_format(self):
        """Test loading unsupported file format falls back to default."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("not yaml or json")
            temp_path = f.name
        
        try:
            settings = Settings(trust_registry_path=temp_path)
            registry = TrustRegistry(settings)
            
            # Should fall back to default
            assert "ocn-orca-v1" in registry.list_providers()
            stats = registry.get_stats()
            assert stats["source"] == "embedded"
                
        finally:
            os.unlink(temp_path)


class TestTrustRegistryValidation:
    """Test trust registry validation."""

    def test_validate_missing_providers_key(self):
        """Test validation falls back to default when providers key is missing."""
        invalid_data = {
            "metadata": {"version": "v0.1.0"}
            # Missing "providers" key
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_data, f)
            temp_path = f.name
        
        try:
            settings = Settings(trust_registry_path=temp_path)
            registry = TrustRegistry(settings)
            
            # Should fall back to default
            assert "ocn-orca-v1" in registry.list_providers()
            stats = registry.get_stats()
            assert stats["source"] == "embedded"
                
        finally:
            os.unlink(temp_path)
            
    def test_validate_providers_not_list(self):
        """Test validation falls back to default when providers is not a list."""
        invalid_data = {
            "metadata": {"version": "v0.1.0"},
            "providers": "not a list"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_data, f)
            temp_path = f.name
        
        try:
            settings = Settings(trust_registry_path=temp_path)
            registry = TrustRegistry(settings)
            
            # Should fall back to default
            assert "ocn-orca-v1" in registry.list_providers()
            stats = registry.get_stats()
            assert stats["source"] == "embedded"
                
        finally:
            os.unlink(temp_path)
            
    def test_validate_provider_missing_fields(self):
        """Test validation falls back to default when provider is missing required fields."""
        invalid_data = {
            "metadata": {"version": "v0.1.0"},
            "providers": [
                {
                    "id": "test-provider",
                    # Missing "name" and "status"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_data, f)
            temp_path = f.name
        
        try:
            settings = Settings(trust_registry_path=temp_path)
            registry = TrustRegistry(settings)
            
            # Should fall back to default
            assert "ocn-orca-v1" in registry.list_providers()
            stats = registry.get_stats()
            assert stats["source"] == "embedded"
                
        finally:
            os.unlink(temp_path)
            
    def test_validate_provider_invalid_status(self):
        """Test validation falls back to default when provider has invalid status."""
        invalid_data = {
            "metadata": {"version": "v0.1.0"},
            "providers": [
                {
                    "id": "test-provider",
                    "name": "Test Provider",
                    "status": "invalid_status"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_data, f)
            temp_path = f.name
        
        try:
            settings = Settings(trust_registry_path=temp_path)
            registry = TrustRegistry(settings)
            
            # Should fall back to default
            assert "ocn-orca-v1" in registry.list_providers()
            stats = registry.get_stats()
            assert stats["source"] == "embedded"
                
        finally:
            os.unlink(temp_path)


class TestTrustRegistryReload:
    """Test trust registry reload functionality."""

    def test_reload(self):
        """Test reloading trust registry."""
        # Create initial file
        initial_data = {
            "metadata": {"version": "v0.1.0"},
            "providers": [
                {
                    "id": "initial-provider",
                    "name": "Initial Provider",
                    "status": "active"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(initial_data, f)
            temp_path = f.name
        
        try:
            settings = Settings(trust_registry_path=temp_path)
            registry = TrustRegistry(settings)
            
            # Verify initial state
            assert "initial-provider" in registry.list_providers()
            
            # Update file
            updated_data = {
                "metadata": {"version": "v0.2.0"},
                "providers": [
                    {
                        "id": "updated-provider",
                        "name": "Updated Provider",
                        "status": "active"
                    }
                ]
            }
            
            with open(temp_path, 'w') as f:
                yaml.dump(updated_data, f)
            
            # Reload registry
            registry.reload()
            
            # Verify updated state
            assert "initial-provider" not in registry.list_providers()
            assert "updated-provider" in registry.list_providers()
            
        finally:
            os.unlink(temp_path)


class TestGlobalTrustRegistry:
    """Test global trust registry functions."""

    def test_get_trust_registry_singleton(self):
        """Test get_trust_registry returns singleton instance."""
        reset_trust_registry()
        
        registry1 = get_trust_registry()
        registry2 = get_trust_registry()
        
        assert registry1 is registry2
        
    def test_reset_trust_registry(self):
        """Test reset_trust_registry creates new instance."""
        registry1 = get_trust_registry()
        reset_trust_registry()
        registry2 = get_trust_registry()
        
        assert registry1 is not registry2

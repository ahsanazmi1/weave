"""
Tests for subscriber trust registry enforcement.
"""

import pytest
from fastapi.testclient import TestClient

from weave.subscriber import app
from weave.trust_registry import reset_trust_registry


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def reset_registry():
    """Reset trust registry before each test."""
    reset_trust_registry()
    yield
    reset_trust_registry()


class TestSubscriberTrustEnforcement:
    """Test trust registry enforcement in subscriber."""

    def test_cloud_event_without_provider_id_succeeds(self, client, reset_registry):
        """Test CloudEvent without provider_id is accepted."""
        event_data = {
            "specversion": "1.0",
            "id": "test-event-1",
            "source": "https://test.ocn.ai/v1",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_test_123",
            "time": "2024-01-01T12:00:00Z",
            "data": {"decision": "APPROVE", "amount": 100.0},
        }

        response = client.post("/events", json=event_data)
        assert response.status_code == 201

        data = response.json()
        assert data["receipt_id"] is not None
        assert data["trace_id"] == "txn_test_123"
        assert data["event_type"] == "ocn.orca.decision.v1"

    def test_cloud_event_with_allowed_provider_succeeds(self, client, reset_registry):
        """Test CloudEvent with allowed provider_id is accepted."""
        event_data = {
            "specversion": "1.0",
            "id": "test-event-2",
            "source": "https://test.ocn.ai/v1",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_test_456",
            "time": "2024-01-01T12:00:00Z",
            "data": {
                "decision": "APPROVE",
                "amount": 100.0,
                "provider_id": "ocn-orca-v1",  # Allowed provider
            },
        }

        response = client.post("/events", json=event_data)
        assert response.status_code == 201

        data = response.json()
        assert data["receipt_id"] is not None
        assert data["trace_id"] == "txn_test_456"

    def test_cloud_event_with_allowed_provider_in_extensions_succeeds(self, client, reset_registry):
        """Test CloudEvent with allowed provider_id in extensions is accepted."""
        event_data = {
            "specversion": "1.0",
            "id": "test-event-3",
            "source": "https://test.ocn.ai/v1",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_test_789",
            "time": "2024-01-01T12:00:00Z",
            "data": {"decision": "APPROVE", "amount": 100.0},
            "extensions": {"provider_id": "ocn-weave-v1"},  # Allowed provider in extensions
        }

        response = client.post("/events", json=event_data)
        assert response.status_code == 201

        data = response.json()
        assert data["receipt_id"] is not None
        assert data["trace_id"] == "txn_test_789"

    def test_cloud_event_with_denied_provider_returns_403(self, client, reset_registry):
        """Test CloudEvent with denied provider_id returns 403."""
        event_data = {
            "specversion": "1.0",
            "id": "test-event-4",
            "source": "https://malicious.example.com/v1",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_test_999",
            "time": "2024-01-01T12:00:00Z",
            "data": {
                "decision": "APPROVE",
                "amount": 100.0,
                "provider_id": "malicious-provider",  # Not in allowlist
            },
        }

        response = client.post("/events", json=event_data)
        assert response.status_code == 403

        data = response.json()
        assert "not in trust registry allowlist" in data["error"]
        assert "malicious-provider" in data["error"]

    def test_cloud_event_with_denied_provider_in_extensions_returns_403(
        self, client, reset_registry
    ):
        """Test CloudEvent with denied provider_id in extensions returns 403."""
        event_data = {
            "specversion": "1.0",
            "id": "test-event-5",
            "source": "https://malicious.example.com/v1",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_test_888",
            "time": "2024-01-01T12:00:00Z",
            "data": {"decision": "APPROVE", "amount": 100.0},
            "extensions": {"provider_id": "unauthorized-provider"},  # Not in allowlist
        }

        response = client.post("/events", json=event_data)
        assert response.status_code == 403

        data = response.json()
        assert "not in trust registry allowlist" in data["error"]
        assert "unauthorized-provider" in data["error"]

    def test_cloud_event_with_empty_provider_id_succeeds(self, client, reset_registry):
        """Test CloudEvent with empty provider_id is accepted (no trust check)."""
        event_data = {
            "specversion": "1.0",
            "id": "test-event-6",
            "source": "https://test.ocn.ai/v1",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_test_777",
            "time": "2024-01-01T12:00:00Z",
            "data": {"decision": "APPROVE", "amount": 100.0, "provider_id": ""},  # Empty string
        }

        response = client.post("/events", json=event_data)
        assert response.status_code == 201

        data = response.json()
        assert data["receipt_id"] is not None

    def test_cloud_event_with_none_provider_id_succeeds(self, client, reset_registry):
        """Test CloudEvent with None provider_id is accepted (no trust check)."""
        event_data = {
            "specversion": "1.0",
            "id": "test-event-7",
            "source": "https://test.ocn.ai/v1",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_test_666",
            "time": "2024-01-01T12:00:00Z",
            "data": {"decision": "APPROVE", "amount": 100.0, "provider_id": None},  # None value
        }

        response = client.post("/events", json=event_data)
        assert response.status_code == 201

        data = response.json()
        assert data["receipt_id"] is not None

    def test_multiple_allowed_providers(self, client, reset_registry):
        """Test multiple allowed providers work correctly."""
        allowed_providers = ["ocn-orca-v1", "ocn-weave-v1", "ocn-okra-v1", "test-provider"]

        for i, provider_id in enumerate(allowed_providers):
            event_data = {
                "specversion": "1.0",
                "id": f"test-event-{provider_id}-{i}",
                "source": "https://test.ocn.ai/v1",
                "type": "ocn.orca.decision.v1",
                "subject": f"txn_test_{provider_id}_{i}",
                "time": "2024-01-01T12:00:00Z",
                "data": {"decision": "APPROVE", "amount": 100.0, "provider_id": provider_id},
            }

            response = client.post("/events", json=event_data)
            assert response.status_code == 201, f"Failed for provider {provider_id}"

            data = response.json()
            assert data["receipt_id"] is not None

    def test_provider_id_takes_precedence_over_extensions(self, client, reset_registry):
        """Test that provider_id in data takes precedence over extensions."""
        event_data = {
            "specversion": "1.0",
            "id": "test-event-precedence",
            "source": "https://test.ocn.ai/v1",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_test_precedence",
            "time": "2024-01-01T12:00:00Z",
            "data": {
                "decision": "APPROVE",
                "amount": 100.0,
                "provider_id": "ocn-orca-v1",  # Allowed in data
            },
            "extensions": {"provider_id": "malicious-provider"},  # Denied in extensions
        }

        response = client.post("/events", json=event_data)
        assert response.status_code == 201  # Should succeed because data takes precedence

        data = response.json()
        assert data["receipt_id"] is not None

    def test_receipt_metadata_includes_provider_info(self, client, reset_registry):
        """Test that receipt metadata includes provider information."""
        event_data = {
            "specversion": "1.0",
            "id": "test-event-metadata",
            "source": "https://test.ocn.ai/v1",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_test_metadata",
            "time": "2024-01-01T12:00:00Z",
            "data": {"decision": "APPROVE", "amount": 100.0, "provider_id": "ocn-orca-v1"},
        }

        response = client.post("/events", json=event_data)
        assert response.status_code == 201

        # Get the receipt to check metadata
        data = response.json()
        receipt_id = data["receipt_id"]

        receipt_response = client.get(f"/receipts/{receipt_id}")
        assert receipt_response.status_code == 200

        receipt_data = receipt_response.json()
        assert "metadata" in receipt_data
        metadata = receipt_data["metadata"]
        assert metadata["provider_id"] == "ocn-orca-v1"
        assert metadata["trust_verified"] is True

    def test_receipt_metadata_without_provider(self, client, reset_registry):
        """Test that receipt metadata correctly handles missing provider."""
        event_data = {
            "specversion": "1.0",
            "id": "test-event-no-provider",
            "source": "https://test.ocn.ai/v1",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_test_no_provider",
            "time": "2024-01-01T12:00:00Z",
            "data": {
                "decision": "APPROVE",
                "amount": 100.0,
                # No provider_id
            },
        }

        response = client.post("/events", json=event_data)
        assert response.status_code == 201

        # Get the receipt to check metadata
        data = response.json()
        receipt_id = data["receipt_id"]

        receipt_response = client.get(f"/receipts/{receipt_id}")
        assert receipt_response.status_code == 200

        receipt_data = receipt_response.json()
        assert "metadata" in receipt_data
        metadata = receipt_data["metadata"]
        assert metadata["provider_id"] is None
        assert metadata["trust_verified"] is False


class TestSubscriberTrustErrorHandling:
    """Test error handling in trust registry enforcement."""

    def test_invalid_event_type_still_checked_for_trust(self, client, reset_registry):
        """Test that trust check happens before event type validation."""
        event_data = {
            "specversion": "1.0",
            "id": "test-event-invalid-type",
            "source": "https://test.ocn.ai/v1",
            "type": "invalid.event.type",  # Invalid event type
            "subject": "txn_test_invalid_type",
            "time": "2024-01-01T12:00:00Z",
            "data": {
                "decision": "APPROVE",
                "amount": 100.0,
                "provider_id": "malicious-provider",  # Denied provider
            },
        }

        response = client.post("/events", json=event_data)

        # Should return 403 for denied provider, not 400 for invalid event type
        assert response.status_code == 403

        data = response.json()
        assert "not in trust registry allowlist" in data["error"]

    def test_malformed_provider_id_handling(self, client, reset_registry):
        """Test handling of malformed provider_id values."""
        test_cases = [
            {"provider_id": 123},  # Integer instead of string
            {"provider_id": {}},  # Object instead of string
            {"provider_id": []},  # Array instead of string
        ]

        for i, provider_data in enumerate(test_cases):
            event_data = {
                "specversion": "1.0",
                "id": f"test-event-malformed-{i}",
                "source": "https://test.ocn.ai/v1",
                "type": "ocn.orca.decision.v1",
                "subject": f"txn_test_malformed_{i}",
                "time": "2024-01-01T12:00:00Z",
                "data": {"decision": "APPROVE", "amount": 100.0, **provider_data},
            }

            response = client.post("/events", json=event_data)

            # Should return 403 for invalid provider_id (converted to string)
            assert response.status_code == 403

            data = response.json()
            assert "not in trust registry allowlist" in data["error"]

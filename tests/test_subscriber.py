"""
Tests for FastAPI subscriber application.
"""

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from weave.subscriber import app, get_storage_backend
from weave.store import InMemoryStorage


@pytest.fixture
def client():
    """Create test client."""
    # Override the storage dependency to use in-memory storage for tests
    from weave.store import InMemoryStorage
    
    # Create a fresh storage instance for each test
    test_storage = InMemoryStorage()
    
    def get_test_storage():
        return test_storage
    
    app.dependency_overrides[get_storage_backend] = get_test_storage
    
    client = TestClient(app)
    yield client
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def sample_cloud_event():
    """Sample CloudEvent for testing."""
    return {
        "specversion": "1.0",
        "id": "evt_decision_001",
        "source": "https://orca.ocn.ai/v1",
        "type": "ocn.orca.decision.v1",
        "subject": "txn_abc123",
        "time": "2024-01-21T12:34:56Z",
        "datacontenttype": "application/json",
        "dataschema": "https://schemas.ocn.ai/events/v1/orca.decision.v1.schema.json",
        "data": {
            "ap2_version": "0.1.0",
            "intent": {
                "actor": {
                    "id": "user_12345",
                    "type": "user"
                },
                "channel": "web",
                "geo": {
                    "country": "US",
                    "region": "CA",
                    "city": "San Francisco"
                },
                "metadata": {}
            },
            "cart": {
                "amount": "99.99",
                "currency": "USD",
                "items": [
                    {
                        "id": "item_001",
                        "name": "Premium Widget",
                        "amount": "99.99",
                        "quantity": 1,
                        "category": "Electronics"
                    }
                ],
                "geo": {
                    "country": "US",
                    "region": "CA",
                    "city": "San Francisco"
                },
                "metadata": {}
            },
            "payment": {
                "method": "card",
                "modality": {
                    "type": "immediate",
                    "description": "One-time payment"
                },
                "auth_requirements": ["cvv"],
                "metadata": {
                    "card_type": "visa",
                    "bin": "411111"
                }
            },
            "decision": {
                "result": "APPROVE",
                "risk_score": 0.15,
                "reasons": ["low_risk_profile", "verified_user"],
                "actions": ["process_payment"],
                "meta": {
                    "rules_triggered": ["rule_low_risk_score"],
                    "model_version": "v1.0.0"
                }
            },
            "signing": {
                "vc_proof": None,
                "receipt_hash": "sha256:mock_receipt_hash"
            }
        }
    }


@pytest.fixture
def sample_explanation_event():
    """Sample explanation CloudEvent for testing."""
    return {
        "specversion": "1.0",
        "id": "evt_explanation_001",
        "source": "https://orca.ocn.ai/v1",
        "type": "ocn.orca.explanation.v1",
        "subject": "txn_abc123",
        "time": "2024-01-21T12:35:00Z",
        "datacontenttype": "application/json",
        "data": {
            "explanation_version": "0.1.0",
            "trace_id": "txn_abc123",
            "decision_id": "evt_decision_001",
            "explanation": {
                "reason": "Low risk profile with verified user identity",
                "key_signals": ["low_velocity", "verified_kyc", "familiar_merchant"],
                "mitigation": "Continue monitoring for unusual patterns",
                "confidence": 0.85
            }
        }
    }


class TestRootEndpoints:
    """Test root endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["service"] == "Weave CloudEvents Subscriber"
        assert data["version"] == "0.1.0"
        assert data["status"] == "operational"
        
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "weave-subscriber"


class TestCloudEventSubmission:
    """Test CloudEvent submission and receipt creation."""

    def test_submit_valid_decision_event(self, client, sample_cloud_event):
        """Test submitting a valid decision CloudEvent."""
        response = client.post("/events", json=sample_cloud_event)
        
        assert response.status_code == 201
        
        data = response.json()
        assert "receipt_id" in data
        assert data["trace_id"] == "txn_abc123"
        assert data["event_type"] == "ocn.orca.decision.v1"
        assert data["event_hash"].startswith("sha256:")
        assert data["status"] == "stored"
        
    def test_submit_valid_explanation_event(self, client, sample_explanation_event):
        """Test submitting a valid explanation CloudEvent."""
        response = client.post("/events", json=sample_explanation_event)
        
        assert response.status_code == 201
        
        data = response.json()
        assert "receipt_id" in data
        assert data["trace_id"] == "txn_abc123"
        assert data["event_type"] == "ocn.orca.explanation.v1"
        assert data["event_hash"].startswith("sha256:")
        
    def test_submit_event_without_subject(self, client):
        """Test submitting event without subject (should use id)."""
        event = {
            "specversion": "1.0",
            "id": "evt_test_001",
            "source": "https://orca.ocn.ai/v1",
            "type": "ocn.orca.decision.v1",
            "time": "2024-01-21T12:00:00Z",
            "data": {"test": "data"}
        }
        
        response = client.post("/events", json=event)
        assert response.status_code == 201
        
        data = response.json()
        assert data["trace_id"] == "evt_test_001"  # Should use id as trace_id
        
    def test_submit_disallowed_event_type(self, client):
        """Test submitting event with disallowed type."""
        event = {
            "specversion": "1.0",
            "id": "evt_test_001",
            "source": "https://orca.ocn.ai/v1",
            "type": "ocn.unknown.event.v1",  # Not in allowed types
            "time": "2024-01-21T12:00:00Z",
            "data": {"test": "data"}
        }
        
        response = client.post("/events", json=event)
        assert response.status_code == 400
        
        data = response.json()
        assert "not allowed" in data["error"]
        
    def test_submit_invalid_cloud_event(self, client):
        """Test submitting invalid CloudEvent structure."""
        invalid_event = {
            "id": "evt_test_001",
            # Missing required fields
        }
        
        response = client.post("/events", json=invalid_event)
        assert response.status_code == 422  # Validation error


class TestReceiptRetrieval:
    """Test receipt retrieval endpoints."""

    def test_get_receipt_by_id(self, client, sample_cloud_event):
        """Test retrieving receipt by ID."""
        # First submit an event
        submit_response = client.post("/events", json=sample_cloud_event)
        assert submit_response.status_code == 201
        
        receipt_id = submit_response.json()["receipt_id"]
        
        # Then retrieve it
        response = client.get(f"/receipts/{receipt_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["receipt_id"] == receipt_id
        assert data["trace_id"] == "txn_abc123"
        assert data["event_type"] == "ocn.orca.decision.v1"
        assert data["event_hash"].startswith("sha256:")
        
    def test_get_nonexistent_receipt(self, client):
        """Test retrieving non-existent receipt."""
        response = client.get("/receipts/nonexistent_id")
        assert response.status_code == 404
        
        data = response.json()
        assert "not found" in data["error"]
        
    def test_list_receipts(self, client, sample_cloud_event):
        """Test listing receipts."""
        # Submit a few events
        for i in range(3):
            event = sample_cloud_event.copy()
            event["id"] = f"evt_{i}"
            event["subject"] = f"txn_{i}"
            
            response = client.post("/events", json=event)
            assert response.status_code == 201
            
        # List receipts
        response = client.get("/receipts")
        assert response.status_code == 200
        
        data = response.json()
        assert "receipts" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert len(data["receipts"]) == 3
        
    def test_list_receipts_with_pagination(self, client, sample_cloud_event):
        """Test listing receipts with pagination."""
        # Submit multiple events
        for i in range(5):
            event = sample_cloud_event.copy()
            event["id"] = f"evt_{i}"
            event["subject"] = f"txn_{i}"
            
            response = client.post("/events", json=event)
            assert response.status_code == 201
            
        # List with pagination
        response = client.get("/receipts?limit=3&offset=0")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["receipts"]) == 3
        
        # Get next page
        response = client.get("/receipts?limit=3&offset=3")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["receipts"]) == 2
        
    def test_get_receipts_by_trace_id(self, client, sample_cloud_event):
        """Test retrieving receipts by trace_id."""
        trace_id = "txn_trace_test"
        
        # Submit multiple events with same trace_id
        for i in range(3):
            event = sample_cloud_event.copy()
            event["id"] = f"evt_{i}"
            event["subject"] = trace_id
            
            response = client.post("/events", json=event)
            assert response.status_code == 201
            
        # Get receipts by trace_id
        response = client.get(f"/receipts/trace/{trace_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 3
        
        # All receipts should have the same trace_id
        for receipt in data:
            assert receipt["trace_id"] == trace_id


class TestHashValidation:
    """Test that only hashes are stored, not raw data."""

    def test_only_hash_stored_not_raw_data(self, client, sample_cloud_event):
        """Test that only event hash is stored, not raw event data."""
        # Submit event
        response = client.post("/events", json=sample_cloud_event)
        assert response.status_code == 201
        
        receipt_id = response.json()["receipt_id"]
        
        # Retrieve receipt
        response = client.get(f"/receipts/{receipt_id}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify that raw event data is NOT stored
        # The receipt should only contain metadata, not the full event data
        assert "data" not in data
        assert "intent" not in data
        assert "cart" not in data
        assert "payment" not in data
        assert "decision" not in data
        
        # But should contain the hash and metadata
        assert "event_hash" in data
        assert "metadata" in data
        
        # Metadata should contain non-sensitive information
        metadata = data["metadata"]
        assert "event_id" in metadata
        assert "source" in metadata
        assert "received_at" in metadata
        
    def test_hash_consistency(self, client, sample_cloud_event):
        """Test that same event data produces same hash."""
        # Submit same event twice
        response1 = client.post("/events", json=sample_cloud_event)
        response2 = client.post("/events", json=sample_cloud_event)
        
        assert response1.status_code == 201
        assert response2.status_code == 201
        
        hash1 = response1.json()["event_hash"]
        hash2 = response2.json()["event_hash"]
        
        # Hashes should be the same for identical data
        assert hash1 == hash2

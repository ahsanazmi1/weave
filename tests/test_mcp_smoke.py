import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from fastapi import FastAPI
from mcp.server import router as mcp_router

# Create a test FastAPI app and include the MCP router
@pytest.fixture(scope="module")
def client():
    app = FastAPI()
    app.include_router(mcp_router)
    with TestClient(app) as c:
        yield c

def test_mcp_get_status(client):
    """Test MCP getStatus verb returns agent status."""
    response = client.post(
        "/mcp/invoke",
        json={"verb": "getStatus", "args": {}}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["data"]["agent"] == "weave"
    assert data["data"]["status"] == "active"

def test_mcp_list_receipts(client):
    """Test MCP listReceipts verb returns deterministic stub receipt list (empty for Weave)."""
    response = client.post(
        "/mcp/invoke",
        json={"verb": "listReceipts", "args": {}}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["data"]["agent"] == "weave"
    assert "receipts" in data["data"]
    assert isinstance(data["data"]["receipts"], list)
    assert len(data["data"]["receipts"]) == 0  # Empty list as specified for Weave
    assert "description" in data["data"]

def test_mcp_unsupported_verb(client):
    """Test MCP with unsupported verb returns error."""
    response = client.post(
        "/mcp/invoke",
        json={"verb": "unsupportedVerb", "args": {}}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert "Unsupported verb" in data["error"]

def test_mcp_missing_verb(client):
    """Test MCP with missing verb returns validation error."""
    response = client.post(
        "/mcp/invoke",
        json={"args": {}}
    )
    assert response.status_code == 422  # FastAPI validation error
    data = response.json()
    assert "detail" in data
    assert "Field required" in data["detail"][0]["msg"]

def test_mcp_invalid_json(client):
    """Test MCP with invalid JSON returns error."""
    response = client.post(
        "/mcp/invoke",
        data="invalid json"
    )
    assert response.status_code == 422  # FastAPI validation error

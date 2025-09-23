from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class MCPRequest(BaseModel):
    """MCP request model."""
    verb: str
    args: Dict[str, Any] = {}

class MCPResponse(BaseModel):
    """MCP response model."""
    ok: bool
    data: Any = None
    error: Any = None

@router.post("/mcp/invoke", response_model=MCPResponse)
async def invoke_mcp_verb(request: MCPRequest) -> MCPResponse:
    """
    Handle MCP protocol requests.

    Supported verbs:
    - getStatus: Returns agent status
    - listReceipts: Returns deterministic stub receipt list (empty for Weave)
    """
    try:
        if request.verb == "getStatus":
            return MCPResponse(ok=True, data={"agent": "weave", "status": "active"})
        elif request.verb == "listReceipts":
            # Return empty list as specified for Weave agent
            return MCPResponse(
                ok=True,
                data={
                    "agent": "weave",
                    "receipts": [],
                    "description": "Deterministic stub receipt list - empty as specified for Weave agent"
                }
            )
        else:
            return MCPResponse(ok=False, error=f"Unsupported verb: {request.verb}")
    except Exception as e:
        return MCPResponse(ok=False, error=str(e))

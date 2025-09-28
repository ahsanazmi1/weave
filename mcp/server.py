from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from weave.auction import run_auction
from weave.models import CartSummary, RailCandidate
from weave.llm.explain import is_auction_llm_configured

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
    - runAuction: Run processor auction for pay-ins (checkout)
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
                    "description": "Deterministic stub receipt list - empty as specified for Weave agent",
                },
            )
        elif request.verb == "runAuction":
            # Extract auction parameters from args
            trace_id = request.args.get("trace_id")
            if not trace_id:
                raise HTTPException(
                    status_code=400, detail="trace_id parameter is required"
                )

            # Extract cart summary
            cart_data = request.args.get("cart_summary", {})
            if not cart_data:
                raise HTTPException(
                    status_code=400, detail="cart_summary parameter is required"
                )

            cart_summary = CartSummary(
                total_amount=cart_data.get("total_amount", 0.0),
                currency=cart_data.get("currency", "USD"),
                item_count=cart_data.get("item_count", 1),
                merchant_id=cart_data.get("merchant_id", "unknown"),
                merchant_category=cart_data.get("merchant_category", "general"),
                channel=cart_data.get("channel", "online"),
            )

            # Extract rail candidates
            rail_candidates_data = request.args.get("rail_candidates", [])
            if not rail_candidates_data:
                raise HTTPException(
                    status_code=400, detail="rail_candidates parameter is required"
                )

            rail_candidates = [
                RailCandidate(
                    rail_type=rail.get("rail_type", "credit"),
                    base_cost_bps=rail.get("base_cost_bps", 150.0),
                    settlement_days=rail.get("settlement_days", 1),
                    risk_score=rail.get("risk_score", 0.3),
                )
                for rail in rail_candidates_data
            ]

            # Get deterministic seed
            deterministic_seed = request.args.get("deterministic_seed", 42)

            # Run auction
            auction_result = run_auction(
                trace_id=trace_id,
                cart_summary=cart_summary,
                rail_candidates=rail_candidates,
                deterministic_seed=deterministic_seed
            )

            # Format response
            return MCPResponse(
                ok=True,
                data={
                    "trace_id": auction_result.trace_id,
                    "auction_id": auction_result.auction_id,
                    "winning_processor": auction_result.winning_processor,
                    "winning_bid": {
                        "processor_id": auction_result.winning_bid.processor_id,
                        "bps": auction_result.winning_bid.bps,
                        "rebate_bps": auction_result.winning_bid.rebate_bps,
                        "effective_cost_bps": auction_result.effective_cost_bps,
                        "expected_settlement_days": auction_result.winning_bid.expected_settlement_days,
                        "confidence": auction_result.winning_bid.confidence,
                        "constraints": auction_result.winning_bid.constraints,
                    },
                    "all_bids": [
                        {
                            "processor_id": bid.processor_id,
                            "bps": bid.bps,
                            "rebate_bps": bid.rebate_bps,
                            "effective_cost_bps": bid.bps - bid.rebate_bps,
                            "expected_settlement_days": bid.expected_settlement_days,
                            "confidence": bid.confidence,
                            "constraints": bid.constraints,
                        }
                        for bid in auction_result.all_bids
                    ],
                    "effective_cost_bps": auction_result.effective_cost_bps,
                    "summary": auction_result.summary,
                    "timestamp": auction_result.timestamp.isoformat(),
                    "llm_configured": is_auction_llm_configured(),
                },
            )
        else:
            return MCPResponse(
                ok=False, 
                error=f"Unsupported verb: {request.verb}. Supported verbs: getStatus, listReceipts, runAuction"
            )
    except HTTPException:
        raise
    except Exception as e:
        return MCPResponse(ok=False, error=str(e))

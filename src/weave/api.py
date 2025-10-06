"""
FastAPI application for Weave auction service.
"""

from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from weave.auction import run_auction
from weave.models import CartSummary, RailCandidate
from weave.llm.explain import is_auction_llm_configured

# Import ML-enhanced auction manager
try:
    from weave.ml_enhanced_auction import get_ml_enhanced_auction_manager
    ML_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ ML models not available: {e}")
    ML_AVAILABLE = False

# Create FastAPI application
app = FastAPI(
    title="Weave Auction Service",
    description="Processor auction and bid aggregation service for the Open Checkout Network",
    version="0.3.0",
    contact={
        "name": "OCN Team",
        "email": "team@ocn.ai",
        "url": "https://github.com/ahsanazmi1/weave",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# MCP router not available in this version


class AuctionRequest(BaseModel):
    """Auction request model."""
    
    trace_id: str = Field(..., description="Trace identifier")
    cart_summary: CartSummary = Field(..., description="Cart summary")
    rail_candidates: List[RailCandidate] = Field(..., description="Available rail candidates")
    deterministic_seed: int = Field(42, description="Seed for deterministic results")


class AuctionResponse(BaseModel):
    """Auction response model."""
    
    trace_id: str = Field(..., description="Trace identifier")
    auction_id: str = Field(..., description="Auction identifier")
    winning_processor: str = Field(..., description="Winning processor ID")
    winning_bid: Dict[str, Any] = Field(..., description="Winning bid details")
    all_bids: List[Dict[str, Any]] = Field(..., description="All received bids")
    effective_cost_bps: float = Field(..., description="Effective cost (bps - rebate_bps)")
    summary: str = Field(..., description="LLM-generated auction summary")
    timestamp: str = Field(..., description="Result timestamp")
    llm_configured: bool = Field(..., description="Whether LLM is configured")


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns:
        Health status information
    """
    return {
        "status": "healthy",
        "service": "weave-auction",
        "version": "0.3.0",
        "capabilities": {
            "auction_management": True,
            "bid_aggregation": True,
            "cloud_events": True,
            "llm_explanations": is_auction_llm_configured(),
        },
    }


@app.post("/auction/run", response_model=AuctionResponse)
async def run_processor_auction(request: AuctionRequest) -> AuctionResponse:
    """
    Run processor auction for pay-ins (checkout).
    
    This endpoint provides processor auction functionality with:
    - Bid request broadcasting to Carat, Adyen, Stripe
    - Bid response aggregation and winner determination
    - CloudEvent emission for bid_request and bid_response
    - LLM-powered auction summaries
    
    Args:
        request: Auction request with cart summary and rail candidates
        
    Returns:
        Auction result with winning processor and aggregated bids
    """
    try:
        # Run auction (ML-enhanced if available)
        if ML_AVAILABLE:
            ml_manager = get_ml_enhanced_auction_manager()
            auction_result = ml_manager.run_auction(
                trace_id=request.trace_id,
                cart_summary=request.cart_summary,
                rail_candidates=request.rail_candidates
            )
        else:
            auction_result = run_auction(
                trace_id=request.trace_id,
                cart_summary=request.cart_summary,
                rail_candidates=request.rail_candidates,
                deterministic_seed=request.deterministic_seed
            )
        
        # Format winning bid
        winning_bid = {
            "processor_id": auction_result.winning_bid.processor_id,
            "bps": auction_result.winning_bid.bps,
            "rebate_bps": auction_result.winning_bid.rebate_bps,
            "effective_cost_bps": auction_result.effective_cost_bps,
            "expected_settlement_days": auction_result.winning_bid.expected_settlement_days,
            "confidence": auction_result.winning_bid.confidence,
            "constraints": auction_result.winning_bid.constraints,
        }
        
        # Format all bids
        all_bids = [
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
        ]
        
        return AuctionResponse(
            trace_id=auction_result.trace_id,
            auction_id=auction_result.auction_id,
            winning_processor=auction_result.winning_processor,
            winning_bid=winning_bid,
            all_bids=all_bids,
            effective_cost_bps=auction_result.effective_cost_bps,
            summary=auction_result.summary,
            timestamp=auction_result.timestamp.isoformat(),
            llm_configured=is_auction_llm_configured(),
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running processor auction: {str(e)}",
        ) from e


@app.get("/auction/status")
async def get_auction_status() -> Dict[str, Any]:
    """
    Get auction service status and capabilities.
    
    Returns:
        Status information including LLM configuration
    """
    return {
        "service": "weave-auction",
        "version": "0.3.0",
        "status": "operational",
        "capabilities": {
            "auction_management": True,
            "bid_aggregation": True,
            "cloud_events": True,
            "llm_explanations": is_auction_llm_configured(),
            "ml_enhancement": ML_AVAILABLE,
        },
        "processors": ["stripe", "adyen", "carat"],
        "supported_rails": ["ACH", "debit", "credit"],
        "features": {
            "deterministic_auctions": True,
            "tie_breaker_logic": True,
            "bid_validation": True,
            "event_emission": True,
        },
    }


@app.get("/ml/status")
async def get_ml_status() -> Dict[str, Any]:
    """Get ML model status and configuration."""
    if not ML_AVAILABLE:
        return {
            "ml_enabled": False,
            "error": "ML models not available"
        }
    
    try:
        from weave.ml.auction_optimization import get_auction_optimizer
        from weave.ml.bid_prediction import get_bid_predictor
        
        auction_optimizer = get_auction_optimizer()
        bid_predictor = get_bid_predictor()
        
        return {
            "ml_enabled": True,
            "ml_weight": 0.7,  # From MLEnhancedAuctionManager
            "models": {
                "auction_optimization": {
                    "loaded": auction_optimizer.is_loaded,
                    "model_type": auction_optimizer.metadata.get("model_type", "unknown"),
                    "version": auction_optimizer.metadata.get("version", "unknown"),
                    "training_date": auction_optimizer.metadata.get("trained_on", "unknown"),
                    "features": len(auction_optimizer.feature_names) if auction_optimizer.feature_names else 0
                },
                "bid_prediction": {
                    "loaded": bid_predictor.is_loaded,
                    "model_type": bid_predictor.metadata.get("model_type", "unknown"),
                    "version": bid_predictor.metadata.get("version", "unknown"),
                    "training_date": bid_predictor.metadata.get("trained_on", "unknown"),
                    "features": len(bid_predictor.feature_names) if bid_predictor.feature_names else 0
                }
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ML status: {str(e)}",
        )


@app.get("/auction/sample-request")
async def get_sample_auction_request() -> Dict[str, Any]:
    """
    Get sample auction request for testing.
    
    Returns:
        Sample auction request data
    """
    return {
        "trace_id": "sample-trace-001",
        "cart_summary": {
            "total_amount": 100.0,
            "currency": "USD",
            "item_count": 2,
            "merchant_id": "sample_merchant_001",
            "merchant_category": "general",
            "channel": "online",
        },
        "rail_candidates": [
            {
                "rail_type": "credit",
                "base_cost_bps": 150.0,
                "settlement_days": 1,
                "risk_score": 0.3,
            },
            {
                "rail_type": "debit",
                "base_cost_bps": 100.0,
                "settlement_days": 2,
                "risk_score": 0.2,
            },
            {
                "rail_type": "ACH",
                "base_cost_bps": 50.0,
                "settlement_days": 1,
                "risk_score": 0.1,
            },
        ],
        "deterministic_seed": 42,
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "weave.api:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )

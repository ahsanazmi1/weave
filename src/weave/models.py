"""
Pydantic models for Weave auction system.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CartSummary(BaseModel):
    """Cart summary for auction requests."""
    
    total_amount: float = Field(..., ge=0.0, description="Total cart amount")
    currency: str = Field("USD", description="Currency code")
    item_count: int = Field(..., ge=1, description="Number of items")
    merchant_id: str = Field(..., description="Merchant identifier")
    merchant_category: str = Field("general", description="Merchant category code")
    channel: str = Field("online", description="Transaction channel")


class RailCandidate(BaseModel):
    """Payment rail candidate for auction."""
    
    rail_type: str = Field(..., description="Rail type: ACH, debit, credit")
    base_cost_bps: float = Field(..., ge=0.0, description="Base cost in basis points")
    settlement_days: int = Field(..., ge=0, description="Expected settlement days")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Risk score (0-1)")


class BidRequest(BaseModel):
    """Bid request sent to processors."""
    
    trace_id: str = Field(..., description="Trace identifier")
    cart_summary: CartSummary = Field(..., description="Cart summary")
    rail_candidates: List[RailCandidate] = Field(..., description="Available rail candidates")
    auction_id: str = Field(..., description="Unique auction identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="Request timestamp")


class BidResponse(BaseModel):
    """Bid response from processors."""
    
    trace_id: str = Field(..., description="Trace identifier")
    processor_id: str = Field(..., description="Processor identifier")
    auction_id: str = Field(..., description="Auction identifier")
    bps: float = Field(..., ge=0.0, description="Cost in basis points")
    rebate_bps: float = Field(..., ge=0.0, description="Rebate in basis points")
    expected_settlement_days: int = Field(..., ge=0, description="Expected settlement days")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Processor constraints")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Bid confidence (0-1)")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    
    # Computed field for effective cost
    effective_cost_bps: Optional[float] = Field(None, description="Effective cost (bps - rebate_bps)")


class AuctionResult(BaseModel):
    """Result of processor auction."""
    
    trace_id: str = Field(..., description="Trace identifier")
    auction_id: str = Field(..., description="Auction identifier")
    winning_processor: str = Field(..., description="Winning processor ID")
    winning_bid: BidResponse = Field(..., description="Winning bid details")
    all_bids: List[BidResponse] = Field(..., description="All received bids")
    effective_cost_bps: float = Field(..., description="Effective cost (bps - rebate_bps)")
    summary: str = Field(..., description="LLM-generated auction summary")
    timestamp: datetime = Field(default_factory=datetime.now, description="Result timestamp")

"""
Pydantic models for Weave auction system.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field

# Define valid rail types - Extended for multi-rail support
RailType = Literal["Card", "ACH", "RTP", "FedNow", "SEPA", "Wire", "Crypto"]

# Define valid instrument types - Extended for multi-instrument support
InstrumentType = Literal[
    "credit_card", "debit_card", "prepaid_card", "bank_transfer", 
    "stablecoin", "digital_wallet", "bnpl", "cash"
]


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
    
    rail_type: RailType = Field(..., description="Rail type: Card, ACH, RTP, FedNow, SEPA, Wire, Crypto")
    instrument_type: Optional[InstrumentType] = Field(None, description="Payment instrument type")
    base_cost_bps: float = Field(..., ge=0.0, description="Base cost in basis points")
    settlement_days: int = Field(..., ge=0, description="Expected settlement days")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Risk score (0-1)")
    is_real_time: bool = Field(default=False, description="Real-time processing capability")
    is_cross_border: bool = Field(default=False, description="Cross-border capability")
    max_amount: float = Field(default=1000000.0, description="Maximum transaction amount")
    min_amount: float = Field(default=0.01, description="Minimum transaction amount")


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


# Phase 4 Enhanced Models

class PaymentInstruction(BaseModel):
    """Final payment instruction from Orca."""
    
    instruction_id: str = Field(..., description="Unique instruction identifier")
    trace_id: str = Field(..., description="Transaction trace ID")
    selected_rail: str = Field(..., description="Selected payment rail")
    selected_processor: str = Field(..., description="Selected payment processor")
    selected_instrument: str = Field(..., description="Selected payment instrument")
    amount: float = Field(..., description="Transaction amount")
    currency: str = Field(..., description="Currency code")
    effective_cost: float = Field(..., description="Total effective cost including risk")
    settlement_time_hours: int = Field(..., description="Expected settlement time")
    confidence: float = Field(..., description="Confidence in this instruction")
    explanation: str = Field(..., description="Explanation of why this instruction was chosen")
    alternatives: List[Dict[str, Any]] = Field(default_factory=list, description="Top-k alternative options")
    constraints_applied: List[Dict[str, Any]] = Field(default_factory=list, description="Applied constraints")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ProcessorAuthResult(BaseModel):
    """Processor authorization result."""
    
    auth_id: str = Field(..., description="Authorization identifier")
    processor_id: str = Field(..., description="Processor that processed the transaction")
    status: str = Field(..., description="Authorization status (approved/declined)")
    auth_code: Optional[str] = Field(None, description="Processor authorization code")
    decline_reason: Optional[str] = Field(None, description="Reason for decline if applicable")
    processor_fee: float = Field(..., description="Actual processor fee charged")
    settlement_time_actual: int = Field(..., description="Actual settlement time in hours")
    processor_metadata: Dict[str, Any] = Field(default_factory=dict, description="Processor-specific metadata")
    timestamp: datetime = Field(default_factory=datetime.now, description="Authorization timestamp")


class SignedReceipt(BaseModel):
    """Signed receipt linking payment instruction and processor result."""
    
    receipt_id: str = Field(..., description="Unique receipt identifier")
    trace_id: str = Field(..., description="Transaction trace ID")
    
    # Core transaction data
    payment_instruction: PaymentInstruction = Field(..., description="Payment instruction from Orca")
    processor_auth_result: ProcessorAuthResult = Field(..., description="Processor authorization result")
    
    # Audit trail
    auction_result: AuctionResult = Field(..., description="Auction result that led to this transaction")
    bid_requests: List[BidRequest] = Field(..., description="All bid requests sent")
    bid_responses: List[BidResponse] = Field(..., description="All bid responses received")
    
    # Signing and verification
    receipt_hash: str = Field(..., description="SHA-256 hash of receipt content")
    signature: str = Field(..., description="Digital signature of receipt hash")
    signing_key_id: str = Field(..., description="Key ID used for signing")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now, description="Receipt creation timestamp")
    verified: bool = Field(False, description="Whether receipt signature has been verified")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional receipt metadata")


class RewardVariant(BaseModel):
    """Reward variant for aggregation and scoring."""
    
    variant_id: str = Field(..., description="Unique variant identifier")
    processor_id: str = Field(..., description="Processor identifier")
    rail_type: RailType = Field(..., description="Rail type")
    reward_type: str = Field(..., description="Type of reward (rebate, discount, etc.)")
    reward_value: float = Field(..., description="Reward value")
    transaction_count: int = Field(default=0, description="Number of transactions")
    total_amount: float = Field(default=0.0, description="Total transaction amount")
    success_rate: float = Field(default=0.0, description="Success rate (0.0-1.0)")
    avg_settlement_time: float = Field(default=0.0, description="Average settlement time in hours")


class Scorecard(BaseModel):
    """Nightly scorecard for reward variants."""
    
    scorecard_id: str = Field(..., description="Unique scorecard identifier")
    date: datetime = Field(..., description="Scorecard date")
    
    # Aggregated metrics
    total_transactions: int = Field(..., description="Total transactions processed")
    total_amount: float = Field(..., description="Total transaction amount")
    avg_success_rate: float = Field(..., description="Average success rate across all variants")
    avg_settlement_time: float = Field(..., description="Average settlement time")
    
    # Variant performance
    variants: List[RewardVariant] = Field(..., description="Performance by variant")
    
    # Top performers
    top_processor: str = Field(..., description="Top performing processor")
    top_rail: str = Field(..., description="Top performing rail type")
    best_reward_type: str = Field(..., description="Best performing reward type")
    
    # Generated content
    markdown_report: str = Field(..., description="Markdown formatted scorecard")
    json_data: Dict[str, Any] = Field(default_factory=dict, description="Raw JSON data")
    
    created_at: datetime = Field(default_factory=datetime.now, description="Scorecard creation timestamp")


class GuardrailMetrics(BaseModel):
    """Guardrail metrics for drift detection."""
    
    metric_id: str = Field(..., description="Unique metric identifier")
    metric_type: str = Field(..., description="Type of metric (PSI, KS, approval_rate, etc.)")
    
    # Baseline metrics
    baseline_value: float = Field(..., description="Baseline metric value")
    baseline_date: datetime = Field(..., description="Baseline measurement date")
    baseline_sample_size: int = Field(..., description="Baseline sample size")
    
    # Current metrics
    current_value: float = Field(..., description="Current metric value")
    current_date: datetime = Field(..., description="Current measurement date")
    current_sample_size: int = Field(..., description="Current sample size")
    
    # Drift detection
    drift_score: float = Field(..., description="Drift score (PSI or KS statistic)")
    drift_threshold: float = Field(..., description="Drift threshold for alerting")
    drift_detected: bool = Field(False, description="Whether drift has been detected")
    severity: str = Field("low", description="Drift severity (low/medium/high/critical)")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now, description="Metric creation timestamp")


class GuardrailBreach(BaseModel):
    """Guardrail breach event."""
    
    breach_id: str = Field(..., description="Unique breach identifier")
    trace_id: str = Field(..., description="Related transaction trace ID")
    
    # Breach details
    guardrail_type: str = Field(..., description="Type of guardrail breached")
    metric: GuardrailMetrics = Field(..., description="Metrics that triggered the breach")
    breach_severity: str = Field(..., description="Severity of the breach")
    breach_description: str = Field(..., description="Human-readable breach description")
    
    # Rollback information
    rollback_triggered: bool = Field(False, description="Whether rollback was triggered")
    rollback_pr_url: Optional[str] = Field(None, description="URL of rollback PR")
    rollback_status: str = Field("pending", description="Rollback status")
    
    # Resolution
    resolved: bool = Field(False, description="Whether breach has been resolved")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")
    
    created_at: datetime = Field(default_factory=datetime.now, description="Breach creation timestamp")
    resolved_at: Optional[datetime] = Field(None, description="Breach resolution timestamp")

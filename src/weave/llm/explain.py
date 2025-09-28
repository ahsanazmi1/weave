"""
LLM explanation generation for Weave auction results.

Provides optional LLM-powered explanations for auction outcomes and processor selection.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from weave.models import AuctionResult, BidResponse, CartSummary

logger = logging.getLogger(__name__)


class AuctionExplanationRequest(BaseModel):
    """Request for LLM auction explanation generation."""
    
    auction_result: AuctionResult = Field(..., description="Auction result")
    cart_summary: CartSummary = Field(..., description="Cart summary")
    merchant_context: Optional[Dict[str, Any]] = Field(None, description="Merchant context")


class AuctionExplanationResponse(BaseModel):
    """Response from LLM auction explanation generation."""
    
    summary: str = Field(..., description="LLM-generated auction summary")
    key_factors: List[str] = Field(default_factory=list, description="Key factors in decision")
    processor_comparison: Dict[str, str] = Field(default_factory=dict, description="Processor comparison")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Explanation confidence")
    model_used: str = Field(..., description="LLM model used for explanation")


class AuctionLLMExplainer:
    """LLM explainer for auction results."""
    
    def __init__(self):
        """Initialize the LLM explainer."""
        self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_openai_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "weave-llm")
        self.azure_openai_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        
        self.is_configured = bool(
            self.azure_openai_endpoint and 
            self.azure_openai_key and 
            self.azure_openai_deployment
        )
        
        if self.is_configured:
            logger.info(f"Auction LLM Explainer configured with deployment: {self.azure_openai_deployment}")
        else:
            logger.info("Auction LLM Explainer not configured - using fallback explanations")
    
    def get_configuration_status(self) -> Dict[str, Any]:
        """Get the configuration status of the LLM explainer."""
        return {
            "configured": self.is_configured,
            "endpoint": self.azure_openai_endpoint is not None,
            "api_key": self.azure_openai_key is not None,
            "deployment": self.azure_openai_deployment,
            "version": self.azure_openai_version,
        }
    
    def explain_auction_result(self, request: AuctionExplanationRequest) -> Optional[AuctionExplanationResponse]:
        """
        Generate LLM explanation for auction result.
        
        Args:
            request: Auction explanation request
            
        Returns:
            LLM explanation response or None if not configured
        """
        if not self.is_configured:
            return None
        
        try:
            # Prepare context for LLM
            auction_data = {
                "winning_processor": request.auction_result.winning_processor,
                "winning_bid": {
                    "bps": request.auction_result.winning_bid.bps,
                    "rebate_bps": request.auction_result.winning_bid.rebate_bps,
                    "effective_cost_bps": request.auction_result.effective_cost_bps,
                    "settlement_days": request.auction_result.winning_bid.expected_settlement_days,
                    "confidence": request.auction_result.winning_bid.confidence,
                },
                "all_bids": [
                    {
                        "processor_id": bid.processor_id,
                        "bps": bid.bps,
                        "rebate_bps": bid.rebate_bps,
                        "effective_cost_bps": bid.bps - bid.rebate_bps,
                        "settlement_days": bid.expected_settlement_days,
                        "confidence": bid.confidence,
                    }
                    for bid in request.auction_result.all_bids
                ],
                "cart_summary": {
                    "total_amount": request.cart_summary.total_amount,
                    "currency": request.cart_summary.currency,
                    "item_count": request.cart_summary.item_count,
                    "merchant_category": request.cart_summary.merchant_category,
                },
                "merchant_context": request.merchant_context or {},
            }
            
            # Create prompt for LLM
            prompt = self._create_auction_explanation_prompt(auction_data)
            
            # Call Azure OpenAI (stub implementation)
            # In a real implementation, this would make an actual API call
            explanation = self._generate_llm_explanation(prompt, auction_data)
            
            return AuctionExplanationResponse(
                summary=explanation["summary"],
                key_factors=explanation["key_factors"],
                processor_comparison=explanation["processor_comparison"],
                confidence=explanation["confidence"],
                model_used=f"azure-openai-{self.azure_openai_deployment}",
            )
            
        except Exception as e:
            logger.error(f"LLM auction explanation generation failed: {e}")
            return None
    
    def _create_auction_explanation_prompt(self, auction_data: Dict[str, Any]) -> str:
        """Create prompt for auction explanation."""
        return f"""
You are an expert in payment processing and auction analysis. 

Analyze the following processor auction data and provide a clear, concise explanation of the auction outcome:

Winning Processor: {auction_data['winning_processor']}
Winning Bid: {auction_data['winning_bid']['bps']:.1f} bps - {auction_data['winning_bid']['rebate_bps']:.1f} bps rebate = {auction_data['winning_bid']['effective_cost_bps']:.1f} bps effective
Settlement: {auction_data['winning_bid']['settlement_days']} days
Confidence: {auction_data['winning_bid']['confidence']:.2f}

All Bids:
{json.dumps(auction_data['all_bids'], indent=2)}

Cart Summary:
- Amount: {auction_data['cart_summary']['total_amount']} {auction_data['cart_summary']['currency']}
- Items: {auction_data['cart_summary']['item_count']}
- Category: {auction_data['cart_summary']['merchant_category']}

Provide a structured explanation in JSON format with:
1. "summary": A clear, human-readable explanation of why this processor won
2. "key_factors": List of key factors that influenced the decision
3. "processor_comparison": Object comparing the winning processor to others
4. "confidence": Confidence score for the explanation (0-1)

Focus on:
- Why this processor was selected over others
- Key differentiators (cost, settlement speed, confidence)
- How the auction mechanics worked
- Specific advantages of the winning bid
"""

    def _generate_llm_explanation(self, prompt: str, auction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate LLM explanation (stub implementation).
        
        In a real implementation, this would call Azure OpenAI API.
        """
        # Stub implementation - generate deterministic explanation based on auction data
        winning_processor = auction_data["winning_processor"]
        winning_bid = auction_data["winning_bid"]
        all_bids = auction_data["all_bids"]
        
        # Identify key factors
        key_factors = []
        if winning_bid["rebate_bps"] > 5.0:
            key_factors.append("competitive rebate structure")
        if winning_bid["settlement_days"] == 1:
            key_factors.append("fast settlement")
        if winning_bid["confidence"] > 0.9:
            key_factors.append("high confidence bid")
        
        # Find runner-up for comparison
        other_bids = [b for b in all_bids if b["processor_id"] != winning_processor]
        if other_bids:
            runner_up = min(other_bids, key=lambda b: b["effective_cost_bps"])
            cost_advantage = runner_up["effective_cost_bps"] - winning_bid["effective_cost_bps"]
        else:
            cost_advantage = 0.0
        
        # Generate summary
        summary_parts = [
            f"{winning_processor.title()} won the auction with {winning_bid['effective_cost_bps']:.1f} bps effective cost"
        ]
        
        if winning_bid["rebate_bps"] > 0:
            summary_parts.append(f"({winning_bid['bps']:.1f} bps - {winning_bid['rebate_bps']:.1f} bps rebate)")
        
        if winning_bid["settlement_days"] == 1:
            summary_parts.append("and 1-day settlement")
        else:
            summary_parts.append(f"and {winning_bid['settlement_days']}-day settlement")
        
        if cost_advantage > 0.1:
            summary_parts.append(f"(saving {cost_advantage:.1f} bps vs runner-up)")
        
        summary = " ".join(summary_parts) + "."
        
        # Processor comparison
        processor_comparison = {}
        for bid in all_bids:
            if bid["processor_id"] != winning_processor:
                advantage = bid["effective_cost_bps"] - winning_bid["effective_cost_bps"]
                if advantage > 0:
                    processor_comparison[bid["processor_id"]] = f"{advantage:.1f} bps more expensive"
                else:
                    processor_comparison[bid["processor_id"]] = f"{abs(advantage):.1f} bps cheaper but lost on other factors"
        
        return {
            "summary": summary,
            "key_factors": key_factors,
            "processor_comparison": processor_comparison,
            "confidence": 0.85,  # High confidence for deterministic explanations
        }


def is_auction_llm_configured() -> bool:
    """Check if auction LLM is configured."""
    explainer = AuctionLLMExplainer()
    return explainer.is_configured


def explain_auction_result_llm(
    auction_result: AuctionResult,
    cart_summary: CartSummary,
    merchant_context: Optional[Dict[str, Any]] = None
) -> Optional[AuctionExplanationResponse]:
    """
    Generate LLM explanation for auction result.
    
    Args:
        auction_result: Auction result
        cart_summary: Cart summary information
        merchant_context: Merchant context information
        
    Returns:
        LLM explanation response or None if not configured
    """
    explainer = AuctionLLMExplainer()
    
    request = AuctionExplanationRequest(
        auction_result=auction_result,
        cart_summary=cart_summary,
        merchant_context=merchant_context
    )
    
    return explainer.explain_auction_result(request)

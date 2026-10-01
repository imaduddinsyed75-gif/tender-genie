from typing import TypedDict, Dict, Any, List, Optional
from pydantic import BaseModel, Field

# --- Pydantic Models for Structured Data Extraction ---

class ScopeDeliverable(BaseModel):
    title: str = Field(description="Deliverable or task title")
    description: str = Field(description="Description of what is expected")
    timeline: Optional[str] = Field(description="Expected completion or delivery timeframe")

class ParsedScope(BaseModel):
    project_title: str
    submission_deadline: str
    client_name: Optional[str] = None
    technical_requirements: List[str] = Field(default_factory=list)
    deliverables: List[ScopeDeliverable] = Field(default_factory=list)
    budget_hints: Optional[str] = None

class RiskFlag(BaseModel):
    clause: str = Field(description="Contract clause or SLA condition")
    severity: str = Field(description="Risk Level: Red (High), Yellow (Medium), Green (Low)")
    penalty_details: Optional[str] = Field(description="Financial or operational consequence")
    mitigation_strategy: str = Field(description="Suggested defense or response")

class ComplianceReport(BaseModel):
    summary: str
    risk_flags: List[RiskFlag] = Field(default_factory=list)
    is_eligible: bool = True

class PricingItem(BaseModel):
    item_name: str
    estimated_hours_or_units: float
    unit_rate_usd: float
    total_usd: float

class PricingEstimate(BaseModel):
    items: List[PricingItem] = Field(default_factory=list)
    subtotal_usd: float
    recommended_margin_pct: float
    final_bid_amount_usd: float

# --- LangGraph Shared State ---

class TenderState(TypedDict):
    raw_text: str                          # Raw text from PDF parser (Shamir)
    parsed_scope: Optional[Dict[str, Any]] # Structured data extracted by Parser Agent
    compliance_report: Optional[Dict[str, Any]] # Output from Abdur Rehman's Risk Auditor
    pricing_estimate: Optional[Dict[str, Any]]  # Output from Abdur Rehman's Pricing Engine
    final_proposal: Optional[str]          # Drafted markdown proposal text (Imad)
    current_status: str                    # Status tag for Streamlit UI tracking (Malaika/Mehak)
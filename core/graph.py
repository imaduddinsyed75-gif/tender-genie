"""
Core LangGraph Orchestration Engine for TenderGenie.
Maintained by: Syed Imad Uddin (Lead)
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from core.state import TenderState

# --- Node 1: Ingestion & Parser Node (Placeholder for Shamir's Module) ---
def parser_node(state: TenderState) -> Dict[str, Any]:
    print("[LOG] Running Parser Node...")
    raw_text = state.get("raw_text", "")
    
    # Baseline logic jab tak Shamir ka parser attach nahi hota
    parsed_scope = {
        "project_title": "Enterprise Cloud Migration RFP",
        "submission_deadline": "2026-10-25",
        "technical_requirements": [
            "AWS Multi-region high availability",
            "Zero downtime database migration",
            "SOC2 compliance"
        ],
        "deliverables": [
            {"title": "Architecture Blueprint", "description": "Cloud infra diagram", "timeline": "Week 2"},
            {"title": "Migration Execution", "description": "Data sync and validation", "timeline": "Week 4"}
        ]
    }
    return {
        "parsed_scope": parsed_scope,
        "current_status": "Document Parsed Successfully"
    }

# --- Node 2: Compliance Auditor Node (Placeholder for Abdur Rehman's Module) ---
def compliance_node(state: TenderState) -> Dict[str, Any]:
    print("[LOG] Running Compliance Auditor Node...")
    # Abdur Rehman ka compliance agent yahan actual check karega
    compliance_report = {
        "summary": "Tender is eligible with 1 medium SLA penalty risk identified.",
        "risk_flags": [
            {
                "clause": "Section 4.2 - SLA Downtime Penalty",
                "severity": "Yellow",
                "penalty_details": "1% cost reduction per hour of unscheduled downtime",
                "mitigation_strategy": "Include automated failover architecture in technical proposal."
            }
        ],
        "is_eligible": True
    }
    return {
        "compliance_report": compliance_report,
        "current_status": "Compliance Audit Complete"
    }

# --- Node 3: Pricing Estimator Node (Placeholder for Abdur Rehman's Module) ---
def pricing_node(state: TenderState) -> Dict[str, Any]:
    print("[LOG] Running Pricing Estimator Node...")
    pricing_estimate = {
        "items": [
            {"item_name": "Cloud Architect Lead", "estimated_hours_or_units": 80, "unit_rate_usd": 120, "total_usd": 9600},
            {"item_name": "DevOps Engineers (x2)", "estimated_hours_or_units": 160, "unit_rate_usd": 75, "total_usd": 12000},
            {"item_name": "Security & QA", "estimated_hours_or_units": 40, "unit_rate_usd": 65, "total_usd": 2600}
        ],
        "subtotal_usd": 24200,
        "recommended_margin_pct": 20,
        "final_bid_amount_usd": 29040
    }
    return {
        "pricing_estimate": pricing_estimate,
        "current_status": "Pricing Estimation Complete"
    }

# --- Node 4: Proposal Drafter Node (Lead / Imad) ---
def drafter_node(state: TenderState) -> Dict[str, Any]:
    print("[LOG] Running Proposal Drafter Node...")
    scope = state.get("parsed_scope", {})
    comp = state.get("compliance_report", {})
    price = state.get("pricing_estimate", {})
    
    # Executive markdown proposal compile karna
    proposal = f"""# PROPOSAL RESPONSE: {scope.get('project_title', 'Enterprise Solution')}

## 1. Executive Summary
We are pleased to submit our formal response to this request for proposal. Our engineering team brings end-to-end expertise aligned with your technical mandates.

## 2. Compliance & Risk Mitigation
- **Audit Status:** {'Eligible' if comp.get('is_eligible') else 'Requires Review'}
- **Key Note:** {comp.get('summary', 'No critical flags detected.')}

## 3. Commercials & Costing Summary
- **Subtotal:** ${price.get('subtotal_usd', 0):,.2f}
- **Recommended Margin:** {price.get('recommended_margin_pct', 0)}%
- **Final Bid Amount:** ${price.get('final_bid_amount_usd', 0):,.2f}

## 4. Scope Deliverables
"""
    for d in scope.get("deliverables", []):
        proposal += f"- **{d['title']}**: {d['description']} ({d.get('timeline', 'TBD')})\n"
        
    return {
        "final_proposal": proposal,
        "current_status": "Proposal Draft Generated Successfully"
    }

# --- StateGraph Construction & Compilation ---

def build_tender_graph():
    builder = StateGraph(TenderState)
    
    # Register Nodes
    builder.add_node("parser_node", parser_node)
    builder.add_node("compliance_node", compliance_node)
    builder.add_node("pricing_node", pricing_node)
    builder.add_node("drafter_node", drafter_node)
    
    # Define Sequential Edges
    builder.set_entry_point("parser_node")
    builder.add_edge("parser_node", "compliance_node")
    builder.add_edge("compliance_node", "pricing_node")
    builder.add_edge("pricing_node", "drafter_node")
    builder.add_edge("drafter_node", END)
    
    return builder.compile()

# Global compiled app
tender_pipeline = build_tender_graph()
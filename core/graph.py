"""
Core LangGraph Orchestration Engine for TenderGenie.
Maintained by: Syed Imad Uddin (Lead)
"""

import os
import json
from typing import Dict, Any
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from core.state import TenderState
# Shamir ke parser module se function import
try:
    from core.parser import parse_tender_scope
except ImportError:
    parse_tender_scope = None

# Load environment variables
load_dotenv()

# LLM Initialization with Safe Fallback
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
else:
    llm = None

# --- Node 1: Ingestion & Parser Node ---
def parser_node(state: TenderState) -> Dict[str, Any]:
    print("[LOG] Running Parser Node...")
    
    # Check 1: Agar scope pehle se processed hai to skip karein
    existing_scope = state.get("parsed_scope")
    if existing_scope:
        return {"current_status": "Document Scope Already Present"}

    raw_text = state.get("raw_text", "")
    
    # Check 2: Agar Shamir ka parser available hai aur raw_text moujood hai
    if parse_tender_scope and raw_text and raw_text != "sample rfp":
        try:
            parsed = parse_tender_scope(raw_text)
            # Agar parser Pydantic model return kare to dict bana lein
            parsed_dict = parsed.model_dump() if hasattr(parsed, "model_dump") else dict(parsed)
            return {
                "parsed_scope": parsed_dict,
                "current_status": "Document Scope Extracted via PyMuPDF Parser"
            }
        except Exception as e:
            print(f"[WARN] Parser execution failed, using baseline: {e}")

    # Fallback default structure (testing ke liye jab text na diya ho)
    default_scope = {
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
        "parsed_scope": default_scope,
        "current_status": "Document Scope Extracted (Baseline)"
    }

# --- Node 2: Compliance Auditor Node ---
def compliance_node(state: TenderState) -> Dict[str, Any]:
    print("[LOG] Running Compliance Auditor Node...")
    
    # Try Abdur Rehman's adapter
    try:
        from agents.adapter import build_compliance_report
        report = build_compliance_report(state)
        if report:
            return {
                "compliance_report": report,
                "current_status": "Compliance Audit Complete (via Agent)"
            }
    except Exception as e:
        print(f"[WARN] Compliance adapter failed, using baseline: {e}")

    # Baseline fallback
    default_compliance = {
        "summary": "Tender is eligible. 1 SLA penalty risk identified regarding downtime.",
        "risk_flags": [
            {
                "clause": "Section 4.2 - SLA Downtime Penalty",
                "severity": "Yellow",
                "penalty_details": "1% cost reduction per hour of unscheduled downtime",
                "mitigation_strategy": "Include automated multi-AZ failover architecture in proposal."
            }
        ],
        "is_eligible": True
    }
    return {
        "compliance_report": default_compliance,
        "current_status": "Compliance Audit Complete (Baseline)"
    }


# --- Node 3: Pricing Estimator Node ---
def pricing_node(state: TenderState) -> Dict[str, Any]:
    print("[LOG] Running Pricing Estimator Node...")
    
    # Try Abdur Rehman's adapter
    try:
        from agents.adapter import build_pricing_estimate
        estimate = build_pricing_estimate(state)
        if estimate:
            return {
                "pricing_estimate": estimate,
                "current_status": "Pricing Estimation Complete (via Agent)"
            }
    except Exception as e:
        print(f"[WARN] Pricing adapter failed, using baseline: {e}")

    # Baseline fallback
    default_pricing = {
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
        "pricing_estimate": default_pricing,
        "current_status": "Pricing Estimation Complete (Baseline)"
    }

# --- Node 4: Proposal Drafter Node (Lead - Imad) ---
def drafter_node(state: TenderState) -> Dict[str, Any]:
    print("[LOG] Running AI Proposal Drafter Node...")
    scope = state.get("parsed_scope", {})
    comp = state.get("compliance_report", {})
    price = state.get("pricing_estimate", {})

    if llm:
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are an executive enterprise bid proposal writer. Synthesize the scope, compliance review, and commercial pricing into an executive winning RFP response proposal in formal Markdown."),
            ("human", "TENDER SCOPE:\n{scope}\n\nCOMPLIANCE:\n{compliance}\n\nPRICING:\n{pricing}")
        ])
        chain = prompt_template | llm | StrOutputParser()
        try:
            generated_proposal = chain.invoke({
                "scope": json.dumps(scope, indent=2),
                "compliance": json.dumps(comp, indent=2),
                "pricing": json.dumps(price, indent=2)
            })
        except Exception as e:
            generated_proposal = f"# Proposal Draft (Offline Mode)\nAPI Call failed: {e}"
    else:
        # Fallback offline generator jab API key configured na ho
        generated_proposal = f"""# PROPOSAL RESPONSE: {scope.get('project_title', 'Enterprise Solution')}

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
            proposal = f"- **{d['title']}**: {d['description']} ({d.get('timeline', 'TBD')})\n"
            generated_proposal += proposal

    return {
        "final_proposal": generated_proposal,
        "current_status": "Proposal Draft Generated Successfully"
    }
# --- StateGraph Construction & Compilation ---
def build_tender_graph():
    builder = StateGraph(TenderState)
    
    # Nodes add karein
    builder.add_node("parser_node", parser_node)
    builder.add_node("compliance_node", compliance_node)
    builder.add_node("pricing_node", pricing_node)
    builder.add_node("drafter_node", drafter_node)
    
    # Workflow flow (Edges)
    builder.set_entry_point("parser_node")
    builder.add_edge("parser_node", "compliance_node")
    builder.add_edge("compliance_node", "pricing_node")
    builder.add_edge("pricing_node", "drafter_node")
    builder.add_edge("drafter_node", END)
    
    return builder.compile()

# Global export for pipeline
tender_pipeline = build_tender_graph()
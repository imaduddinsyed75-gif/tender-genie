from statistics import median

from agents.compliance import run_compliance_audit
from agents.pricing import compute_tiers, run_pricing, sla_stress_test


USD_PER_PKR = 1 / 280  # approximate, configurable


def build_compliance_report(state: dict) -> dict:
    audit_state = run_compliance_audit({"extracted_text": state["raw_text"]})
    matrix = audit_state["compliance_matrix"]
    risk_counts = {level: sum(item["risk_level"] == level for item in matrix) for level in ("RED", "YELLOW", "GREEN")}
    severity_map = {"RED": "Red", "YELLOW": "Yellow", "GREEN": "Green"}
    return {
        "summary": (
            f"{risk_counts['RED']} RED, {risk_counts['YELLOW']} YELLOW, "
            f"{risk_counts['GREEN']} GREEN risks identified."
        ),
        "risk_flags": [
            {
                "clause": item["clause"],
                "severity": severity_map[item["risk_level"]],
                "penalty_details": item["excerpt"],
                "mitigation_strategy": item["mitigation"],
            }
            for item in matrix
        ],
        "is_eligible": True,
        "compliance_matrix": matrix,
        "risk_counts": risk_counts,
    }


def build_pricing_estimate(state: dict) -> dict:
    raw_text = state.get("raw_text", "")
    if raw_text.strip():
        pricing_state = run_pricing(
            {"extracted_text": raw_text, "extracted_tables": []}
        )
        boq_items = pricing_state["boq_items"]
    else:
        boq_items = []

    tiers = compute_tiers(boq_items)
    expected_total_pkr = tiers["expected"]["grand_total"]
    stress_test = sla_stress_test(expected_total_pkr, 0.5, 14)
    margins = [float(item["margin_pct"]) for item in boq_items]
    recommended_margin_pct = median(margins) if margins else 0
    items = [
        {
            "item_name": item["item"],
            "estimated_hours_or_units": item["qty"],
            "unit_rate_usd": item["unit_cost"] * (1 + item["margin_pct"] / 100) * USD_PER_PKR,
            "total_usd": item["total"] * USD_PER_PKR,
        }
        for item in boq_items
    ]
    return {
        "items": items,
        "subtotal_usd": sum(item["qty"] * item["unit_cost"] for item in boq_items) * USD_PER_PKR,
        "recommended_margin_pct": recommended_margin_pct,
        "final_bid_amount_usd": sum(item["total"] for item in boq_items) * USD_PER_PKR,
        "boq_items": boq_items,
        "tiers": tiers,
        "sla_stress_test": stress_test,
        "currency": "PKR",
        "usd_per_pkr": USD_PER_PKR,
    }

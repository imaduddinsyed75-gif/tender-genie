import re
from statistics import median
from typing import Any

from agents.memory import query_similar
from agents.schemas import BOQItem


MAX_DISTANCE = 1.0
RELATIVE_BAND = 0.15

_KEYWORDS = (
    "firewall",
    "switch",
    "router",
    "cloud hosting",
    "security audit",
    "penetration test",
    "software development",
    "support",
    "training",
    "installation",
)

_KEYWORD_DISPLAY_NAMES = {
    "firewall": "Firewall",
    "switch": "Network Switch",
    "router": "Network Router",
    "cloud hosting": "Cloud Hosting",
    "security audit": "Security Audit",
    "penetration test": "Penetration Test",
    "software development": "Software Development",
    "support": "Support Services",
    "training": "Training Services",
    "installation": "Installation Services",
}


def extract_line_items(state: dict[str, Any]) -> list[dict]:
    tables = state.get("extracted_tables") or []
    line_items: list[dict] = []
    for row in tables:
        if not isinstance(row, dict):
            continue
        item = row.get("item") or row.get("description")
        quantity = row.get("quantity")
        if item is not None and quantity is not None:
            line_items.append({"item": str(item), "qty": float(quantity)})
    if line_items:
        return line_items

    text = str(state.get("extracted_text", ""))
    for keyword in _KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", text, re.IGNORECASE):
            line_items.append({"item": _KEYWORD_DISPLAY_NAMES[keyword], "qty": 1.0})
    if line_items:
        return line_items

    return [
        {"item": "Professional services", "qty": 1.0},
        {"item": "Implementation and configuration", "qty": 1.0},
        {"item": "Support and maintenance", "qty": 1.0},
    ]


def _is_relevant_match(item_name: str, match: dict) -> bool:
    item_name = item_name.lower()
    query_terms = [term for term in re.findall(r"[a-z0-9]+", item_name) if len(term) >= 4]
    match_text = " ".join(
        str(match.get(key, "")).lower() for key in ("item", "category", "notes")
    )
    match_terms = [
        term for term in re.findall(r"[a-z0-9]+", match_text) if len(term) >= 4
    ]
    query_prefixes = {term[:5] for term in query_terms}
    match_prefixes = {term[:5] for term in match_terms}
    return bool(
        query_prefixes & match_prefixes
        or any(
            query_term in match_term or match_term in query_term
            for query_term in query_terms
            for match_term in match_terms
        )
    )


def run_pricing(state: dict[str, Any]) -> dict[str, Any]:
    boq_items: list[BOQItem] = []
    for line_item in extract_line_items(state):
        item_name = line_item["item"]
        matches = [
            match
            for match in query_similar(item_name, k=3, only_won=True)
            if float(match.get("distance", float("inf"))) <= MAX_DISTANCE
            and _is_relevant_match(item_name, match)
        ]
        if matches:
            best_distance = min(float(match["distance"]) for match in matches)
            matches = [
                match
                for match in matches
                if float(match["distance"]) <= best_distance * (1 + RELATIVE_BAND)
            ]
        if matches:
            unit_cost = float(median(float(match["unit_cost_pkr"]) for match in matches))
            margin_pct = float(median(float(match["margin_pct"]) for match in matches))
        else:
            unit_cost = 0.0
            margin_pct = 0.0
            item_name = f"{item_name} [USER INPUT REQUIRED]"
        boq_items.append(
            BOQItem(
                item=item_name,
                qty=float(line_item.get("qty", 1)),
                unit_cost=unit_cost,
                margin_pct=margin_pct,
                total=0.0,
            )
        )

    state["boq_items"] = [item.model_dump() for item in boq_items]
    return state


def recalc_boq(boq_items: list, margin_pct: float) -> list[dict]:
    return [
        BOQItem(
            item=item["item"],
            qty=float(item["qty"]),
            unit_cost=float(item["unit_cost"]),
            margin_pct=margin_pct,
            total=0.0,
        ).model_dump()
        for item in boq_items
    ]


def compute_tiers(boq_items: list) -> dict:
    tiers = {}
    for name, multiplier in (
        ("optimistic", 0.90),
        ("expected", 1.00),
        ("conservative", 1.10),
    ):
        items = [
            BOQItem(
                item=item["item"],
                qty=float(item["qty"]),
                unit_cost=float(item["unit_cost"]) * multiplier,
                margin_pct=float(item["margin_pct"]),
                total=0.0,
            ).model_dump()
            for item in boq_items
        ]
        tiers[name] = {
            "items": items,
            "grand_total": sum(item["total"] for item in items),
        }
    return tiers


def sla_stress_test(
    contract_value: float,
    penalty_pct_per_day: float,
    delay_days: int,
    cap_pct: float | None = None,
) -> dict:
    penalty_amount = contract_value * (penalty_pct_per_day / 100) * delay_days
    if cap_pct is not None:
        penalty_amount = min(penalty_amount, contract_value * (cap_pct / 100))
    margin_amount = contract_value * 0.20
    return {
        "penalty_amount": penalty_amount,
        "percent_of_contract": round(
            (penalty_amount / contract_value * 100) if contract_value else 0,
            2,
        ),
        "margin_wiped": penalty_amount >= margin_amount,
    }

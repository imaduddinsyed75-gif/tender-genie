import re
from typing import Any

from agents.schemas import ComplianceItem


RULES = [
    {
        "name": "Liquidated damages",
        "regex": r"(?i:\bliquidated damages?\b)|\bLD\b",
        "case_sensitive": True,
        "category": "Liquidated damages",
        "risk_level": "RED",
        "mitigation": "Request a clear aggregate cap and limit on liquidated damages.",
    },
    {
        "name": "Sub-contracting prohibited",
        "regex": r"\bsub[- ]contract(?:ing)?\b[^.!?]{0,100}\b(?:prohibited|not allowed|not permitted)\b",
        "category": "Sub-contracting",
        "risk_level": "RED",
        "mitigation": "Seek approval for qualified subcontractors or clarify permitted specialist support.",
    },
    {
        "name": "Mandatory certification",
        "regex": r"(?=[^.!?]{0,200}\b(?:mandatory|required|must)\b)[^.!?]{0,200}\b(?:ISO\s*9001|ISO\s*27001|PEC|NTN|SECP)\b",
        "category": "Certifications and registration",
        "risk_level": "RED",
        "mitigation": "Confirm that the required certification or registration is current and available.",
    },
    {
        "name": "Uptime requirement of 99.9% or higher",
        "regex": r"(?:(?:uptime|availability)[^.!?]{0,100}\b(?:99\.9\d*|100(?:\.0+)?)\s*%|(?:99\.9\d*|100(?:\.0+)?)\s*%[^.!?]{0,100}\b(?:uptime|availability))",
        "category": "Service levels",
        "risk_level": "YELLOW",
        "mitigation": "Validate the service-level target, exclusions, monitoring, and service credits.",
    },
    {
        "name": "Payment terms over 90 days net",
        "regex": r"\b(?:(?:9[1-9]|[1-9]\d{2,})\s*days?\s*net|(?:more than|over|exceeding|greater than)\s*90\s*days?\s*net)\b",
        "category": "Payment terms",
        "risk_level": "YELLOW",
        "mitigation": "Negotiate shorter payment terms or include milestone payments and financing protection.",
    },
    {
        "name": "Penalty charged per day or week",
        "regex": r"\bpenalt(?:y|ies)\b[^.!?]{0,100}\b(?:per|each)\s+(?:day|week)\b",
        "category": "Penalties",
        "risk_level": "YELLOW",
        "mitigation": "Clarify the penalty trigger, maximum exposure, cure period, and dispute process.",
    },
]


def split_pages(text: str) -> list[tuple[int, str]]:
    """Split extracted text into numbered pages using ``[PAGE n]`` markers."""
    markers = list(re.finditer(r"\[PAGE\s+(\d+)\]", text, re.IGNORECASE))
    if not markers:
        return [(1, text)]

    pages: list[tuple[int, str]] = []
    if text[: markers[0].start()].strip():
        pages.append((1, text[: markers[0].start()]))

    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        pages.append((int(marker.group(1)), text[marker.end() : end]))
    return pages


def _sentence_bounds(text: str, position: int) -> tuple[int, int]:
    start = max(text.rfind(".", 0, position), text.rfind("!", 0, position), text.rfind("?", 0, position))
    end_candidates = [index for index in (text.find(".", position), text.find("!", position), text.find("?", position)) if index >= 0]
    end = min(end_candidates) + 1 if end_candidates else len(text)
    return start + 1, end


def _sentence_around(text: str, position: int) -> str:
    start, end = _sentence_bounds(text, position)
    return text[start:end].strip()


def _has_liquidated_damages_cap(text: str, position: int) -> bool:
    _, sentence_end = _sentence_bounds(text, position)
    next_start = sentence_end
    while next_start < len(text) and text[next_start].isspace():
        next_start += 1
    _, next_end = _sentence_bounds(text, next_start)
    sentences = text[_sentence_bounds(text, position)[0] : sentence_end]
    sentences += text[next_start:next_end]
    return re.search(
        r"\b(?:capped at|maximum of|not exceed|up to a maximum|limited to)\b",
        sentences,
        re.IGNORECASE,
    ) is not None


def _excerpt_around(text: str, start: int, end: int) -> str:
    excerpt_start = max(0, start - 100)
    excerpt_end = min(len(text), end + 100)
    return " ".join(text[excerpt_start:excerpt_end].split())


def scan_rules(text: str) -> list[ComplianceItem]:
    items: list[ComplianceItem] = []
    for page_number, page_text in split_pages(text):
        for rule in RULES:
            flags = 0 if rule.get("case_sensitive") else re.IGNORECASE
            for match in re.finditer(rule["regex"], page_text, flags):
                risk_level = rule["risk_level"]
                mitigation = rule["mitigation"]
                if rule["name"] == "Liquidated damages" and _has_liquidated_damages_cap(page_text, match.start()):
                    risk_level = "YELLOW"
                    mitigation = "Cap exists, verify percentage is acceptable"
                items.append(
                    ComplianceItem(
                        clause=_sentence_around(page_text, match.start()),
                        category=rule["category"],
                        risk_level=risk_level,
                        mitigation=mitigation,
                        page=page_number,
                        excerpt=_excerpt_around(page_text, match.start(), match.end()),
                    )
                )
    return items


def run_compliance_audit(state: dict[str, Any]) -> dict[str, Any]:
    items = scan_rules(state["extracted_text"])
    state["compliance_matrix"] = [item.model_dump() for item in items]
    return state

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from agents.adapter import build_compliance_report, build_pricing_estimate
from core.parser import extract_text_from_pdf


PDF_PATH = PROJECT_ROOT / "demo" / "sample_tender.pdf"


def main() -> None:
    text = extract_text_from_pdf(PDF_PATH.read_bytes())
    compliance = build_compliance_report({"raw_text": text})
    pricing = build_pricing_estimate({"raw_text": text})

    print("Compliance summary:")
    print(compliance["summary"])
    print("Compliance matrix risk/page:")
    print(
        [
            (item["risk_level"], item["page"])
            for item in compliance["compliance_matrix"]
        ]
    )
    print("Pricing items:")
    print(pricing["items"])
    print("Final bid:")
    print(pricing["final_bid_amount_usd"], "USD")


if __name__ == "__main__":
    main()

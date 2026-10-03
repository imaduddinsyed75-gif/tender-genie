from pathlib import Path

import fitz


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = PROJECT_ROOT / "demo" / "sample_tender.pdf"

PAGE_TEXT = [
    "REQUEST FOR PROPOSAL. Project: Enterprise Network Upgrade. Client: Karachi Port Authority. Submission deadline: 2026-11-15",
    "The vendor shall supply firewall appliances and network switch units. A security audit is required before go-live.",
    "The vendor shall pay liquidated damages of 2% per day for any delay in delivery.",
    "The system must provide uptime of 99.95%. Payment within 120 days net after invoice.",
    "Sub-contracting is strictly prohibited. Bidder must hold ISO 27001 certification.",
]


def main() -> None:
    document = fitz.open()
    try:
        for text in PAGE_TEXT:
            page = document.new_page()
            page.insert_textbox(
                fitz.Rect(54, 54, 558, 738),
                text,
                fontsize=11,
            )
        document.save(PDF_PATH)
    finally:
        document.close()
    print(f"Created {PDF_PATH}")


if __name__ == "__main__":
    main()

"""
TenderGenie PDF ingestion and tender scope parser.

Owner: Shamir

Responsibilities:
1. Extract text and tables from tender PDFs using PyMuPDF.
2. Parse the extracted text into the ParsedScope data contract
   defined in core/state.py.
"""

from typing import List, Optional
import re

import fitz  # PyMuPDF


def _clean_text(text: str) -> str:
    """Normalize common PDF extraction whitespace."""
    if not text:
        return ""

    text = text.replace("\u00a0", " ")
    text = text.replace("\u00ad", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    cleaned_lines = []

    for raw_line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", raw_line).strip()

        if line:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def _extract_tables(page: fitz.Page) -> List[str]:
    """
    Extract tables detected by PyMuPDF.

    Returns each table as pipe-separated rows.
    If no tables are detected, returns an empty list.
    """
    try:
        table_finder = page.find_tables()
    except (AttributeError, RuntimeError, ValueError):
        return []

    tables = []

    for table in table_finder.tables:
        try:
            rows = table.extract()
        except Exception:
            continue

        if not rows:
            continue

        formatted_rows = []

        for row in rows:
            cells = []

            for cell in row:
                if cell is None:
                    cells.append("")
                else:
                    cells.append(
                        re.sub(r"\s+", " ", str(cell)).strip()
                    )

            if any(cells):
                formatted_rows.append(" | ".join(cells))

        if formatted_rows:
            tables.append("\n".join(formatted_rows))

    return tables


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text and tables from a PDF.

    Args:
        pdf_bytes: Raw bytes of the PDF document.

    Returns:
        Clean extracted text with page markers.

    Raises:
        TypeError: If pdf_bytes is not bytes or bytearray.
        ValueError: If the PDF is empty or cannot be opened.
    """

    if not isinstance(pdf_bytes, (bytes, bytearray)):
        raise TypeError("pdf_bytes must be bytes or bytearray.")

    if not pdf_bytes:
        raise ValueError("PDF data is empty.")

    try:
        document = fitz.open(
            stream=bytes(pdf_bytes),
            filetype="pdf"
        )
    except Exception as exc:
        raise ValueError(f"Unable to open PDF: {exc}") from exc

    page_blocks = []

    try:
        for page_number, page in enumerate(document, start=1):

            text = _clean_text(
                page.get_text("text")
            )

            tables = _extract_tables(page)

            page_parts = []

            if text:
                page_parts.append(text)

            if tables:
                page_parts.append(
                    "TABLES:\n" +
                    "\n\n".join(tables)
                )

            page_content = "\n\n".join(page_parts)

            page_blocks.append(
                f"[PAGE {page_number}]\n{page_content}"
            )

    finally:
        document.close()

    return "\n\n".join(page_blocks).strip()


def _first_match(
    patterns: List[str],
    text: str
) -> Optional[str]:
    """Return the first captured value matching any pattern."""

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE | re.MULTILINE
        )

        if match:
            value = match.group(1).strip()

            if value:
                return value

    return None


def _extract_project_title(raw_text: str) -> str:
    """Extract an explicitly labelled project/tender title."""

    value = _first_match(
        [
            r"(?:project\s+title|project\s+name|tender\s+title|rfp\s+title)\s*[:\-]\s*(.+)",
            r"title\s+of\s+(?:the\s+)?tender\s*[:\-]\s*(.+)",
        ],
        raw_text,
    )

    return value or "Tender Project"


def _extract_client_name(
    raw_text: str
) -> Optional[str]:
    """Extract an explicitly labelled client/authority."""

    return _first_match(
        [
            r"(?:client\s+name|client)\s*[:\-]\s*(.+)",
            r"(?:procuring\s+entity|issuing\s+authority)\s*[:\-]\s*(.+)",
            r"(?:organization|organisation)\s*[:\-]\s*(.+)",
        ],
        raw_text,
    )


def _extract_submission_deadline(
    raw_text: str
) -> str:
    """Extract the text associated with a submission deadline."""

    value = _first_match(
        [
            r"(?:submission\s+deadline)\s*[:\-]?\s*([^\n]+)",
            r"(?:bid\s+submission\s+deadline)\s*[:\-]?\s*([^\n]+)",
            r"(?:proposal\s+deadline)\s*[:\-]?\s*([^\n]+)",
            r"(?:deadline\s+for\s+(?:submission|bid|proposal))\s*[:\-]?\s*([^\n]+)",
            r"(?:closing\s+date|closing\s+deadline)\s*[:\-]?\s*([^\n]+)",
        ],
        raw_text,
    )

    return value or ""


def _extract_technical_requirements(
    raw_text: str
) -> List[str]:
    """
    Extract requirement-like statements.

    This is intentionally conservative and only returns text already present
    in the tender document.
    """

    requirements = []

    requirement_terms = (
        "must ",
        "shall ",
        "required",
        "requirement",
        "mandatory",
        "bidder must",
        "vendor must",
        "supplier must",
        "provide ",
        "submit ",
    )

    section_headings = {
        "technical requirements",
        "technical requirement",
        "requirements",
        "mandatory requirements",
    }

    for raw_line in raw_text.splitlines():

        line = raw_line.strip()

        if not line or line.startswith("[PAGE"):
            continue

        cleaned = re.sub(
            r"^(?:[-•*]|\d+(?:\.\d+)*[.)])\s*",
            "",
            line,
        ).strip()

        lower = cleaned.lower()

        if lower in section_headings:
            continue

        if (
            len(cleaned) >= 12
            and any(term in lower for term in requirement_terms)
        ):
            if cleaned not in requirements:
                requirements.append(cleaned)

    return requirements


def _extract_deliverables(
    raw_text: str
) -> List[dict]:
    """
    Extract deliverables from an explicitly labelled Deliverables section.
    """

    deliverables = []

    inside_section = False

    for raw_line in raw_text.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        lower = line.lower()

        if re.search(
            r"\b(deliverables?|outputs?)\b",
            lower
        ):
            inside_section = True
            continue

        if inside_section:

            if re.match(
                r"^\[PAGE\s+\d+\]$",
                line,
                flags=re.IGNORECASE,
            ):
                continue

            # Stop when another obvious numbered section starts.
            if re.match(
                r"^\d+(?:\.\d+)*[\s.)-]+",
                line
            ):
                inside_section = False
                continue

            item = re.sub(
                r"^(?:[-•*]|\d+(?:\.\d+)*[.)])\s*",
                "",
                line,
            ).strip()

            if len(item) < 3:
                continue

            # Do not treat budget information as a deliverable.
            if re.match(
                r"^(?:estimated\s+)?(?:budget|contract\s+value|estimated\s+contract\s+value)\s*:",
                item,
                flags=re.IGNORECASE,
            ):
                continue

            deliverables.append(
                {
                    "title": item,
                    "description": item,
                    "timeline": None,
                }
            )

    return deliverables


def _extract_budget_hints(
    raw_text: str
) -> Optional[str]:
    """Extract explicitly labelled budget information."""

    return _first_match(
        [
            r"(?:estimated\s+budget)\s*[:\-]\s*([^\n]+)",
            r"(?:budget\s+range)\s*[:\-]\s*([^\n]+)",
            r"(?:contract\s+value)\s*[:\-]\s*([^\n]+)",
            r"(?:estimated\s+contract\s+value)\s*[:\-]\s*([^\n]+)",
            r"(?:budget)\s*[:\-]\s*([^\n]+)",
        ],
        raw_text,
    )


def parse_tender_scope(raw_text: str) -> dict:
    """
    Parse extracted tender text into the ParsedScope contract.

    The function only extracts information explicitly present in the
    document and leaves optional fields empty when they cannot be found.
    """

    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be a string.")

    raw_text = _clean_text(raw_text)

    return {
        "project_title": _extract_project_title(raw_text),

        "submission_deadline": _extract_submission_deadline(
            raw_text
        ),

        "client_name": _extract_client_name(
            raw_text
        ),

        "technical_requirements": (
            _extract_technical_requirements(raw_text)
        ),

        "deliverables": (
            _extract_deliverables(raw_text)
        ),

        "budget_hints": _extract_budget_hints(raw_text),
    }
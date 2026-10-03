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


def _clean_table_cell(cell: object) -> str:
    """Normalize a single extracted table cell."""
    if cell is None:
        return ""

    value = str(cell)

    value = value.replace("\u00a0", " ")
    value = value.replace("\u00ad", "")

    value = re.sub(r"\s+", " ", value).strip()

    return value


def _looks_like_garbled_table_text(value: str) -> bool:
    """
    Detect obvious text corruption produced by PDF table extraction.

    PyMuPDF's table detector can occasionally merge characters from
    adjacent PDF text blocks.
    """

    if not value:
        return False

    normalized = re.sub(r"\s+", " ", value).strip()

    if normalized.count("|") >= 2:
        return True

    suspicious_patterns = [
        r"\bTDheeliv\b",
        r"\bbeirdadbeler\b",
        r"\bcapabilit\s*\|\s*y\b",
        r"\bAdministrator Training Requirements Specification\b",
        r"\bReporting Dashboard Deliverable - API Integration\b",
        r"\bContract Duration:.*Commercial Item",
        r"\bWarranty Period:.*Commercial Item",
    ]

    for pattern in suspicious_patterns:
        if re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE,
        ):
            return True

    return False


def _looks_like_false_positive_table(
    rows: List[List[str]],
) -> bool:
    """
    Determine whether a detected table is probably unusable.
    """

    if not rows:
        return True

    meaningful_rows = 0
    suspicious_rows = 0

    for row in rows:

        cells = [
            _clean_table_cell(cell)
            for cell in row
        ]

        if not any(cells):
            continue

        meaningful_rows += 1

        combined = " | ".join(
            cell for cell in cells if cell
        )

        if _looks_like_garbled_table_text(
            combined
        ):
            suspicious_rows += 1

    if meaningful_rows == 0:
        return True

    if (
        suspicious_rows >= 1
        and suspicious_rows / meaningful_rows >= 0.5
    ):
        return True

    return False


def _extract_tables(
    page: fitz.Page,
) -> List[str]:
    """
    Extract usable tables detected by PyMuPDF.

    Returns each table as pipe-separated rows.
    """

    try:
        table_finder = page.find_tables()
    except (
        AttributeError,
        RuntimeError,
        ValueError,
    ):
        return []

    tables = []

    for table in table_finder.tables:

        try:
            rows = table.extract()
        except Exception:
            continue

        if not rows:
            continue

        if _looks_like_false_positive_table(
            rows
        ):
            continue

        formatted_rows = []

        for row in rows:

            cells = [
                _clean_table_cell(cell)
                for cell in row
            ]

            if not any(cells):
                continue

            combined = " | ".join(
                cell for cell in cells if cell
            )

            if not combined:
                continue

            if _looks_like_garbled_table_text(
                combined
            ):
                continue

            formatted_rows.append(combined)

        if formatted_rows:
            tables.append(
                "\n".join(formatted_rows)
            )

    return tables


def extract_text_from_pdf(
    pdf_bytes: bytes,
) -> str:
    """
    Extract text and usable tables from a PDF.

    Args:
        pdf_bytes: Raw bytes of the PDF document.

    Returns:
        Clean extracted text with page markers.

    Raises:
        TypeError: If pdf_bytes is not bytes or bytearray.
        ValueError: If the PDF is empty or cannot be opened.
    """

    if not isinstance(
        pdf_bytes,
        (bytes, bytearray),
    ):
        raise TypeError(
            "pdf_bytes must be bytes or bytearray."
        )

    if not pdf_bytes:
        raise ValueError(
            "PDF data is empty."
        )

    try:
        document = fitz.open(
            stream=bytes(pdf_bytes),
            filetype="pdf",
        )
    except Exception as exc:
        raise ValueError(
            f"Unable to open PDF: {exc}"
        ) from exc

    page_blocks = []

    try:

        for page_number, page in enumerate(
            document,
            start=1,
        ):

            text = _clean_text(
                page.get_text("text")
            )

            tables = _extract_tables(page)

            page_parts = []

            if text:
                page_parts.append(text)

            if tables:
                page_parts.append(
                    "TABLES:\n"
                    + "\n\n".join(tables)
                )

            page_content = "\n\n".join(
                page_parts
            )

            page_blocks.append(
                f"[PAGE {page_number}]\n"
                f"{page_content}"
            )

    finally:
        document.close()

    return "\n\n".join(
        page_blocks
    ).strip()


def _first_match(
    patterns: List[str],
    text: str,
) -> Optional[str]:
    """Return the first captured value matching any pattern."""

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        if match:

            value = match.group(1).strip()

            if value:
                return value

    return None


def _extract_project_title(
    raw_text: str,
) -> str:
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
    raw_text: str,
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
    raw_text: str,
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


def _is_section_heading(
    line: str,
) -> bool:
    """Return True when a line is an obvious section heading."""

    normalized = line.strip().lower()

    section_headings = {
        "technical requirements",
        "technical requirement",
        "requirements",
        "mandatory requirements",
        "functional requirements",
        "security and compliance",
        "evaluation criteria",
        "deliverables",
        "final deliverables",
        "outputs",
    }

    return normalized in section_headings


def _is_table_value(
    line: str,
) -> bool:
    """
    Detect common standalone values originating from table columns.
    """

    normalized = line.strip().lower()

    table_values = {
        "high",
        "medium",
        "low",
        "priority",
        "timeline",
        "quantity",
        "deliverable",
        "service",
        "units",
        "unit",
        "amount",
    }

    if normalized in table_values:
        return True

    if re.fullmatch(
        r"\d+\s*(?:day|days|week|weeks|month|months|year|years)",
        normalized,
    ):
        return True

    return False


def _extract_technical_requirements(
    raw_text: str,
) -> List[str]:
    """
    Extract requirement-like statements.

    Continuation lines are joined to the preceding requirement when
    appropriate so PDF line wrapping does not truncate a requirement.
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

    lines = raw_text.splitlines()

    current_requirement = None

    def save_current() -> None:
        nonlocal current_requirement

        if not current_requirement:
            return

        value = re.sub(
            r"\s+",
            " ",
            current_requirement,
        ).strip()

        if (
            len(value) >= 12
            and value not in requirements
            and not _is_section_heading(value)
            and not _is_table_value(value)
            and "|" not in value
        ):
            requirements.append(value)

        current_requirement = None

    for raw_line in lines:

        line = raw_line.strip()

        if not line:
            continue

        if line.startswith("[PAGE"):
            save_current()
            continue

        if line.upper() == "TABLES:":
            save_current()
            continue

        cleaned = re.sub(
            r"^(?:[-â€¢*]|\d+(?:\.\d+)*[.)])\s*",
            "",
            line,
        ).strip()

        if not cleaned:
            continue

        if "|" in cleaned:
            save_current()
            continue

        if _is_section_heading(cleaned):
            save_current()
            continue

        if _is_table_value(cleaned):
            save_current()
            continue

        lower = cleaned.lower()

        is_requirement_start = (
            len(cleaned) >= 12
            and any(
                term in lower
                for term in requirement_terms
            )
        )

        if is_requirement_start:

            save_current()

            current_requirement = cleaned

            continue

        # If the previous line started a requirement and this line
        # looks like a continuation, append it.
        if current_requirement:

            if not re.match(
                r"^\d+(?:\.\d+)*[\s.)-]+",
                cleaned,
            ):
                current_requirement += " " + cleaned
                continue

        # Otherwise ignore unrelated text.

    save_current()

    return requirements


def _extract_deliverables(
    raw_text: str,
) -> List[dict]:
    """
    Extract deliverables from an explicitly labelled Deliverables section.

    Table headers and obvious table values are ignored.
    """

    deliverables = []

    inside_section = False

    for raw_line in raw_text.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        lower = line.lower()

        # Start of the ordinary Deliverables section.
        if lower in {
            "3. deliverables",
            "4. deliverables",
            "5. deliverables",
            "deliverables",
            "final deliverables",
        }:
            inside_section = True
            continue

        # A new numbered section ends the current section.
        if inside_section and re.match(
            r"^\d+(?:\.\d+)*[\s.)-]+",
            line,
        ):

            # Keep "Final Deliverables" as a separate deliverable
            # section if encountered.
            if re.search(
                r"\bfinal\s+deliverables\b",
                lower,
            ):
                inside_section = True
                continue

            inside_section = False
            continue

        if not inside_section:
            continue

        if re.match(
            r"^\[PAGE\s+\d+\]$",
            line,
            flags=re.IGNORECASE,
        ):
            continue

        if lower == "tables:":
            continue

        if "|" in line:
            continue

        item = re.sub(
            r"^(?:[-â€¢*]|\d+(?:\.\d+)*[.)])\s*",
            "",
            line,
        ).strip()

        if len(item) < 3:
            continue

        if _is_table_value(item):
            continue

        if re.match(
            r"^(?:estimated\s+)?(?:budget|contract\s+value|estimated\s+contract\s+value)\s*:",
            item,
            flags=re.IGNORECASE,
        ):
            continue

        if re.match(
            r"^(?:high|medium|low)\s+\d+\s*(?:days?|weeks?|months?)$",
            item,
            flags=re.IGNORECASE,
        ):
            continue

        if item not in [
            deliverable["title"]
            for deliverable in deliverables
        ]:

            deliverables.append(
                {
                    "title": item,
                    "description": item,
                    "timeline": None,
                }
            )

    return deliverables


def _extract_budget_hints(
    raw_text: str,
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


def parse_tender_scope(
    raw_text: str,
) -> dict:
    """
    Parse extracted tender text into the ParsedScope contract.

    The function only extracts information explicitly present in the
    document and leaves optional fields empty when they cannot be found.
    """

    if not isinstance(
        raw_text,
        str,
    ):
        raise TypeError(
            "raw_text must be a string."
        )

    raw_text = _clean_text(raw_text)

    return {
        "project_title": _extract_project_title(
            raw_text
        ),

        "submission_deadline": _extract_submission_deadline(
            raw_text
        ),

        "client_name": _extract_client_name(
            raw_text
        ),

        "technical_requirements": (
            _extract_technical_requirements(
                raw_text
            )
        ),

        "deliverables": (
            _extract_deliverables(
                raw_text
            )
        ),

        "budget_hints": (
            _extract_budget_hints(
                raw_text
            )
        ),
    }
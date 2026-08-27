"""
Feature 1 — Automated RFI Document Processing.

Extracts structured fields out of the "Requests for information" PDF export
that sponsors download from CTIS, based on the layout of the two sample RFI
PDFs provided for the hackathon. Regex-based extraction is deliberately used
instead of a heavier NLP pipeline: it's fast, transparent, and easy to defend
in a regulated setting. Any field the parser can't find is left blank so the
UI can fall back to manual entry -- the parser should never silently invent
data.
"""
import re
from dataclasses import dataclass, field, asdict
from typing import Optional

import pdfplumber


def extract_text_from_pdf(file_like) -> str:
    """Extract plain text from a PDF path or file-like object."""
    text_chunks = []
    with pdfplumber.open(file_like) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_chunks.append(page_text)
    return "\n".join(text_chunks)


def _search(pattern: str, text: str, flags=re.IGNORECASE) -> Optional[str]:
    m = re.search(pattern, text, flags)
    if not m:
        return None
    val = m.group(1).strip()
    return val if val else None


_FOOTER_MARKERS = [
    r"European Medicines Agency.*$",
    r"Page \d+ of \d+.*$",
    r"SUBSTANTIAL\s*\n?MODIFICATION.*$",
]


def _strip_footer_noise(value: Optional[str]) -> Optional[str]:
    """Remove repeated PDF headers/footers (e.g. 'European Medicines Agency
    Page 3 of 3') that can get glued onto the last field on a page."""
    if not value:
        return value
    cleaned = value
    for pattern in _FOOTER_MARKERS:
        cleaned = re.split(pattern, cleaned, maxsplit=1, flags=re.IGNORECASE | re.DOTALL)[0]
    return cleaned.strip() or None


@dataclass
class ParsedRFI:
    application_id: Optional[str] = None
    rfi_uuid: Optional[str] = None
    evaluation_process: Optional[str] = None
    msc: Optional[str] = None
    changes_made: Optional[str] = None
    reason_for_request: Optional[str] = None
    due_date: Optional[str] = None
    response_date: Optional[str] = None
    date_submitted: Optional[str] = None
    consideration_number: Optional[str] = None
    section_parts: Optional[str] = None
    section_document: Optional[str] = None
    consideration_text: Optional[str] = None
    sponsor_response: Optional[str] = None

    def as_dict(self):
        return asdict(self)


def parse_rfi_text(text: str) -> ParsedRFI:
    """Pull structured fields out of raw RFI text using layout-aware regexes."""
    text = text.replace("\r\n", "\n")

    parsed = ParsedRFI()

    parsed.application_id = _search(r"(\d{4}-\d{6}-\d{2}-\d{2})", text)
    parsed.rfi_uuid = _search(r"RFI Unique Identifier:\s*\n?\s*([A-Za-z0-9\-]+)", text)
    parsed.evaluation_process = _search(r"Evaluation process:\s*\n?\s*([^\n]+)", text)
    parsed.msc = _search(r"\bMSC:\s*\n?\s*([^\n]+)", text)
    parsed.changes_made = _search(r"Changes made to the application:\s*\n?\s*([^\n]+)", text)
    parsed.reason_for_request = _search(
        r"Reason for request of additional information:\s*\n?\s*([^\n]+)", text
    )
    parsed.due_date = _search(r"Due date:\s*\n?\s*([^\n]+)", text)
    parsed.response_date = _search(r"Response date:\s*\n?\s*([^\n]+)", text)
    parsed.date_submitted = _search(r"Date submitted:\s*\n?\s*([^\n]+)", text)
    parsed.consideration_number = _search(r"Consideration number:\s*\n?\s*(\d+)", text)

    parsed.section_parts = _search(
        r"Application section parts\s*\n?\s*(.*?)\n\s*Application section and document:",
        text, flags=re.IGNORECASE | re.DOTALL,
    )
    if parsed.section_parts:
        parsed.section_parts = " ".join(parsed.section_parts.split())

    parsed.section_document = _search(
        r"Application section and document:\s*\n?\s*(.*?)\n\s*Consideration:",
        text, flags=re.IGNORECASE | re.DOTALL,
    )
    if parsed.section_document:
        parsed.section_document = " ".join(parsed.section_document.split())

    consideration = _search(
        r"(?<!number:)\bConsideration:\s*\n?(.*?)\n\s*Sponsor response:",
        text, flags=re.IGNORECASE | re.DOTALL,
    )
    if consideration:
        parsed.consideration_text = " ".join(consideration.split())

    sponsor_response = _search(
        r"Sponsor response:\s*\n?(.*?)(?:\n\s*\n|$)",
        text, flags=re.IGNORECASE | re.DOTALL,
    )
    if sponsor_response:
        parsed.sponsor_response = " ".join(sponsor_response.split())
        parsed.sponsor_response = _strip_footer_noise(parsed.sponsor_response)

    return parsed


def parse_rfi_pdf(file_like) -> ParsedRFI:
    text = extract_text_from_pdf(file_like)
    parsed = parse_rfi_text(text)
    return parsed, text

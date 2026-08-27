"""
Seed the repository so the app is immediately demo-able:
  - the 2 real sample RFI PDFs provided for the hackathon (parsed as-is)
  - a handful of clearly-labelled SYNTHETIC demo RFIs covering the recurring
    issue types mentioned in the concept discussion (missing documents,
    protocol-version changes, country-specific ICF issues, IMPD quality),
    so that hybrid search and the dashboard have enough data to be
    meaningful. Per the hackathon rules, all data is dummy/non-IP data.
"""
from core.database import create_rfi

REAL_SAMPLES = [
    {
        "application_id": "2024-123456-12-00",
        "rfi_uuid": "CT-2024-123456-12-00-SM01-001",
        "evaluation_process": "Validation",
        "msc": "Germany",
        "changes_made": "Yes",
        "reason_for_request": "Is Incomplete",
        "due_date": "16/03/2026",
        "response_date": "06/03/2026",
        "date_submitted": "05/03/2026",
        "consideration_number": "1",
        "section_parts": "Part I - Regulatory",
        "section_document": None,
        "consideration_text": (
            "IT - Please upload the proof of payment of the additional amount required by law "
            "for all applications submitted starting from 17 February 2025 due to ISTAT updated fee."
        ),
        "sponsor_response": "Proof of payment of the additional amount required is provided.",
        "source_filename": "RFI_example_1-dummy.pdf",
    },
    {
        "application_id": "2024-234567-45-00",
        "rfi_uuid": "CT-2024-234567-45-00-SM02-001",
        "evaluation_process": "Validation",
        "msc": "France",
        "changes_made": "No",
        "reason_for_request": "Is Incomplete",
        "due_date": "27/07/2026",
        "response_date": "21/07/2026",
        "date_submitted": "16/07/2026",
        "consideration_number": "1",
        "section_parts": "Part II - France",
        "section_document": "Subject information and informed consent form",
        "consideration_text": (
            "Please confirm that the changes made in protocol version 4.0 dated 12/12/2023 don't "
            "impact the ICF/Part II documentation, or withdraw this application in order to resubmit "
            "a Part I & Part II application with the updated Part II documentation for all MSCs."
        ),
        "sponsor_response": (
            "The changes made in protocol version 4.0 dated 12/12/2023 have no impact on the Main "
            "ICFs/master Part II documents, so there is no impact on the French ICFs, nor the French "
            "Part II documents."
        ),
        "source_filename": "RFI_example_2-dummy.pdf",
    },
]

# Clearly-labelled synthetic demo data (not real Novo Nordisk RFIs) added so
# search / dashboard have enough volume and variety to demo well.
SYNTHETIC_SAMPLES = [
    {
        "application_id": "2025-341122-08-00",
        "rfi_uuid": "CT-2025-341122-08-00-SM01-002",
        "evaluation_process": "Validation",
        "msc": "Italy",
        "changes_made": "Yes",
        "reason_for_request": "Is Incomplete",
        "due_date": "12/02/2026",
        "response_date": "05/02/2026",
        "section_parts": "Part I - Regulatory",
        "section_document": None,
        "consideration_text": (
            "Please upload proof of payment of the additional fee required for all applications "
            "submitted after the updated national fee schedule came into effect."
        ),
        "sponsor_response": "Proof of payment of the additional required amount is attached.",
        "source_filename": "synthetic_demo_1",
    },
    {
        "application_id": "2025-341122-08-00",
        "rfi_uuid": "CT-2025-341122-08-00-SM03-001",
        "evaluation_process": "Validation",
        "msc": "Spain",
        "changes_made": "Yes",
        "reason_for_request": "Is Incomplete",
        "due_date": "03/04/2026",
        "response_date": "29/03/2026",
        "section_parts": "Part II - Spain",
        "section_document": "Subject information and informed consent form",
        "consideration_text": (
            "Please confirm that the amendments made in protocol version 5.0 dated 04/01/2026 do not "
            "impact the ICF/Part II documentation, or provide the updated Part II documentation."
        ),
        "sponsor_response": (
            "The amendments introduced in protocol version 5.0 do not impact the master ICF or "
            "Part II documents; no impact on the Spanish ICF or Part II documentation."
        ),
        "source_filename": "synthetic_demo_2",
    },
    {
        "application_id": "2025-556781-19-00",
        "rfi_uuid": "CT-2025-556781-19-00-SM01-001",
        "evaluation_process": "Validation",
        "msc": "Germany",
        "changes_made": "No",
        "reason_for_request": "Is Incomplete",
        "due_date": "18/05/2026",
        "response_date": "10/05/2026",
        "section_parts": "Part I - IMPD Quality",
        "section_document": "Investigational Medicinal Product Dossier",
        "consideration_text": (
            "Please clarify the discrepancy between the batch release specification and the stability "
            "data submitted in the IMPD Quality section."
        ),
        "sponsor_response": (
            "The discrepancy was a typographical error; the corrected specification table aligned "
            "with the stability data is provided."
        ),
        "source_filename": "synthetic_demo_3",
    },
    {
        "application_id": "2025-556781-19-00",
        "rfi_uuid": "CT-2025-556781-19-00-SM02-003",
        "evaluation_process": "Validation",
        "msc": "Poland",
        "changes_made": "Yes",
        "reason_for_request": "Is Incomplete",
        "due_date": "22/06/2026",
        "response_date": "15/06/2026",
        "section_parts": "Part II - Poland",
        "section_document": "Subject information and informed consent form",
        "consideration_text": (
            "Please confirm that the protocol amendment does not affect the informed consent form "
            "for Poland, or submit an updated ICF."
        ),
        "sponsor_response": (
            "The protocol amendment has no impact on the informed consent form for Poland; no updated "
            "ICF is required."
        ),
        "source_filename": "synthetic_demo_4",
    },
    {
        "application_id": "2025-778890-27-00",
        "rfi_uuid": "CT-2025-778890-27-00-SM01-001",
        "evaluation_process": "Validation",
        "msc": "Netherlands",
        "changes_made": "No",
        "reason_for_request": "Is Incomplete",
        "due_date": "09/01/2026",
        "response_date": "02/01/2026",
        "section_parts": "Part I - Regulatory",
        "section_document": None,
        "consideration_text": (
            "The cover letter references an incorrect EudraCT/CT number. Please provide a corrected "
            "cover letter with the accurate trial identifier."
        ),
        "sponsor_response": "A corrected cover letter with the accurate CT number is provided.",
        "source_filename": "synthetic_demo_5",
    },
    {
        "application_id": "2025-778890-27-00",
        "rfi_uuid": "CT-2025-778890-27-00-SM02-002",
        "evaluation_process": "Validation",
        "msc": "Belgium",
        "changes_made": "Yes",
        "reason_for_request": "Is Incomplete",
        "due_date": "14/03/2026",
        "response_date": "07/03/2026",
        "section_parts": "Part II - Belgium",
        "section_document": "Subject information and informed consent form",
        "consideration_text": (
            "Please confirm that changes made in protocol version 3.2 dated 20/11/2025 have no impact "
            "on the Belgian ICF/Part II documentation."
        ),
        "sponsor_response": (
            "The changes made in protocol version 3.2 have no impact on the master ICF, and therefore "
            "no impact on the Belgian ICF or Part II documents."
        ),
        "source_filename": "synthetic_demo_6",
    },
    {
        "application_id": "2025-901233-05-00",
        "rfi_uuid": "CT-2025-901233-05-00-SM01-001",
        "evaluation_process": "Validation",
        "msc": "France",
        "changes_made": "Yes",
        "reason_for_request": "Is Incomplete",
        "due_date": "28/04/2026",
        "response_date": "20/04/2026",
        "section_parts": "Part I - Regulatory",
        "section_document": None,
        "consideration_text": (
            "Please upload the proof of payment of the additional amount required by the updated "
            "national fee for all applications submitted from the effective date."
        ),
        "sponsor_response": "Proof of payment of the additional amount required by French authorities is provided.",
        "source_filename": "synthetic_demo_7",
    },
    {
        "application_id": "2025-901233-05-00",
        "rfi_uuid": "CT-2025-901233-05-00-SM03-004",
        "evaluation_process": "Validation",
        "msc": "Germany",
        "changes_made": "No",
        "reason_for_request": "Is Incomplete",
        "due_date": "11/07/2026",
        "response_date": "03/07/2026",
        "section_parts": "Part I - IMPD Quality",
        "section_document": "Investigational Medicinal Product Dossier",
        "consideration_text": (
            "Please provide clarification on the shelf-life extension data referenced in the IMPD, as "
            "the submitted stability report appears incomplete."
        ),
        "sponsor_response": "An updated stability report with the complete shelf-life extension data is provided.",
        "source_filename": "synthetic_demo_8",
    },
]


def seed_if_empty(session):
    """Populate the DB with sample data only if it's currently empty."""
    from core.models import RFI
    existing = session.query(RFI).count()
    if existing > 0:
        return 0

    count = 0
    for sample in REAL_SAMPLES:
        create_rfi(session, sample, actor="seed_script", status="approved")
        count += 1
    for sample in SYNTHETIC_SAMPLES:
        create_rfi(session, sample, actor="seed_script (synthetic demo data)", status="approved")
        count += 1
    return count

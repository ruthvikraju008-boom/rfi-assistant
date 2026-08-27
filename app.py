"""
Novo Nordisk GBS Hackathon 2026 — EU CTR RFI Knowledge Assistant
==================================================================
Single-file Streamlit UI wired directly to the `core/` package (parser,
search, LLM draft assistant, analytics). Run with:

    streamlit run app.py

See README.md for setup instructions.
"""
import io
from datetime import datetime

import pandas as pd
import streamlit as st

from core.database import (
    init_db, get_session, create_rfi, update_status, all_rfis, get_audit_trail,
)
from core.models import RFI
from core.seed_data import seed_if_empty
from core.parser import parse_rfi_pdf, parse_rfi_text, ParsedRFI
from core.search import hybrid_search
from core.llm import generate_draft
from core.analytics import rfis_to_dataframe, count_by_country, count_by_section, top_keywords
from core.embeddings import get_backend_name

st.set_page_config(
    page_title="EU CTR RFI Knowledge Assistant",
    page_icon="🧬",
    layout="wide",
)

# --- one-time setup -------------------------------------------------------
init_db()
with get_session() as _session:
    _added = seed_if_empty(_session)

# --- sidebar ----------------------------------------------------------------
st.sidebar.title("🧬 RFI Knowledge Assistant")
st.sidebar.caption("Novo Nordisk GBS Hackathon 2026 — prototype")

actor_name = st.sidebar.text_input("Your name", value="Hackathon User")
role = st.sidebar.selectbox("Role", ["User", "Reviewer"], index=0)

page = st.sidebar.radio(
    "Navigate",
    [
        "🏠 Overview",
        "📤 Upload & Process RFI",
        "🔍 Search Repository",
        "🤖 Draft Assistant",
        "✅ Reviewer Queue",
        "📊 Intelligence Dashboard",
        "🕒 Audit Trail",
    ],
)

st.sidebar.divider()
st.sidebar.caption(f"Semantic search backend: **{get_backend_name()}**")
st.sidebar.caption(
    "Tip: set ANTHROPIC_API_KEY or OPENAI_API_KEY in a `.env` file to enable "
    "real LLM-generated drafts (otherwise a transparent template fallback is used)."
)


def _rfi_card(r, score_info: str = ""):
    with st.container(border=True):
        top = f"**RFI #{r.id}** · {r.msc or 'Unknown'} · {r.section_parts or 'Unknown section'}"
        if score_info:
            top += f"  \n{score_info}"
        st.markdown(top)
        st.markdown(f"**Consideration:** {r.consideration_text}")
        st.markdown(f"**Sponsor response:** {r.sponsor_response}")
        cols = st.columns(4)
        cols[0].caption(f"Application: {r.application_id or '—'}")
        cols[1].caption(f"RFI ID: {r.rfi_uuid or '—'}")
        cols[2].caption(f"Status: {r.status}")
        cols[3].caption(f"Source: {r.source_filename or 'manual entry'}")


# =============================================================================
# PAGE: Overview
# =============================================================================
if page == "🏠 Overview":
    st.title("EU CTR RFI Knowledge Assistant")
    st.write(
        "A searchable, evidence-grounded knowledge repository for validation "
        "Requests for Information (RFIs) under the EU Clinical Trial Regulation — "
        "so teams stop re-researching issues they've already solved."
    )

    with get_session() as session:
        rfis = all_rfis(session)
    df = rfis_to_dataframe(rfis)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total RFIs in repository", len(df))
    c2.metric("Approved (searchable)", int((df["status"] == "approved").sum()) if not df.empty else 0)
    c3.metric("Pending review", int((df["status"] == "pending_review").sum()) if not df.empty else 0)
    c4.metric("Countries covered", df["msc"].nunique() if not df.empty else 0)

    st.divider()
    st.subheader("The 5 core features")
    st.markdown(
        """
1. **📤 Automated RFI Document Processing** — upload a CTIS RFI PDF and auto-extract the structured fields (with manual-entry fallback).
2. **🔍 Intelligent Repository + Hybrid Search** — keyword + semantic search across every stored consideration/response.
3. **🤖 Evidence-Grounded AI Response Assistant** — drafts a new response citing the historical RFIs it's based on, and flags differences for review.
4. **📊 RFI Intelligence Dashboard** — what's recurring, where, and how often.
5. **✅ Continuous Knowledge Loop** — every reviewer-approved draft becomes new, searchable repository knowledge.
        """
    )
    st.info(
        "Data note: 2 records are the real dummy sample RFIs provided for the hackathon; "
        "the rest are clearly-labelled synthetic demo records added so search and the "
        "dashboard have enough volume to demo well.",
        icon="ℹ️",
    )

# =============================================================================
# PAGE: Upload & Process RFI  (Feature 1)
# =============================================================================
elif page == "📤 Upload & Process RFI":
    st.title("📤 Upload & Process RFI")
    st.write(
        "Upload a CTIS 'Requests for information' PDF, or paste its text. "
        "Fields are auto-extracted; anything the parser misses (or gets wrong) "
        "can be corrected before saving — this becomes part of the searchable repository."
    )

    input_mode = st.radio("Input method", ["Upload PDF", "Paste text", "Manual entry (blank form)"], horizontal=True)

    parsed: ParsedRFI = ParsedRFI()
    full_text = ""
    source_filename = None

    if input_mode == "Upload PDF":
        uploaded_files = st.file_uploader(
            "RFI PDF(s)",
            type=["pdf"],
            accept_multiple_files=True,
            help="Upload one PDF for the normal review flow, or up to 500 PDFs for automatic bulk processing.",
        )

        if uploaded_files:
            if len(uploaded_files) > 500:
                st.warning("You selected more than 500 PDFs. Only the first 500 will be processed.")
                uploaded_files = uploaded_files[:500]

            # Exactly one PDF keeps the existing manual review workflow.
            if len(uploaded_files) == 1:
                uploaded = uploaded_files[0]
                source_filename = uploaded.name
                parsed, full_text = parse_rfi_pdf(io.BytesIO(uploaded.getvalue()))
                st.success("Text extracted and fields auto-parsed below — please review before saving.")
            else:
                st.info(
                    f"📚 {len(uploaded_files)} PDFs selected. Bulk mode will parse and save each file automatically. "
                    "Files with missing key fields go to the Reviewer Queue instead of stopping the batch."
                )

                if st.button(f"🚀 Process {len(uploaded_files)} RFIs", type="primary"):
                    progress = st.progress(0, text="Starting bulk RFI processing...")
                    results = {
                        "approved": [],
                        "review": [],
                        "skipped": [],
                        "failed": [],
                    }

                    for index, uploaded in enumerate(uploaded_files, start=1):
                        filename = uploaded.name

                        try:
                            parsed_item, item_text = parse_rfi_pdf(
                                io.BytesIO(uploaded.getvalue())
                            )

                            if not parsed_item.consideration_text or not parsed_item.consideration_text.strip():
                                results["failed"].append(
                                    (filename, "No consideration text could be extracted.")
                                )
                                progress.progress(
                                    index / len(uploaded_files),
                                    text=f"Processing {index}/{len(uploaded_files)} — {filename}",
                                )
                                continue

                            with get_session() as session:
                                duplicate = None

                                if parsed_item.rfi_uuid:
                                    duplicate = (
                                        session.query(RFI)
                                        .filter(RFI.rfi_uuid == parsed_item.rfi_uuid)
                                        .first()
                                    )

                                if duplicate is None:
                                    duplicate = (
                                        session.query(RFI)
                                        .filter(RFI.source_filename == filename)
                                        .first()
                                    )

                                if duplicate is not None:
                                    results["skipped"].append(
                                        (filename, f"Already exists as RFI #{duplicate.id}.")
                                    )
                                    progress.progress(
                                        index / len(uploaded_files),
                                        text=f"Processing {index}/{len(uploaded_files)} — {filename}",
                                    )
                                    continue

                                fields = dict(
                                    application_id=parsed_item.application_id,
                                    rfi_uuid=parsed_item.rfi_uuid,
                                    evaluation_process=parsed_item.evaluation_process or "Validation",
                                    msc=parsed_item.msc,
                                    section_parts=parsed_item.section_parts,
                                    section_document=parsed_item.section_document,
                                    due_date=parsed_item.due_date,
                                    response_date=parsed_item.response_date,
                                    date_submitted=parsed_item.date_submitted,
                                    consideration_number=parsed_item.consideration_number,
                                    consideration_text=parsed_item.consideration_text,
                                    sponsor_response=parsed_item.sponsor_response,
                                    changes_made=parsed_item.changes_made,
                                    reason_for_request=parsed_item.reason_for_request,
                                    source_filename=filename,
                                    full_text=item_text,
                                )

                                missing_fields = [
                                    label
                                    for label, value in [
                                        ("Application ID", parsed_item.application_id),
                                        ("RFI Unique Identifier", parsed_item.rfi_uuid),
                                        ("MSC / Country", parsed_item.msc),
                                        ("Application section parts", parsed_item.section_parts),
                                        ("Section document", parsed_item.section_document),
                                        ("Consideration", parsed_item.consideration_text),
                                    ]
                                    if not value or not str(value).strip()
                                ]

                                status = "pending_review" if missing_fields else "approved"

                                rfi = create_rfi(
                                    session,
                                    fields,
                                    actor=actor_name,
                                    status=status,
                                )
                                new_id = rfi.id

                            if missing_fields:
                                results["review"].append(
                                    (filename, new_id, ", ".join(missing_fields))
                                )
                            else:
                                results["approved"].append((filename, new_id))

                        except Exception as exc:
                            # One bad PDF never aborts the entire batch.
                            results["failed"].append((filename, str(exc)))

                        progress.progress(
                            index / len(uploaded_files),
                            text=f"Processing {index}/{len(uploaded_files)} — {filename}",
                        )

                    progress.empty()

                    st.success(
                        f"Bulk processing complete: {len(results['approved'])} approved, "
                        f"{len(results['review'])} sent to review, "
                        f"{len(results['skipped'])} skipped, "
                        f"{len(results['failed'])} failed. ✅"
                    )

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Auto-approved", len(results["approved"]))
                    m2.metric("Needs review", len(results["review"]))
                    m3.metric("Duplicates skipped", len(results["skipped"]))
                    m4.metric("Failed", len(results["failed"]))

                    if results["review"]:
                        with st.expander(f"⚠️ {len(results['review'])} files need review"):
                            for filename, rfi_id, missing in results["review"]:
                                st.write(
                                    f"**RFI #{rfi_id} — {filename}** — missing: {missing}"
                                )
                            st.info("Open Reviewer Queue to inspect these records.")

                    if results["skipped"]:
                        with st.expander(f"↩️ {len(results['skipped'])} duplicates skipped"):
                            for filename, reason in results["skipped"]:
                                st.write(f"**{filename}** — {reason}")

                    if results["failed"]:
                        with st.expander(f"❌ {len(results['failed'])} files failed"):
                            for filename, reason in results["failed"]:
                                st.write(f"**{filename}** — {reason}")

                # Never render the single-file review form for a bulk selection.
                st.stop()
    elif input_mode == "Paste text":
        pasted = st.text_area("Paste the RFI text here", height=200)
        if pasted.strip():
            parsed = parse_rfi_text(pasted)
            full_text = pasted
            st.success("Fields auto-parsed below — please review before saving.")

    with st.form("rfi_form"):
        st.subheader("Review / edit extracted fields")
        c1, c2, c3 = st.columns(3)
        application_id = c1.text_input("Application ID", value=parsed.application_id or "")
        rfi_uuid = c2.text_input("RFI Unique Identifier", value=parsed.rfi_uuid or "")
        evaluation_process = c3.text_input("Evaluation process", value=parsed.evaluation_process or "Validation")

        c4, c5, c6 = st.columns(3)
        msc = c4.text_input("MSC / Country", value=parsed.msc or "")
        section_parts = c5.text_input("Application section parts", value=parsed.section_parts or "")
        section_document = c6.text_input("Section document", value=parsed.section_document or "")

        c7, c8, c9 = st.columns(3)
        due_date = c7.text_input("Due date", value=parsed.due_date or "")
        response_date = c8.text_input("Response date", value=parsed.response_date or "")
        date_submitted = c9.text_input("Date submitted", value=parsed.date_submitted or "")

        consideration_text = st.text_area("Consideration", value=parsed.consideration_text or "", height=120)
        sponsor_response = st.text_area("Sponsor response", value=parsed.sponsor_response or "", height=120)

        submitted = st.form_submit_button("💾 Save to repository", type="primary")

        if submitted:
            if not consideration_text.strip():
                st.error("Consideration text is required.")
            else:
                fields = dict(
                    application_id=application_id, rfi_uuid=rfi_uuid,
                    evaluation_process=evaluation_process, msc=msc,
                    section_parts=section_parts, section_document=section_document,
                    due_date=due_date, response_date=response_date, date_submitted=date_submitted,
                    consideration_text=consideration_text, sponsor_response=sponsor_response,
                    source_filename=source_filename, full_text=full_text,
                )
                with get_session() as session:
                    rfi = create_rfi(session, fields, actor=actor_name, status="approved")
                    session.flush()
                    new_id = rfi.id
                st.success(f"Saved as RFI #{new_id} and added to the searchable repository. ✅")

# =============================================================================
# PAGE: Search Repository  (Feature 2)
# =============================================================================
elif page == "🔍 Search Repository":
    st.title("🔍 Search Repository")
    st.write("Hybrid search: exact regulatory terminology (keyword) + conceptual similarity (semantic).")

    query = st.text_input("Search query", placeholder="e.g. protocol amendment impact on informed consent")
    with st.expander("Advanced: search weighting"):
        kw_weight = st.slider("Keyword weight", 0.0, 1.0, 0.4)
        sem_weight = st.slider("Semantic weight", 0.0, 1.0, 0.6)

    if query.strip():
        with get_session() as session:
            results = hybrid_search(session, query, top_k=8, keyword_weight=kw_weight, semantic_weight=sem_weight)
            results = [(r.rfi.id, r) for r in results]  # keep ids to detach-safe re-fetch not needed; small scale
        if not results:
            st.warning("No matches found in the approved repository yet.")
        else:
            st.caption(f"{len(results)} result(s)")
            for _id, r in results:
                score_info = (
                    f"Relevance: **{round(r.combined_score * 100)}%** "
                    f"(keyword {round(r.keyword_score * 100)}% · semantic {round(r.semantic_score * 100)}%)"
                )
                _rfi_card(r.rfi, score_info)
    else:
        st.info("Enter a query above to search the repository.")

# =============================================================================
# PAGE: Draft Assistant  (Feature 3)
# =============================================================================
elif page == "🤖 Draft Assistant":
    st.title("🤖 Evidence-Grounded AI Response Assistant")
    st.write(
        "Paste the **Consideration** text from a new RFI. The assistant retrieves the most "
        "similar historical RFIs and drafts a response grounded in their approved answers, "
        "citing sources and flagging anything that needs human review."
    )

    new_consideration = st.text_area("New RFI — Consideration text", height=120)
    top_k = st.slider("Number of historical RFIs to ground the draft in", 1, 5, 3)

    if st.button("✨ Generate draft", type="primary", disabled=not new_consideration.strip()):
        with get_session() as session:
            matches = hybrid_search(session, new_consideration, top_k=top_k)
            draft = generate_draft(new_consideration, matches)
        st.session_state["last_draft"] = draft
        st.session_state["last_consideration"] = new_consideration

    draft = st.session_state.get("last_draft")
    if draft:
        st.subheader("Draft response")
        st.caption(f"Generated via: `{draft.provider}`")
        edited_draft = st.text_area("Draft (editable before submitting for review)", value=draft.draft_text, height=220)

        if draft.difference_flags:
            st.warning("⚠️ Points for human review:\n\n" + "\n".join(f"- {f}" for f in draft.difference_flags))

        st.subheader("Sources used")
        if draft.sources:
            st.table(pd.DataFrame(draft.sources))
        else:
            st.caption("No historical sources were found for this consideration.")

        if st.button("📨 Submit draft for review"):
            fields = dict(
                consideration_text=st.session_state["last_consideration"],
                sponsor_response=edited_draft,
                section_parts="(pending — set by reviewer)",
            )
            with get_session() as session:
                rfi = create_rfi(session, fields, actor=actor_name, status="pending_review")
                session.flush()
                update_status(session, rfi.id, "pending_review", actor=actor_name,
                               note=f"AI-assisted draft generated via {draft.provider}, submitted for review.")
                new_id = rfi.id
            st.success(f"Draft saved as RFI #{new_id} with status 'pending_review'. See the Reviewer Queue.")
            del st.session_state["last_draft"]

# =============================================================================
# PAGE: Reviewer Queue  (Feature 3 / 5 — approval + knowledge loop)
# =============================================================================
elif page == "✅ Reviewer Queue":
    st.title("✅ Reviewer Queue")
    st.write("Approved items automatically become part of the searchable repository (the knowledge loop).")

    with get_session() as session:
        pending = all_rfis(session, statuses=["pending_review"])

    if not pending:
        st.info("No drafts are currently pending review. 🎉")
    else:
        for r in pending:
            with st.container(border=True):
                st.markdown(f"**RFI #{r.id}** · submitted by {r.created_by} · {r.created_at:%Y-%m-%d %H:%M}")
                st.markdown(f"**Consideration:** {r.consideration_text}")
                st.markdown(f"**Draft response:** {r.sponsor_response}")

                c1, c2, c3 = st.columns([1, 1, 3])
                approve = c1.button("✅ Approve", key=f"approve_{r.id}")
                reject = c2.button("❌ Reject", key=f"reject_{r.id}")
                note = c3.text_input("Reviewer note (optional)", key=f"note_{r.id}")

                if approve:
                    with get_session() as session:
                        update_status(session, r.id, "approved", actor=actor_name,
                                       note=note or "Approved by reviewer.")
                    st.success(f"RFI #{r.id} approved and added to the searchable repository.")
                    st.rerun()
                if reject:
                    with get_session() as session:
                        update_status(session, r.id, "rejected", actor=actor_name,
                                       note=note or "Rejected by reviewer.")
                    st.warning(f"RFI #{r.id} rejected.")
                    st.rerun()

# =============================================================================
# PAGE: Intelligence Dashboard  (Feature 4)
# =============================================================================
elif page == "📊 Intelligence Dashboard":
    st.title("📊 RFI Intelligence Dashboard")
    st.caption("What is recurring? Where is it recurring? How often?")

    with get_session() as session:
        rfis = all_rfis(session, statuses=["approved"])
    df = rfis_to_dataframe(rfis)

    if df.empty:
        st.info("No approved RFIs yet — upload or approve some first.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("RFI count by country (MSC)")
            st.bar_chart(count_by_country(df))
        with c2:
            st.subheader("RFI count by application section")
            st.bar_chart(count_by_section(df))

        st.subheader("Most recurring terms in Consideration text")
        kw = top_keywords(df)
        if kw.empty:
            st.caption("Not enough text yet to compute recurring terms.")
        else:
            st.bar_chart(kw)

        st.subheader("Raw data")
        st.dataframe(df.drop(columns=["consideration_text"]), width="stretch")

# =============================================================================
# PAGE: Audit Trail
# =============================================================================
elif page == "🕒 Audit Trail":
    st.title("🕒 Audit Trail")
    st.write("Simple, append-only history of who created / reviewed / approved each RFI record.")

    with get_session() as session:
        rfis = all_rfis(session)

    if not rfis:
        st.info("No RFIs in the repository yet.")
    else:
        options = {f"RFI #{r.id} — {r.msc or 'Unknown'} — {(r.consideration_text or '')[:60]}...": r.id for r in rfis}
        choice = st.selectbox("Select an RFI", list(options.keys()))
        rfi_id = options[choice]

        with get_session() as session:
            entries = get_audit_trail(session, rfi_id)

        for e in entries:
            st.markdown(f"**{e.timestamp:%Y-%m-%d %H:%M} UTC** — `{e.action}` by **{e.actor}**  \n{e.note or ''}")
            st.divider()

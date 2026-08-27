# EU CTR RFI Knowledge Assistant

A working prototype for the **Novo Nordisk GBS Hackathon 2026**: a searchable,
evidence-grounded knowledge repository for validation **Requests for Information
(RFIs)** under the EU Clinical Trial Regulation (CTR) — so teams stop
re-researching issues they've already solved.

Built around the 5 core features from the concept note:

1. **Automated RFI Document Processing** — upload a CTIS RFI PDF, auto-extract structured fields (manual-entry fallback for anything missed).
2. **Intelligent Repository + Hybrid Search** — keyword + semantic search over every stored consideration/response.
3. **Evidence-Grounded AI Response Assistant** — RAG draft generation that cites its historical sources and flags differences for human review.
4. **RFI Intelligence Dashboard** — what's recurring, where, and how often.
5. **Continuous Knowledge Loop** — every reviewer-approved draft becomes new, searchable repository knowledge.

It's a single Streamlit app talking directly to a small, well-separated
Python "core" package — this maps to the UI / Application / Data layers in
the concept note's architecture, without the overhead of running a separate
API server for a 1-month hackathon build.

## 1. Setup

```bash
# from inside the rfi-assistant/ folder
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

> **Note on `sentence-transformers`**: it's listed in requirements.txt for
> real semantic embeddings (all-MiniLM-L6-v2) but pulls in `torch`, which is
> a large download. If you want to get running fast, you can remove it (and
> `faiss`-style heavy deps aren't used at all) — the app **automatically
> falls back to a TF-IDF-based semantic search** with zero code changes if
> `sentence-transformers` isn't installed. Everything still works, including
> the hybrid search and draft assistant; only the "semantic" half of the
> score is less deeply semantic.

Optional: copy `.env.example` to `.env` and add an `ANTHROPIC_API_KEY` or
`OPENAI_API_KEY` to get real LLM-generated drafts in the Draft Assistant. If
you skip this, the app still works — it uses a transparent, clearly-labelled
template fallback built from the closest historical match, so demos never
break because of a missing API key.

```bash
cp .env.example .env
# then edit .env
```

## 2. Initialize the database

```bash
python init_db.py
```

This creates `data/rfi_assistant.db` (SQLite) and seeds it with:
- the 2 real dummy sample RFIs provided for the hackathon, and
- 8 clearly-labelled **synthetic** demo RFIs (varied countries/sections)
  so search and the dashboard have enough volume to demo well from minute one.

Re-running `init_db.py` is safe — it only seeds if the database is empty.

## 3. Run the app

```bash
streamlit run app.py
```

Open the URL Streamlit prints (typically `http://localhost:8501`).

## Project structure

```
rfi-assistant/
├── app.py                 # Streamlit UI — all 7 pages
├── init_db.py              # one-time DB init + seed script
├── requirements.txt
├── .env.example
├── data/
│   └── rfi_assistant.db    # created on first run
└── core/
    ├── config.py            # env/config loading
    ├── models.py            # SQLAlchemy models: RFI, AuditLogEntry
    ├── database.py          # engine/session + CRUD helpers
    ├── parser.py             # Feature 1 — PDF/text -> structured fields (regex-based)
    ├── embeddings.py          # sentence-transformers with automatic TF-IDF fallback
    ├── search.py              # Feature 2 — hybrid (keyword + semantic) search
    ├── llm.py                  # Feature 3 — RAG draft generation (Anthropic/OpenAI/template)
    ├── analytics.py            # Feature 4 — dashboard aggregations
    └── seed_data.py             # sample + synthetic demo data
```

## How each feature maps to the app

| Feature | Where in the app | Where in the code |
|---|---|---|
| 1. Automated RFI Document Processing | "📤 Upload & Process RFI" page | `core/parser.py` |
| 2. Intelligent Repository + Hybrid Search | "🔍 Search Repository" page | `core/search.py`, `core/embeddings.py` |
| 3. Evidence-Grounded AI Response Assistant | "🤖 Draft Assistant" page | `core/llm.py` |
| 4. RFI Intelligence Dashboard | "📊 Intelligence Dashboard" page | `core/analytics.py` |
| 5. Continuous Knowledge Loop | "✅ Reviewer Queue" page (approve → repository) | `core/database.py::update_status` |
| Simple audit trail | "🕒 Audit Trail" page | `AuditLogEntry` model, written on every create/approve/reject |
| Simple role awareness | Sidebar "Role" selector (User / Reviewer) | `app.py` |

## Suggested demo script (for your presentation)

1. **Upload & Process**: upload one of the sample RFI PDFs, show the
   auto-extracted fields, save it.
2. **Search**: search `"protocol amendment impact on informed consent"` —
   show keyword + semantic score breakdown across matches.
3. **Draft Assistant**: paste a *new* consideration (e.g. about a different
   country or protocol version) and generate a draft — point out the cited
   sources and the "points for human review" flags.
4. **Reviewer Queue**: switch role to "Reviewer", approve the draft — note
   that it's now part of the searchable repository (the knowledge loop).
5. **Dashboard**: show recurring countries/sections/keywords.
6. **Audit Trail**: show the full history for that RFI (created → drafted →
   reviewed → approved).

## Things intentionally kept out of scope (per the concept note)

- **Proactive risk scoring** — flagged as an optional/advanced extension
  only, since it needs labelled RFI vs. non-RFI application data that isn't
  available for the hackathon; a rule-based version could be added later.
- **Enterprise RBAC / a real auth system** — the sidebar role selector is a
  simulated stand-in, sufficient to demonstrate the User/Reviewer workflow.
- **A separate FastAPI service** — the `core/` package is already cleanly
  separated from the UI, so a thin FastAPI layer could be added later
  without restructuring the logic, but wasn't needed to prove out the
  prototype within the hackathon timeline.

## Extending it further

- Swap SQLite for Postgres by changing `DATABASE_URL` in `core/config.py`.
- Add a `faiss`/vector-DB index in `core/embeddings.py` if the repository
  grows beyond a few thousand RFIs (the current approach re-embeds the
  corpus per search, which is fine at hackathon/pilot scale).
- Wire `core/` up behind a FastAPI app if you want a separate API layer for
  a richer frontend later.

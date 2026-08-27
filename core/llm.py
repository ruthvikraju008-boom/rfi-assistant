"""
Feature 3 — Evidence-Grounded AI Response Assistant.

Takes a new RFI "Consideration" text, retrieves the most similar historical
RFIs (via hybrid_search), and asks an LLM to draft a response grounded ONLY
in those historical considerations/responses -- explicitly citing which
historical RFIs it used and flagging any material differences for human
review.

Supports Anthropic or OpenAI as the LLM provider (configured via .env). If
neither API key is set, a transparent template-based fallback is used
instead so the app always produces a (clearly-labelled, non-hallucinated)
draft, built directly from the single closest historical response -- useful
for demos without needing any API key.
"""
from dataclasses import dataclass, field
from typing import List

from core.search import SearchResult
from core.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, OPENAI_API_KEY, OPENAI_MODEL

PROMPT_TEMPLATE = """You are an expert regulatory assistant helping to draft a response to an RFI (Request for Information) from a health authority, for a EU Clinical Trial Regulation (CTR) submission.

## Your Task
Draft a professional, concise, and accurate response to the new RFI listed below. Your draft must be based ONLY on the provided Historical Context -- do not invent facts, dates, or approvals that are not present in it.

## Instructions
1. Base your response on the approved responses from similar, historical RFIs below.
2. Clearly reference which historical RFI(s) you are relying on.
3. CRITICALLY: If there is a meaningful difference between the new RFI and the historical ones (e.g. different protocol version, different country/MSC, different document), explicitly call this out under a "Points for human review" heading rather than papering over it.

## Historical Context (from the knowledge repository)
{historical_context}

## New RFI to Answer
Consideration: {new_consideration}

## Draft Response:"""


@dataclass
class DraftResult:
    draft_text: str
    sources: List[dict]
    difference_flags: List[str]
    provider: str


def _format_historical_context(matches: List[SearchResult]) -> str:
    blocks = []
    for i, m in enumerate(matches, 1):
        r = m.rfi
        blocks.append(
            f"[Historical RFI #{r.id}] (relevance {round(m.combined_score * 100)}%)\n"
            f"  Country/MSC: {r.msc or 'n/a'} | Section: {r.section_parts or 'n/a'}\n"
            f"  Consideration: {r.consideration_text}\n"
            f"  Approved response: {r.sponsor_response}\n"
        )
    return "\n".join(blocks) if blocks else "(no similar historical RFIs found)"


def _detect_differences(new_consideration: str, matches: List[SearchResult]) -> List[str]:
    """Lightweight, explainable heuristic -- not ML -- flags for human review."""
    flags = []
    if not matches:
        flags.append("No sufficiently similar historical RFI was found -- draft with extra caution.")
        return flags

    top = matches[0].rfi
    countries_mentioned = {"germany", "france", "italy", "spain", "netherlands", "poland", "belgium"}
    mentioned_in_new = {c for c in countries_mentioned if c in new_consideration.lower()}
    if top.msc and mentioned_in_new and top.msc.lower() not in mentioned_in_new:
        flags.append(
            f"New RFI appears to concern {', '.join(mentioned_in_new).title()}, "
            f"but the closest historical match was for {top.msc}. Confirm applicability."
        )

    if "version" in new_consideration.lower() and top.consideration_text and "version" in top.consideration_text.lower():
        flags.append(
            "Both the new and historical RFI reference a protocol/document version -- "
            "double-check the version numbers actually match before reusing the response."
        )

    if matches[0].combined_score < 0.35:
        flags.append(
            "Best match relevance score is low -- treat this draft as a starting point only, "
            "not a ready-to-submit response."
        )
    return flags


def _fallback_template_draft(new_consideration: str, matches: List[SearchResult]) -> str:
    if not matches:
        return (
            "[DRAFT -- NO HISTORICAL PRECEDENT FOUND]\n\n"
            "No sufficiently similar historical RFI exists in the repository yet. "
            "Please prepare this response manually and, once approved, add it to the "
            "repository so future similar RFIs can reuse it."
        )
    top = matches[0].rfi
    lines = [
        "[DRAFT -- generated from closest historical precedent, please review]",
        "",
        f"Based on historical RFI #{top.id} ({top.msc or 'n/a'}, {top.section_parts or 'n/a'}), "
        f"which raised a similar consideration:",
        f'  "{top.consideration_text}"',
        "",
        "the following response is proposed, adapted from the previously approved answer:",
        "",
        f"  {top.sponsor_response}",
        "",
        "Please review and adjust the wording above to precisely match the specifics of the new RFI "
        "before submission.",
    ]
    return "\n".join(lines)


def _call_anthropic(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")


def _call_openai(prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content


def generate_draft(new_consideration: str, matches: List[SearchResult]) -> DraftResult:
    historical_context = _format_historical_context(matches)
    prompt = PROMPT_TEMPLATE.format(
        historical_context=historical_context,
        new_consideration=new_consideration,
    )

    provider = "template_fallback"
    draft_text = None

    try:
        if ANTHROPIC_API_KEY:
            draft_text = _call_anthropic(prompt)
            provider = "anthropic"
        elif OPENAI_API_KEY:
            draft_text = _call_openai(prompt)
            provider = "openai"
    except Exception as e:  # pragma: no cover - network/credentials issues
        draft_text = None
        provider = f"template_fallback (LLM call failed: {e})"

    if not draft_text:
        draft_text = _fallback_template_draft(new_consideration, matches)
        if provider == "template_fallback":
            pass

    sources = [
        {
            "id": m.rfi.id,
            "rfi_uuid": m.rfi.rfi_uuid,
            "msc": m.rfi.msc,
            "section_parts": m.rfi.section_parts,
            "relevance_pct": round(m.combined_score * 100),
        }
        for m in matches
    ]

    return DraftResult(
        draft_text=draft_text,
        sources=sources,
        difference_flags=_detect_differences(new_consideration, matches),
        provider=provider,
    )

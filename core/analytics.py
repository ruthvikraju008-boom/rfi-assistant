"""
Feature 4 — RFI Intelligence Dashboard.

Answers three questions, deliberately kept simple per the project plan:
  1. What is recurring?   -> top keywords in Consideration text
  2. Where is it recurring? -> counts by country (MSC) and by application section
  3. How often?            -> counts over time / totals

No black-box ML here on purpose -- these are plain, explainable aggregations
over the structured repository, which is easy to defend in a regulated
environment.
"""
import re
from collections import Counter
from typing import List

import pandas as pd

from core.models import RFI

_STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "for", "and", "or", "on", "is",
    "are", "with", "this", "that", "please", "confirm", "was", "were",
    "has", "have", "not", "be", "as", "by", "at", "from", "all", "which",
    "documentation", "application", "provided",
}


def rfis_to_dataframe(rfis: List[RFI]) -> pd.DataFrame:
    rows = []
    for r in rfis:
        rows.append({
            "id": r.id,
            "rfi_uuid": r.rfi_uuid,
            "application_id": r.application_id,
            "msc": r.msc or "Unknown",
            "section_parts": r.section_parts or "Unknown",
            "status": r.status,
            "consideration_text": r.consideration_text or "",
            "created_at": r.created_at,
        })
    return pd.DataFrame(rows)


def count_by_country(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=int)
    return df["msc"].value_counts()


def count_by_section(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=int)
    return df["section_parts"].value_counts()


def top_keywords(df: pd.DataFrame, n: int = 15) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=int)
    counter = Counter()
    for text in df["consideration_text"]:
        words = re.findall(r"[a-zA-Z]{4,}", text.lower())
        counter.update(w for w in words if w not in _STOPWORDS)
    if not counter:
        return pd.Series(dtype=int)
    common = counter.most_common(n)
    return pd.Series({w: c for w, c in common})

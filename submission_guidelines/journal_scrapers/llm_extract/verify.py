"""Pulls the non-null numeric/categorical claims out of an extracted record,
and checks the model's supporting quotes for them are real substrings of the
source text -- not a semantic check (that would need another model call and
more trust), just "did you actually quote something that's really there".
A model that can't produce a genuine quote for a number it claimed is a
model that likely invented the number.
"""
from __future__ import annotations

import re


def _norm(text: str) -> str:
    """Collapse whitespace so minor formatting differences (newlines, double
    spaces) don't cause false negatives in the substring check."""
    return re.sub(r"\s+", " ", text).strip().lower()


def _range_str(lo: int | None, hi: int | None) -> str:
    if lo is not None and hi is not None and lo != hi:
        return f"{lo}-{hi}"
    return str(hi if hi is not None else lo)


def extract_claims(record: dict) -> list[dict]:
    """Walks the record for fields worth citation-checking: numeric ranges and
    fixed categorical values. Free-text fields (notes, description, reference_style)
    are deliberately NOT included -- there's no crisp "claim" to verify a quote
    against for open-ended prose, and that's fine, they're lower-stakes than a
    number a downstream comparison might actually rely on."""
    claims: list[dict] = []

    def add(path: str, claim: str) -> None:
        claims.append({"path": path, "claim": claim})

    def word_limit(path: str, label: str, wl: dict | None) -> None:
        if wl and (wl.get("min") is not None or wl.get("max") is not None):
            unit = wl.get("unit", "words")
            add(path, f"{label} word limit: {_range_str(wl.get('min'), wl.get('max'))} {unit}")

    def count_range(path: str, label: str, cr: dict | None) -> None:
        if cr and (cr.get("min") is not None or cr.get("max") is not None):
            add(path, f"{label}: {_range_str(cr.get('min'), cr.get('max'))}")

    for i, at in enumerate(record.get("article_types") or []):
        prefix = f"article_types[{i}] ({at.get('type', '?')})"
        word_limit(f"{prefix}.total_word_limit", f"{at.get('type')}", at.get("total_word_limit"))
        for j, fl in enumerate(at.get("figure_limits") or []):
            count_range(f"{prefix}.figure_limits[{j}]", f"{at.get('type')} {fl.get('counts', 'figures')}", fl)
        count_range(f"{prefix}.reference_limit", f"{at.get('type')} references", at.get("reference_limit"))
        count_range(f"{prefix}.author_limit", f"{at.get('type')} authors", at.get("author_limit"))

    prm = record.get("peer_review_model")
    if prm and prm.get("value"):
        add("peer_review_model", f"Peer review model: {', '.join(prm['value'])}")

    return claims


def verify_claims(claims: list[dict], quotes: list[dict], page_text: str) -> list[dict]:
    """`quotes` is the model's own output from the citation-check call: a list of
    {"claim": ..., "quote": ...}. Matches back to `claims` by claim text, then
    checks the quote is a real (whitespace-normalized) substring of page_text."""
    quote_by_claim = {q.get("claim", "").strip(): q.get("quote", "") for q in quotes if isinstance(q, dict)}
    normalized_text = _norm(page_text)

    report = []
    for c in claims:
        quote = quote_by_claim.get(c["claim"], "")
        found_quote = bool(quote) and quote.strip().upper() != "NOT FOUND"
        verified = found_quote and _norm(quote) in normalized_text
        report.append({**c, "quote": quote, "verified": verified})
    return report

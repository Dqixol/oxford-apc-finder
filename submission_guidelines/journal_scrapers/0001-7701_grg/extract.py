"""Builds General Relativity and Gravitation's structured JSON from HTML
already fetched by direct_fetch.py -- no live fetching here. Same
generic-extraction approach as journal_scrapers/1756-1833_bmj/extract.py and
journal_scrapers/1939-8980_annals-of-mathematics/extract.py.

Single page, the standard Springer "submission-guidelines" template also used
by Mathematische Annalen/Inventiones/Selecta -- but this is a physics
journal, not a maths one, and its own text was read on its own terms (no
assumptions carried over from the maths journals about LaTeX class names or
arXiv-first culture).

Scope: this page documents no distinct named article types (no "Research
Article" vs "Review" vs "Letter" split the way BMJ/Nature do) -- just one
general manuscript format, same situation as Annals of Mathematics. No
overall word/page limit is stated anywhere on the page; that's a confirmed
absence (common for this Springer template), not a gap.

Run directly: `python journal_scrapers/0001-7701_grg/extract.py`
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.schema import ArticleType, ISSN, JournalRecord, WordLimit  # noqa: E402

SOURCE_URL = "https://link.springer.com/journal/10714/submission-guidelines"
ISSN_PRINT = "0001-7701"
JSON_DIR = Path(__file__).resolve().parents[2] / "data_scrapes" / "json"


def build() -> JournalRecord:
    article_type = ArticleType(
        type="Article",
        description="General manuscript format -- the page documents no distinct named submission "
        "categories (no Research/Review/Letter split), just one general set of rules.",
        total_word_limit=WordLimit(
            notes=(
                "No overall word/page limit stated anywhere on the page (confirmed absence, consistent "
                "with this Springer template's usual pattern)."
            ),
        ),
        structure=(
            "Title page (title, author info, ORCID if available), Abstract (150-250 words, no "
            "undefined abbreviations or unspecified references), Keywords (4-6), Statements and "
            "Declarations, References"
        ),
        source_urls=[SOURCE_URL],
    )

    return JournalRecord(
        journal="General Relativity and Gravitation",
        publisher="Springer",
        issn=ISSN(print=ISSN_PRINT, electronic=None),
        LLM=True,
        validated=False,
        date_scraped=date.today().isoformat(),
        article_types=[article_type],
    )


def main() -> None:
    record = build()
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(record.to_dict(), indent=2, ensure_ascii=False)
    out_path = JSON_DIR / f"{ISSN_PRINT}.json"
    out_path.write_text(payload, encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

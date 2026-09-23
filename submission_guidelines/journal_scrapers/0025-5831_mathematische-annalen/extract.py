"""Builds Mathematische Annalen's structured JSON from HTML already fetched by
direct_fetch.py -- no live fetching here. See journal_scrapers/1756-1833_bmj/
extract.py for the general approach.

The source page is Springer's *generic* journal submission-guidelines
template (shared boilerplate reused across many Springer math/science
journals, not Mathematische Annalen-specific content) -- it describes one
general research-article submission format with no distinct article-type
breakdown (no Review/Letter/Comment categories stated).

Run directly: `python journal_scrapers/0025-5831_mathematische-annalen/extract.py`
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.schema import ArticleType, ISSN, JournalRecord, WordLimit  # noqa: E402

SOURCE_URL = "https://link.springer.com/journal/208/submission-guidelines"
ISSN_PRINT = "0025-5831"
JSON_DIR = Path(__file__).resolve().parents[2] / "data_scrapes" / "json"


def build() -> JournalRecord:
    article_type = ArticleType(
        type="Article",
        description="General research-article submission format -- the page states no distinct "
        "submission categories (no Review/Letter/Comment types named).",
        total_word_limit=WordLimit(
            notes=(
                "No total manuscript word/page limit stated anywhere on the page -- confirmed "
                "absence, consistent with this Springer template's usual pattern for math journals."
            ),
        ),
        structure=(
            "Title page (author names, affiliations, corresponding author, ORCID if available), "
            "Abstract (150-250 words, no undefined abbreviations or unspecified references), "
            "MSC classification codes (Mathematics Subject Classification -- 'an appropriate number' "
            "should be provided), Main text (decimal-system headings, max 3 levels), Statements and "
            "Declarations (competing interests, funding, data availability, etc.), Reference list "
            "(numbered, cited in square brackets in text)"
        ),
        source_urls=[SOURCE_URL],
    )

    return JournalRecord(
        journal="Mathematische Annalen",
        publisher="Springer",
        issn=ISSN(print="0025-5831"),
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

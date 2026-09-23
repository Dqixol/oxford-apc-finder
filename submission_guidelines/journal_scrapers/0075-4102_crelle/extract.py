"""Builds Crelle's (Journal für die reine und angewandte Mathematik) structured
JSON from HTML already fetched by direct_fetch.py -- no live fetching here.
See journal_scrapers/1939-8980_annals-of-mathematics/extract.py for the
general approach this follows (another single-page pure-math journal).

Single article type: like Annals of Mathematics, the journal doesn't document
distinct submission categories -- just one general research-paper format. No
word/page limit is stated anywhere on the page; confirmed absence, not a gap
(the journal instead constrains formatting -- title/running-head length,
Proclamation typesetting, reference style -- not manuscript length).

Real content lives in a '#submit' accordion section of the journal homepage,
mixed in with a full page's worth of nav chrome, recent-articles list, and
indexing-service badges -- read directly from the raw HTML for the two
plain-text details the Markdown conversion lost (the actual submission-system
URL, and confirmation that "download the class file here" has no real href
behind it, unlike the submission-system "here" earlier in the same
paragraph).

Run directly: `python journal_scrapers/0075-4102_crelle/extract.py`
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.schema import ArticleType, ISSN, JournalRecord, WordLimit  # noqa: E402

SOURCE_URL = "https://www.degruyterbrill.com/journal/key/crll/html"
ISSN_PRINT = "0075-4102"
JSON_DIR = Path(__file__).resolve().parents[2] / "data_scrapes" / "json"


def build() -> JournalRecord:
    article_type = ArticleType(
        type="Article",
        description="Original mathematics research papers -- the journal documents only one general "
        "submission format, no distinct named categories.",
        total_word_limit=WordLimit(
            notes=(
                "No word/page limit stated anywhere on the page -- confirmed absence; the page instead "
                "specifies formatting rules (title/running-head length, Proclamation typesetting, "
                "reference style), not manuscript length."
            ),
        ),
        structure=(
            "Short but informative abstract, Mathematics Subject Classification 2010 codes (primary "
            "and secondary), References (listed alphabetically), Author's address(es), with e-mail if "
            "available, following the reference list"
        ),
        source_urls=[SOURCE_URL],
    )

    return JournalRecord(
        journal="Journal für die reine und angewandte Mathematik (Crelle)",
        publisher="Walter de Gruyter GmbH (De Gruyter)",
        issn=ISSN(print=ISSN_PRINT),
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

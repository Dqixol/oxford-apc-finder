"""Builds Annals of Mathematics' structured JSON from HTML already fetched by
direct_fetch.py -- no live fetching here. See journal_scrapers/1756-1833_bmj/
extract.py for the general approach (and journal_scrapers/1476-4687_nature/
scrape.py for the bespoke-regex alternative this is being compared against).

Single article type: the journal doesn't document distinct submission
categories the way Nature/BMJ do -- just one general research-paper format.
No word/reference/figure count limits are stated anywhere on the page; that's
a confirmed absence (unrestricted length is a real, common policy for pure
maths journals, not a gap), not something unchecked.

Run directly: `python journal_scrapers/1939-8980_annals-of-mathematics/extract.py`
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.schema import ArticleType, ISSN, JournalRecord, WordLimit  # noqa: E402

SOURCE_URL = "https://annals.math.princeton.edu/submission-guidelines"
ISSN_PRINT = "0003-486X"
JSON_DIR = Path(__file__).resolve().parents[2] / "data_scrapes" / "json"


def build() -> JournalRecord:
    article_type = ArticleType(
        type="Article",
        description="Original mathematics research papers -- the journal documents only one general submission format.",
        total_word_limit=WordLimit(
            notes=(
                "No word/page limit stated anywhere on the page (confirmed absence, common for pure maths "
                "journals where proof length is dictated by the mathematics, not an editorial target)."
            ),
        ),
        structure="Abstract (~200 words or less, self-contained, no bibliography references), Bibliography",
        source_urls=[SOURCE_URL],
    )

    return JournalRecord(
        journal="Annals of Mathematics",
        publisher="Princeton University (self-published)",
        issn=ISSN(print="0003-486X", electronic="1939-8980"),
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

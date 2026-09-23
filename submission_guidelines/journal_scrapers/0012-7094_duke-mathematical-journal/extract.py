"""Builds Duke Mathematical Journal's structured JSON from HTML already fetched
by direct_fetch.py -- no live fetching here. Same general approach as
journal_scrapers/1939-8980_annals-of-mathematics/extract.py (single general
article type, same MSP EditFlow submission platform), but this page is
richer: it states an explicit AI/LLM disclosure policy, an abstract length,
a running-head length, and a precise LaTeX page-dimension spec, none of
which Annals' page states.

Single article type: like Annals, the page doesn't document distinct
submission categories (no Letters/Notes/etc. called out separately) -- just
one general research-paper format.

Run directly: `python journal_scrapers/0012-7094_duke-mathematical-journal/extract.py`
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.schema import ArticleType, ISSN, JournalRecord, WordLimit  # noqa: E402

SOURCE_URL = "https://www.dukeupress.edu/duke-mathematical-journal"
ISSN_PRINT = "0012-7094"
JSON_DIR = Path(__file__).resolve().parents[2] / "data_scrapes" / "json"


def build() -> JournalRecord:
    article_type = ArticleType(
        type="Article",
        description="Original mathematics research papers -- the journal documents only one general "
        "submission format, no separately named article categories.",
        total_word_limit=WordLimit(
            notes=(
                "No total word/page limit stated anywhere on the page -- unlike Annals of Mathematics' "
                "page, this one never frames it as an explicit 'no limit' policy, it's simply never "
                "mentioned alongside the other precise numeric specs given (abstract, running head). "
                "Treated as not stated rather than a confirmed-unlimited policy."
            ),
        ),
        structure=(
            "Abstract (no more than 300 words; French-language submissions include both English and "
            "French versions)"
        ),
        source_urls=[SOURCE_URL],
    )

    return JournalRecord(
        journal="Duke Mathematical Journal",
        publisher="Duke University Press",
        issn=ISSN(print="0012-7094", electronic="1547-7398"),
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

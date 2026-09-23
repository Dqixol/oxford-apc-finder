"""Builds Inventiones Mathematicae's structured JSON from HTML already fetched
by direct_fetch.py -- no live fetching here. See journal_scrapers/
1939-8980_annals-of-mathematics/extract.py for the general approach.

Single article type: like Annals of Mathematics, this page (Springer's
generic journal-submission-guidelines template) describes one general
manuscript-submission process, not distinct named submission categories.

No total manuscript word/page limit is stated anywhere on this page --
direct_fetch.py's own note on this journal ("Standard Springer math-journal
template (same as Mathematische Annalen/GRG); no explicit word/page limit
found, which is consistent with that template's usual pattern") already
established this as the template's normal behavior, not something this
script is guessing at. Only the Abstract has a stated length (150-250 words).

Unlike Annals of Mathematics, this journal is NOT free: it's a Springer
hybrid-OA (Open Choice) journal with APCs that vary by journal -- out of
scope for the current schema (see common/schema.py), not recorded here.

Run directly: `python journal_scrapers/0020-9910_inventiones-mathematicae/extract.py`
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.schema import ArticleType, ISSN, JournalRecord, WordLimit  # noqa: E402

SOURCE_URL = "https://link.springer.com/journal/222/submission-guidelines"
ISSN_PRINT = "0020-9910"
JSON_DIR = Path(__file__).resolve().parents[2] / "data_scrapes" / "json"


def build() -> JournalRecord:
    article_type = ArticleType(
        type="Article",
        description="General mathematics research papers -- the page describes one manuscript-submission "
        "process with no distinct named submission categories (Research Article vs Review, etc.).",
        total_word_limit=WordLimit(
            notes=(
                "No total manuscript word/page limit stated on this page -- consistent with the "
                "'no explicit limit' pattern this same Springer template shows on other math journals in "
                "this project, but only independently confirmed by reading this page's own silence on the topic."
            ),
        ),
        structure=(
            "Title page (title, author names/affiliations, corresponding author, ORCID if available), "
            "Abstract (150-250 words, no undefined abbreviations or unspecified references), "
            "Statements and Declarations (Competing Interests, and other declarations as applicable)"
        ),
        source_urls=[SOURCE_URL],
    )

    return JournalRecord(
        journal="Inventiones Mathematicae",
        publisher="Springer (Springer Nature)",
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

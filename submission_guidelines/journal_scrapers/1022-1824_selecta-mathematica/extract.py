"""Builds Selecta Mathematica's structured JSON from the page already fetched by
direct_fetch.py -- no live fetching here. See journal_scrapers/1756-1833_bmj/
extract.py for the general approach and journal_scrapers/1939-8980_annals-of-
mathematics/extract.py for the closer analogue (single-article-type pure-math
journal, no live fetching, hand-filled dataclass).

Source page is genuinely short (real content, confirmed by reading the whole
thing -- not a stub): one "Instructions for Authors" page covering authorship
conditions, the editorial process, LaTeX formatting settings, figure/table
formats, reference style, corrections, the submission email address, optional
paid editing services, and a pointer to a separate (unfetched) open-access
fees/licences page.

Single article type: like Annals of Mathematics and Duke Mathematical Journal,
the page describes one general manuscript-submission process -- no distinct
named article categories (Research Article vs Review, etc.). No word count,
reference count, figure count, or author count limits are stated anywhere;
that's a confirmed absence, not a gap -- common for pure-math journals where
proof length is dictated by the mathematics itself.

Run directly: `python journal_scrapers/1022-1824_selecta-mathematica/extract.py`
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.schema import ArticleType, ISSN, JournalRecord, WordLimit  # noqa: E402

SOURCE_URL = "https://link.springer.com/journal/29/submission-guidelines"
ISSN_PRINT = "1022-1824"
JSON_DIR = Path(__file__).resolve().parents[2] / "data_scrapes" / "json"


def build() -> JournalRecord:
    article_type = ArticleType(
        type="Article",
        description=(
            "General mathematics research manuscripts -- the page documents one manuscript-"
            "submission process with no distinct named article categories."
        ),
        total_word_limit=WordLimit(
            notes=(
                "No word/page count limit stated anywhere on the page -- confirmed absence, "
                "common for pure-maths journals where proof length is set by the mathematics, not "
                "an editorial target."
            ),
        ),
        structure=(
            "Abstract (in English, summarizing the principal techniques and conclusions in "
            "relation to known results), Keywords, AMS subject classification (where appropriate), "
            "Bibliography/references"
        ),
        figures_tables=(
            "No figure/table count limit stated. Figures/tables sent either as part of the document "
            "in a LaTeX 'picture' environment, as EPS files (fonts restricted to TeX/PostScript "
            "Base 35/MathPifonts, via epsf.sty), as uncompressed TIFF files, or as fair-copy paper "
            "scaled to about 200%."
        ),
        source_urls=[SOURCE_URL],
    )

    return JournalRecord(
        journal="Selecta Mathematica",
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

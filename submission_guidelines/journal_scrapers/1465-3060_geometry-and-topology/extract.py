"""Builds Geometry & Topology's structured JSON from the page already fetched
by direct_fetch.py (data_scrapes/raw_html/1465-3060/submissions.md, cleaned
from the .html in the same directory) -- no live fetching here. See
journal_scrapers/1756-1833_bmj/extract.py for the general approach and
journal_scrapers/1939-8980_annals-of-mathematics/extract.py for the closest
sibling: same publisher (MSP) and same EditFlow submission platform, also a
single-article-type pure-maths journal with no stated word/reference limits.

Single article type: like Annals of Mathematics, the submissions page
documents one general research-paper format, not distinct categories.

ISSN and publisher/platform confirmed from the raw HTML (not visible in the
.md rendering): the page's own sidebar states "ISSN (print): 1465-3060" and
"ISSN (electronic): 1364-0380" (data_scrapes/raw_html/1465-3060/
submissions.html, class="about-area issn"), and the submission-form links
point at https://ef.msp.org/submit/gt and https://ef.msp.org/submit_new.php?
j=gt -- confirming both the publisher (Mathematical Sciences Publishers,
msp.org) and the EditFlow platform directly from source, not just from
external/background knowledge.

Run directly: `python3 journal_scrapers/1465-3060_geometry-and-topology/extract.py`
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.schema import ArticleType, ISSN, JournalRecord, WordLimit  # noqa: E402

SOURCE_URL = "https://msp.org/gt/about/journal/submissions.html"
ISSN_ID = "1465-3060"  # print ISSN, used as the file/folder identifier (repo convention for this journal)
JSON_DIR = Path(__file__).resolve().parents[2] / "data_scrapes" / "json"


def build() -> JournalRecord:
    article_type = ArticleType(
        type="Article",
        description="Original mathematics research papers -- the journal documents only one general submission format.",
        total_word_limit=WordLimit(
            notes=(
                "No overall word/page limit stated anywhere on the page -- confirmed absence, consistent "
                "with Annals of Mathematics and other MSP/pure-maths journals. Only the abstract carries an "
                "explicit word target (see structure)."
            ),
        ),
        structure=(
            "Abstract (~150 words or fewer, self-contained, no bibliography references -- if the article "
            "is not in English, two abstracts required: one in the article's language, one in English), "
            "Keywords, Mathematics Subject Classification (MSC) code (at least one), Author postal address "
            "and affiliation (if appropriate) for each coauthor, Bibliography"
        ),
        figures_tables=(
            "No count limit stated. Figures must be publication quality; after acceptance, source files "
            "must be supplied as vector graphics (EPS or PDF preferred), bundled into a single archive "
            "(zip/tar/rar/etc). Each figure must be captioned and numbered so it can float; small figures "
            "may instead be kept inline in the text."
        ),
        source_urls=[SOURCE_URL],
    )

    return JournalRecord(
        journal="Geometry & Topology",
        publisher="Mathematical Sciences Publishers (MSP)",
        issn=ISSN(print="1465-3060", electronic="1364-0380"),
        LLM=True,
        validated=False,
        date_scraped=date.today().isoformat(),
        article_types=[article_type],
    )


def main() -> None:
    record = build()
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(record.to_dict(), indent=2, ensure_ascii=False)
    out_path = JSON_DIR / f"{ISSN_ID}.json"
    out_path.write_text(payload, encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

"""Builds JHEP's structured JSON from HTML already fetched by direct_fetch.py --
no live fetching here. Same hand-transcription approach as
journal_scrapers/1756-1833_bmj/extract.py.

Two source pages were fetched (see direct_fetch.py's TARGETS entry for
"jhep"): Springer's submission-guidelines page is nearly empty (just a link
out to a separate, unfetched "Open access publishing" page for fee info --
so no APC/fee figure is captured here, out of scope for this schema anyway
per Annals of Mathematics' extract.py precedent, but flagged here since it's
directly the kind of thing this project cares about). The real content is
SISSA's author-help page (jhep.sissa.it), which is what this file is built
from.

JHEP doesn't document distinct named article-submission categories the way
Nature/BMJ do -- it's a single research-article format (physics preprint/
journal hybrid, arXiv-linked, SCOAP3-funded) plus one explicitly separate
category: Errata/Addenda, which has its own real length guidance and
submission rules.

Run directly: `python journal_scrapers/1126-6708_jhep/extract.py`
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.schema import ArticleType, ISSN, JournalRecord, WordLimit  # noqa: E402

SOURCE_URL = "https://jhep.sissa.it/jhep/help/helpLoader.jsp?pgType=author"
ISSN_PRINT = "1126-6708"
JSON_DIR = Path(__file__).resolve().parents[2] / "data_scrapes" / "json"


def build() -> JournalRecord:
    article_types = [
        ArticleType(
            type="Article",
            description="Standard JHEP research article. Submission is arXiv-linked (an arXiv ID is "
            "required at submission, since JHEP articles are funded by the SCOAP3 consortium and must be "
            "categorised/published accordingly) and requires selecting keywords from JHEP's keyword list.",
            total_word_limit=WordLimit(
                notes=(
                    "No explicit word/page limit stated on the fetched page -- genuinely not found "
                    "(the page only says editors 'will consider whether the content is of sufficient "
                    "scientific interest compared to the overall length', implying no fixed number exists "
                    "rather than one being omitted from what was fetched)."
                ),
            ),
            figures_tables=(
                "No limit on the number of figures/tables stated. Figure resolution: minimum 150 dpi, "
                "maximum 250 dpi. Vector images with fonts must have the fonts embedded."
            ),
            source_urls=[SOURCE_URL],
        ),
        ArticleType(
            type="Erratum/Addendum",
            description="Post-publication correction (Erratum) or addition (Addendum) to a previously "
            "published JHEP article, submitted as a stand-alone article referencing the original.",
            total_word_limit=WordLimit(
                max=2,
                unit="pages",
                notes="Usually no more than 1-2 pages -- explicit guideline in the source, not phrased as a hard cap.",
            ),
            structure="Title (\"Erratum: <original title>\" or \"Addendum: <original title>\")",
            source_urls=[SOURCE_URL],
        ),
    ]

    return JournalRecord(
        journal="Journal of High Energy Physics (JHEP)",
        publisher="Springer -- SISSA (the International School for Advanced Studies) operates JHEP's "
        "submission and peer-review platform at jhep.sissa.it, and the source states accepted papers are "
        "'sent for publication on the Springer website'; the source never uses the word 'publisher' "
        "directly, so this is inferred from those two facts.",
        issn=ISSN(print=ISSN_PRINT, electronic=None),
        LLM=True,
        validated=False,
        date_scraped=date.today().isoformat(),
        article_types=article_types,
    )


def main() -> None:
    record = build()
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(record.to_dict(), indent=2, ensure_ascii=False)
    out_path = JSON_DIR / f"{ISSN_PRINT}.json"
    out_path.write_text(payload, encoding="utf-8")
    print(f"Wrote {out_path} -- {len(record.article_types)} article types")


if __name__ == "__main__":
    main()

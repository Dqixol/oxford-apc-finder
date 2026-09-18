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
from common.schema import (  # noqa: E402
    ArticleType,
    ISSN,
    JournalRecord,
    SourcedValue,
    WordLimit,
)

SOURCE_URL = "https://annals.math.princeton.edu/submission-guidelines"
ISSN_PRINT = "0003-486X"
JSON_DIR = Path(__file__).resolve().parents[2] / "data_scrapes" / "json"


def build() -> JournalRecord:
    article_type = ArticleType(
        type="Article",
        source_url=SOURCE_URL,
        description="Original mathematics research papers -- the journal documents only one general submission format.",
        total_word_limit=WordLimit(
            notes="No word/page limit stated anywhere on the page -- confirmed absence, common for pure "
            "maths journals where proof length is dictated by the mathematics, not an editorial target."
        ),
        required_sections=["Abstract (~200 words or less, self-contained, no bibliography references)", "Bibliography"],
        reference_style=(
            "Complete references including article titles and page ranges; BibTeX preferred; DOI, Math "
            "Reviews (MathSciNet), and Zentralblatt MATH numbers included where available; arXiv number or "
            "URL for unpublished references."
        ),
        notes=(
            "Submitted as a PDF via MSP's EditFlow system (ef.msp.org/submit/annals) -- same submission "
            "platform as Geometry & Topology and Duke Mathematical Journal. LaTeX encouraged (class file "
            "'aomart', available from CTAN) but not required. Figures must be vector graphics (EPS or PDF "
            "preferred), bundled into a single archive."
        ),
    )

    return JournalRecord(
        journal="Annals of Mathematics",
        publisher="Princeton University (self-published)",
        issn=ISSN(print="0003-486X", electronic="1939-8980"),
        url=SOURCE_URL,
        date_scraped=date.today().isoformat(),
        ai_use_policy=SourcedValue(
            value=(
                "Authors must be human and take full responsibility for the submission's correctness and "
                "citation accuracy. AI agents cannot be named authors. If an AI tool/LLM contributed an idea, "
                "authors must describe that idea and specify its location in the paper."
            ),
            source_url=SOURCE_URL,
        ),
        latex_accepted=SourcedValue(
            value=True,
            source_url=SOURCE_URL,
            notes="Encouraged (class file 'aomart' from CTAN) but not required.",
        ),
        template_provided=SourcedValue(
            value=True,
            source_url=SOURCE_URL,
            notes="The 'aomart' LaTeX class file, available from CTAN -- optional, not mandatory.",
        ),
        # The source page just says "available from CTAN" without a direct link; this URL follows
        # CTAN's standard /pkg/<name> convention and was verified live (200) before including it here.
        template_url="https://ctan.org/pkg/aomart",
        languages_accepted=["English", "French", "German"],
        article_types=[article_type],
        remarks=(
            "No article processing charges (out of scope for this schema, noted here since it was explicitly "
            "stated on the page). Non-English submissions require an English abstract in addition to the "
            "original-language one."
        ),
        needs_review=["peer_review_model", "preprint_policy", "robots_txt_allowed"],
        source="scraped",
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

"""Builds JCAP's structured JSON from HTML already fetched by direct_fetch.py --
no live fetching here. See journal_scrapers/1756-1833_bmj/extract.py for the
general approach.

Two pages were fetched (`data_scrapes/raw_html/1475-7516/`): `about.md`, the
IOPscience listing, is a thin stub with no rules at all (just a one-paragraph
scope description) -- direct_fetch.py's own note flags this. The real content
lives on `author-help.md` (jcap.sissa.it, run by SISSA Medialab jointly with
IOP Publishing), which is what almost everything below is sourced from.

Single article type: the page never names distinct submission categories
(no Letter/Review/Comment split like Nature/BMJ) -- just one general research
submission, arXiv-integrated (an arXiv id is required at submission time and
the submitted version must match it). Errata/Addenda exist as a separate
post-publication submission path but aren't modelled as a distinct
ArticleType here since the source states no independent formatting rules for
them beyond a title-prefix convention.

Run directly: `python journal_scrapers/1475-7516_jcap/extract.py`
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.schema import ArticleType, ISSN, JournalRecord, WordLimit  # noqa: E402

SOURCE_URL = "https://jcap.sissa.it/jcap/help/helpLoader.jsp?pgType=author"
ISSN_PRINT = "1475-7516"
JSON_DIR = Path(__file__).resolve().parents[2] / "data_scrapes" / "json"


def build() -> JournalRecord:
    article_type = ArticleType(
        type="Article",
        description="General research submission -- theoretical, observational, and experimental cosmology "
        "and astroparticle physics. No distinct submission categories (Letter/Review/Comment) are documented; "
        "Errata and Addenda exist as a separate post-publication submission path, not an article type with "
        "its own formatting rules.",
        total_word_limit=WordLimit(
            max=50,
            unit="pages",
            notes=(
                "'JCAP papers do not normally exceed 50 pages' -- explicit editorial-discretion guidance, not a "
                "hard cap. The Editors may recommend shortening if length isn't justified by content; no fixed "
                "minimum target stated either."
            ),
        ),
        structure=(
            "Title, authors, affiliations, e-mail addresses; Abstract (must fit on the first page; no "
            "formulae or references in title/abstract); 2-4 keywords from the JCAP keyword list"
        ),
        source_urls=[SOURCE_URL],
    )

    return JournalRecord(
        journal="Journal of Cosmology and Astroparticle Physics (JCAP)",
        publisher="IOP Publishing and SISSA Medialab (joint)",
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
    print(f"Wrote {out_path} -- {len(record.article_types)} article type(s)")


if __name__ == "__main__":
    main()

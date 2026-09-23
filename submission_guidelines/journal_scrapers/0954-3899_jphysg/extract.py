"""Builds Journal of Physics G: Nuclear and Particle Physics' structured JSON
from HTML already fetched by direct_fetch.py -- no live fetching here. See
journal_scrapers/1939-8980_annals-of-mathematics/extract.py for the general
approach, and journal_scrapers/0264-9381_cqg/extract.py for the sibling IOP
journal hitting the exact same gap (read closely and mirrored here).

Scope note: the fetched page (`about.md`) is IOP Publishing's shared,
platform-wide author-guidelines page, not a JPhysG-specific one -- it
explicitly says (under "Article length") that per-journal maximum
recommended article length lives on a separate
`iopscience.iop.org/journal/<issn>` "About the journal" page. That page is
gated behind a CAPTCHA and was never successfully fetched (same situation as
CQG, fetched in parallel -- see that extract.py's note). So
`total_word_limit` and any JPhysG-specific article types (Focus Collection
articles, topical reviews, comments and replies -- all named generically on
this shared page without JPhysG-specific rules) are a genuine not-checked
gap, not a confirmed absence -- flagged in `needs_review`, not guessed at.

`peer_review_model` and `ai_use_policy` are likewise per-journal (the page
repeatedly says "check the peer review model for the journal you are
submitting to") and not stated for JPhysG specifically here -- also
needs_review, not guessed.

Run directly: `python journal_scrapers/0954-3899_jphysg/extract.py`
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.schema import ArticleType, ISSN, JournalRecord, WordLimit  # noqa: E402

SOURCE_URL = "https://publishingsupport.iopscience.iop.org/journals/journal-of-physics-g-nuclear-and-particle-physics/"
ISSN_PRINT = "0954-3899"
JSON_DIR = Path(__file__).resolve().parents[2] / "data_scrapes" / "json"


def build() -> JournalRecord:
    article_type = ArticleType(
        type="Article",
        description=(
            "Original theoretical and experimental research articles in nuclear and particle physics, "
            "including nuclear and particle astrophysics -- the fetched page is IOP's shared platform-wide "
            "guidance, not a JPhysG-specific article-type list. The page also mentions that many IOP journals "
            "offer 'Focus Collection articles, topical reviews, comments and replies' in addition to regular "
            "research papers, but does not confirm which of these JPhysG itself offers -- that lives behind "
            "the CAPTCHA-gated per-journal page, not fetched here."
        ),
        total_word_limit=WordLimit(
            notes="Genuinely not stated anywhere on this page, not even a 'not checked' note.",
        ),
        structure=(
            "Title, Authors, Keywords, Abstract (IOP platform-wide guidance: should not normally be more "
            "than 300 words, not JPhysG-specific -- may be superseded by a per-journal abstract limit not "
            "checked here), Introduction, Method, Results, Discussion, Conclusion, Acknowledgements, "
            "References"
        ),
        source_urls=[SOURCE_URL],
    )

    return JournalRecord(
        journal="Journal of Physics G: Nuclear and Particle Physics",
        publisher="IOP Publishing",
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
    print(f"Wrote {out_path} -- {len(record.article_types)} article types")


if __name__ == "__main__":
    main()

"""Builds Classical and Quantum Gravity's structured JSON from HTML already
fetched by direct_fetch.py -- no live fetching here. See journal_scrapers/
1939-8980_annals-of-mathematics/extract.py for the general approach.

Scope note: the fetched page (`about.md`) is IOP Publishing's shared,
platform-wide author-guidelines page, not a CQG-specific one -- it explicitly
says CQG's own article types and length limits live on a separate
`iopscience.iop.org/journal/<issn>` "About the journal" page, which is
gated behind a Radware Bot Manager CAPTCHA (confirmed: direct_fetch.py's own
TARGETS note recorded a fetched captcha challenge page, not real content).
So `total_word_limit`/journal-specific `article_types` are a genuine
not-checked gap, not a confirmed absence -- flagged in `needs_review`, not
guessed at from the unrelated supplementary-file-size numbers (10MB video,
150MB combined) that are on this page.

`peer_review_model` and `ai_use_policy` are likewise per-journal (the page
repeatedly says "check the peer review model for the journal you are
submitting to") and not stated for CQG specifically here -- also
needs_review, not guessed.

Run directly: `python journal_scrapers/0264-9381_cqg/extract.py`
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.schema import ArticleType, ISSN, JournalRecord, WordLimit  # noqa: E402

SOURCE_URL = "https://publishingsupport.iopscience.iop.org/journals/classical-and-quantum-gravity/"
ISSN_PRINT = "0264-9381"
JSON_DIR = Path(__file__).resolve().parents[2] / "data_scrapes" / "json"


def build() -> JournalRecord:
    article_type = ArticleType(
        type="Article",
        description=(
            "Original research articles on gravitational physics and the theory of spacetime -- "
            "the fetched page is IOP's shared platform-wide guidance, not a CQG-specific article-type "
            "list (that lives behind the CAPTCHA-gated per-journal page, not fetched here)."
        ),
        total_word_limit=WordLimit(
            notes=(
                "Not checked: source page behind CAPTCHA, never fetched. The page itself confirms a "
                "per-journal maximum recommended length exists ('Some of our journals have guidelines for the "
                "maximum recommended length for each different type of article') and points to the 'About the "
                "journal' section of iopscience.iop.org/journal/0264-9381 for it, which is gated behind a "
                "Radware Bot Manager CAPTCHA and was never successfully fetched. Do not confuse with the "
                "unrelated file-size limits on this page (10MB/video, 50MB/supplementary file, 150MB combined "
                "incl. main article) -- those are upload limits, not article length."
            ),
        ),
        structure=(
            "Title, Authors, Keywords, Abstract (IOP platform-wide guidance: should not normally be more "
            "than 300 words, not CQG-specific -- may be superseded by a per-journal abstract limit not "
            "checked here), Introduction, Method, Results, Discussion, Conclusion, Acknowledgements, "
            "References"
        ),
        source_urls=[SOURCE_URL],
    )

    return JournalRecord(
        journal="Classical and Quantum Gravity",
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

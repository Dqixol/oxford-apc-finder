"""Builds Nature Sustainability's structured JSON from HTML already fetched by
direct_fetch.py -- no live fetching here. Same "frozen transcript" approach as
journal_scrapers/1756-1833_bmj/extract.py and journal_scrapers/1939-8980_annals-of-mathematics/extract.py.

Second pass (2026-09-22): the first pass only had 3 pages (submission-guidelines,
initial-formatting, aip-and-formatting) and left article_types/peer_review_model/
preprint_policy/ai_use_policy all in needs_review -- aip-and-formatting.md itself
proved per-type word limits exist ("ensure the legend does not exceed the word
limit of the article type") without stating them, so those fields were genuinely
unfetched, not absent. direct_fetch.py's manifest for this journal was extended
to 7 pages (see its own note) -- content.md (the actual per-type Format sections),
peer-review-policy.md, preprint-policy.md, ai-policy.md, all newly fetched and
converted. This pass fills article_types from the new content.md page; the
policy-page fields fetched in that same pass (peer review model, preprint
policy, AI-use policy) are out of scope for the current schema (see
common/schema.py) and are no longer carried in the JSON output.

Article types: content.md names 13 content types total. Only 8 have a real
**Format** section with actual word/reference/display-item rules attached --
Article, Analysis, Resource, Brief Communication, Correspondence, Review,
Perspective, Comment -- modelled as ArticleType below. The other 5 are excluded
per this project's established rule (BMJ's own scope note / prompts.py rule 8:
don't invent an ArticleType from a bare name with no real content behind it):
Matters Arising has no format on this page, just a pointer to a separate
submission process (same pattern as Nature's own real ground truth, which also
excludes it as an ArticleType); News & Views and Book Review are explicitly
non-primary, invited/contact-only content with no Format section (Nature's own
extract.py's remarks similarly excludes "staff-written content: News, Careers,
Obituaries... News & Views"); Feature and Policy Brief ARE invited-pitch-only
("They do not contain unsolicited material") even though Feature does have a
short Format section -- excluded on the same "not an author-submission path"
basis Nature's own ground truth used to exclude Technology Features, not
because the format is thin.

Run directly: `python journal_scrapers/2398-9629_nature-sustainability/extract.py`
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.schema import ArticleType, ISSN, JournalRecord, WordLimit  # noqa: E402

CONTENT_URL = "https://www.nature.com/natsustain/content"
ISSN_PRINT = "2398-9629"
JSON_DIR = Path(__file__).resolve().parents[2] / "data_scrapes" / "json"


def build() -> JournalRecord:
    article_types = [
        ArticleType(
            type="Article",
            description="A substantial novel research study, with a complex story often involving several techniques or approaches.",
            total_word_limit=WordLimit(
                min=3500, max=3500, excludes=["abstract", "Methods", "references", "figure legends"],
            ),
            structure=(
                "Title (≤10 words or 90 characters), Abstract (≤150 words, unreferenced, no heading), "
                "Introduction (no heading), Results, Discussion, Methods"
            ),
            figures_tables="Up to 6 display items (figures and/or tables).",
            source_urls=[CONTENT_URL],
        ),
        ArticleType(
            type="Analysis",
            description="A new analysis of existing data, or new data obtained in a comparative analysis, leading to novel and arresting conclusions of importance to a broad audience.",
            total_word_limit=WordLimit(
                min=3500, max=3500, excludes=["abstract", "Methods", "references", "figure legends"],
            ),
            structure=(
                "Title (≤10 words or 90 characters), Abstract (≤150 words, unreferenced, no heading), "
                "Introduction (no heading), Results, Discussion, Methods"
            ),
            figures_tables="Up to 6 display items (figures and/or tables).",
            source_urls=[CONTENT_URL],
        ),
        ArticleType(
            type="Resource",
            description="Presents a large data set of broad utility, interest and significance to the community.",
            total_word_limit=WordLimit(
                min=3500, max=3500, excludes=["abstract", "Methods", "references", "figure legends"],
            ),
            structure=(
                "Title (≤10 words or 90 characters), Abstract (≤150 words, unreferenced, no heading), "
                "Introduction (no heading), Results, Discussion, Methods"
            ),
            figures_tables="Up to 6 display items (figures and/or tables).",
            source_urls=[CONTENT_URL],
        ),
        ArticleType(
            type="Brief Communication",
            description="Reports a concise study of high quality and broad interest.",
            total_word_limit=WordLimit(
                min=1500, max=1500, excludes=["abstract", "Methods", "references", "figure legends"],
                notes="No subheadings within the main text.",
            ),
            structure="Title (≤10 words or 90 characters), Abstract (≤70 words, 3 sentences, unreferenced), Methods (≤500 words)",
            figures_tables="Up to 2 display items, flexible at editor discretion if page limit observed.",
            source_urls=[CONTENT_URL],
        ),
        ArticleType(
            type="Correspondence",
            description="Forum for comment on issues relevant to the journal's community -- not for presenting research data or analysis. Technical comments on peer-reviewed papers go through Matters Arising instead.",
            total_word_limit=WordLimit(min=300, max=800),
            figures_tables="1 display item.",
            source_urls=[CONTENT_URL],
        ),
        ArticleType(
            type="Review",
            description="An authoritative, balanced and scholarly survey of recent developments in a research field; not dominated by a single laboratory's work. Mostly editor-invited; unsolicited proposals considered via a 1-2 page synopsis submission (Synopsis-Review option). A study using a structured, replicable literature-extraction method is reclassified as original research and should follow the Article/Analysis format instead.",
            total_word_limit=WordLimit(min=5000, max=5000),
            structure="Preface (≤100 words, unreferenced)",
            figures_tables="Up to 6 display items. Illustrations strongly encouraged.",
            source_urls=[CONTENT_URL],
        ),
        ArticleType(
            type="Perspective",
            description="A forum for authors to discuss models and ideas from a personal viewpoint -- more forward-looking/speculative than Reviews, may take a narrower field of view, may advocate a controversial position. Mostly editor-invited; unsolicited proposals considered via a 1-2 page synopsis submission (Synopsis-Perspective option).",
            total_word_limit=WordLimit(min=5000, max=5000),
            structure="Preface (≤100 words, unreferenced)",
            figures_tables="Up to 6 display items.",
            source_urls=[CONTENT_URL],
        ),
        ArticleType(
            type="Comment",
            description="Opinionated pieces on a topical issue in sustainability research, policy or societal debate -- agenda-setting, authoritative, can be provocative but must road-map a proposed solution, not just describe a problem. Mostly editor-invited; unsolicited proposals considered via a 1-page synopsis submission (Synopsis-Comment option).",
            total_word_limit=WordLimit(min=1500, max=1500),
            figures_tables="Figures/diagrams encouraged, not required; does not normally contain primary research data.",
            source_urls=[CONTENT_URL],
        ),
    ]

    return JournalRecord(
        journal="Nature Sustainability",
        publisher="Springer Nature",
        issn=ISSN(electronic="2398-9629"),  # single ISSN stated across fetched pages; no separate print ISSN found -- confirmed absence, not checked against ISSN Portal
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
    print(f"Wrote {out_path} -- {len(record.article_types)} article type(s)")


if __name__ == "__main__":
    main()

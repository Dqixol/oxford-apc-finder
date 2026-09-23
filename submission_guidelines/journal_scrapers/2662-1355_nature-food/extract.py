"""Builds Nature Food's structured JSON from HTML already fetched by
direct_fetch.py -- no live fetching here. Same "frozen transcript" approach as
journal_scrapers/1756-1833_bmj/extract.py and journal_scrapers/1939-8980_annals-of-mathematics/extract.py.

Article types: content.md names 11 content types total. Only 8 have a real
**Format** section with actual word/reference/display-item rules attached --
Article, Analysis, Resource, Brief Communication, Correspondence, Review,
Perspective, Comment -- modelled as ArticleType below (same rule as Nature
Sustainability: don't invent an ArticleType from a bare name with no real
content behind it). The other 3 -- Matters Arising (pointer to a separate
process, no format on this page), News & Views and Book Reviews (explicitly
non-primary, invited/contact-only, "not peer reviewed") -- are omitted
rather than invented. Unlike Nature Sustainability, this journal's content.md
has no Feature or Policy Brief entries at all.

Every number below was read from this journal's own content.md, not copied
from Nature Sustainability's -- the two journals share the same content-type
names but use different word/reference/display-item limits throughout (e.g.
Article is 3,000 words here vs 3,500 there; Review is 6,000 words here vs
5,000 there; Perspective is a narrower ~3,000-word format here vs a broader
5,000-word one there) -- confirmed by reading, not assumed.

Run directly: `python journal_scrapers/2662-1355_nature-food/extract.py`
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.schema import ArticleType, ISSN, JournalRecord, WordLimit  # noqa: E402

CONTENT_URL = "https://www.nature.com/natfood/content"
ISSN_PRINT = "2662-1355"
JSON_DIR = Path(__file__).resolve().parents[2] / "data_scrapes" / "json"


def build() -> JournalRecord:
    article_types = [
        ArticleType(
            type="Article",
            description="A substantial novel research study, often involving several techniques or approaches.",
            total_word_limit=WordLimit(
                min=3000, max=3000, excludes=["abstract", "methods", "references", "figure legends"],
            ),
            structure="Abstract (≤150 words, unreferenced), Introduction (no heading), Results, Discussion, Methods",
            figures_tables="≤6 display items (figures and/or tables).",
            source_urls=[CONTENT_URL],
        ),
        ArticleType(
            type="Analysis",
            description="A new analysis of existing data, or new data obtained in a comparative analysis, leading to novel and arresting conclusions of importance to a broad audience.",
            total_word_limit=WordLimit(
                min=3000, max=3000, excludes=["abstract", "methods", "references", "figure legends"],
            ),
            structure="Abstract (100-150 words, unreferenced), Introduction (no heading), Results, Discussion, Methods",
            figures_tables="≤6 display items.",
            source_urls=[CONTENT_URL],
        ),
        ArticleType(
            type="Resource",
            description="Presents a large data set of broad utility, interest and significance to the community.",
            total_word_limit=WordLimit(
                min=3000, max=3000, excludes=["abstract", "methods", "references", "figure legends"],
            ),
            structure="Abstract (100-150 words, unreferenced), Introduction (no heading), Main text, Discussion/Conclusions, Methods",
            figures_tables="≤8 display items (higher than the other types' 6).",
            source_urls=[CONTENT_URL],
        ),
        ArticleType(
            type="Brief Communication",
            description="Reports a concise study of high quality and broad interest.",
            total_word_limit=WordLimit(
                min=1500, max=1500,
                notes="Unlike this journal's other types, this INCLUDES abstract, references and figure legends, not just main text.",
            ),
            structure="Title (≤10 words or 90 characters), Abstract (≤70 words, unreferenced), Methods (no headings within the main text otherwise)",
            figures_tables="≤2 display items, flexible at editor discretion if page limit observed.",
            source_urls=[CONTENT_URL],
        ),
        ArticleType(
            type="Correspondence",
            description="Forum for comment on issues relevant to the journal's community -- not for presenting research data or analysis. Technical comments on peer-reviewed papers go through Matters Arising instead.",
            total_word_limit=WordLimit(min=300, max=800),
            figures_tables="Max 1 display item.",
            source_urls=[CONTENT_URL],
        ),
        ArticleType(
            type="Review",
            description="An authoritative, balanced and scholarly survey of recent developments in a research field; not dominated by a single laboratory/group's work. A structured, replicable literature-extraction study (meta-analysis) is reclassified as original research and should follow the Article/Analysis format instead. Not stated whether Reviews are editor-invited or open to unsolicited proposals.",
            total_word_limit=WordLimit(min=6000, max=6000),
            structure="Abstract (100-150 words, unreferenced)",
            figures_tables="≤6 display items. Illustrations strongly encouraged.",
            source_urls=[CONTENT_URL],
        ),
        ArticleType(
            type="Perspective",
            description="Scholarly reviews/discussions of the primary research literature too technical for a Comment but not meeting Review criteria (narrower scope, or advocating a controversial/speculative position, or one-group-centric). A related sub-format, 'Historical Perspective', is a scholarly (not merely personal) account of a scientific development.",
            total_word_limit=WordLimit(min=3000, max=3000),
            structure="Abstract (≤100 words, unreferenced). Does NOT contain a Methods section (explicit exclusion, unlike this journal's other research-adjacent types).",
            figures_tables="≤5 display items.",
            source_urls=[CONTENT_URL],
        ),
        ArticleType(
            type="Comment",
            description="Flexible-format piece on scientific/commercial/ethical/legal/societal/political issues surrounding research -- topical, readable, provocative, a personal perspective on a matter of public or scientific importance. A related sub-format, 'Historical Comment', is a journalistic (not necessarily scholarly-balanced) treatment of a discovery's history, which may be personal opinion.",
            total_word_limit=WordLimit(max=2000, notes="Typically up to 2000 words -- not stated as a hard ceiling."),
            structure="Standfirst/short abstract (2-3 sentences or 70 words, unreferenced). No strict structure, but headings/subheadings used sparingly.",
            figures_tables="Typically ≤2 display items.",
            source_urls=[CONTENT_URL],
        ),
    ]

    return JournalRecord(
        journal="Nature Food",
        publisher="Springer Nature",
        issn=ISSN(electronic="2662-1355"),  # single ISSN stated across fetched pages; no separate print ISSN found
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

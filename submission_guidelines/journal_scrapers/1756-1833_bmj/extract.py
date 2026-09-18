"""Builds BMJ's structured JSON from HTML already fetched by direct_fetch.py --
no live fetching here. This is a test of "generic" extraction: read the saved
page directly and construct the schema objects from what's actually there,
rather than writing/debugging bespoke regex per fact (compare against
journal_scrapers/1476-4687_nature/scrape.py, which does the regex-per-fact
version). See docs/usage_log.csv for the cost comparison.

Scope: research-submission types only, same principle as Nature -- excludes
BMJ Careers (pure pitch, no format) and Obituaries (family submissions, no
formatting rules) and "Summary of NICE Guidelines" (explicitly "solely
commissioned by our editors", no author-submission path at all -- stronger
exclusion signal than Nature's Reviews, which explicitly allow unsolicited
synopsis submissions).

Peer review model / preprint policy / AI-use policy are NOT included here --
those pages were never fetched for BMJ (see direct_fetch.py's note), and
finding+fetching them is a separate task from this extraction-quality test,
not folded in here.

Run directly: `python journal_scrapers/1756-1833_bmj/extract.py`
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.schema import (  # noqa: E402
    ArticleType,
    CountRange,
    ISSN,
    JournalRecord,
    SectionWordLimit,
    WordLimit,
)

SOURCE_URL = "https://www.bmj.com/about-bmj/resources-authors/article-types"
DATA_DIR = Path(__file__).resolve().parents[2] / "data_scrapes" / "1756-1833_bmj"

REQUIRED_STATEMENTS_ALL = [
    "Title page and authorship (ICMJE criteria)",
    "Competing interests declaration",
    "Ethics approval statement",
    "Transparency declaration",
]

RESEARCH_REQUIRED_STATEMENTS = REQUIRED_STATEMENTS_ALL + ["Data sharing statement"]


def _wl(value: int, ceiling: bool = False, notes: str | None = None) -> WordLimit:
    """A bare number in source prose ("Analysis papers should be 2000 words") is a target,
    so min==max by the schema's own convention. Only set ceiling=True for explicit "up to"/
    "maximum"/"no more than" phrasing, where there's no real floor."""
    return WordLimit(min=None if ceiling else value, max=value, unit="words", notes=notes)


def _cr(max_n: int | None, notes: str | None = None) -> CountRange | None:
    return CountRange(max=max_n, notes=notes) if max_n is not None else None


def build() -> JournalRecord:
    article_types = [
        ArticleType(
            type="Research",
            source_url=SOURCE_URL,
            description="Original research articles, following IMRaD style (introduction, methods, results, discussion).",
            total_word_limit=WordLimit(
                notes="No fixed word count limit -- authors state their own word count at submission "
                "(main text, excluding abstract/references/tables/boxes/figures). This is a confirmed "
                "'no published number', not a gap."
            ),
            required_sections=["Structured abstract", "Introduction (max 3 paragraphs)", "Methods", "Results", "Discussion"],
            section_word_limits=[
                SectionWordLimit("Structured abstract", 300, "250-300 words typical; up to 400 for CONSORT/PRISMA-style; MEDLINE can handle up to 600"),
            ],
            reference_limit=None,
            required_statements=RESEARCH_REQUIRED_STATEMENTS + [
                "Mandatory patient and public involvement statement",
                "Statistical methods statement",
            ],
        ),
        ArticleType(
            type="Research Methods and Reporting (RMR)",
            source_url=SOURCE_URL,
            description="Articles on research methodology and reporting standards.",
            total_word_limit=WordLimit(notes="No fixed word count limit -- same 'make every word count' guidance as Research."),
            required_sections=["Title and standfirst (100-150 words)", "Introduction", "Text (subheaded)"],
            reference_limit=None,
            required_statements=REQUIRED_STATEMENTS_ALL,
        ),
        ArticleType(
            type="Analysis",
            source_url=SOURCE_URL,
            description="International-readership pieces for policy makers, health professionals, and doctors of all disciplines; avoids jargon.",
            total_word_limit=_wl(2000),
            reference_limit=_cr(20),
            required_statements=REQUIRED_STATEMENTS_ALL,
            notes="Up to 3 non-text items (box, figure, or table).",
        ),
        ArticleType(
            type="Editorials",
            source_url=SOURCE_URL,
            description="Scholarly, balanced, evidence-based responses to something topical; usually 1-3 authors, max 4 (5 if the extra author is a patient).",
            total_word_limit=_wl(800, ceiling=True, notes="'Up to 800 words' -- explicit ceiling."),
            reference_limit=CountRange(min=12, max=20),
            author_limit=CountRange(max=4, notes="5 allowed only if the extra author is a patient."),
            notes="Invited only. Authors must be free of relevant financial ties to industry (since 2014 policy).",
        ),
        ArticleType(
            type="Personal Views",
            source_url=SOURCE_URL,
            description="A strong, novel, well-argued personal viewpoint. Published online first on BMJ Opinion; may not appear in print.",
            total_word_limit=_wl(600),
            reference_limit=_cr(10),
        ),
        ArticleType(
            type="BMJ Opinion",
            source_url=SOURCE_URL,
            description="Comment and opinion from BMJ's international community of readers, authors, and editors, on medicine/healthcare/publishing.",
            total_word_limit=WordLimit(min=650, max=800),
            notes="Submitted via email (blogs@bmj.com), not the main submission system.",
        ),
        ArticleType(
            type="Rapid responses",
            source_url=SOURCE_URL,
            description="Electronic letters to the editor -- the only route for a letter to appear in print/bmj.com; all print letters originate as rapid responses.",
            total_word_limit=WordLimit(notes="No word limit stated (n/a in the source table)."),
        ),
        # -- Education sub-formats: each is a distinct, separately named, separately
        # limited submission category (same pattern as Frontiers' 6 article types),
        # not sub-sections of one "Education" bucket.
        ArticleType(
            type="Clinical Updates",
            source_url=SOURCE_URL,
            description="Up-to-date overview of a clinical condition, evidence-based, aimed at non-specialists.",
            total_word_limit=_wl(1800),
            reference_limit=_cr(40),
        ),
        ArticleType(
            type="Practice Pointer",
            source_url=SOURCE_URL,
            total_word_limit=_wl(1600),
            reference_limit=_cr(20),
        ),
        ArticleType(
            type="Easily Missed",
            source_url=SOURCE_URL,
            total_word_limit=_wl(1600),
            reference_limit=_cr(20),
        ),
        ArticleType(
            type="10 Minute Consultation",
            source_url=SOURCE_URL,
            total_word_limit=_wl(1000),
            reference_limit=_cr(10),
        ),
        ArticleType(
            type="Sustainable Practice",
            source_url=SOURCE_URL,
            total_word_limit=WordLimit(min=400, max=700),
        ),
        ArticleType(
            type="What Your Patient Is Thinking (WYPIT)",
            source_url=SOURCE_URL,
            total_word_limit=_wl(650, notes="Includes the closing 'What You Need To Know' summary box."),
        ),
        ArticleType(
            type="Minerva Pictures",
            source_url=SOURCE_URL,
            total_word_limit=_wl(150),
        ),
        ArticleType(
            type="Endgames",
            source_url=SOURCE_URL,
            total_word_limit=None,
            notes="150-word vignette (case history) section plus a 200-word answer section -- two separately "
            "limited parts of one piece, not a single total word count. See template referenced on the source page.",
        ),
        ArticleType(
            type="State of the Art Reviews",
            source_url=SOURCE_URL,
            total_word_limit=None,
            notes="Word limit cell was blank in the source table -- genuinely not checked, not a confirmed absence.",
        ),
    ]
    needs_review = ["article_types[State of the Art Reviews].total_word_limit", "peer_review_model", "preprint_policy", "ai_use_policy", "latex_accepted", "template_provided", "languages_accepted"]

    return JournalRecord(
        journal="The BMJ",
        publisher="BMJ Publishing Group",
        issn=ISSN(print="0959-8138", electronic="1756-1833"),
        url="https://www.bmj.com/about-bmj/resources-authors",
        date_scraped=date.today().isoformat(),
        article_types=article_types,
        remarks=(
            "Scope limited to research-submission types -- excludes BMJ Careers (pure pitch, no format), "
            "Obituaries (family submissions), and 'Summary of NICE Guidelines' (solely commissioned, no "
            "author-submission path). Peer review model, preprint policy, and AI-use policy pages have not "
            "been fetched yet (separate task from this extraction pass)."
        ),
        needs_review=needs_review,
        source="scraped",
    )


def main() -> None:
    record = build()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(record.to_dict(), indent=2, ensure_ascii=False)
    today = date.today().isoformat()
    (DATA_DIR / f"{today}.json").write_text(payload, encoding="utf-8")
    (DATA_DIR / "latest.json").write_text(payload, encoding="utf-8")
    print(f"Wrote {DATA_DIR / f'{today}.json'} -- {len(record.article_types)} article types")


if __name__ == "__main__":
    main()

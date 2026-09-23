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

Peer review model / preprint policy / AI-use policy are out of scope for the
current schema (see common/schema.py) and weren't fetched for BMJ anyway.

Run directly: `python journal_scrapers/1756-1833_bmj/extract.py`
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.schema import ArticleType, ISSN, JournalRecord, WordLimit  # noqa: E402

SOURCE_URL = "https://www.bmj.com/about-bmj/resources-authors/article-types"
ISSN_PRINT = "0959-8138"
JSON_DIR = Path(__file__).resolve().parents[2] / "data_scrapes" / "json"


def build() -> JournalRecord:
    article_types = [
        ArticleType(
            type="Research",
            description="Original research articles, following IMRaD style (introduction, methods, results, discussion).",
            total_word_limit=WordLimit(
                notes=(
                    "No fixed word count limit -- authors state their own word count at submission (main text, "
                    "excluding abstract/references/tables/boxes/figures). Confirmed 'no published number', not a gap."
                ),
            ),
            structure=(
                "Structured abstract (250-300 words typical; up to 400 for CONSORT/PRISMA-style; MEDLINE can "
                "handle up to 600), Introduction (max 3 paragraphs), Methods, Results, Discussion"
            ),
            source_urls=[SOURCE_URL],
        ),
        ArticleType(
            type="Research Methods and Reporting (RMR)",
            description="Articles on research methodology and reporting standards.",
            total_word_limit=WordLimit(
                notes="No fixed word count limit -- same 'make every word count' guidance as Research.",
            ),
            structure="Title and standfirst (100-150 words), Introduction, Text (subheaded)",
            source_urls=[SOURCE_URL],
        ),
        ArticleType(
            type="Analysis",
            description="International-readership pieces for policy makers, health professionals, and doctors of all disciplines; avoids jargon.",
            total_word_limit=WordLimit(min=2000, max=2000),
            structure=(
                "Title and standfirst (short title plus an italicised single-sentence standfirst), "
                "Introduction, Text (subheaded), Boxes/tables/figures, Key messages box (3-4 points "
                "summing up the main conclusions), Contributors and sources (100-150 words, excluded "
                "from word count)"
            ),
            figures_tables="Up to 3 non-text items (box, figure, or table).",
            source_urls=[SOURCE_URL],
        ),
        ArticleType(
            type="Editorials",
            description="Scholarly, balanced, evidence-based responses to something topical; usually 1-3 authors, max 4 (5 if the extra author is a patient).",
            total_word_limit=WordLimit(max=800, notes="'Up to 800 words' -- explicit ceiling."),
            source_urls=[SOURCE_URL],
        ),
        ArticleType(
            type="Personal Views",
            description="A strong, novel, well-argued personal viewpoint. Published online first on BMJ Opinion; may not appear in print.",
            total_word_limit=WordLimit(min=600, max=600),
            source_urls=[SOURCE_URL],
        ),
        ArticleType(
            type="BMJ Opinion",
            description="Comment and opinion from BMJ's international community of readers, authors, and editors, on medicine/healthcare/publishing.",
            total_word_limit=WordLimit(min=650, max=800),
            source_urls=[SOURCE_URL],
        ),
        ArticleType(
            type="Rapid responses",
            description="Electronic letters to the editor -- the only route for a letter to appear in print/bmj.com; all print letters originate as rapid responses.",
            total_word_limit=WordLimit(notes="No word limit stated (n/a in the source table)."),
            source_urls=[SOURCE_URL],
        ),
        # -- Education sub-formats: each is a distinct, separately named, separately
        # limited submission category (same pattern as Frontiers' 6 article types),
        # not sub-sections of one "Education" bucket.
        ArticleType(
            type="Clinical Updates",
            description=(
                "Up-to-date overview of a clinical condition, evidence-based, aimed at non-specialists "
                "and having international appeal. Should include a broad update of recent developments "
                "(from the past 1-2 years) and their likely clinical applications in primary/community "
                "and secondary/hospital care."
            ),
            total_word_limit=WordLimit(min=1800, max=1800),
            source_urls=[SOURCE_URL],
        ),
        ArticleType(
            type="Practice Pointer",
            description=(
                "Practical, often problem-based articles. Should help clinicians who are not specialists "
                "in a particular field know 'how to' approach a problem, diagnosis, or management better."
            ),
            total_word_limit=WordLimit(min=1600, max=1600),
            source_urls=[SOURCE_URL],
        ),
        ArticleType(
            type="Easily Missed",
            description=(
                "Highlights conditions that are often missed at first presentation in general practice or "
                "the emergency department -- evidence that the condition may be misdiagnosed or diagnosis "
                "delayed, and that timely recognition benefits the patient. The condition should be "
                "reasonably common, or serious with delayed diagnosis likely to worsen prognosis, and have "
                "easily defined diagnostic features and/or tests with known predictive characteristics."
            ),
            total_word_limit=WordLimit(min=1600, max=1600),
            source_urls=[SOURCE_URL],
        ),
        ArticleType(
            type="10 Minute Consultation",
            description=(
                "Describes how clinicians might use a single consultation to tackle a common scenario in "
                "primary care. Must address a tightly framed issue -- e.g. exploring a new symptom, "
                "explaining a diagnosis or an aspect of its management, or acting in an urgent situation."
            ),
            total_word_limit=WordLimit(min=1000, max=1000),
            source_urls=[SOURCE_URL],
        ),
        ArticleType(
            type="Sustainable Practice",
            description=(
                "Outlines tangible actions clinicians can undertake within their clinical practice to "
                "promote sustainable healthcare. System-level changes can be incorporated, but the "
                "suggested actions should primarily be focused at the individual level. Short articles "
                "with a structured format; usually one to two authors."
            ),
            total_word_limit=WordLimit(min=400, max=700),
            source_urls=[SOURCE_URL],
        ),
        ArticleType(
            type="What Your Patient Is Thinking (WYPIT)",
            description=(
                "A series led, edited, and written by patients and their carers, containing messages that "
                "are thought-provoking and challenging for readers, along the lines of 'What I wish you "
                "[The BMJ's audience] knew, and why.'"
            ),
            total_word_limit=WordLimit(
                min=650, max=650, notes="Includes the closing 'What You Need To Know' summary box.",
            ),
            source_urls=[SOURCE_URL],
        ),
        ArticleType(
            type="Minerva Pictures",
            description=(
                "Pictures that offer an educational message and obviously depict an abnormality -- "
                "generally unusual presentations of common conditions. Consist of one clear image and a "
                "vignette outlining the steps taken to reach the diagnosis."
            ),
            total_word_limit=WordLimit(min=150, max=150),
            structure="One clear image, Vignette (150 words) outlining the steps taken to reach the diagnosis",
            figures_tables="One clear image.",
            source_urls=[SOURCE_URL],
        ),
        ArticleType(
            type="Endgames",
            description=(
                "Quizzes based on genuine clinical scenarios; difficulty should reflect knowledge needed "
                "for postgraduate exams. Also offer doctors who have passed postgraduate exams a chance to "
                "test their knowledge for continuing medical education."
            ),
            total_word_limit=WordLimit(
                notes=(
                    "150-word vignette (case history) section plus a 200-word answer section -- two separately "
                    "limited parts of one piece, not a single total word count."
                ),
            ),
            structure="Single clinical image, Vignette (case history, 150 words), Answer (200 words). See template referenced on the source page.",
            figures_tables="A single clinical image.",
            source_urls=[SOURCE_URL],
        ),
        ArticleType(
            type="State of the Art Reviews",
            total_word_limit=WordLimit(
                notes="Word limit cell was blank in the source table -- genuinely not checked, not a confirmed absence.",
            ),
            source_urls=[SOURCE_URL],
        ),
    ]

    return JournalRecord(
        journal="The BMJ",
        publisher="BMJ Publishing Group",
        issn=ISSN(print="0959-8138", electronic="1756-1833"),
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

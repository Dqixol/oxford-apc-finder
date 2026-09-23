"""Builds Perspectives in Ecology and Conservation's structured JSON from
sources already fetched by direct_fetch.py -- no live fetching here. Same
"generic" hand-extraction test as journal_scrapers/1756-1833_bmj/extract.py
and journal_scrapers/1939-8980_annals-of-mathematics/extract.py: read the
saved source directly and construct the schema objects from what's actually
there.

Two sources, very different value:
- data_scrapes/raw_html/2530-0644/guia-autores.md -- the live HTML page is
  client-side rendered and only surfaces the journal's overview paragraph
  (scope, publisher, no-APC statement); confirmed by reading it directly.
- data_scrapes/raw_html/2530-0644/guide-for-authors.pdf -- the real 20-page
  "Guide for authors" (Elsevier/ScienceDirect), which has the actual article
  types, peer review, AI-use, preprint, and reference-style rules.

Known, confirmed defect in the PDF (documented in direct_fetch.py's own note
on this journal, and independently re-confirmed here with pdfplumber before
writing this file): every numeric digit in the extracted text is missing --
"up to      words", "with    -words abstract", "up to   to   boxes" -- real
glyphs exist in the PDF with correct width/position but a null ToUnicode
mapping (Elsevier's own PDF export defect, not a tooling limitation; also
confirmed with pypdf). OCR would recover the real numbers; not attempted
here. Every total_word_limit below therefore explains this rather than
guessing at a number -- the qualitative structure (which article types
exist, what each is for, mandatory-vs-optional components) is real and used
as-is; no digit from this PDF is trusted, even where an extracted figure
looks plausible.

The source text (page 2 of the PDF) says article types "follow six main
formats" but names seven distinctly-ruled categories in total: five in that
paragraph (Essays & Perspectives/Trends, Research Letters/Research Paper,
Policy Forums/Reflective Practice, Correspondences, Book reviews) plus two
more introduced separately just after (Society Position Statement/White
papers, Opinion Papers -- both explicitly "invited only"). All seven are
included as separate ArticleType entries since each has its own distinct
description; the "six" vs. seven-named discrepancy is noted here rather than
silently resolved by dropping one.

Run directly: `python journal_scrapers/2530-0644_perspectives-ecology-conservation/extract.py`
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.schema import ArticleType, ISSN, JournalRecord, WordLimit  # noqa: E402

SOURCE_URL_PDF = "https://www.perspectecolconserv.com/en-guia-autores-pdf"
ISSN_ELECTRONIC = "2530-0644"
JSON_DIR = Path(__file__).resolve().parents[2] / "data_scrapes" / "json"

_NUMBERS_LOST_NOTE = (
    "Source PDF states an explicit limit here, but every digit is unrecoverable by text "
    "extraction (Elsevier PDF export defect -- null ToUnicode mapping on real glyphs, "
    "confirmed with pdfplumber and pypdf). OCR needed to recover the real number; not "
    "attempted. Not a confirmed absence of a limit -- a confirmed limit whose value is lost."
)


def _twc(extra: str) -> str:
    return f"{_NUMBERS_LOST_NOTE} {extra}"


def build() -> JournalRecord:
    article_types = [
        ArticleType(
            type="Essays & Perspectives / Trends",
            description=(
                "Longer essays and reviews updating recent topics of interest in conservation science; "
                "propose new conceptual frameworks or personal viewpoints, supported by evidence but not "
                "yet fully explored. Should stimulate new cutting-edge research or applied perspectives."
            ),
            total_word_limit=WordLimit(
                notes=_twc("Also has an abstract word limit, a box count/size limit, and a figure-or-table count limit, all lost the same way."),
            ),
            structure="Abstract, Graphical abstract, Highlights (bullet points, separate editable file)",
            source_urls=[SOURCE_URL_PDF],
        ),
        ArticleType(
            type="Research Letters / Research Paper",
            description="Original scientific research presented in a more concise manuscript than Essays & Perspectives.",
            total_word_limit=WordLimit(
                notes=_twc("Also has an abstract word limit, one box (with its own word limit), and a figure-or-table count limit, all lost the same way."),
            ),
            structure="Abstract, Graphical abstract, Highlights (bullet points, separate editable file)",
            source_urls=[SOURCE_URL_PDF],
        ),
        ArticleType(
            type="Policy Forums / Reflective Practice",
            description=(
                "Brief essays for a general audience on issues related to conservation and society; must "
                "clearly articulate the significance of the ideas for conservation policy and practice."
            ),
            total_word_limit=WordLimit(
                notes=_twc("Given as a min-max word range in the source, plus a short-abstract limit and a figure-count range, all lost the same way."),
            ),
            structure="Short abstract, Graphical abstract, Highlights (bullet points, separate editable file)",
            source_urls=[SOURCE_URL_PDF],
        ),
        ArticleType(
            type="Correspondences",
            description=(
                "Letters commenting on papers published in one of the three previous issues of the journal. "
                "Should be short, polite and constructive, with references kept to a minimum."
            ),
            total_word_limit=WordLimit(
                notes=_twc("This is a ceiling ('less than N words'), not a target -- the N itself, plus one allowed figure, both lost the same way."),
            ),
            source_urls=[SOURCE_URL_PDF],
        ),
        ArticleType(
            type="Book reviews",
            description=(
                "Consider relevant and internationally available publications not more than two years old, "
                "covering conservation-science topics of interest to a broad audience. Submissions should be "
                "discussed with the editor-in-chief in advance."
            ),
            total_word_limit=WordLimit(
                notes=_twc("Explicit ceiling ('up to N words') in the source, digits lost the same way -- even the order of magnitude (thousands digit) is missing, not just a units digit."),
            ),
            source_urls=[SOURCE_URL_PDF],
        ),
        ArticleType(
            type="Society Position Statement / White papers",
            description=(
                "State-of-the-art pieces on topical and conflicting environmental issues, including a "
                "political positioning of a scientific association. Usually invited, though topic "
                "suggestions are welcomed. May be published as a bilingual supplementary issue when necessary."
            ),
            total_word_limit=WordLimit(
                notes=_twc("Given as an example length ('e.g. N words') plus abstract/figure-table-box/reference counts, all lost the same way."),
            ),
            structure="Abstract, Graphical abstract, Highlights (bullet points, separate editable file)",
            source_urls=[SOURCE_URL_PDF],
        ),
        ArticleType(
            type="Opinion Papers",
            description=(
                "Combines a brief review of a research topic's literature (setting the scene) with the "
                "author's own opinion, based on scientific evidence -- intended to stimulate new research "
                "ideas, conceptual models, or innovative challenges. Accessible to a wide readership. Invited only."
            ),
            total_word_limit=WordLimit(
                notes=_twc("Given as an approximate length ('~N words') plus abstract/figure-table-box/reference counts and a box word limit, all lost the same way."),
            ),
            source_urls=[SOURCE_URL_PDF],
        ),
    ]

    return JournalRecord(
        journal="Perspectives in Ecology and Conservation",
        publisher="Elsevier (ScienceDirect), on behalf of the Associacao Brasileira de Ciencia Ecologica e Conservacao (ABECO)",
        issn=ISSN(print=None, electronic=ISSN_ELECTRONIC),
        LLM=True,
        validated=False,
        date_scraped=date.today().isoformat(),
        article_types=article_types,
    )


def main() -> None:
    record = build()
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(record.to_dict(), indent=2, ensure_ascii=False)
    out_path = JSON_DIR / f"{ISSN_ELECTRONIC}.json"
    out_path.write_text(payload, encoding="utf-8")
    print(f"Wrote {out_path} -- {len(record.article_types)} article types")


if __name__ == "__main__":
    main()

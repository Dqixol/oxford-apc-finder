"""Builds Frontiers in Sustainable Food Systems' structured JSON from HTML
already fetched by direct_fetch.py -- no live fetching here. Third of three
journals used to test generic (read-then-construct) extraction against
journal_scrapers/1476-4687_nature/scrape.py's bespoke-regex approach; see
docs/usage_log.csv for the cost comparison.

Scope: excludes Correction (a post-publication amendment mechanism, not a
submission category with its own format), Editorial ("submitted exclusively
by the host editor(s)" -- explicitly staff/host-only, same exclusion logic
as Nature's News/Careers), and FAIR² Data (a data-deposit platform/service,
not an article type with its own manuscript format).

The word/figure limits below cluster into two real tiers stated on the page
(fee category isn't captured here -- that's APC-adjacent and out of scope
per this project's schema). All limits are stated on the source page as a
single ceiling number, not a range.

Run directly: `python journal_scrapers/2571-581X_frontiers-sustainable-food-systems/extract.py`
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.schema import ArticleType, ISSN, JournalRecord, WordLimit  # noqa: E402

ARTICLE_TYPES_URL = "https://www.frontiersin.org/journals/sustainable-food-systems/for-authors/article-types"
ISSN_ELECTRONIC = "2571-581X"  # no print edition -- Frontiers journals are electronic-only
JSON_DIR = Path(__file__).resolve().parents[2] / "data_scrapes" / "json"


def _wl(words: int) -> WordLimit:
    return WordLimit(max=words, notes=f"'Up to {words} words' -- explicit ceiling.")


def _figs(n: int) -> str:
    return f"Up to {n} figures and tables combined."


def build() -> JournalRecord:
    article_types = [
        ArticleType(
            type="Original Research",
            description="Reports on primary, unpublished studies; also covers confirming/disconfirming studies and non-reproducibility reports.",
            total_word_limit=_wl(12000),
            structure="Abstract, Introduction, Materials and Methods, Results, Discussion",
            source_urls=[ARTICLE_TYPES_URL],
        ),
        ArticleType(
            type="Systematic Review",
            description="Synthesis of previous research using clearly defined methods; includes meta-syntheses, meta-analyses, mapping/scoping reviews.",
            total_word_limit=_wl(12000),
            source_urls=[ARTICLE_TYPES_URL],
        ),
        ArticleType(
            type="Methods",
            description="Presents a new or established method, protocol, or technique of significant interest in the field.",
            total_word_limit=_wl(12000),
            structure="Abstract, Introduction (outlining the protocol)",
            source_urls=[ARTICLE_TYPES_URL],
        ),
        ArticleType(
            type="Review",
            description="Comprehensive, balanced overview of a topic with significant recent development -- a full state-of-the-art treatment, not a mere literature summary.",
            total_word_limit=_wl(12000),
            source_urls=[ARTICLE_TYPES_URL],
        ),
        ArticleType(
            type="Mini Review",
            description="Succinct, focused summary of a current area of investigation and its recent developments.",
            total_word_limit=_wl(3000),
            figures_tables=_figs(2),
            source_urls=[ARTICLE_TYPES_URL],
        ),
        ArticleType(
            type="Policy and Practice Reviews",
            description="Comprehensive, balanced overview of policy/regulation/guideline topics from academia, societies, regulators, or industry. More space than Policy Briefs to elaborate.",
            total_word_limit=_wl(12000),
            source_urls=[ARTICLE_TYPES_URL],
        ),
        ArticleType(
            type="Hypothesis and Theory",
            description="Presents a novel, testable argument, interpretation, or model intended to introduce a new hypothesis or theory.",
            total_word_limit=_wl(12000),
            source_urls=[ARTICLE_TYPES_URL],
        ),
        ArticleType(
            type="Perspective",
            description="A viewpoint on a specific area of investigation, discussing current advances and future directions; may include original data plus personal insight.",
            total_word_limit=_wl(3000),
            figures_tables=_figs(2),
            source_urls=[ARTICLE_TYPES_URL],
        ),
        ArticleType(
            type="Community Case Study",
            description="Documents local experience delivering a service to meet an identified need -- reflection on a program/practice, in contrast to investigator-driven research.",
            total_word_limit=_wl(5000),
            figures_tables=_figs(5),
            source_urls=[ARTICLE_TYPES_URL],
        ),
        ArticleType(
            type="Conceptual Analysis",
            description="Explores the concepts and issues that define a field, examining constituent elements and their connections. Must not include unpublished material.",
            total_word_limit=_wl(8000),
            figures_tables=_figs(10),
            source_urls=[ARTICLE_TYPES_URL],
        ),
        ArticleType(
            type="Data Report",
            description="Describes a research dataset; the dataset must be deposited in a public repository and fixed/publicly available on publication.",
            total_word_limit=_wl(3000),
            figures_tables=_figs(2),
            source_urls=[ARTICLE_TYPES_URL],
        ),
        ArticleType(
            type="Policy Brief",
            description="Short, practical, evidence-based evaluation of a policy issue, with policy options and actionable recommendations -- a decision-making tool.",
            total_word_limit=_wl(3000),
            figures_tables=_figs(5),
            source_urls=[ARTICLE_TYPES_URL],
        ),
        ArticleType(
            type="Brief Research Report",
            description="Original research and/or preliminary findings presented more succinctly and with fewer details than Original Research; negative/non-reproducibility results encouraged.",
            total_word_limit=_wl(4000),
            figures_tables=_figs(4),
            source_urls=[ARTICLE_TYPES_URL],
        ),
        ArticleType(
            type="General Commentary",
            description="Critical comment on a previous Frontiers publication. Commentary on non-Frontiers articles should be submitted as an Opinion instead.",
            total_word_limit=_wl(1000),
            figures_tables=_figs(1),
            source_urls=[ARTICLE_TYPES_URL],
        ),
        ArticleType(
            type="Opinion",
            description=(
                "Viewpoint on the interpretation of recent findings, method value, or hypothesis strengths/"
                "weaknesses. Must not contain unpublished/original data; must be evidence-supported, fully "
                "referenced, and avoid emotional language."
            ),
            total_word_limit=_wl(2000),
            figures_tables=_figs(1),
            source_urls=[ARTICLE_TYPES_URL],
        ),
        ArticleType(
            type="Technology and Code",
            description="Presents new technology, code, software, or a novel application of known technology/software, including existing algorithms under novel settings.",
            total_word_limit=_wl(12000),
            source_urls=[ARTICLE_TYPES_URL],
        ),
    ]

    return JournalRecord(
        journal="Frontiers in Sustainable Food Systems",
        publisher="Frontiers",
        issn=ISSN(electronic="2571-581X"),
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

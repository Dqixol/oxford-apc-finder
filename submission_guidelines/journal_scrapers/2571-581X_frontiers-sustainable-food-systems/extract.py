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
per this project's schema).

Run directly: `python journal_scrapers/2571-581X_frontiers-sustainable-food-systems/extract.py`
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.schema import (  # noqa: E402
    ArticleType,
    FigureLimit,
    ISSN,
    JournalRecord,
    WordLimit,
)

ARTICLE_TYPES_URL = "https://www.frontiersin.org/journals/sustainable-food-systems/for-authors/article-types"
GUIDELINES_URL = "https://www.frontiersin.org/guidelines/author-guidelines"
DATA_DIR = Path(__file__).resolve().parents[2] / "data_scrapes" / "2571-581X_frontiers-sustainable-food-systems"


def _wl(words: int) -> WordLimit:
    return WordLimit(min=words, max=words, unit="words", notes="Maximum word count stated as a single ceiling on the source page.")


def _figs(n: int) -> list[FigureLimit]:
    return [FigureLimit(max=n, counts="figures and tables combined")]


def build() -> JournalRecord:
    article_types = [
        ArticleType(
            type="Original Research",
            source_url=ARTICLE_TYPES_URL,
            description="Reports on primary, unpublished studies; also covers confirming/disconfirming studies and non-reproducibility reports.",
            total_word_limit=_wl(12000),
            required_sections=["Abstract", "Introduction", "Materials and Methods", "Results", "Discussion"],
        ),
        ArticleType(
            type="Systematic Review",
            source_url=ARTICLE_TYPES_URL,
            description="Synthesis of previous research using clearly defined methods; includes meta-syntheses, meta-analyses, mapping/scoping reviews.",
            total_word_limit=_wl(12000),
        ),
        ArticleType(
            type="Methods",
            source_url=ARTICLE_TYPES_URL,
            description="Presents a new or established method, protocol, or technique of significant interest in the field.",
            total_word_limit=_wl(12000),
            required_sections=["Abstract", "Introduction (outlining the protocol)"],
        ),
        ArticleType(
            type="Review",
            source_url=ARTICLE_TYPES_URL,
            description="Comprehensive, balanced overview of a topic with significant recent development -- a full state-of-the-art treatment, not a mere literature summary.",
            total_word_limit=_wl(12000),
        ),
        ArticleType(
            type="Mini Review",
            source_url=ARTICLE_TYPES_URL,
            description="Succinct, focused summary of a current area of investigation and its recent developments.",
            total_word_limit=_wl(3000),
            figure_limits=_figs(2),
        ),
        ArticleType(
            type="Policy and Practice Reviews",
            source_url=ARTICLE_TYPES_URL,
            description="Comprehensive, balanced overview of policy/regulation/guideline topics from academia, societies, regulators, or industry. More space than Policy Briefs to elaborate.",
            total_word_limit=_wl(12000),
        ),
        ArticleType(
            type="Hypothesis and Theory",
            source_url=ARTICLE_TYPES_URL,
            description="Presents a novel, testable argument, interpretation, or model intended to introduce a new hypothesis or theory.",
            total_word_limit=_wl(12000),
        ),
        ArticleType(
            type="Perspective",
            source_url=ARTICLE_TYPES_URL,
            description="A viewpoint on a specific area of investigation, discussing current advances and future directions; may include original data plus personal insight.",
            total_word_limit=_wl(3000),
            figure_limits=_figs(2),
        ),
        ArticleType(
            type="Community Case Study",
            source_url=ARTICLE_TYPES_URL,
            description="Documents local experience delivering a service to meet an identified need -- reflection on a program/practice, in contrast to investigator-driven research.",
            total_word_limit=_wl(5000),
            figure_limits=_figs(5),
        ),
        ArticleType(
            type="Conceptual Analysis",
            source_url=ARTICLE_TYPES_URL,
            description="Explores the concepts and issues that define a field, examining constituent elements and their connections. Must not include unpublished material.",
            total_word_limit=_wl(8000),
            figure_limits=_figs(10),
        ),
        ArticleType(
            type="Data Report",
            source_url=ARTICLE_TYPES_URL,
            description="Describes a research dataset; the dataset must be deposited in a public repository and fixed/publicly available on publication.",
            total_word_limit=_wl(3000),
            figure_limits=_figs(2),
        ),
        ArticleType(
            type="Policy Brief",
            source_url=ARTICLE_TYPES_URL,
            description="Short, practical, evidence-based evaluation of a policy issue, with policy options and actionable recommendations -- a decision-making tool.",
            total_word_limit=_wl(3000),
            figure_limits=_figs(5),
        ),
        ArticleType(
            type="Brief Research Report",
            source_url=ARTICLE_TYPES_URL,
            description="Original research and/or preliminary findings presented more succinctly and with fewer details than Original Research; negative/non-reproducibility results encouraged.",
            total_word_limit=_wl(4000),
            figure_limits=_figs(4),
        ),
        ArticleType(
            type="General Commentary",
            source_url=ARTICLE_TYPES_URL,
            description="Critical comment on a previous Frontiers publication. Commentary on non-Frontiers articles should be submitted as an Opinion instead.",
            total_word_limit=_wl(1000),
            figure_limits=_figs(1),
        ),
        ArticleType(
            type="Opinion",
            source_url=ARTICLE_TYPES_URL,
            description=(
                "Viewpoint on the interpretation of recent findings, method value, or hypothesis strengths/"
                "weaknesses. Must not contain unpublished/original data; must be evidence-supported, fully "
                "referenced, and avoid emotional language."
            ),
            total_word_limit=_wl(2000),
            figure_limits=_figs(1),
        ),
        ArticleType(
            type="Technology and Code",
            source_url=ARTICLE_TYPES_URL,
            description="Presents new technology, code, software, or a novel application of known technology/software, including existing algorithms under novel settings.",
            total_word_limit=_wl(12000),
        ),
    ]

    return JournalRecord(
        journal="Frontiers in Sustainable Food Systems",
        publisher="Frontiers",
        issn=ISSN(electronic="2571-581X"),
        url=ARTICLE_TYPES_URL,
        date_scraped=date.today().isoformat(),
        article_types=article_types,
        remarks=(
            "Excludes Correction (procedural amendment mechanism, not a submission category), Editorial "
            "('submitted exclusively by the host editor(s)' -- staff/host-only), and FAIR² Data (a "
            "data-deposit platform/service, not an article type). General reference/figure-format/section "
            "rules live on the platform-wide guidelines page rather than being repeated per type -- "
            f"see {GUIDELINES_URL}."
        ),
        needs_review=[
            "peer_review_model", "preprint_policy", "ai_use_policy", "latex_accepted",
            "template_provided", "robots_txt_allowed", "orcid_required", "languages_accepted",
        ],
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

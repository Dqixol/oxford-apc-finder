"""Scraper for Nature's author guidelines.

Scope: research-submission article types only (things external authors
submit, with formatting/word/figure rules attached) -- Article, Correspondence,
Matters Arising, Review, Perspective, Analysis, Registered Reports. Nature's
in-house editorial content (News, Careers, Obituaries, Books & Arts, Futures,
News & Views, Technology Features, Outlooks, Comment and World View) is
staff-written with no author-facing formatting guidelines, so it's out of
scope here.

Peer review model, preprint policy, AI-use policy, LaTeX/template support and
robots.txt status are out of scope for the current schema (see
common/schema.py) -- this scraper only fetches the pages that feed
article_types.

Run directly: `python journal_scrapers/1476-4687_nature/scrape.py`
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/

from common.base_scraper import BaseJournalScraper  # noqa: E402
from common.schema import ArticleType, ISSN, JournalRecord, WordLimit  # noqa: E402

FOR_AUTHORS_URL = "https://www.nature.com/nature/for-authors"
FORMATTING_GUIDE_URL = "https://www.nature.com/nature/for-authors/formatting-guide"
OTHER_SUBS_URL = "https://www.nature.com/nature/for-authors/other-subs"
MATTERS_ARISING_URL = "https://www.nature.com/nature/for-authors/matters-arising"
REGISTERED_REPORTS_URL = "https://www.nature.com/nature/for-authors/registered-reports"


def _section_text(soup: BeautifulSoup, heading_text: str, levels: tuple[str, ...] = ("h2", "h3")) -> str:
    """Concatenate text between a heading with this exact text and the next heading of the same or higher level."""
    heading = soup.find(list(levels), string=lambda s: s and s.strip() == heading_text)
    if heading is None:
        return ""
    level = int(heading.name[1])
    parts = []
    for sib in heading.find_next_siblings():
        if sib.name and re.match(r"h[1-6]$", sib.name) and int(sib.name[1]) <= level:
            break
        parts.append(sib.get_text(" ", strip=True))
    return " ".join(parts)


def _subheadings_under(soup: BeautifulSoup, parent_heading_text: str, parent_level: str = "h2") -> list[str]:
    """h3 headings following a heading with this text, until the next heading at parent_level."""
    heading = soup.find(parent_level, string=lambda s: s and s.strip() == parent_heading_text)
    if heading is None:
        return []
    names = []
    for sib in heading.find_next_siblings():
        if sib.name == parent_level:
            break
        if sib.name == "h3":
            names.append(sib.get_text(strip=True))
    return names


def _find_int(pattern: str, source: str) -> int | None:
    m = re.search(pattern, source, re.IGNORECASE)
    return int(m.group(1).replace(",", "")) if m else None


def _paragraph_containing(soup: BeautifulSoup, needle: str) -> str | None:
    """Text of the first <p> whose text contains `needle` -- locates a known paragraph without hardcoding its wording."""
    for p in soup.find_all("p"):
        if needle in p.get_text():
            return p.get_text(" ", strip=True)
    return None


def _first_sentences(text: str | None, n: int) -> str | None:
    if not text:
        return None
    sentences = re.split(r"(?<=[.])\s+", text)
    return " ".join(sentences[:n])


def _structure_str(sections: list[str], limits: dict[str, str]) -> str | None:
    """Section names, with a matching sub word count appended in brackets where known.
    `limits` maps a (loosely-matched) section name to its rendered limit text."""
    if not sections and not limits:
        return None
    parts = []
    matched: set[str] = set()
    for section in sections:
        key = next((k for k in limits if k.lower() in section.lower() or section.lower() in k.lower()), None)
        if key:
            matched.add(key)
            parts.append(f"{section} ({limits[key]})")
        else:
            parts.append(section)
    for key, value in limits.items():
        if key not in matched:
            parts.append(f"{key} ({value})")
    return ", ".join(parts) if parts else None


class NatureScraper(BaseJournalScraper):
    journal = "Nature"
    publisher = "Springer Nature"
    issn_print = "0028-0836"
    issn_electronic = "1476-4687"

    def scrape(self) -> JournalRecord:
        for_authors_html = self.fetch(FOR_AUTHORS_URL)
        self.save_raw_html("for-authors", for_authors_html)

        formatting_html = self.fetch(FORMATTING_GUIDE_URL)
        self.save_raw_html("formatting-guide", formatting_html)
        formatting_soup = BeautifulSoup(formatting_html, "html.parser")

        other_subs_html = self.fetch(OTHER_SUBS_URL)
        self.save_raw_html("other-subs", other_subs_html)
        other_subs_soup = BeautifulSoup(other_subs_html, "html.parser")

        matters_arising_html = self.fetch(MATTERS_ARISING_URL)
        self.save_raw_html("matters-arising", matters_arising_html)
        matters_arising_soup = BeautifulSoup(matters_arising_html, "html.parser")

        registered_reports_html = self.fetch(REGISTERED_REPORTS_URL)  # no formatting content beyond what's hardcoded below; fetched for save_raw_html only
        self.save_raw_html("registered-reports", registered_reports_html)

        article_type = self._parse_article(formatting_soup)
        correspondence_type = self._parse_correspondence(other_subs_soup)
        matters_arising_type = self._parse_matters_arising(matters_arising_soup)
        review_type, perspective_type = self._parse_review_and_perspective()
        analysis_type = self._parse_analysis()
        registered_reports_type = self._parse_registered_reports()

        return JournalRecord(
            journal=self.journal,
            publisher=self.publisher,
            issn=ISSN(print=self.issn_print, electronic=self.issn_electronic),
            LLM=True,
            validated=False,
            date_scraped=date.today().isoformat(),
            article_types=[
                article_type,
                correspondence_type,
                matters_arising_type,
                review_type,
                perspective_type,
                analysis_type,
                registered_reports_type,
            ],
        )

    # -- Article -----------------------------------------------------------

    def _parse_article(self, soup: BeautifulSoup) -> ArticleType:
        articles_text = _section_text(soup, "Articles")
        text_section = _section_text(soup, "Text")
        methods_text = _section_text(soup, "Methods")
        legends_text = _section_text(soup, "Figure legends")

        summary_limit = _find_int(r"summary paragraph,?\s*ideally of no more than (\d+) words", articles_text)
        methods_limit = _find_int(r"does not typically exceed ([\d,]+) words", methods_text)
        legend_limit = _find_int(r"fewer than (\d+) words each", legends_text)

        body_lengths = re.findall(
            r"typical (\d+)-page Article contains about ([\d,]+) words", text_section, re.IGNORECASE
        )
        if body_lengths:
            words = [int(w.replace(",", "")) for _, w in body_lengths]
            total_word_limit = WordLimit(
                min=min(words),
                max=max(words),
                excludes=["title", "author list", "acknowledgements", "references"],
                notes=(
                    "Range reflects discipline, not a distinct article type: "
                    + "; ".join(f"~{w} words for a {p}-page article" for p, w in body_lengths)
                    + " (physical sciences typically 6 pages, biological/clinical/social sciences typically 8)."
                ),
            )
        else:
            total_word_limit = None

        limits = {}
        if summary_limit:
            limits["Summary paragraph"] = f"ideally no more than {summary_limit} words"
        if methods_limit:
            limits["Methods"] = f"typically no more than {methods_limit} words (guideline, not a hard cap)"
        if legend_limit:
            limits["Figure legends"] = f"fewer than {legend_limit} words each"
        structure = _structure_str(_subheadings_under(soup, "Format of Articles"), limits)

        display_items = re.findall(r"(\d+)(?:-(\d+))? modest display items", articles_text + " " + text_section, re.IGNORECASE)
        if display_items:
            nums = [int(n) for pair in display_items for n in pair if n]
            figures_tables = (
                f"{min(nums)}-{max(nums)} modest display items (figures and tables combined). A 'modest' item "
                "occupies about a quarter of a page; 4 for a 6-page article, 5-6 for an 8-page article."
            )
        else:
            figures_tables = None

        description = _first_sentences(articles_text, 1)  # "Articles are original reports whose conclusions represent..."

        return ArticleType(
            type="Article",
            description=description,
            total_word_limit=total_word_limit,
            structure=structure,
            figures_tables=figures_tables,
            source_urls=[FORMATTING_GUIDE_URL],
        )

    # -- Correspondence ------------------------------------------------------

    def _parse_correspondence(self, soup: BeautifulSoup) -> ArticleType:
        text = _section_text(soup, "Correspondence")
        word_limit_val = _find_int(r"less than (\d+) words in length", text)

        return ArticleType(
            type="Correspondence",
            description=(
                "Brief comments on topical Nature content (Editorials, World View, News, News Features, "
                "Books & Arts reviews, Comment pieces or Correspondence) -- not technical comments on "
                "peer-reviewed research papers (those go to Matters Arising instead)."
            ),
            total_word_limit=(
                WordLimit(max=word_limit_val, notes=f"Source states 'less than {word_limit_val} words' -- hard ceiling, not a target.")
                if word_limit_val
                else None
            ),
            source_urls=[OTHER_SUBS_URL],
        )

    # -- Matters Arising -------------------------------------------------------

    def _parse_matters_arising(self, soup: BeautifulSoup) -> ArticleType:
        text = _section_text(soup, "Manuscript preparation and formatting")
        word_limit_val = _find_int(r"ideally not exceed ([\d,]+) words", text)

        return ArticleType(
            type="Matters Arising",
            description="Post-publication technical comments on a Nature research paper published within the past 18 months, plus the author's Reply.",
            total_word_limit=(
                WordLimit(
                    max=word_limit_val,
                    excludes=["Methods"],
                    notes=(
                        f"Ideally not exceed {word_limit_val} words (target, not a hard cap; Methods may be "
                        "moved to Supplementary Information, hence the exclusion)."
                    ),
                )
                if word_limit_val
                else None
            ),
            structure="Summary paragraph (used as the abstract), Main text, Methods (may be moved to Supplementary Information)",
            figures_tables=(
                "Ideally only one or two small figures or tables; complex ones may go into Extended Data instead "
                "(ideally no more than three such items)."
            ),
            source_urls=[MATTERS_ARISING_URL],
        )

    # -- Review / Perspective -----------------------------------------------

    def _parse_review_and_perspective(self) -> tuple[ArticleType, ArticleType]:
        word_count_notes = (
            "No fixed word/figure/reference limit is published -- length is agreed with the commissioning editor "
            "once the synopsis is accepted. This is a confirmed 'no published number', not a gap in scraping."
        )
        submission_notes = (
            " Most articles are commissioned, but authors wishing to submit an unsolicited Review or Perspective "
            "must do so through the online submission system via a synopsis."
        )
        review = ArticleType(
            type="Review",
            description="Focuses on one topical aspect of a field; should not focus on the author's own work." + submission_notes,
            total_word_limit=WordLimit(notes=word_count_notes),
            structure="Synopsis (basic structure, material to be covered, proposed depth/arrangement)",
            source_urls=[OTHER_SUBS_URL],
        )
        perspective = ArticleType(
            type="Perspective",
            description=(
                "Follows the same formatting guidelines as Reviews; more forward-looking/speculative and may be "
                "opinionated but balanced." + submission_notes
            ),
            total_word_limit=WordLimit(notes=word_count_notes),
            structure="Synopsis (basic structure, material to be covered, proposed depth/arrangement)",
            source_urls=[OTHER_SUBS_URL],
        )
        return review, perspective

    # -- Analysis --------------------------------------------------------------

    def _parse_analysis(self) -> ArticleType:
        return ArticleType(
            type="Analysis",
            description=(
                "Peer-reviewed; presents a new analysis of existing data rather than original data. Published "
                "only occasionally. Submitted via synopsis through the online submission system, with "
                "'Analysis:' inserted before the title."
            ),
            total_word_limit=WordLimit(notes="No fixed word limit published."),
            source_urls=[OTHER_SUBS_URL],
        )

    # -- Registered Reports ------------------------------------------------

    def _parse_registered_reports(self) -> ArticleType:
        return ArticleType(
            type="Registered Reports",
            description=(
                "Two-stage process: Stage 1 protocol (introduction, hypotheses, methods, analysis plan) is peer "
                "reviewed and can earn in-principle acceptance before data collection; Stage 2 is the full "
                "manuscript with results and discussion added."
            ),
            total_word_limit=WordLimit(
                notes=(
                    "The guidelines page doesn't state distinct word/figure/reference limits -- Stage 2 manuscripts "
                    "likely follow the standard Article formatting guide, but that's not confirmed on this page."
                ),
            ),
            structure="Stage 1: Registered Report Protocol, Stage 2: Full manuscript",
            source_urls=[REGISTERED_REPORTS_URL],
        )


if __name__ == "__main__":
    path = NatureScraper().run()
    print(f"Wrote {path}")

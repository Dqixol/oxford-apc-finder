"""Scraper for Nature's author guidelines.

Scope: research-submission article types only (things external authors
submit, with formatting/word/figure rules attached) -- Article, Correspondence,
Matters Arising, Review, Perspective, Analysis, Registered Reports. Nature's
in-house editorial content (News, Careers, Obituaries, Books & Arts, Futures,
News & Views, Technology Features, Outlooks, Comment and World View) is
staff-written with no author-facing formatting guidelines, so it's out of
scope here.

Each journal-level fact (peer review model, preprint policy, AI-use policy,
LaTeX/template support, robots.txt) is sourced from whichever page actually
states it, not the general for-authors landing page -- see SourcedValue in
common/schema.py.

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
from common.schema import (  # noqa: E402
    ArticleType,
    CountRange,
    FigureLimit,
    ISSN,
    JournalRecord,
    SectionWordLimit,
    SourcedValue,
    WordLimit,
)

FOR_AUTHORS_URL = "https://www.nature.com/nature/for-authors"
FORMATTING_GUIDE_URL = "https://www.nature.com/nature/for-authors/formatting-guide"
OTHER_SUBS_URL = "https://www.nature.com/nature/for-authors/other-subs"
MATTERS_ARISING_URL = "https://www.nature.com/nature/for-authors/matters-arising"
REGISTERED_REPORTS_URL = "https://www.nature.com/nature/for-authors/registered-reports"
PEER_REVIEW_POLICY_URL = "https://www.nature.com/nature-research/editorial-policies/peer-review"
PREPRINT_POLICY_URL = "https://www.nature.com/nature-portfolio/editorial-policies/preprints-conference-proceedings"
AI_POLICY_URL = "https://www.nature.com/nature-portfolio/editorial-policies/ai"


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


def _href_of_link_text(soup: BeautifulSoup, link_text: str) -> str | None:
    a = soup.find("a", string=lambda s: s and s.strip() == link_text)
    return a["href"] if a else None


_STATEMENT_KEYWORDS = ("availability", "funding statement", "author contributions", "competing interest")


def _extract_required_statements(text: str) -> list[str]:
    """Pulls declaration-type items (competing interests, data/code availability, funding,
    author contributions) out of a comma-separated manuscript-structure sentence, rather than
    every structural section -- these are checkbox-like declarations, not narrative sections."""
    found = []
    for chunk in re.split(r",\s*", text):
        chunk = chunk.strip().rstrip(".")
        if "including" in chunk.lower() and "(" in chunk:
            # e.g. "methods (including separate data and code availability statements)" --
            # the declaration is the parenthetical, not the whole structural section it's nested in.
            inner = re.search(r"including\s+(.*?)\)", chunk, re.IGNORECASE)
            if inner:
                found.append(inner.group(1).strip())
            continue
        if any(kw in chunk.lower() for kw in _STATEMENT_KEYWORDS):
            found.append(chunk)
    return found


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

        registered_reports_html = self.fetch(REGISTERED_REPORTS_URL)
        self.save_raw_html("registered-reports", registered_reports_html)

        peer_review_html = self.fetch(PEER_REVIEW_POLICY_URL)
        self.save_raw_html("peer-review-policy", peer_review_html)
        peer_review_soup = BeautifulSoup(peer_review_html, "html.parser")

        preprint_html = self.fetch(PREPRINT_POLICY_URL)
        self.save_raw_html("preprint-policy", preprint_html)
        preprint_soup = BeautifulSoup(preprint_html, "html.parser")

        ai_html = self.fetch(AI_POLICY_URL)
        self.save_raw_html("ai-policy", ai_html)
        ai_soup = BeautifulSoup(ai_html, "html.parser")

        needs_review: list[str] = []

        article_type = self._parse_article(formatting_soup, needs_review)
        correspondence_type = self._parse_correspondence(other_subs_soup, needs_review)
        matters_arising_type = self._parse_matters_arising(matters_arising_soup, needs_review)
        review_type, perspective_type = self._parse_review_and_perspective(other_subs_soup)
        analysis_type = self._parse_analysis(other_subs_soup)
        registered_reports_type = self._parse_registered_reports(needs_review)

        all_urls = (
            FOR_AUTHORS_URL, FORMATTING_GUIDE_URL, OTHER_SUBS_URL, MATTERS_ARISING_URL,
            REGISTERED_REPORTS_URL, PEER_REVIEW_POLICY_URL, PREPRINT_POLICY_URL, AI_POLICY_URL,
        )
        robots_ok = all(self.check_robots(u) for u in all_urls)
        robots_url = self.robots_txt_url(FOR_AUTHORS_URL)

        peer_review_model = self._parse_peer_review_model(peer_review_soup)
        preprint_policy = self._parse_preprint_policy(preprint_soup)
        ai_use_policy = self._parse_ai_policy(ai_soup)
        latex_accepted, template_provided, template_note = self._parse_latex_and_template(formatting_soup)

        return JournalRecord(
            journal=self.journal,
            publisher=self.publisher,
            issn=ISSN(print=self.issn_print, electronic=self.issn_electronic),
            url=FOR_AUTHORS_URL,
            date_scraped=date.today().isoformat(),
            robots_txt_allowed=SourcedValue(
                value=robots_ok,
                source_url=robots_url,
                notes=(
                    "The generic User-agent: * group allows these author-guideline pages, but robots.txt "
                    "explicitly disallows several named AI-crawler user agents (including anthropic-ai, "
                    "ClaudeBot, GPTBot) site-wide. This scraper identifies as its own named bot, not as a "
                    "browser or an AI-crawler UA."
                ),
            ),
            peer_review_model=peer_review_model,
            preprint_policy=preprint_policy,
            ai_use_policy=ai_use_policy,
            latex_accepted=latex_accepted,
            template_provided=template_provided,
            template_url=None,
            languages_accepted=["English"],  # explicit: "Contributions should be double-spaced and written in English"
            article_types=[
                article_type,
                correspondence_type,
                matters_arising_type,
                review_type,
                perspective_type,
                analysis_type,
                registered_reports_type,
            ],
            remarks=(
                "Scope limited to research-submission types (excludes staff-written content: News, Careers, "
                "Obituaries, Books & Arts, Futures, News & Views, Technology Features, Outlooks, Comment and "
                "World View). " + template_note
            ),
            needs_review=needs_review,
            source="scraped",
        )

    # -- Journal-level policy fields -----------------------------------------

    def _parse_peer_review_model(self, soup: BeautifulSoup) -> SourcedValue:
        """value is a list of PEER_REVIEW_MODELS members Nature actually offers -- not a sentence.
        Nature offers two, with single-anonymized as the default; which is default and under what
        condition lives in `notes`, not `value` (see schema.py module docstring on why that split matters)."""
        anonymity_first_sentence = _first_sentences(
            _paragraph_containing(soup, "We do not release referees"), 1
        )
        double_anon = _first_sentences(
            _paragraph_containing(soup, "double-anonymized peer review option"), 2
        )
        parts = [p for p in (anonymity_first_sentence, double_anon) if p]
        return SourcedValue(
            value=["single-anonymized", "double-anonymized"] if parts else None,
            source_url=PEER_REVIEW_POLICY_URL,
            notes=("single-anonymized is the default; " + " ".join(parts)) if parts else None,
        )

    def _parse_preprint_policy(self, soup: BeautifulSoup) -> SourcedValue:
        summary = _first_sentences(
            _paragraph_containing(soup, "Nature Portfolio journals encourage posting of preprints"), 2
        )
        return SourcedValue(value=summary, source_url=PREPRINT_POLICY_URL)

    def _parse_ai_policy(self, soup: BeautifulSoup) -> SourcedValue:
        p1 = _paragraph_containing(soup, "Springer Nature supports the responsible")
        p2 = _paragraph_containing(soup, "AI is treated as a supporting technology")
        summary = " ".join(p for p in (p1, p2) if p) or None
        return SourcedValue(value=summary, source_url=AI_POLICY_URL)

    def _parse_latex_and_template(self, soup: BeautifulSoup) -> tuple[SourcedValue, SourcedValue, str]:
        text_section = _section_text(soup, "Text")
        latex_ok = "TeX/LaTeX" in text_section or bool(_paragraph_containing(soup, "TeX/LaTeX"))
        latex_note = _paragraph_containing(soup, "TeX/LaTeX")
        chemdraw_url = _href_of_link_text(soup, "ChemDraw template")
        example_url = _href_of_link_text(soup, "annotated example")

        latex_accepted = SourcedValue(value=latex_ok, source_url=FORMATTING_GUIDE_URL, notes=latex_note)
        template_provided = SourcedValue(
            value=False,
            source_url=FORMATTING_GUIDE_URL,
            notes="No general manuscript template. Nature provides a subject-specific ChemDraw template for "
            f"chemical structures ({chemdraw_url}) and an annotated example of the summary paragraph "
            f"({example_url}), but neither is a full manuscript template.",
        )
        template_note = (
            f"Peer review model, preprint policy, and AI-use policy sourced from {PEER_REVIEW_POLICY_URL}, "
            f"{PREPRINT_POLICY_URL}, and {AI_POLICY_URL} respectively."
        )
        return latex_accepted, template_provided, template_note

    # -- Article -----------------------------------------------------------

    def _parse_article(self, soup: BeautifulSoup, needs_review: list[str]) -> ArticleType:
        articles_text = _section_text(soup, "Articles")
        text_section = _section_text(soup, "Text")
        methods_text = _section_text(soup, "Methods")
        references_text = _section_text(soup, "References")
        legends_text = _section_text(soup, "Figure legends")

        summary_limit = _find_int(r"summary paragraph,?\s*ideally of no more than (\d+) words", articles_text)
        methods_limit = _find_int(r"does not typically exceed ([\d,]+) words", methods_text)
        legend_limit = _find_int(r"fewer than (\d+) words each", legends_text)
        reference_limit = _find_int(r"(?:allow up to|no more than) (\d+) references", references_text)

        body_lengths = re.findall(
            r"typical (\d+)-page Article contains about ([\d,]+) words", text_section, re.IGNORECASE
        )
        if body_lengths:
            words = [int(w.replace(",", "")) for _, w in body_lengths]
            word_limit = WordLimit(
                min=min(words),
                max=max(words),
                unit="words",
                excludes=["title", "author list", "acknowledgements", "references"],
                notes="Range reflects discipline, not a distinct article type: "
                + "; ".join(f"~{w} words for a {p}-page article" for p, w in body_lengths)
                + " (physical sciences typically 6 pages, biological/clinical/social sciences typically 8).",
            )
        else:
            word_limit = WordLimit(notes=None)
            needs_review.append("article_types[Article].total_word_limit")

        section_word_limits = []
        if summary_limit:
            section_word_limits.append(SectionWordLimit("Summary paragraph", summary_limit, "ideally no more than this many words"))
        else:
            needs_review.append("article_types[Article].section_word_limits (Summary paragraph)")
        if methods_limit:
            section_word_limits.append(SectionWordLimit("Methods", methods_limit, "typical guideline, not a hard cap"))
        if legend_limit:
            section_word_limits.append(SectionWordLimit("Figure legends", legend_limit, "per legend"))

        required_sections = _subheadings_under(soup, "Format of Articles")
        if not required_sections:
            needs_review.append("article_types[Article].required_sections")

        display_items = re.findall(r"(\d+)(?:-(\d+))? modest display items", articles_text + " " + text_section, re.IGNORECASE)
        figure_limits = []
        if display_items:
            nums = [int(n) for pair in display_items for n in pair if n]
            figure_limits.append(
                FigureLimit(
                    min=min(nums),
                    max=max(nums),
                    counts="figures and tables combined",
                    notes="A 'modest' item occupies about a quarter of a page; 4 for a 6-page article, 5-6 for an 8-page article.",
                )
            )
        else:
            needs_review.append("article_types[Article].figure_limits")

        reference_style = None
        if references_text:
            sentences = re.split(r"(?<=[.])\s+", references_text)
            reference_style = " ".join(sentences[:2]) if sentences else None

        description = _first_sentences(articles_text, 1)  # "Articles are original reports whose conclusions represent..."

        sequence_text = _paragraph_containing(soup, "organized in the sequence")
        required_statements = _extract_required_statements(sequence_text) if sequence_text else []
        if not required_statements:
            needs_review.append("article_types[Article].required_statements")

        return ArticleType(
            type="Article",
            source_url=FORMATTING_GUIDE_URL,
            description=description,
            total_word_limit=word_limit,
            required_sections=required_sections,
            section_word_limits=section_word_limits,
            figure_limits=figure_limits,
            reference_limit=CountRange(max=reference_limit) if reference_limit else None,
            reference_style=reference_style,
            required_statements=required_statements,
            notes="Word/figure/reference limits are editorial guidelines, not hard caps; final length is at the editor's discretion.",
        )

    # -- Correspondence ------------------------------------------------------

    def _parse_correspondence(self, soup: BeautifulSoup, needs_review: list[str]) -> ArticleType:
        text = _section_text(soup, "Correspondence")
        word_limit_val = _find_int(r"less than (\d+) words in length", text)
        reference_limit = _find_int(r"no more than (\d+) references", text)

        word_limit = WordLimit(
            min=None,
            max=word_limit_val,
            unit="words",
            notes="Hard ceiling, not a target." if word_limit_val else None,
        )
        if word_limit_val is None:
            needs_review.append("article_types[Correspondence].total_word_limit")

        # "maximum of FOUR authors" -- spelled-out number, _find_int's \d pattern won't catch it.
        # Small, deliberately narrow word->int map rather than a general spelled-number parser.
        spelled_numbers = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
        author_max_match = re.search(r"maximum of (\w+) authors", text, re.IGNORECASE)
        author_limit = spelled_numbers.get(author_max_match.group(1).lower()) if author_max_match else None
        if author_limit is None:
            needs_review.append("article_types[Correspondence].author_limit")

        return ArticleType(
            type="Correspondence",
            source_url=OTHER_SUBS_URL,
            description=(
                "Brief comments on topical Nature content (Editorials, World View, News, News Features, "
                "Books & Arts reviews, Comment pieces or Correspondence) -- not technical comments on "
                "peer-reviewed research papers (those go to Matters Arising instead)."
            ),
            total_word_limit=word_limit,
            required_sections=[],
            figure_limits=[],
            reference_limit=CountRange(max=reference_limit) if reference_limit else None,
            reference_style="With links to citations; further citations allowed for fact-checking only.",
            author_limit=CountRange(max=author_limit, notes="Collective/consortium authorship not permitted.") if author_limit else None,
            notes="Supplementary material is not permitted.",
        )

    # -- Matters Arising -------------------------------------------------------

    def _parse_matters_arising(self, soup: BeautifulSoup, needs_review: list[str]) -> ArticleType:
        text = _section_text(soup, "Manuscript preparation and formatting")
        word_limit_val = _find_int(r"ideally not exceed ([\d,]+) words", text)
        reference_limit = _find_int(r"up to (\d+) references", text)

        word_limit = WordLimit(
            min=None,
            max=word_limit_val,
            unit="words",
            excludes=["methods (may be moved to Supplementary Information)"],
            notes="Target, not a hard cap ('ideally')." if word_limit_val else None,
        )
        if word_limit_val is None:
            needs_review.append("article_types[Matters Arising].total_word_limit")

        return ArticleType(
            type="Matters Arising",
            source_url=MATTERS_ARISING_URL,
            description="Post-publication technical comments on a Nature research paper published within the past 18 months, plus the author's Reply.",
            total_word_limit=word_limit,
            required_sections=[
                "Summary paragraph (used as the abstract)",
                "Main text",
                "Methods (may be moved to Supplementary Information)",
            ],
            figure_limits=[
                FigureLimit(
                    counts="figures and tables combined",
                    notes="Ideally only one or two small figures or tables (stated as words, not a fixed digit, on the source page); "
                    "complex ones may go into Extended Data instead (ideally no more than three such items).",
                )
            ],
            reference_limit=CountRange(max=reference_limit) if reference_limit else None,
            reference_style="Same reference style as Articles.",
            required_statements=["Competing interests statement"],
        )

    # -- Review / Perspective -----------------------------------------------

    def _parse_review_and_perspective(self, soup: BeautifulSoup) -> tuple[ArticleType, ArticleType]:
        word_limit_notes = (
            "No fixed word/figure/reference limit is published -- length is agreed with the commissioning editor "
            "once the synopsis is accepted. This is a confirmed 'no published number', not a gap in scraping."
        )
        submission_notes = (
            "Most articles are commissioned, but authors wishing to submit an unsolicited Review or Perspective "
            "must do so through the online submission system via a synopsis."
        )
        review = ArticleType(
            type="Review",
            source_url=OTHER_SUBS_URL,
            description="Focuses on one topical aspect of a field; should not focus on the author's own work.",
            total_word_limit=WordLimit(notes=word_limit_notes),
            required_sections=["Synopsis (basic structure, material to be covered, proposed depth/arrangement)"],
            figure_limits=[],
            notes=submission_notes,
        )
        perspective = ArticleType(
            type="Perspective",
            source_url=OTHER_SUBS_URL,
            description=(
                "Follows the same formatting guidelines as Reviews; more forward-looking/speculative and may be "
                "opinionated but balanced."
            ),
            total_word_limit=WordLimit(notes=word_limit_notes),
            required_sections=["Synopsis (basic structure, material to be covered, proposed depth/arrangement)"],
            figure_limits=[],
            notes=submission_notes,
        )
        return review, perspective

    # -- Analysis --------------------------------------------------------------

    def _parse_analysis(self, soup: BeautifulSoup) -> ArticleType:
        return ArticleType(
            type="Analysis",
            source_url=OTHER_SUBS_URL,
            description="Peer-reviewed; presents a new analysis of existing data rather than original data. Published only occasionally.",
            total_word_limit=WordLimit(notes="No fixed word limit published."),
            required_sections=[],
            figure_limits=[],
            notes="Submitted via synopsis through the online submission system, with 'Analysis:' inserted before the title.",
        )

    # -- Registered Reports ------------------------------------------------

    def _parse_registered_reports(self, needs_review: list[str]) -> ArticleType:
        needs_review.append("article_types[Registered Reports].total_word_limit")
        needs_review.append("article_types[Registered Reports].figure_limits")
        needs_review.append("article_types[Registered Reports].reference_limit")
        return ArticleType(
            type="Registered Reports",
            source_url=REGISTERED_REPORTS_URL,
            description=(
                "Two-stage process: Stage 1 protocol (introduction, hypotheses, methods, analysis plan) is peer "
                "reviewed and can earn in-principle acceptance before data collection; Stage 2 is the full "
                "manuscript with results and discussion added."
            ),
            total_word_limit=None,
            required_sections=["Stage 1: Registered Report Protocol", "Stage 2: Full manuscript"],
            figure_limits=[],
            notes=(
                "The guidelines page doesn't state distinct word/figure/reference limits -- Stage 2 manuscripts "
                "likely follow the standard Article formatting guide, but that's not confirmed on this page."
            ),
        )


if __name__ == "__main__":
    path = NatureScraper().run()
    print(f"Wrote {path}")

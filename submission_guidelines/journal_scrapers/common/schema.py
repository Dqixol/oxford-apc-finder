"""Canonical output schema shared by every journal scraper.

As of 2026-09-23 this schema is deliberately short: exploratory work with a
much larger schema (peer-review model, preprint/AI-use policy, LaTeX/template
fields, structured reference/author/figure count ranges, etc.) showed it was
more than the project actually needs. This version keeps only what's needed
to answer, per journal and per article type: what are you submitting, how
long can it be, what does it need to contain, and where did that come from.

Word limits are a structured `WordLimit` (min/max/unit/excludes/notes) so
downstream code can filter/aggregate numerically across journals. Numeric
limits are stored as min/max ranges rather than a single value, because
sources often give a range (e.g. "2,500-4,300 words") rather than one
number. When a source gives a single fixed number, set min == max. When a
source gives no number at all -- either because it genuinely doesn't
publish one, or because it hasn't been checked -- leave min/max as None and
explain which case it is in `notes`.

Figure/table guidance stays a free-text string (`figures_tables`) rather
than a structured count: unlike word limits, it isn't something the project
currently needs to filter/aggregate on, and sources state it in too many
different shapes (a count, "modest" qualitative language, per-item-type
splits) to force into one structure without inventing detail the source
doesn't have.

Provenance: source_urls lives on ArticleType (not JournalRecord) because a
journal's author-guidance is usually spread across several pages, and in
practice one page (or a small set of pages) fully describes one article
type's rules. If a field needs its own separate citation, put that citation
inline in the field's text rather than adding structure back.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class ISSN:
    print: Optional[str] = None
    electronic: Optional[str] = None


@dataclass
class WordLimit:
    min: Optional[int] = None
    max: Optional[int] = None
    unit: str = "words"  # words | pages | characters
    excludes: list[str] = field(default_factory=list)  # e.g. ["title", "references", "acknowledgements"]
    notes: Optional[str] = None  # free text for anything that doesn't reduce to a min/max


@dataclass
class ArticleType:
    type: str
    description: Optional[str] = None  # what this article type is/for -- not every journal states this, leave None rather than guess
    total_word_limit: Optional[WordLimit] = None
    structure: Optional[str] = None  # required/typical sections, with sub word counts inline where the source gives them, e.g. "Abstract (250 words), Introduction, Methods, Results, Discussion"
    figures_tables: Optional[str] = None  # free text guidance on number of figures/tables, e.g. "typically no more than 6 figures/tables combined"
    source_urls: list[str] = field(default_factory=list)  # every page this entry's fields were read from

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class JournalRecord:
    journal: str
    publisher: Optional[str]
    issn: ISSN
    LLM: bool  # True if this record's values were produced by an LLM (agent-assisted "frozen transcript" or an automated vLLM pipeline), False if fully manual
    validated: bool  # True once an independent human has reviewed/confirmed the record's values
    date_scraped: str
    article_types: list[ArticleType] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

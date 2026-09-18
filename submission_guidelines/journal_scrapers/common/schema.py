"""Canonical output schema shared by every journal scraper.

Design note: word limits, required sections, figure limits, reference limits
and reference style usually vary *by article type* within a journal (Research
Article vs Review vs Letter, etc.), not just by journal. That's why those
fields live on ArticleType rather than on JournalRecord directly.

Numeric limits (word counts, figure/table counts, reference counts, author
counts) are stored as min/max ranges rather than a single value, because
sources often give a range (e.g. "2,500-4,300 words depending on discipline",
"12-20 references") rather than one number. When a source gives a single
fixed number, set min == max. When a source gives no number at all -- either
because it genuinely doesn't publish one (e.g. a commissioned Review with
editor-negotiated length) or because we haven't checked yet -- leave min/max
as None and explain which case it is in `notes`.

Structure vs. free text: only fields we actually want to compare/filter/
aggregate across journals are structured (word/figure/reference/author
counts, peer-review category, LaTeX/template/ORCID booleans). Everything
else -- figure DPI, file size limits, LaTeX class/margin specifics, and any
nuance that doesn't reduce to a clean category or number -- stays in a
`notes` field rather than getting its own dedicated field. Trying to model
every possible constraint type doesn't scale past a handful of journals;
free text is the honest answer for the long tail. Every structured field
that can fail to reduce cleanly carries a `notes` companion for exactly that
reason (see WordLimit, FigureLimit, CountRange, SourcedValue below).

Provenance: a journal's author-guidance is usually spread across several
pages (formatting guide, editorial-policy pages, robots.txt...), so a single
`JournalRecord.url` can't honestly be "the" source for every field. Any field
whose value was read from a page *other than* `JournalRecord.url` is wrapped
in `SourcedValue`, carrying its own `source_url` so it can be traced back to
exactly where it came from. `ArticleType.source_url` covers the whole
article-type entry instead of wrapping each of its fields individually,
since in practice one page fully describes one article type; if a future
journal splits an article type's rules across multiple pages, that's the
point to start wrapping individual ArticleType fields too.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

# Soft, documented vocabularies -- not runtime-enforced (dataclasses don't
# validate), but the point of a fixed list is that `value` holds a real
# category, not a sentence. If a journal's actual policy doesn't fit one of
# these cleanly, that's what `notes` is for -- don't invent a new one-off
# string in `value` (see schema.py history: peer_review_model.value used to
# hold a full sentence for Nature, defeating the point of the field).
PEER_REVIEW_MODELS = ("single-anonymized", "double-anonymized", "open", "transparent", "none", "other")
SUBMISSION_MODES = ("open", "invited", "presubmission-required", "pitch-required", "other")


@dataclass
class SourcedValue:
    value: Optional[Any] = None
    source_url: Optional[str] = None
    notes: Optional[str] = None


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
class SectionWordLimit:
    section: str
    limit: Optional[int] = None
    notes: Optional[str] = None


@dataclass
class FigureLimit:
    min: Optional[int] = None
    max: Optional[int] = None
    counts: str = "figures"  # what min/max is counting, e.g. "figures", "tables", "figures and tables combined"
    notes: Optional[str] = None  # DPI, file size, format, colour fees, anything else that isn't a count -- see module docstring


@dataclass
class CountRange:
    """A plain min/max count with no unit -- for references, authors, anything
    that's just counted rather than measured. See WordLimit if a unit matters."""
    min: Optional[int] = None
    max: Optional[int] = None
    notes: Optional[str] = None


@dataclass
class ArticleType:
    type: str
    source_url: Optional[str] = None
    description: Optional[str] = None  # what this article type is/for, e.g. "post-publication technical comments on a paper published within 18 months" -- not every journal states this, leave None rather than guess
    submission_mode: Optional[str] = None  # see SUBMISSION_MODES; None if not stated/checked
    total_word_limit: Optional[WordLimit] = None
    required_sections: list[str] = field(default_factory=list)
    section_word_limits: list[SectionWordLimit] = field(default_factory=list)
    figure_limits: list[FigureLimit] = field(default_factory=list)
    reference_limit: Optional[CountRange] = None
    reference_style: Optional[str] = None
    author_limit: Optional[CountRange] = None
    required_statements: list[str] = field(default_factory=list)  # e.g. ["competing interests", "data availability", "ethics approval"]
    notes: Optional[str] = None  # caveats about the rules above (e.g. "guidelines, not hard caps") -- NOT what the type is, see `description`


@dataclass
class JournalRecord:
    journal: str
    publisher: Optional[str]
    issn: ISSN
    url: str  # general "for authors" landing page -- not necessarily the source of any individual field below
    date_scraped: str
    robots_txt_allowed: Optional[SourcedValue] = None  # source_url is the domain's /robots.txt
    peer_review_model: Optional[SourcedValue] = None  # value: list[str], each a member of PEER_REVIEW_MODELS -- a journal can offer more than one (e.g. single by default, double optional); notes says which is default and under what conditions
    preprint_policy: Optional[SourcedValue] = None
    ai_use_policy: Optional[SourcedValue] = None
    latex_accepted: Optional[SourcedValue] = None
    template_provided: Optional[SourcedValue] = None
    template_url: Optional[str] = None  # the actual template file/resource, when one exists -- not a citation
    orcid_required: Optional[SourcedValue] = None
    languages_accepted: list[str] = field(default_factory=list)  # e.g. ["English", "French", "German"]; empty means not stated/checked, not "English only"
    article_types: list[ArticleType] = field(default_factory=list)
    remarks: Optional[str] = None
    needs_review: list[str] = field(default_factory=list)  # field names not yet confirmed one way or the other
    source: str = "scraped"  # scraped | manual | mixed

    def to_dict(self) -> dict:
        return asdict(self)

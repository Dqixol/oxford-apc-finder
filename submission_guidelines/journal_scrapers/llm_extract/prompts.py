"""Prompt templates for extracting JournalRecord-shaped JSON from a journal's
author-guideline page text, using a locally-hosted model via vLLM's
guided_json.

Two-call design, deliberately not one combined call:
  1. `build_extraction_messages` -- guided_json call, constrained to
     common/schema.py's shape (via json_schema.py). Gets the structured data.
  2. `build_citation_check_messages` -- a second, unconstrained call that asks
     the model to quote the exact source sentence backing each numeric/
     categorical claim it made in call 1. `verify.py` then checks each quote
     is a real substring of the source text -- a cheap, no-second-model-needed
     way to catch fabrication, since a model that can't find a real quote for
     a number it claimed is a model that likely invented the number.

Why two calls instead of one schema with a citations field baked in: keeps
the guided_json schema simple (better compliance from smaller models under
structural constraints) and keeps the citation check legible/debuggable on
its own. Untested against your specific Qwen/Llama setup -- start here, but
expect to iterate on wording based on what you actually see it get wrong.

The few-shot example below is the REAL output of clean_text.py against
Annals of Mathematics' actual page (not hand-typed prose) -- it matters that
the example matches the real input format (Markdown, from trafilatura) the
model will see at inference time, headings and all.
"""
from __future__ import annotations

import json
from pathlib import Path

FEW_SHOT_INPUT_TEXT = """\
The Annals of Mathematics now receives submissions via an online editorial system*.*  This will not affect papers submitted before August 22, 2026, which will remain in the existing Annals database until further notice.  Authors must now use this link to submit their manuscripts:  https://ef.msp.org/submit/annals

The submitted manuscript must be a PDF file. Submissions must be written in English, French, or German. There are no article publishing charges (APCs).

**AI & LLM Policy**

Authors must be human, and they must take full responsibility for the content of the submission, including its correctness and the integrity and accuracy of its citations. AI agents cannot be named authors. If an AI tool or LLM contributed an idea, authors should describe that idea and specify its location in the paper.

**Acceptance Policy**

Authors of papers which have been accepted for publication will be asked to sign a copyright agreement(pdf). Authors can link to the publisher's version of their articles as soon as they are available.

As stated in the copyright agreement, authors of accepted papers can post PDF files of the final accepted version of their paper on personal webpages, electronic preprint servers, and institutional non-commercial repositories. Authors may attach a CC-BY license only to the accepted version of their paper that resides in an open access environment such as the arXiv or personal webpage. The CC-BY license is not applicable to the version published by the Annals of Mathematics.

**Required Items**

A brief abstract of about 200 words or less and a bibliography must be included in a submission. The abstract should be self-contained and not make any reference to the bibliography. If the submission is not in English, then two versions of the abstract must be included, one in the language of the article and one in English.

**Format**

If a paper is accepted, we will ask the authors to submit all source material by email to the Annals office. Authors are encouraged to use LaTeX. The class file for the journal is aomart, and it is available from CTAN. Authors are not required to format their files with aomart.

**References**

Bibliographical references should be complete, including article titles and page ranges. All references in the bibliography should be cited in the text. The use of BibTeX is preferred.

When a paper is published, the references will include the available links to the DOI number, Math Reviews number (accessible through MRLookup or MathSciNet), and Zentralblatt MATH number for each reference. If a reference has not been published, we will include the arXiv number or a URL to access the reference (if available).

**Figures**

Figures must be of publication quality. After acceptance, authors will need to submit the original source files in vector graphics format for all diagrams in your manuscript: vector EPS or vector PDF files are the most useful.

Each figure should be captioned and numbered so that it can float. Small figures occupying no more than three lines of vertical space can be kept in the text ("the curve looks like this:"). It is acceptable to submit a manuscript with all figures at the end, if their placement is specified in the text by means of comments such as "Place Figure 1 here." The same considerations apply to tables.

**aomart.sty**

Authors whose papers are accepted for publication in the Annals of Mathematics may choose to format their final versions with the journal's LaTeX style file "aomart.sty". Information about aomart.sty is available here.

**Offprints**

Authors of accepted papers will receive 10 offprints and a copy of published issue. Extra offprints may be purchased through the editorial office.
"""

# The real, verified output for the text above -- see data_scrapes/1939-8980_annals-of-mathematics/latest.json
FEW_SHOT_OUTPUT = {
    "journal": "Annals of Mathematics",
    "publisher": "Princeton University (self-published)",
    "issn": {"print": "0003-486X", "electronic": "1939-8980"},
    "url": "https://annals.math.princeton.edu/submission-guidelines",
    "date_scraped": "2026-09-17",
    "robots_txt_allowed": None,
    "peer_review_model": None,
    "preprint_policy": None,
    "ai_use_policy": {
        "value": "Authors must be human and take full responsibility for the submission's correctness and citation accuracy. AI agents cannot be named authors. If an AI tool/LLM contributed an idea, authors must describe that idea and specify its location in the paper.",
        "source_url": "https://annals.math.princeton.edu/submission-guidelines",
        "notes": None,
    },
    "latex_accepted": {
        "value": True,
        "source_url": "https://annals.math.princeton.edu/submission-guidelines",
        "notes": "Encouraged (class file 'aomart' from CTAN) but not required.",
    },
    "template_provided": {
        "value": True,
        "source_url": "https://annals.math.princeton.edu/submission-guidelines",
        "notes": "The 'aomart' LaTeX class file, available from CTAN -- optional, not mandatory.",
    },
    "template_url": None,  # the model shouldn't invent the CTAN URL -- that took a live web check to verify, not something in the given text
    "languages_accepted": ["English", "French", "German"],
    "article_types": [
        {
            "type": "Article",
            "source_url": "https://annals.math.princeton.edu/submission-guidelines",
            "description": "Original mathematics research papers -- the page documents only one general submission format.",
            "total_word_limit": {
                "min": None, "max": None, "unit": "words", "excludes": [],
                "notes": "No word/page limit stated anywhere in the text -- confirmed absence, not something unchecked.",
            },
            "required_sections": ["Abstract (~200 words or less, self-contained, no bibliography references)", "Bibliography"],
            "section_word_limits": [],
            "figure_limits": [],
            "reference_limit": None,
            "reference_style": "Complete references including article titles and page ranges; BibTeX preferred; DOI, Math Reviews (MathSciNet), and Zentralblatt MATH numbers included where available; arXiv number or URL for unpublished references.",
            "author_limit": None,
            "required_statements": [],
            "notes": "Submitted as a PDF via an online editorial system. LaTeX encouraged (class file 'aomart') but not required. Figures must be vector graphics (EPS or PDF preferred).",
        }
    ],
    "remarks": "No article processing charges (out of scope for this schema, noted here since it was explicitly stated in the text). Non-English submissions require an English abstract in addition to the original-language one.",
    "needs_review": ["peer_review_model", "preprint_policy", "robots_txt_allowed"],
    "source": "scraped",
}

SYSTEM_PROMPT = """\
You extract structured facts about academic journal author-guidelines from page text, into a \
fixed JSON schema. Follow these rules exactly -- they matter more than completeness.

1. NEVER GUESS. Only include a value if the text states it. If a field genuinely isn't \
mentioned, set it to null (or an empty list, for list fields) -- do not invent a plausible-\
sounding number, URL, or category. A missing field is far better than a wrong one.

2. Distinguish "confirmed no limit" from "not checked". If the text explicitly discusses word \
count, article length, or a similar constraint and says nothing is required (e.g. "we do not \
set fixed word count limits"), record that as a real fact: set min/max to null AND write a \
`notes` explanation like "No fixed word count limit -- confirmed, not a gap". If the text \
simply never brings the topic up at all, leave the field null with no such note, and add the \
field's name (as a dotted path, e.g. "article_types[0].total_word_limit") to the top-level \
`needs_review` list instead.

3. Numeric ranges: when a source gives ONE bare number as a target ("Analysis papers should be \
2000 words"), set min == max == that number. When a source gives an explicit ceiling ("up to \
800 words", "no more than 20 references", "maximum of 4 authors"), set only max, leave min \
null. When a source gives a real range ("12-20 references", "2,500-4,300 words"), set both min \
and max to the two different numbers.

4. Qualitative/non-numeric limits: if a limit is real but never reduces to an actual number \
(e.g. "1-2 small figures or tables", "a modest number of references"), do NOT invent a min/max \
to fill the field -- leave min/max null and put the qualitative description in `notes` \
verbatim instead.

5. `peer_review_model.value`, when set, must be a JSON list whose entries are ONLY drawn from: \
single-anonymized, double-anonymized, open, transparent, none, other. If a journal offers more \
than one (e.g. single by default, double optional), list all that apply and explain which is \
the default / under what condition in `notes` -- do not write a sentence into `value` itself.

6. `description` (on each article type) is what that type IS/is FOR -- its purpose or scope. \
`notes` is caveats about the numeric rules (e.g. "guidelines, not hard caps"). Don't mix them.

7. Article/processing charges, fees, and open-access licensing are OUT OF SCOPE for this \
schema -- do not try to force fee information into any field. If the text states there are no \
fees, a one-line mention in `remarks` is fine; don't invent a dedicated field for it.

8. Only include an article type if authors can actually submit to it (a real research/opinion/ \
letter category with some formatting guidance). Exclude purely staff-written content (news, \
careers pages, "solely commissioned by our editors" with no author-submission path at all).

9. Do not invent URLs. `source_url` should be the URL you were told this text came from, or \
null if you don't know it. Do not guess a template/resource URL that isn't given to you \
verbatim in the text.

10. For any free-text field (policy summaries, `notes`, `description`), write a concise \
factual summary in your own words -- do not reproduce large verbatim blocks of the source \
page.

Output must be valid JSON matching the provided schema exactly -- no markdown fences, no \
commentary outside the JSON object.
"""


def build_extraction_messages(journal_name: str, source_url: str, date_scraped: str, page_text: str) -> list[dict]:
    """Chat messages for the guided_json extraction call. `page_text` should already be
    cleaned (Readability-style or BeautifulSoup get_text()) -- don't feed raw HTML; we learned
    the hard way (see docs/journal_access_survey.csv notes, Crelle) that nav chrome and
    boilerplate genuinely hide/dilute the real content even for careful human readers."""
    few_shot_user = (
        f"Journal: Annals of Mathematics\n"
        f"Source URL: https://annals.math.princeton.edu/submission-guidelines\n"
        f"Date scraped: 2026-09-17\n\n"
        f"Page text:\n{FEW_SHOT_INPUT_TEXT}"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": few_shot_user},
        {"role": "assistant", "content": json.dumps(FEW_SHOT_OUTPUT, ensure_ascii=False)},
        {
            "role": "user",
            "content": (
                f"Journal: {journal_name}\n"
                f"Source URL: {source_url}\n"
                f"Date scraped: {date_scraped}\n\n"
                f"Page text:\n{page_text}"
            ),
        },
    ]


CITATION_CHECK_SYSTEM_PROMPT = """\
You previously extracted structured facts from a journal's author-guideline text. Now verify \
your own work: for each claim listed below, find the exact sentence (or near-exact -- minor \
whitespace differences are fine, but the words must genuinely be there) in the ORIGINAL TEXT \
that supports it, and quote it verbatim. If you cannot find real supporting text for a claim, \
say exactly NOT FOUND for that one -- do not paraphrase or approximate a quote that isn't \
really there. This is a check for your own possible mistakes, not a formality.

Respond as a JSON list of objects, each with "claim" and "quote" keys. No other text.
"""


def build_citation_check_messages(page_text: str, claims: list[str]) -> list[dict]:
    """`claims` should be short human-readable strings describing each non-null numeric/
    categorical fact pulled out of the call-1 output, e.g. 'Editorials reference_limit: 12-20'."""
    claims_block = "\n".join(f"- {c}" for c in claims)
    return [
        {"role": "system", "content": CITATION_CHECK_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"ORIGINAL TEXT:\n{page_text}\n\nCLAIMS TO VERIFY:\n{claims_block}",
        },
    ]

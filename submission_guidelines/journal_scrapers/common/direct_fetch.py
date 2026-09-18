"""Grabs raw author-guideline HTML for the journals we can reach directly
(no blocking WAF, no Wayback needed) -- see docs/journal_access_survey.csv for how
each of these was classified as "direct".

This is a deliberately dumb fetch-and-save step: no parsing, no field
extraction. The Python extraction phase (reading this HTML into the JSON
schema) is separate, later work.

Each journal often needs MORE THAN ONE page to cover word limits, sections,
figure limits, and policy fields -- exactly what we learned building the
real Nature scraper (8 pages) and rediscovered here: a "submission
guidelines" landing page is usually a table of contents, not the content
itself. `pages` below lists every page actually verified (by reading it) to
either contain real content or -- for a few math/physics journals -- confirm
that the journal genuinely doesn't publish numeric limits at all.

Output goes to data_scrapes/raw_html/<print-issn>/<page-name>.html -- the
print ISSN alone, no journal-name slug, falling back to the electronic ISSN
only for journals with no print edition at all. `slug` below is just this
file's own human-readable label for each TARGETS entry (used in log output),
not part of the output path.

Run directly: `python journal_scrapers/common/direct_fetch.py`
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.base_scraper import DATA_SCRAPES_DIR, USER_AGENT  # noqa: E402
from common.robots import Robots  # noqa: E402

# One entry per journal marked "direct" in docs/journal_access_survey.csv (plus
# Perspectives in Ecology and Conservation, whose HTML is fetchable even
# though the guide content itself needs JS rendering to extract -- see its note).
#
# issn is the print ISSN, falling back to electronic only for journals
# confirmed to have no print edition at all (checked against the ISSN Portal,
# not assumed from publisher type) -- matching issn_dir's convention in
# base_scraper.py.
TARGETS = [
    {
        "slug": "nature", "journal": "Nature", "issn": "0028-0836",
        "pages": [
            {"name": "formatting-guide", "url": "https://www.nature.com/nature/for-authors/formatting-guide"},
        ],
        "note": "Full 8-page set (for-authors, formatting-guide, other-subs, matters-arising, "
                "registered-reports, peer-review-policy, preprint-policy, ai-policy) already exists "
                "from the bespoke scraper build -- journal_scrapers/1476-4687_nature/scrape.py. "
                "This entry just keeps the corpus consistent; nothing new needed here.",
    },
    {
        "slug": "bmj", "journal": "The BMJ", "issn": "0959-8138",
        "pages": [
            {"name": "article-types", "url": "https://www.bmj.com/about-bmj/resources-authors/article-types"},
        ],
        "note": "Rich content (word/reference limits for 8 article types, confirmed earlier). "
                "Peer review / preprint / AI-use policy pages still not fetched -- same gap as Nature "
                "had before its second pass. Left for a future round, not blocking this batch.",
    },
    {
        "slug": "nature-sustainability", "journal": "Nature Sustainability", "issn": "2398-9629",
        "pages": [
            {"name": "submission-guidelines", "url": "https://www.nature.com/natsustain/submission-guidelines"},
            {"name": "initial-formatting", "url": "https://www.nature.com/natsustain/submission-guidelines/initial-formatting"},
            {"name": "aip-and-formatting", "url": "https://www.nature.com/natsustain/submission-guidelines/aip-and-formatting"},
        ],
        "note": "3-page depth needed, same pattern as Nature itself. aip-and-formatting is genuinely "
                "comprehensive (16 sections) but states no explicit word-count limit -- confirmed absence, not a gap.",
    },
    {
        "slug": "nature-food", "journal": "Nature Food", "issn": "2662-1355",
        "pages": [
            {"name": "submission-guidelines", "url": "https://www.nature.com/natfood/submission-guidelines"},
            {"name": "initial-formatting", "url": "https://www.nature.com/natfood/submission-guidelines/initial-formatting"},
            {"name": "aip-and-formatting", "url": "https://www.nature.com/natfood/submission-guidelines/aip-and-formatting"},
        ],
        "note": "See Nature Sustainability note -- identical platform, identical pattern.",
    },
    {
        "slug": "frontiers-sustainable-food-systems", "journal": "Frontiers in Sustainable Food Systems", "issn": "2571-581X",
        "pages": [
            {"name": "for-authors", "url": "https://www.frontiersin.org/journals/sustainable-food-systems/for-authors"},
            {"name": "author-guidelines-platform-wide", "url": "https://www.frontiersin.org/guidelines/author-guidelines"},
            {"name": "article-types", "url": "https://www.frontiersin.org/journals/sustainable-food-systems/for-authors/article-types"},
        ],
        "note": "for-authors redirects to a marketing 'why submit' page -- not useful alone. "
                "Real word limits (125-12,000 words depending on type) are on article-types, a "
                "journal-specific page; formatting/reference rules are on the platform-wide guidelines page.",
    },
    {
        "slug": "annals-of-mathematics", "journal": "Annals of Mathematics", "issn": "0003-486X",
        "pages": [
            {"name": "submission-guidelines", "url": "https://annals.math.princeton.edu/submission-guidelines"},
        ],
        "note": "Confirmed complete as a single page: submission format, abstract length (~200 words), "
                "no APCs, AI policy. Mathematics journals often genuinely have short guidelines -- verified "
                "by reading, not assumed from length.",
    },
    {
        "slug": "geometry-and-topology", "journal": "Geometry and Topology", "issn": "1465-3060",
        "pages": [
            {"name": "submissions", "url": "https://msp.org/gt/about/journal/submissions.html"},
        ],
        "note": "Looked thin by character-count heuristic only because of a huge issue-archive sidebar "
                "diluting the page; the actual guidelines (150-word abstract, references, figures) are "
                "real and complete, just at the end of the document.",
    },
    {
        "slug": "crelle", "journal": "Journal für die reine und angewandte Mathematik (Crelle)", "issn": "0075-4102",
        "pages": [
            {"name": "journal-home", "url": "https://www.degruyterbrill.com/journal/key/crll/html"},
        ],
        "note": "The journal homepage itself has a #submit section with real, Crelle-specific rules "
                "(80-char title/running-head limit, Proposition/Theorem/Lemma formatting, reference style, "
                "languages allowed, repository policy, hybrid OA/APC terms) -- initially missed because an "
                "earlier link-scan only checked <a href> nav links and never read the page's own body text. "
                "The generic 'prepare-your-journal-submission' page fetched first is publisher-wide, not "
                "Crelle-specific, and isn't needed now that the real content is found.",
    },
    {
        "slug": "mathematische-annalen", "journal": "Mathematische Annalen", "issn": "0025-5831",
        "pages": [
            {"name": "submission-guidelines", "url": "https://link.springer.com/journal/208/submission-guidelines"},
        ],
    },
    {
        "slug": "inventiones-mathematicae", "journal": "Inventiones Mathematicae", "issn": "0020-9910",
        "pages": [
            {"name": "submission-guidelines", "url": "https://link.springer.com/journal/222/submission-guidelines"},
        ],
        "note": "Standard Springer math-journal template (same as Mathematische Annalen/GRG); no explicit "
                "word/page limit found, which is consistent with that template's usual pattern.",
    },
    {
        "slug": "selecta-mathematica", "journal": "Selecta Mathematica", "issn": "1022-1824",
        "pages": [
            {"name": "submission-guidelines", "url": "https://link.springer.com/journal/29/submission-guidelines"},
        ],
        "note": "Same Springer template, genuinely shorter page (real content, not a stub -- confirmed by "
                "reading, not just length). Only numeric rule found: running head <=50 characters.",
    },
    {
        "slug": "duke-mathematical-journal", "journal": "Duke Mathematical Journal", "issn": "0012-7094",
        "pages": [
            {"name": "for-authors", "url": "https://www.dukeupress.edu/duke-mathematical-journal"},
        ],
        "note": "Real content lives in a #ForAuthors in-page section (same anchor pattern as Crelle) -- read "
                "directly this time rather than repeating the link-scan mistake. Rich content: submissions via "
                "MSP's EditFlow system (same platform as Geometry & Topology and Annals of Mathematics), "
                "11pt amsart LaTeX class with specific page dimensions, abstract <=300 words, running head "
                "<=50 characters, no APCs, explicit AI/LLM disclosure policy. projecteuclid.org also hosts "
                "this journal but its journal-specific page intermittently returned an Incapsula WAF "
                "challenge on first attempt (succeeded on retry) -- dukeupress.edu was reliable and used instead.",
    },
    {
        "slug": "jhep", "journal": "Journal of High Energy Physics", "issn": "1126-6708",
        "pages": [
            {"name": "submission-guidelines", "url": "https://link.springer.com/journal/13130/submission-guidelines"},
            {"name": "author-help", "url": "https://jhep.sissa.it/jhep/help/helpLoader.jsp?pgType=author"},
        ],
        "note": "submission-guidelines alone is nearly empty (2.2KB, just nav chrome) -- Springer's site is "
                "React-based and the real 'Instructions for authors' link isn't in the static HTML. Resolved "
                "by rendering the page with Playwright (see render_js.py) to reveal the real destination: "
                "jhep.sissa.it, a plain HTML page (SISSA-hosted, same partnership as JCAP) with real content "
                "-- figure DPI limits, keyword rules, revision timelines, Addendum/Erratum length. No JS "
                "rendering needed for author-help itself, just for discovering its URL.",
    },
    {
        "slug": "grg", "journal": "General Relativity and Gravitation", "issn": "0001-7701",
        "pages": [
            {"name": "submission-guidelines", "url": "https://link.springer.com/journal/10714/submission-guidelines"},
        ],
    },
    {
        "slug": "jcap", "journal": "Journal of Cosmology and Astroparticle Physics", "issn": "1475-7516",
        "pages": [
            {"name": "about", "url": "https://publishingsupport.iopscience.iop.org/journals/journal-of-cosmology-and-astroparticle-physics/"},
            {"name": "author-help", "url": "https://jcap.sissa.it/jcap/help/helpLoader.jsp?pgType=author"},
        ],
        "note": "The IOPscience 'about' page is just a stub pointing to the real journal site "
                "(jcap.sissa.it, run by SISSA, a different domain than the other IOP journals here). "
                "author-help has real, detailed content (registration, manuscript prep, file prep) -- "
                "including a real length limit initially missed on first read: 'JCAP papers do not "
                "normally exceed 50 pages' (editor discretion, not a hard cap).",
    },
    {
        "slug": "cqg", "journal": "Classical and Quantum Gravity", "issn": "0264-9381",
        "pages": [
            {"name": "about", "url": "https://publishingsupport.iopscience.iop.org/journals/classical-and-quantum-gravity/"},
        ],
        "note": "Confirmed genuinely comprehensive -- shared IOP-wide guidelines (figures, formats, "
                "copyright/permissions). This page explicitly states the per-journal article-length limit "
                "lives on iopscience.iop.org/journal/<issn> ('About the journal' section) -- but that page "
                "is gated behind a Radware Bot Manager CAPTCHA (confirmed: fetched a captcha challenge page, "
                "not content). This is a genuine access barrier like the WAF-blocked publishers, not "
                "something a more careful read of what we have would fix. Only length-adjacent numbers found "
                "here are supplementary-file limits (10MB video, 30-char titles, 150MB combined), not article length.",
    },
    {
        "slug": "jphysg", "journal": "Journal of Physics G-Nuclear and Particle Physics", "issn": "0954-3899",
        "pages": [
            {"name": "about", "url": "https://publishingsupport.iopscience.iop.org/journals/journal-of-physics-g-nuclear-and-particle-physics/"},
        ],
        "note": "See Classical and Quantum Gravity note -- identical shared-template page, same CAPTCHA gap.",
    },
    {
        "slug": "perspectives-ecology-conservation", "journal": "Perspectives in Ecology and Conservation", "issn": "2530-0644",
        "pages": [
            {"name": "guia-autores", "url": "https://www.perspectecolconserv.com/en-guia-autores"},
        ],
        "pdfs": [
            {"name": "guide-for-authors", "url": "https://www.perspectecolconserv.com/en-guia-autores-pdf"},
        ],
        "note": "guia-autores alone is client-side rendered -- only nav chrome (~5KB) in plain HTML. Resolved "
                "by rendering with Playwright (see render_js.py), which revealed a downloadable 'Guide for "
                "authors' PDF (20 pages, real structure: six article types -- Essays & Perspectives/Trends, "
                "Research Letters, Policy Forums, Correspondences, Book reviews, etc. -- each with word/"
                "abstract/box/figure/reference limits described). BUT every numeric limit in the PDF is "
                "unrecoverable by text extraction (confirmed with both pypdf and pdfplumber, and at the "
                "character level: real glyphs with correct width/position exist but their ToUnicode mapping "
                "is null -- a defect in Elsevier's own PDF export, not a tooling limitation). OCR would be "
                "needed to recover the actual numbers; flagged and deferred rather than pursued, per "
                "explicit decision -- the article-type structure and descriptions are usable as-is, just "
                "missing the specific limit numbers.",
    },
]


def robots_allows(session: requests.Session, url: str) -> tuple[bool, str]:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    try:
        resp = session.get(f"{origin}/robots.txt", timeout=20)
        robots = Robots(resp.text)
    except requests.RequestException:
        return True, "no robots.txt reachable, defaulting to allow"
    return robots.can_fetch(USER_AGENT, url), ""


def fetch_page(session: requests.Session, out_dir: Path, page: dict) -> dict:
    url = page["url"]
    allowed, robots_note = robots_allows(session, url)
    if not allowed:
        return {**page, "ok": False, "status": None, "reason": f"robots.txt disallows: {robots_note}"}

    try:
        resp = session.get(url, timeout=30)
    except requests.RequestException as e:
        return {**page, "ok": False, "status": None, "reason": str(e)}

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{page['name']}.html").write_text(resp.text, encoding="utf-8")

    return {**page, "ok": resp.status_code == 200, "status": resp.status_code,
            "final_url": resp.url, "bytes": len(resp.text)}


def fetch_pdf(session: requests.Session, out_dir: Path, pdf: dict) -> dict:
    url = pdf["url"]
    allowed, robots_note = robots_allows(session, url)
    if not allowed:
        return {**pdf, "ok": False, "status": None, "reason": f"robots.txt disallows: {robots_note}"}

    try:
        resp = session.get(url, timeout=30)
    except requests.RequestException as e:
        return {**pdf, "ok": False, "status": None, "reason": str(e)}

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{pdf['name']}.pdf").write_bytes(resp.content)

    return {**pdf, "ok": resp.status_code == 200, "status": resp.status_code, "bytes": len(resp.content)}


def main() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    last_domain = None
    total_ok = total_pages = 0
    for target in TARGETS:
        issn_dir = target["issn"]
        out_dir = DATA_SCRAPES_DIR / "raw_html" / issn_dir
        print(f"\n=== {target['journal']} ({issn_dir}) ===")
        if target.get("note"):
            print(f"  note: {target['note']}")

        for page in target["pages"]:
            domain = urlparse(page["url"]).netloc
            if domain == last_domain:
                time.sleep(2)  # polite gap between consecutive requests to the same host
            last_domain = domain

            result = fetch_page(session, out_dir, page)
            total_pages += 1
            total_ok += result["ok"]
            status = "OK" if result["ok"] else "FAIL"
            print(f"  [{page['name']}] {status} status={result.get('status')} bytes={result.get('bytes', '-')} "
                  f"{'' if result['ok'] else result.get('reason', '')}")

        for pdf in target.get("pdfs", []):
            domain = urlparse(pdf["url"]).netloc
            if domain == last_domain:
                time.sleep(2)
            last_domain = domain

            result = fetch_pdf(session, out_dir, pdf)
            total_pages += 1
            total_ok += result["ok"]
            status = "OK" if result["ok"] else "FAIL"
            print(f"  [{pdf['name']}.pdf] {status} status={result.get('status')} bytes={result.get('bytes', '-')} "
                  f"{'' if result['ok'] else result.get('reason', '')}")

    print(f"\n{total_ok}/{total_pages} pages fetched successfully across {len(TARGETS)} journals.")
    print(f"Output: {DATA_SCRAPES_DIR}/raw_html/<issn>/")


if __name__ == "__main__":
    main()

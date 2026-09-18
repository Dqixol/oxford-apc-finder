"""Per-journal lists of (page, source_url) pairs -- the thing extract_journal.py
needs to run every page a journal's guidance is actually spread across,
instead of just whichever one --page happens to name.

This is hand-researched, same as everything in common/direct_fetch.py's
TARGETS -- see the project README's "Known gap: URL discovery doesn't scale"
section. Not derived from anything automatically: a page's real URL is only
knowable by having actually read the journal's site, which is why this data
lives in its own small file rather than being inferred from raw_html/*.md
filenames (a filename like "other-subs" doesn't tell you what URL it came
from).

Nature's 8 entries are transcribed from journal_scrapers/1476-4687_nature/
scrape.py's own URL constants (FOR_AUTHORS_URL etc.) -- that's the actual
source of truth for what produced data_scrapes/1476-4687_nature/latest.json,
so these are the same URLs, not re-researched. Kept as a duplicate literal
list rather than importing scrape.py's constants because scrape.py is a
bespoke BeautifulSoup parser with its own heavy dependencies/parsing
functions bundled in the same module -- importing it just for 8 strings
would pull all of that in for no reason. If Nature's real URLs ever change,
update both places; there's only the one journal with this duplication risk
today.
"""
from __future__ import annotations

PAGE_MANIFESTS: dict[str, list[tuple[str, str]]] = {
    "1476-4687_nature": [
        ("for-authors", "https://www.nature.com/nature/for-authors"),
        ("formatting-guide", "https://www.nature.com/nature/for-authors/formatting-guide"),
        ("other-subs", "https://www.nature.com/nature/for-authors/other-subs"),
        ("matters-arising", "https://www.nature.com/nature/for-authors/matters-arising"),
        ("registered-reports", "https://www.nature.com/nature/for-authors/registered-reports"),
        ("peer-review-policy", "https://www.nature.com/nature-research/editorial-policies/peer-review"),
        ("preprint-policy", "https://www.nature.com/nature-portfolio/editorial-policies/preprints-conference-proceedings"),
        ("ai-policy", "https://www.nature.com/nature-portfolio/editorial-policies/ai"),
    ],
}


def pages_for_slug(slug: str) -> list[tuple[str, str]]:
    if slug not in PAGE_MANIFESTS:
        raise SystemExit(
            f"No page manifest registered for {slug!r} in page_manifests.py. "
            f"Registered slugs: {sorted(PAGE_MANIFESTS)}. Add one (page name, source URL) "
            f"pair per page this journal's guidance is spread across -- see the file's "
            f"docstring for where the Nature URLs came from -- or pass --page/--source-url "
            f"to client.py directly for a single-page run instead."
        )
    return PAGE_MANIFESTS[slug]

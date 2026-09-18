"""Converts already-fetched HTML into clean Markdown, as its own explicit
phase between direct_fetch.py and client.py -- matching the fetch-then-parse
pattern used everywhere else in this project (direct_fetch.py -> extract.py).

This is a Python port of the approach in archive/example_webarchive_API_code/
(Mozilla Readability + Turndown, in Node.js): trafilatura plays the role of
Readability (identifies the real article content, discards nav/boilerplate),
markdownify-via-trafilatura's own markdown output plays the role of Turndown
(HTML -> Markdown, preserving headings/tables/lists). Ported rather than
reused as-is so the whole pipeline -- including client.py, meant to run on
the HPC side alongside vLLM -- stays a single Python runtime; see the
conversation this was designed in for the reasoning.

Verified against real saved pages before being trusted here (unlike
client.py, which is untested against the actual HPC models): correctly
extracted BMJ's two separate limit tables (the overview table AND the
detailed "12-20 references" one) with real Markdown table structure intact,
and correctly found the Crelle #submit content that an earlier manual
link-scan missed entirely. Not a guarantee it's perfect on every journal,
but a real, checked baseline.

Run directly to batch-convert every fetched HTML page across all journals:
    python clean_text.py
Or for one journal only:
    python clean_text.py --slug 1756-1833_bmj
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import trafilatura

DATA_SCRAPES_DIR = Path(__file__).resolve().parents[2] / "data_scrapes"


def html_to_markdown(html: str) -> str | None:
    """Returns None if trafilatura couldn't identify real article content
    (e.g. a JS-rendered stub page with only nav chrome) -- that's a genuine
    signal worth surfacing, not something to paper over with a fallback."""
    return trafilatura.extract(html, output_format="markdown", include_tables=True, include_links=False)


def convert_journal(slug_dir: Path) -> list[tuple[Path, bool]]:
    raw_dir = slug_dir / "raw_html"
    if not raw_dir.is_dir():
        return []
    results = []
    for html_path in sorted(raw_dir.glob("*.html")):
        md_path = html_path.with_suffix(".md")
        html = html_path.read_text(encoding="utf-8")
        md = html_to_markdown(html)
        if md:
            md_path.write_text(md, encoding="utf-8")
        results.append((html_path, bool(md)))
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default=None, help="convert only this journal (e.g. 1756-1833_bmj); default: all")
    args = ap.parse_args()

    slug_dirs = [DATA_SCRAPES_DIR / args.slug] if args.slug else sorted(DATA_SCRAPES_DIR.glob("*"))

    total = ok = 0
    for slug_dir in slug_dirs:
        if not slug_dir.is_dir():
            continue
        results = convert_journal(slug_dir)
        if not results:
            continue
        print(f"\n=== {slug_dir.name} ===")
        for html_path, success in results:
            total += 1
            ok += success
            status = "OK" if success else "FAILED (no article content identified -- check manually)"
            print(f"  {html_path.name}: {status}")

    print(f"\n{ok}/{total} pages converted. PDFs are skipped here -- see pypdf-based extraction elsewhere for those.")


if __name__ == "__main__":
    main()

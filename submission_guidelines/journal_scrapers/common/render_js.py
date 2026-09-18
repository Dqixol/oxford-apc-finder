"""Renders JS-driven author-guideline pages with a real browser engine (Playwright)
so the actual content can be captured, for the small set of pages where a plain
HTTP GET only returns nav chrome because the content loads via client-side JS.

This is NOT a workaround for a site blocking us -- both targets below are
confirmed not blocked (robots.txt allows our bot, no WAF 403; see
docs/journal_access_survey.csv). It's purely rendering: the site's own JS runs and
produces the page a human visitor would see, same as any browser does. That's
a different thing from the stealth/evasion automation ruled out for the
WAF-blocked publishers (Science.org etc.) -- there's no detection to evade
here, since nothing is detecting or blocking us in the first place.

We still identify honestly: Playwright's default UA is overridden to our own
project UA, not a spoofed "real browser" string pretending to be something
we're not.

Outcome for the two targets below: rendering didn't turn out to be the final
answer for either -- it was the *discovery* step that revealed the real,
plain-HTML destination each JS-driven page links to (jhep.sissa.it for JHEP,
a downloadable PDF for Perspectives in Ecology and Conservation). Those real
pages are fetched directly elsewhere (direct_fetch.py) and don't need
Playwright themselves. Kept here as a general tool for the next journal that
turns out to be genuinely JS-rendered with no plain-HTML escape hatch.

Run directly: `python journal_scrapers/common/render_js.py`
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # journal_scrapers/
from common.base_scraper import DATA_SCRAPES_DIR, USER_AGENT  # noqa: E402

TARGETS = [
    {
        "issn": "1126-6708",
        "page_name": "submission-guidelines",
        "url": "https://link.springer.com/journal/13130/submission-guidelines",
    },
    {
        "issn": "2530-0644",
        "page_name": "guia-autores",
        "url": "https://www.perspectecolconserv.com/en-guia-autores",
    },
]


def main() -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=USER_AGENT)

        for target in TARGETS:
            print(f"rendering {target['url']} ...")
            page.goto(target["url"], wait_until="networkidle", timeout=30000)

            # Cookie-consent overlays commonly block the real content from
            # loading/rendering underneath until dismissed.
            for label in ("Reject optional cookies", "Reject all", "Accept all cookies", "Accept all"):
                button = page.get_by_role("button", name=label, exact=False)
                if button.count() > 0:
                    button.first.click()
                    page.wait_for_load_state("networkidle", timeout=15000)
                    print(f"  dismissed cookie banner via '{label}'")
                    break

            html = page.content()
            visible_text_len = len(page.inner_text("body"))

            out_dir = DATA_SCRAPES_DIR / "raw_html" / target["issn"]
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{target['page_name']}.rendered.html"
            out_path.write_text(html, encoding="utf-8")

            print(f"  saved {out_path} ({len(html)} bytes HTML, {visible_text_len} chars visible text)")

        browser.close()


if __name__ == "__main__":
    main()

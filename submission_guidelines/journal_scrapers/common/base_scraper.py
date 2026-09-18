"""Shared scraping infrastructure: robots.txt checks, polite fetching, saving output.

Each journal gets its own subclass under journal_scrapers/<issn>_<slug>/scrape.py
implementing `scrape()`, since page structure differs too much per publisher to
share a parser. This base class only handles what's common: compliance,
fetching, and writing the JSON + raw HTML to data_scrapes/.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import requests

from .robots import Robots
from .schema import JournalRecord

# Identify ourselves honestly as our own project's bot, not as a browser and
# not as an AI-crawler UA string (some publishers, e.g. nature.com, disallow
# those by name in robots.txt). Update the contact URL/email for your project.
USER_AGENT = (
    "OxfordRSETrainingBot/0.1 "
    "(+https://github.com/<your-org>/oxford_apc_training; contact: talithabee@gmail.com)"
)

DATA_SCRAPES_DIR = Path(__file__).resolve().parents[2] / "data_scrapes"


class RobotsDisallowedError(RuntimeError):
    """Raised when robots.txt disallows fetching a URL for our user agent."""


class BaseJournalScraper(ABC):
    journal: str
    issn_print: str | None = None
    issn_electronic: str | None = None
    publisher: str | None = None

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._robots_cache: dict[str, Robots] = {}

    @property
    def folder_slug(self) -> str:
        issn = self.issn_electronic or self.issn_print
        slug = self.journal.lower().replace(" ", "-")
        return f"{issn}_{slug}" if issn else slug

    def robots_txt_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    def _robots_parser(self, url: str) -> Robots:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._robots_cache:
            try:
                response = self.session.get(f"{origin}/robots.txt", timeout=30)
                self._robots_cache[origin] = Robots(response.text)
            except requests.RequestException:
                self._robots_cache[origin] = Robots.unreachable()
        return self._robots_cache[origin]

    def check_robots(self, url: str) -> bool:
        return self._robots_parser(url).can_fetch(USER_AGENT, url)

    def fetch(self, url: str, allow_disallowed: bool = False) -> str:
        if not self.check_robots(url) and not allow_disallowed:
            raise RobotsDisallowedError(f"robots.txt disallows fetching {url!r} for {USER_AGENT!r}")
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.text

    @abstractmethod
    def scrape(self) -> JournalRecord:
        """Fetch and parse whatever pages are needed; return a populated JournalRecord."""

    def save_raw_html(self, name: str, html: str) -> None:
        raw_dir = DATA_SCRAPES_DIR / self.folder_slug / "raw_html"
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / f"{name}.html").write_text(html, encoding="utf-8")

    def run(self) -> Path:
        record = self.scrape()
        out_dir = DATA_SCRAPES_DIR / self.folder_slug
        out_dir.mkdir(parents=True, exist_ok=True)
        today = date.today().isoformat()
        payload = json.dumps(record.to_dict(), indent=2, ensure_ascii=False)
        (out_dir / f"{today}.json").write_text(payload, encoding="utf-8")
        (out_dir / "latest.json").write_text(payload, encoding="utf-8")
        return out_dir / f"{today}.json"

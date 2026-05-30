"""Web scraping source - fetches articles from HTML pages using CSS selectors."""

from __future__ import annotations

import time
import logging
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from models import FeedResult, Entry, SourceConfig
from .base import BaseSource

log = logging.getLogger("signal")


class WebSource(BaseSource):
    """Fetches articles from web pages using CSS selectors.

    Configuration via SourceConfig.metadata:
        selector: CSS selector for article containers (default: "article")
        title_sel: CSS selector for title within container (default: "h2 a")
        summary_sel: CSS selector for summary within container (default: "p")
        link_sel: CSS selector for link within container (default: "a")
        headers: dict of custom HTTP headers
    """

    # Default selectors
    DEFAULTS = {
        "selector": "article",
        "title_sel": "h2",
        "summary_sel": "p",
        "link_sel": "a",
    }

    def fetch(self, since: datetime, **kwargs) -> FeedResult:
        """Fetch articles by scraping the configured URL."""
        start = time.monotonic()
        meta = {**self.DEFAULTS, **self.config.metadata}

        try:
            headers = meta.get("headers", {})
            headers.setdefault("User-Agent", "Mozilla/5.0 (compatible; Signal/1.0)")

            resp = requests.get(self.config.url, timeout=15, headers=headers)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            entries = []
            for item in soup.select(meta["selector"]):
                entry = self._extract_entry(item, meta)
                if entry:
                    entries.append(entry)

            log.info(f"[{self.config.name}] Scraped {len(entries)} items from {self.config.url}")

            return FeedResult(
                config=self.config,
                entries=entries,
                fetch_duration=time.monotonic() - start,
            )
        except Exception as e:
            log.warning(f"[{self.config.name}] Scraping failed: {e}")
            return FeedResult(
                config=self.config,
                error=str(e),
                fetch_duration=time.monotonic() - start,
            )

    def _extract_entry(self, item, meta: dict) -> Entry | None:
        """Extract a single entry from an HTML element."""
        # Find title
        title_el = item.select_one(meta["title_sel"])
        if not title_el:
            return None
        title = title_el.get_text(strip=True)
        if not title:
            return None

        # Find link
        link_el = item.select_one(meta["link_sel"])
        link = ""
        if link_el:
            link = link_el.get("href", "")
            if link.startswith("/"):
                link = urljoin(self.config.url, link)

        # Find summary
        summary = ""
        if meta["summary_sel"]:
            summary_el = item.select_one(meta["summary_sel"])
            if summary_el:
                summary = summary_el.get_text(strip=True)[:500]

        return Entry(
            title=title,
            link=link,
            summary=summary,
            source_name=self.config.name,
            source_type="web",
        )

    def discover(self) -> list[SourceConfig]:
        """Web sources don't support auto-discovery yet."""
        return []

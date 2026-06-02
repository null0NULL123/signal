"""Web scraping source - fetches articles from HTML pages using CSS selectors."""

from __future__ import annotations

import time
import logging
from datetime import datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from config import HTTP_USER_AGENT, WEB_SUMMARY_TRUNCATE_LENGTH, get_int
from models import FeedResult, Entry, SourceConfig
from .base import BaseSource

log = logging.getLogger("sift")

_DEFAULTS = {"selector": "article", "title_sel": "h2", "summary_sel": "p", "link_sel": "a"}


class WebSource(BaseSource):
    """Fetches articles from web pages using CSS selectors.

    Configuration via SourceConfig.metadata:
        selector, title_sel, summary_sel, link_sel, headers
    """

    def fetch(self, since: datetime, **kwargs) -> FeedResult:
        start = time.monotonic()
        meta = {**_DEFAULTS, **self.config.metadata}

        try:
            headers = meta.get("headers", {})
            headers.setdefault("User-Agent", HTTP_USER_AGENT)

            resp = httpx.get(self.config.url, timeout=get_int("HTTP_TIMEOUT", 15), headers=headers)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            entries = [e for item in soup.select(meta["selector"]) if (e := self._extract(item, meta))]

            log.info(f"[{self.config.name}] Scraped {len(entries)} items from {self.config.url}")
            return FeedResult(config=self.config, entries=entries, fetch_duration=time.monotonic() - start)
        except Exception as e:
            log.warning(f"[{self.config.name}] Scraping failed: {e}")
            return FeedResult(config=self.config, error=str(e), fetch_duration=time.monotonic() - start)

    def _extract(self, item, meta: dict) -> Entry | None:
        title_el = item.select_one(meta["title_sel"])
        if not title_el:
            return None
        title = title_el.get_text(strip=True)
        if not title:
            return None

        link_el = item.select_one(meta["link_sel"])
        link = ""
        if link_el:
            link = link_el.get("href", "")
            if link.startswith("/"):
                link = urljoin(self.config.url, link)

        summary = ""
        if meta["summary_sel"] and (summary_el := item.select_one(meta["summary_sel"])):
            summary = summary_el.get_text(strip=True)[:WEB_SUMMARY_TRUNCATE_LENGTH]

        return Entry(title=title, link=link, summary=summary, source_name=self.config.name, source_type="web")

    def discover(self) -> list[SourceConfig]:
        return []

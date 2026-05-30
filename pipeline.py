"""Pipeline orchestrator for Signal.

Coordinates fetching, deduplication, storage, summarization, and delivery
using the layered architecture (sources, storage, processors, channels).
"""

from __future__ import annotations

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from channels.base import BaseChannel
from models import Digest, FeedResult, SourceConfig
from processors.base import BaseProcessor
from processors.dedup import DedupProcessor
from processors.summarizer import SummarizeProcessor
from sources.base import BaseSource
from sources.rss import RSSSource
from sources.web import WebSource
from storage.base import BaseStorage

log = logging.getLogger("signal")

# ---------------------------------------------------------------------------
# Source registry: maps source_type string -> concrete BaseSource subclass
# ---------------------------------------------------------------------------
SOURCE_REGISTRY: dict[str, type[BaseSource]] = {
    "rss": RSSSource,
    "web": WebSource,
}


def create_source(config: SourceConfig) -> BaseSource:
    """Factory: instantiate the correct BaseSource subclass for *config*.

    Raises:
        ValueError: If ``config.source_type`` is not in ``SOURCE_REGISTRY``.
    """
    cls = SOURCE_REGISTRY.get(config.source_type)
    if cls is None:
        raise ValueError(
            f"Unknown source_type {config.source_type!r}. "
            f"Registered types: {list(SOURCE_REGISTRY)}"
        )
    return cls(config)


def fetch_sources(
    sources: list[SourceConfig],
    days: int = 7,
    max_workers: int = 8,
) -> list[FeedResult]:
    """Fetch entries from all *sources* in parallel, filtering to the last *days*.

    Results are returned sorted by the original order of *sources* so that
    downstream consumers see a deterministic sequence regardless of which
    thread finished first.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    results: list[FeedResult] = [None] * len(sources)  # type: ignore[list-item]

    def _fetch(idx: int, config: SourceConfig) -> tuple[int, FeedResult]:
        src = create_source(config)
        return idx, src.fetch(since)

    with ThreadPoolExecutor(max_workers=min(len(sources), max_workers)) as pool:
        futures = {
            pool.submit(_fetch, i, cfg): i for i, cfg in enumerate(sources)
        }
        for future in as_completed(futures):
            idx, result = future.result()
            results[idx] = result

    return results


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class Pipeline:
    """Full pipeline orchestrator using dependency injection.

    Parameters
    ----------
    sources:
        Feed source configurations to fetch from.
    storage:
        Storage backend for persisting articles and digests.
    channels:
        Delivery channels (file, email, etc.) for the final digest.
    summarize_processor:
        Processor that produces a :class:`Digest` from feed results.
        Pass ``None`` to skip summarization.
    days:
        How many days of articles to fetch (default 7).
    language:
        Target language for the generated digest (default ``zh-CN``).
    """

    def __init__(
        self,
        sources: list[SourceConfig],
        storage: BaseStorage,
        channels: list[BaseChannel] | None = None,
        summarize_processor: SummarizeProcessor | None = None,
        days: int = 7,
        language: str = "zh-CN",
    ) -> None:
        self.sources = sources
        self.storage = storage
        self.channels: list[BaseChannel] = channels or []
        self.summarize_processor = summarize_processor
        self.days = days
        self.language = language

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> Digest:
        """Execute the full pipeline: fetch -> dedup -> save -> summarize -> deliver.

        Returns the generated :class:`Digest`.
        """
        # 0. Initialize storage
        log.info("Initializing storage...")
        self.storage.initialize()

        # 1. Fetch
        log.info(f"Fetching {len(self.sources)} sources (last {self.days} days)...")
        results = fetch_sources(self.sources, days=self.days)
        total_entries = sum(len(r.entries) for r in results if r.ok)
        errors = [r.config.name for r in results if not r.ok]
        log.info(f"Fetched {total_entries} articles from {len(results)} sources")
        if errors:
            log.warning(f"Failed sources: {', '.join(errors)}")

        # 2. Dedup
        log.info("Deduplicating entries...")
        dedup = DedupProcessor(self.storage)
        results = dedup.process(results)
        new_total = sum(len(r.entries) for r in results if r.ok)
        log.info(f"{new_total} new articles after deduplication")

        # 3. Save articles
        saved = self.storage.save_articles(results)
        log.info(f"Saved {saved} new articles to storage")

        # 4. Summarize
        digest: Digest
        if self.summarize_processor is not None:
            trend_context = self.storage.generate_trend_context()
            if trend_context:
                log.info("Injecting historical trend context into summary")
            log.info("Generating AI summary...")
            digest = self.summarize_processor.process(
                results, language=self.language, trend_context=trend_context
            )
            log.info(f"Summary generated ({len(digest.content)} chars)")
        else:
            log.info("No summarizer configured; building raw digest")
            digest = self._raw_digest(results)

        # 5. Save digest
        self.storage.save_digest(digest)
        log.info("Digest saved to storage")

        # 6. Deliver via channels
        for ch in self.channels:
            log.info(f"Delivering via {ch.name} channel...")
            ok = ch.send(digest)
            if ok:
                log.info(f"Delivered via {ch.name}")
            else:
                log.error(f"Delivery via {ch.name} failed")

        return digest

    def fetch_only(self) -> list[FeedResult]:
        """Fetch and store articles only (no summarization, no delivery).

        Useful for incremental collection runs.
        """
        log.info("Initializing storage...")
        self.storage.initialize()

        log.info(f"Fetching {len(self.sources)} sources (last {self.days} days)...")
        results = fetch_sources(self.sources, days=self.days)
        total_entries = sum(len(r.entries) for r in results if r.ok)
        errors = [r.config.name for r in results if not r.ok]
        log.info(f"Fetched {total_entries} articles from {len(results)} sources")
        if errors:
            log.warning(f"Failed sources: {', '.join(errors)}")

        # Dedup
        dedup = DedupProcessor(self.storage)
        results = dedup.process(results)

        # Save
        saved = self.storage.save_articles(results)
        log.info(f"Saved {saved} new articles to storage")

        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _raw_digest(results: list[FeedResult]) -> Digest:
        """Build a plain-text digest when no summarizer is configured."""
        parts: list[str] = []
        total = 0
        for r in results:
            if r.error:
                parts.append(f"## {r.config.name} (fetch failed: {r.error})")
                continue
            if not r.entries:
                parts.append(f"## {r.config.name} (no new articles)")
                continue
            parts.append(f"## {r.config.name} ({len(r.entries)} articles)")
            for entry in r.entries:
                parts.append(f"- **{entry.title}**  \n  {entry.link}")
                total += 1
            parts.append("")
        return Digest(content="\n".join(parts), article_count=total)

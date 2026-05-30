"""Pipeline orchestration for Signal.

Coordinates: fetch -> dedup -> store -> summarize -> deliver.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from channels.base import BaseChannel
from config import DEFAULT_DAYS, DEFAULT_LANGUAGE, FETCH_MAX_WORKERS, get_int
from models import Digest, FeedResult, SourceConfig
from processors.dedup import DedupProcessor
from processors.summarizer import SummarizeProcessor
from sources.base import BaseSource
from sources.rss import RSSSource
from sources.web import WebSource
from storage.base import BaseStorage

log = logging.getLogger("signal")

_SOURCE_TYPES: dict[str, type[BaseSource]] = {
    "rss": RSSSource,
    "web": WebSource,
}


def create_source(config: SourceConfig) -> BaseSource:
    cls = _SOURCE_TYPES.get(config.source_type or "rss")
    if cls is None:
        raise ValueError(f"Unknown source type: {config.source_type}")
    return cls(config)


class Pipeline:
    """Main pipeline: fetch -> dedup -> store -> summarize -> deliver."""

    def __init__(
        self,
        sources: list[SourceConfig],
        storage: BaseStorage,
        channels: list[BaseChannel] | None = None,
        summarize_processor: SummarizeProcessor | None = None,
        days: int | None = None,
        language: str | None = None,
    ) -> None:
        self.sources = sources
        self.storage = storage
        self.channels = channels or []
        self.summarize_processor = summarize_processor
        self.days = days if days is not None else DEFAULT_DAYS
        self.language = language or DEFAULT_LANGUAGE

    def _fetch_dedup_store(self) -> list[FeedResult]:
        """Shared logic: fetch -> dedup -> store. Returns deduped results."""
        since = datetime.now(timezone.utc) - timedelta(days=self.days)
        max_workers = get_int("FETCH_MAX_WORKERS", FETCH_MAX_WORKERS)

        log.info(f"Fetching from {len(self.sources)} sources (last {self.days} days, workers={max_workers})...")
        results = self._fetch_all(since, max_workers)

        results = DedupProcessor(self.storage).process(results)

        saved = self.storage.save_articles(results)
        log.info(f"Saved {saved} new articles to knowledge base")

        return results

    def fetch_only(self) -> list[FeedResult]:
        """Fetch articles from all sources and store new ones. Returns raw results."""
        self.storage.initialize()
        try:
            return self._fetch_dedup_store()
        finally:
            self.storage.close()

    def run(self) -> Digest | None:
        """Run the full pipeline: fetch -> dedup -> store -> summarize -> deliver."""
        self.storage.initialize()
        try:
            results = self._fetch_dedup_store()

            if not self.summarize_processor:
                log.warning("No summarize processor configured, skipping summary")
                return None

            # Build knowledge context
            parts = [ctx for ctx in (
                self.storage.generate_trend_context(),
                self.storage.generate_related_context(results),
            ) if ctx]
            if parts:
                log.info(f"Injecting {len(parts)} context block(s) into summary")

            log.info("Generating AI summary...")
            digest = self.summarize_processor.process(
                results, language=self.language, trend_context="\n\n".join(parts)
            )

            for channel in self.channels:
                log.info(f"Delivering via {channel.name}...")
                try:
                    channel.send(digest)
                except Exception as e:
                    log.error(f"Channel {channel.name} failed: {e}")

            self.storage.save_digest(digest)

            # Clean up old embeddings to keep DB size manageable
            cleaned = self.storage.cleanup_old_embeddings()
            if cleaned:
                log.info(f"Cleaned {cleaned} old embeddings (kept articles)")

            return digest
        finally:
            self.storage.close()

    def _fetch_all(self, since: datetime, max_workers: int) -> list[FeedResult]:
        """Fetch all sources in parallel."""
        results: list[FeedResult] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(create_source(cfg).fetch, since): cfg
                for cfg in self.sources if cfg.enabled
            }
            for future in as_completed(futures):
                cfg = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    if result.ok:
                        log.info(f"  {cfg.name}: {len(result.entries)} entries")
                    else:
                        log.warning(f"  {cfg.name}: FAILED - {result.error}")
                except Exception as exc:
                    log.error(f"  {cfg.name}: EXCEPTION - {exc}")
                    results.append(FeedResult(config=cfg, error=str(exc)))
        return results

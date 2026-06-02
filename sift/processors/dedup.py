"""Deduplication processor - filters out articles already seen in storage."""

from __future__ import annotations

import hashlib

from config import HASH_TRUNCATE_LENGTH
from models import Entry, FeedResult

from .base import BaseProcessor


class DedupProcessor(BaseProcessor):
    """Removes entries whose hash already exists in the knowledge storage."""

    def __init__(self, storage) -> None:
        self._storage = storage

    def process(self, results: list[FeedResult], **kwargs) -> list[FeedResult]:
        """Filter out entries that have already been stored. Single batch query."""
        # Collect all hashes
        all_hashes = [
            self._hash(entry.title, entry.link)
            for result in results if result.ok and result.entries
            for entry in result.entries
        ]

        existing = self._storage.articles_exist(all_hashes) if all_hashes else set()

        return [
            FeedResult(
                config=result.config,
                entries=[e for e in result.entries if self._hash(e.title, e.link) not in existing] if result.ok and result.entries else [],
                error=result.error,
                fetch_duration=result.fetch_duration,
            )
            for result in results
        ]

    @staticmethod
    def _hash(title: str, link: str) -> str:
        return hashlib.sha256(f"{title}|{link}".encode()).hexdigest()[:HASH_TRUNCATE_LENGTH]

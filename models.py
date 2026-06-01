"""Data models for Sift layered architecture.

All dataclasses used across the pipeline: fetching, processing, digest generation, and storage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class SourceConfig:
    """Configuration for a single RSS/Atom feed source."""

    name: str
    url: str
    lang: str = "en"        # default from config.DEFAULT_SOURCE_LANG
    source_type: str = "rss"  # default from config.DEFAULT_SOURCE_TYPE
    enabled: bool = True
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)  # source-type specific config (CSS selectors, etc.)


@dataclass
class Entry:
    """A single parsed feed entry before storage."""

    title: str
    link: str
    published: datetime | None = None
    summary: str = ""
    source_name: str = ""
    source_type: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class FeedResult:
    """Result of fetching and parsing a single source."""

    config: SourceConfig
    entries: list[Entry] = field(default_factory=list)
    error: str | None = None
    fetch_duration: float = 0.0

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class Digest:
    """A generated weekly digest."""

    content: str = ""
    article_count: int = 0
    week: str = ""
    language: str = "zh-CN"  # default from config.DEFAULT_LANGUAGE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)


@dataclass
class ArticleRecord:
    """Article record for persistence in the knowledge database.

    Field types and defaults mirror the SQLite schema in knowledge.py.
    """

    id: int | None = None
    hash: str = ""
    title: str = ""
    link: str = ""
    source: str = ""
    published: str = ""
    summary: str = ""
    llm_summary: str = ""
    tags: list[str] = field(default_factory=list)
    week: str = ""
    created_at: str | None = None

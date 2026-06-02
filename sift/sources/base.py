from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from models import FeedResult, SourceConfig


class BaseSource(ABC):
    """Abstract base for all feed sources."""

    def __init__(self, config: SourceConfig) -> None:
        self.config = config

    @abstractmethod
    def fetch(self, since: datetime, **kwargs) -> FeedResult:
        """Fetch entries from this source newer than *since*."""

    @abstractmethod
    def discover(self) -> list[SourceConfig]:
        """Return a list of known sub-sources (e.g. from OPML)."""

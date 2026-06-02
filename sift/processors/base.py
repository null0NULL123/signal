"""Base processor interface for the Sift pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod

from models import Digest, FeedResult


class BaseProcessor(ABC):
    """Abstract base class for all pipeline processors."""

    @abstractmethod
    def process(self, results: list[FeedResult], **kwargs) -> list[FeedResult] | Digest:
        """Process a list of feed results and return filtered results or a digest."""
        ...

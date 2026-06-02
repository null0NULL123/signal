from __future__ import annotations

from abc import ABC, abstractmethod

from models import Digest


class BaseChannel(ABC):
    """Abstract base for all delivery channels."""

    @abstractmethod
    def send(self, digest: Digest) -> bool:
        """Send the digest via this channel. Returns True on success."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the channel identifier name."""

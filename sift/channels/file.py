from __future__ import annotations

import logging
import os
from datetime import datetime

from models import Digest

from .base import BaseChannel

log = logging.getLogger("sift")


class FileChannel(BaseChannel):
    """Save digest to a local markdown file."""

    def __init__(self, output_dir: str | None = None) -> None:
        from config import get_env, DEFAULT_OUTPUT_DIR
        self.output_dir = output_dir or get_env("OUTPUT_DIR", DEFAULT_OUTPUT_DIR)

    @property
    def name(self) -> str:
        return "file"

    def send(self, digest: Digest) -> bool:
        os.makedirs(self.output_dir, exist_ok=True)
        filepath = os.path.join(self.output_dir, f"sift-{datetime.now().strftime('%Y-%m-%d')}.md")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(digest.content)
            log.info(f"Digest saved to {filepath}")
            return True
        except OSError as e:
            log.error(f"Failed to save digest to {filepath}: {e}")
            return False

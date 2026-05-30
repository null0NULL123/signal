"""Configuration loading for Tech Pipeline.

Handles .env loading, environment variable access, and feeds.json parsing.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from models import SourceConfig

# Required environment variables that must be present after load_env()
_REQUIRED_ENV_VARS = [
    "API_BASE_URL",
    "API_KEY",
    "MODEL_NAME",
    "SMTP_SERVER",
    "SMTP_PORT",
    "SMTP_SENDER",
    "SMTP_AUTH_CODE",
    "SMTP_RECEIVER",
]

_DEFAULT_FEEDS_PATH = "feeds.json"


def load_env(env_path: str = ".env") -> None:
    """Load variables from a .env file into os.environ.

    Parses simple KEY=VALUE lines, ignoring comments and blanks.
    Does NOT override variables already set in the environment.

    Raises:
        EnvironmentError: If any required variable is missing after loading.
    """
    path = Path(env_path)
    if path.exists():
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # Don't override existing env vars
            if key and key not in os.environ:
                os.environ[key] = value

    # Validate required vars
    missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}"
        )


def get_env(key: str, default: str = "") -> str:
    """Get an environment variable with a default fallback."""
    return os.environ.get(key, default)


def load_sources(feeds_path: str = _DEFAULT_FEEDS_PATH) -> list[SourceConfig]:
    """Load feed sources from a JSON file into SourceConfig objects.

    Backward compatible with the current feeds.json format:
    [{"name": "...", "url": "...", "lang": "en"}, ...]

    Extra keys (source_type, enabled, tags) are optional and use defaults.
    """
    path = Path(feeds_path)
    if not path.exists():
        return []

    raw = json.loads(path.read_text(encoding="utf-8"))
    sources: list[SourceConfig] = []

    for item in raw:
        sources.append(SourceConfig(
            name=item.get("name", ""),
            url=item.get("url", ""),
            lang=item.get("lang", "en"),
            source_type=item.get("source_type", "rss"),
            enabled=item.get("enabled", True),
            tags=item.get("tags", []),
            metadata=item.get("metadata", {}),
        ))

    return sources


def get_summary_days() -> int:
    """Return the number of days to look back for article summaries."""
    return int(get_env("SUMMARY_DAYS", "7"))


def get_summary_language() -> str:
    """Return the target language for digest generation."""
    return get_env("SUMMARY_LANGUAGE", "zh-CN")

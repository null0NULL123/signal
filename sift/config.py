"""Configuration loading for Tech Pipeline.

Handles .env loading, environment variable access, and feeds.json parsing.
All default values and project-wide constants are defined here as single source of truth.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from sift.models import SourceConfig

# ---------------------------------------------------------------------------
# Project-wide constants (single source of truth)
# ---------------------------------------------------------------------------

# Paths
DEFAULT_FEEDS_PATH = "feeds.json"  # Fallback only; workspace feeds.json takes priority
DEFAULT_ENV_PATH = ".env"

# Source defaults
DEFAULT_SOURCE_TYPE = "rss"

# Summary defaults
DEFAULT_LANGUAGE = "zh-CN"
DEFAULT_DAYS = 7
DEFAULT_PROMPT_NAME = "tech-weekly"

# LLM parameters
DEFAULT_LLM_TEMPERATURE = 0.3
DEFAULT_LLM_MAX_TOKENS = 4096

# Text truncation limits
SUMMARY_TRUNCATE_LENGTH = 300
RSS_SUMMARY_TRUNCATE_LENGTH = 500
WEB_SUMMARY_TRUNCATE_LENGTH = 500
CONTEXT_SUMMARY_TRUNCATE_LENGTH = 150
CONTEXT_TITLE_TRUNCATE_LENGTH = 200
EMBEDDING_MAX_INPUT_LENGTH = 2000

# Hash
HASH_TRUNCATE_LENGTH = 16

# HTTP
HTTP_TIMEOUT = 15
HTTP_USER_AGENT = "Mozilla/5.0 (compatible; Sift/1.0)"

# Email
EMAIL_MAX_RETRIES = 3
EMAIL_RETRY_DELAY = 10
EMAIL_SMTP_TIMEOUT = 30

# Fetch concurrency
FETCH_MAX_WORKERS = 8

# Knowledge / semantic search
DEFAULT_EMBEDDING_DIM = 2560
RISING_TOPIC_MULTIPLIER = 1.5
RISING_TOPIC_MIN_COUNT = 2
MAX_RISING_TOPICS = 5
EMBEDDING_RETENTION_MONTHS = 12
MAX_TREND_TOPICS = 10
MAX_SEMANTIC_QUERIES = 10
MAX_KEYWORD_SEARCH = 5
MIN_KEYWORD_LENGTH = 3

# Locale strings
LOCALE = {
    "email_subject": "Sift 周报",
    "email_footer": "由 Sift 自动生成",
    "email_ai_tag": "自动摘要",
    "pages_subtitle": "从噪音中提取信号",
    "pages_description": "每周自动从高质量信息源抓取内容，生成精炼摘要。",
    "pages_footer": "由 Sift 自动生成",
    "pages_history_title": "历史周报",
    "pages_back": "← 返回目录",
    "trend_header": "历史趋势参考（供摘要参考，不输出到周报中）",
    "trend_rising": "上升趋势话题",
    "trend_frequent": "近 3 个月高频话题",
    "related_header": "相关历史文章参考（供摘要参考，不输出到周报中）",
    "related_intro": "以下是知识库中与本周文章相关的历史内容，可用于补充背景和引用。",
    "no_articles": "本周所有订阅源均无新文章发布。",
    "fetch_failed": "拉取失败",
    "no_new_articles": "本周无新文章",
    "articles_collected": "篇",
    "week_header": "以下是本周（最近 {days} 天）从 {sources} 个技术博客收集到的 {count} 篇新文章。",
    "week_prompt": "请生成一份中文技术周报。目标语言: {language}",
}

# ---------------------------------------------------------------------------
# Required environment variables
# ---------------------------------------------------------------------------

_REQUIRED_ENV_VARS = [
    "API_BASE_URL",
    "API_KEY",
    "MODEL_NAME",
]

_SMTP_ENV_VARS = [
    "SMTP_SERVER",
    "SMTP_PORT",
    "SMTP_SENDER",
    "SMTP_AUTH_CODE",
    "SMTP_RECEIVER",
]


# ---------------------------------------------------------------------------
# Environment loading
# ---------------------------------------------------------------------------


def load_env(env_path: str | None = None) -> None:
    """Load .env file into os.environ. Does NOT override existing vars."""
    path = Path(env_path or os.environ.get("ENV_PATH", DEFAULT_ENV_PATH))
    if path.exists():
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if key and key not in os.environ:
                os.environ[key] = value


def validate_env(include_smtp: bool = True) -> None:
    """Validate required env vars. Raises EnvironmentError if any are missing."""
    required = list(_REQUIRED_ENV_VARS)
    if include_smtp:
        required.extend(_SMTP_ENV_VARS)
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")


def get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def get_int(key: str, default: int) -> int:
    return int(os.environ.get(key, str(default)))


def get_float(key: str, default: float) -> float:
    return float(os.environ.get(key, str(default)))


# ---------------------------------------------------------------------------
# Feeds loading
# ---------------------------------------------------------------------------


def load_sources(feeds_path: str | None = None) -> list[SourceConfig]:
    """Load feed sources from a JSON file."""
    path = Path(feeds_path or get_env("FEEDS_PATH", DEFAULT_FEEDS_PATH))
    if not path.exists():
        return []

    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        SourceConfig(
            name=item.get("name", ""),
            url=item.get("url", ""),
            source_type=item.get("source_type", DEFAULT_SOURCE_TYPE),
            enabled=item.get("enabled", True),
            tags=item.get("tags", []),
            metadata=item.get("metadata", {}),
        )
        for item in raw
    ]


# ---------------------------------------------------------------------------
# Typed accessors
# ---------------------------------------------------------------------------


def get_summary_days() -> int:
    return get_int("SUMMARY_DAYS", DEFAULT_DAYS)


def get_summary_language() -> str:
    return get_env("SUMMARY_LANGUAGE", DEFAULT_LANGUAGE)

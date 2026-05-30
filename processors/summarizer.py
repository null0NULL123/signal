"""LLM summarizer processor - generates a Chinese tech digest from fetched entries."""

from __future__ import annotations

import os
import re
from pathlib import Path

from openai import OpenAI

from config import (
    DEFAULT_DAYS,
    DEFAULT_LANGUAGE,
    DEFAULT_LLM_MAX_TOKENS,
    DEFAULT_LLM_TEMPERATURE,
    DEFAULT_PROMPT_NAME,
    LOCALE,
    SUMMARY_TRUNCATE_LENGTH,
    get_float,
    get_int,
    get_summary_days,
)
from models import Digest, FeedResult

from .base import BaseProcessor


def _prompts_dir() -> Path:
    env_dir = os.environ.get("PROMPTS_DIR", "")
    return Path(env_dir) if env_dir else Path(__file__).parent.parent / "prompts"


def load_prompt(name: str = "") -> str:
    if not name:
        name = os.environ.get("PROMPT_NAME", DEFAULT_PROMPT_NAME)
    path = _prompts_dir() / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}. Available: {[f.stem for f in _prompts_dir().glob('*.md')]}")
    return path.read_text(encoding="utf-8").strip()


class SummarizeProcessor(BaseProcessor):
    """Calls an LLM API to generate a Chinese tech digest."""

    def __init__(
        self,
        api_key: str | None = None,
        api_base_url: str | None = None,
        model: str | None = None,
        prompt: str | None = None,
        prompt_name: str | None = None,
    ) -> None:
        self._api_key = api_key or os.environ["API_KEY"]
        self._api_base_url = api_base_url or os.environ["API_BASE_URL"]
        self._model = model or os.environ.get("MODEL_NAME", "")
        self._temperature = get_float("LLM_TEMPERATURE", DEFAULT_LLM_TEMPERATURE)
        self._max_tokens = get_int("LLM_MAX_TOKENS", DEFAULT_LLM_MAX_TOKENS)
        self._system_prompt = prompt or load_prompt(prompt_name)

    def process(self, results: list[FeedResult], language: str = "", trend_context: str = "", **kwargs) -> Digest:
        language = language or os.environ.get("SUMMARY_LANGUAGE", DEFAULT_LANGUAGE)
        user_prompt = self._build_user_prompt(results, language)

        if LOCALE["no_articles"] in user_prompt:
            return Digest(content=f"{LOCALE['no_articles']}\n", language=language)

        if trend_context:
            user_prompt = trend_context + "\n\n" + user_prompt

        client = OpenAI(api_key=self._api_key, base_url=self._api_base_url)
        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )

        return Digest(
            content=response.choices[0].message.content,
            article_count=sum(len(r.entries) for r in results if r.ok),
            language=language,
        )

    def _build_user_prompt(self, results: list[FeedResult], language: str) -> str:
        days = get_summary_days()
        parts: list[str] = []
        total = 0

        for result in results:
            if result.error:
                parts.append(f"### {result.config.name}（{LOCALE['fetch_failed']}: {result.error}）")
            elif not result.entries:
                parts.append(f"### {result.config.name}（{LOCALE['no_new_articles']}）")
            else:
                parts.append(f"### {result.config.name}（{len(result.entries)} {LOCALE['articles_collected']}）")
                for entry in result.entries:
                    parts.append(f"- **{entry.title}**")
                    if entry.summary:
                        parts.append(f"  摘要: {re.sub(r'<[^>]+>', '', entry.summary)[:SUMMARY_TRUNCATE_LENGTH]}")
                    parts.append(f"  链接: {entry.link}")
                    total += 1

        if total == 0:
            return LOCALE["no_articles"]

        header = LOCALE["week_header"].format(days=days, sources=len(results), count=total) + "\n"
        header += LOCALE["week_prompt"].format(language=language) + "\n\n"
        return header + "\n".join(parts)

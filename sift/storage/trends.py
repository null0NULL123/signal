"""Trend analysis - topic trends, rising topics, and related context."""

from __future__ import annotations

import json
import os
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from config import (
    CONTEXT_SUMMARY_TRUNCATE_LENGTH,
    CONTEXT_TITLE_TRUNCATE_LENGTH,
    LOCALE,
    MAX_RISING_TOPICS,
    MAX_SEMANTIC_QUERIES,
    MAX_TREND_TOPICS,
    MIN_KEYWORD_LENGTH,
    RISING_TOPIC_MIN_COUNT,
    RISING_TOPIC_MULTIPLIER,
)
from models import ArticleRecord, FeedResult

from .base import BaseStorage


class TrendStorage(BaseStorage):
    """Topic trend analysis and related article discovery."""

    # ------------------------------------------------------------------
    # Topic trends (aggregated from articles.tags)
    # ------------------------------------------------------------------

    def get_topic_trends(self, months: int = 3) -> list[dict]:
        db = self._get_db()
        cutoff = self._week_id(datetime.now(timezone.utc) - timedelta(days=months * 30))
        rows = db.execute(
            "SELECT tags, week FROM articles WHERE week >= ? AND tags != '[]'",
            (cutoff,),
        ).fetchall()

        topic_weeks: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for tags_json, week in rows:
            try:
                tags = json.loads(tags_json)
            except (json.JSONDecodeError, TypeError):
                continue
            for tag in tags:
                tag_lower = tag.strip().lower()
                if tag_lower:
                    topic_weeks[tag_lower][week] += 1

        trends = []
        for topic, weeks in topic_weeks.items():
            week_list = [{"week": w, "count": c} for w, c in sorted(weeks.items())]
            total = sum(c for c in weeks.values())
            trends.append({"topic": topic, "weeks": week_list, "total": total})
        return sorted(trends, key=lambda x: x["total"], reverse=True)

    def get_rising_topics(self) -> list[dict]:
        trends = self.get_topic_trends(months=2)
        rising = []
        for t in trends:
            if len(t["weeks"]) < 2:
                continue
            recent = t["weeks"][-1]["count"]
            previous = sum(w["count"] for w in t["weeks"][:-1]) / max(len(t["weeks"]) - 1, 1)
            if recent > previous * RISING_TOPIC_MULTIPLIER and recent >= RISING_TOPIC_MIN_COUNT:
                rising.append({"topic": t["topic"], "recent_count": recent, "avg_previous": round(previous, 1), "trend": "rising"})
        return rising

    def generate_trend_context(self) -> str:
        trends = self.get_topic_trends(months=3)
        rising = self.get_rising_topics()
        if not trends and not rising:
            return ""

        lines = [f"## {LOCALE['trend_header']}\n"]
        if rising:
            lines.append(f"### {LOCALE['trend_rising']}")
            for r in rising[:MAX_RISING_TOPICS]:
                lines.append(f"- {r['topic']}: 近期 {r['recent_count']} 次，此前平均 {r['avg_previous']} 次")
        if trends:
            lines.append(f"\n### {LOCALE['trend_frequent']}")
            for t in trends[:MAX_TREND_TOPICS]:
                weeks_str = ", ".join(f"{w['week']}({w['count']})" for w in t["weeks"][-4:])
                lines.append(f"- {t['topic']}: 总计 {t['total']} 次 | 近期: {weeks_str}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Related context (semantic + keyword fallback)
    # ------------------------------------------------------------------

    def generate_related_context(self, current_articles: list[FeedResult], limit: int = 8) -> str:
        current_titles: set[str] = set()
        queries: list[str] = []
        keywords: set[str] = set()

        for feed in current_articles:
            for entry in feed.entries:
                current_titles.add(entry.title)
                text = entry.title
                if entry.summary:
                    text += " " + re.sub(r"<[^>]+>", "", entry.summary)[:CONTEXT_TITLE_TRUNCATE_LENGTH]
                queries.append(text)
                for word in entry.title.split():
                    if len(word) > MIN_KEYWORD_LENGTH:
                        keywords.add(word.lower())

        if not queries:
            return ""

        # Phase 1: Batch semantic search
        related: list[ArticleRecord] = []
        if os.environ.get("EMBEDDING_API_KEY"):
            for r in self.search_similar_batch(queries[:MAX_SEMANTIC_QUERIES], limit_per_query=3):
                if r.title not in current_titles:
                    related.append(r)
                    if len(related) >= limit:
                        break

        # Phase 2: Keyword fallback
        if not related and keywords:
            for r in self.search_by_keywords(list(keywords), limit=limit):
                if r.title not in current_titles:
                    related.append(r)

        if not related:
            return ""

        lines = [f"## {LOCALE['related_header']}", f"{LOCALE['related_intro']}\n"]
        for r in related[:limit]:
            line = f"- **{r.title}**（{r.source}，{r.week}）"
            if r.summary:
                line += f"\n  {re.sub(r'<[^>]+>', '', r.summary)[:CONTEXT_SUMMARY_TRUNCATE_LENGTH]}"
            lines.append(line)
        return "\n".join(lines)

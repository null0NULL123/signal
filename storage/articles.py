"""Article storage - save, query, and search articles."""

from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone

from config import (
    CONTEXT_TITLE_TRUNCATE_LENGTH,
    MAX_KEYWORD_SEARCH,
    MAX_SEMANTIC_QUERIES,
    MIN_KEYWORD_LENGTH,
    get_int,
)
from models import ArticleRecord, Entry, FeedResult

from .base import BaseStorage


class ArticleStorage(BaseStorage):
    """Article save, query, and search operations."""

    # ------------------------------------------------------------------
    # Batch existence check
    # ------------------------------------------------------------------

    def articles_exist(self, hashes: list[str]) -> set[str]:
        """Check which hashes already exist. Single query with batched IN-clause."""
        if not hashes:
            return set()
        db = self._get_db()
        existing: set[str] = set()
        for i in range(0, len(hashes), 500):
            batch = hashes[i:i + 500]
            ph = ",".join("?" for _ in batch)
            rows = db.execute(f"SELECT hash FROM articles WHERE hash IN ({ph})", batch).fetchall()
            existing.update(r[0] for r in rows)
        return existing

    def article_exists(self, article_hash: str) -> bool:
        db = self._get_db()
        return db.execute("SELECT 1 FROM articles WHERE hash = ? LIMIT 1", (article_hash,)).fetchone() is not None

    # ------------------------------------------------------------------
    # Save operations
    # ------------------------------------------------------------------

    def save_articles(self, results: list[FeedResult]) -> int:
        """Save fetched articles. Returns count of new articles."""
        db = self._get_db()
        week = self._week_id()

        # Collect entries with hashes
        entries: list[tuple[str, str, Entry]] = []  # (hash, source_name, entry)
        for feed in results:
            if feed.error:
                continue
            for entry in feed.entries:
                entries.append((self._hash(entry.title, entry.link), feed.config.name, entry))

        if not entries:
            return 0

        # Pre-check existing (1 query instead of N)
        existing = self.articles_exist([h for h, _, _ in entries])

        # Insert new articles, collect IDs for embeddings
        article_ids: list[tuple[int, Entry]] = []
        for h, source_name, entry in entries:
            if h in existing:
                continue
            try:
                cur = db.execute(
                    "INSERT OR IGNORE INTO articles (hash, title, link, source, published, summary, week) VALUES (?,?,?,?,?,?,?)",
                    (h, entry.title, entry.link, source_name, entry.published or "", entry.summary, week),
                )
                if cur.rowcount > 0:
                    article_ids.append((cur.lastrowid, entry))
            except sqlite3.IntegrityError:
                pass

        # Batch insert embeddings (binary Float32 format, ~60% smaller than JSON)
        embed_rows = [
            (aid, self._pack_embedding(emb))
            for aid, entry in article_ids
            if (emb := self._get_embedding(f"{entry.title} {entry.summary}"))
        ]
        if embed_rows:
            db.executemany(
                "INSERT OR REPLACE INTO article_vec (article_id, embedding) VALUES (?, vec_f32(?))",
                embed_rows,
            )

        db.commit()
        return len(article_ids)

    def save_topics(self, topics: list[str], week: str | None = None) -> None:
        db = self._get_db()
        week = week or self._week_id()
        clean = [(week, t.strip().lower()) for t in topics if t.strip()]
        if not clean:
            return
        db.executemany(
            "INSERT INTO topics (week, topic, count) VALUES (?, ?, 1) ON CONFLICT(week, topic) DO UPDATE SET count = count + 1",
            clean,
        )
        db.commit()

    def cleanup_old_embeddings(self, months: int | None = None) -> int:
        """Remove embeddings older than N months. Articles are kept, only vectors are deleted."""
        from config import EMBEDDING_RETENTION_MONTHS

        months = months or get_int("EMBEDDING_RETENTION_MONTHS", EMBEDDING_RETENTION_MONTHS)
        db = self._get_db()
        cutoff_week = self._week_id(datetime.now(timezone.utc) - timedelta(days=months * 30))
        old_ids = [
            r[0] for r in db.execute(
                "SELECT a.id FROM articles a JOIN article_vec v ON a.id = v.article_id WHERE a.week < ?",
                (cutoff_week,),
            ).fetchall()
        ]
        if not old_ids:
            return 0
        for i in range(0, len(old_ids), 500):
            batch = old_ids[i:i + 500]
            ph = ",".join("?" for _ in batch)
            db.execute(f"DELETE FROM article_vec WHERE article_id IN ({ph})", batch)
        db.commit()
        return len(old_ids)

    # ------------------------------------------------------------------
    # Query operations
    # ------------------------------------------------------------------

    def get_articles(self, weeks: int = 4, source: str | None = None) -> list[ArticleRecord]:
        db = self._get_db()
        db.row_factory = sqlite3.Row
        cutoff = self._week_id(datetime.now(timezone.utc) - timedelta(weeks=weeks))
        if source:
            rows = db.execute("SELECT * FROM articles WHERE week >= ? AND source = ? ORDER BY published DESC", (cutoff, source)).fetchall()
        else:
            rows = db.execute("SELECT * FROM articles WHERE week >= ? ORDER BY published DESC", (cutoff,)).fetchall()
        db.row_factory = None
        return [self._row_to_article(r) for r in rows]

    def search_similar(self, query: str, limit: int = 5) -> list[ArticleRecord]:
        embedding = self._get_embedding(query)
        if not embedding:
            return []
        db = self._get_db()
        db.row_factory = sqlite3.Row
        rows = db.execute("""
            SELECT a.*, v.distance FROM article_vec v
            JOIN articles a ON a.id = v.article_id
            WHERE v.embedding MATCH vec_f32(?) AND k = ?
            ORDER BY v.distance ASC
        """, (self._pack_embedding(embedding), limit)).fetchall()
        db.row_factory = None
        return [self._row_to_article(r) for r in rows]

    def search_similar_batch(self, queries: list[str], limit_per_query: int = 3) -> list[ArticleRecord]:
        """Batch semantic search. Returns deduplicated results across all queries."""
        if not queries:
            return []
        db = self._get_db()
        db.row_factory = sqlite3.Row
        seen: set[int] = set()
        results: list[ArticleRecord] = []
        for query in queries:
            embedding = self._get_embedding(query)
            if not embedding:
                continue
            rows = db.execute("""
                SELECT a.*, v.distance FROM article_vec v
                JOIN articles a ON a.id = v.article_id
                WHERE v.embedding MATCH vec_f32(?) AND k = ?
                ORDER BY v.distance ASC
            """, (self._pack_embedding(embedding), limit_per_query)).fetchall()
            for r in rows:
                if r["id"] not in seen:
                    seen.add(r["id"])
                    results.append(self._row_to_article(r))
        db.row_factory = None
        return results

    def search_by_keywords(self, keywords: list[str], limit: int = 5) -> list[ArticleRecord]:
        """Keyword search in title and summary."""
        db = self._get_db()
        db.row_factory = sqlite3.Row
        conditions, params = [], []
        for kw in keywords[:MAX_KEYWORD_SEARCH]:
            conditions.append("(title LIKE ? OR summary LIKE ?)")
            params.extend([f"%{kw}%", f"%{kw}%"])
        if not conditions:
            return []
        rows = db.execute(
            f"SELECT * FROM articles WHERE {' OR '.join(conditions)} ORDER BY published DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        db.row_factory = None
        return [self._row_to_article(r) for r in rows]

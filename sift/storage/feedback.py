"""Feedback storage - user feedback on articles and preference learning."""

from __future__ import annotations

import json
import sqlite3

from models import ArticleRecord

from .base import BaseStorage


class FeedbackStorage(BaseStorage):
    """User feedback operations and preference-based recommendations."""

    # ------------------------------------------------------------------
    # Basic feedback CRUD
    # ------------------------------------------------------------------

    def set_feedback(self, article_id: int, feedback_type: str) -> bool:
        """Set feedback for an article. Returns True if added, False if already exists."""
        db = self._get_db()
        try:
            db.execute(
                "INSERT INTO article_feedback (article_id, feedback_type) VALUES (?, ?)",
                (article_id, feedback_type),
            )
            db.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def remove_feedback(self, article_id: int, feedback_type: str) -> bool:
        """Remove feedback for an article. Returns True if removed."""
        db = self._get_db()
        cur = db.execute(
            "DELETE FROM article_feedback WHERE article_id = ? AND feedback_type = ?",
            (article_id, feedback_type),
        )
        db.commit()
        return cur.rowcount > 0

    def toggle_feedback(self, article_id: int, feedback_type: str) -> bool:
        """Toggle feedback. Returns True if now active, False if removed."""
        db = self._get_db()
        existing = db.execute(
            "SELECT 1 FROM article_feedback WHERE article_id = ? AND feedback_type = ?",
            (article_id, feedback_type),
        ).fetchone()
        if existing:
            self.remove_feedback(article_id, feedback_type)
            return False
        else:
            self.set_feedback(article_id, feedback_type)
            return True

    def get_article_feedback(self, article_id: int) -> list[str]:
        """Get all feedback types for an article."""
        db = self._get_db()
        rows = db.execute(
            "SELECT feedback_type FROM article_feedback WHERE article_id = ?",
            (article_id,),
        ).fetchall()
        return [r[0] for r in rows]

    def get_feedback_articles(self, feedback_type: str, limit: int = 50) -> list[ArticleRecord]:
        """Get articles with specific feedback type."""
        db = self._get_db()
        db.row_factory = sqlite3.Row
        rows = db.execute("""
            SELECT a.* FROM articles a
            JOIN article_feedback f ON a.id = f.article_id
            WHERE f.feedback_type = ?
            ORDER BY f.created_at DESC
            LIMIT ?
        """, (feedback_type, limit)).fetchall()
        db.row_factory = None
        return [self._row_to_article(r) for r in rows]

    # ------------------------------------------------------------------
    # Feedback statistics
    # ------------------------------------------------------------------

    def get_feedback_stats(self) -> dict:
        """Get feedback statistics."""
        db = self._get_db()
        stats = {}
        for ft in ['like', 'dislike', 'bookmark']:
            count = db.execute(
                "SELECT COUNT(*) FROM article_feedback WHERE feedback_type = ?",
                (ft,),
            ).fetchone()[0]
            stats[ft] = count
        return stats

    # ------------------------------------------------------------------
    # Preference analysis
    # ------------------------------------------------------------------

    def get_liked_sources(self, limit: int = 10) -> list[dict]:
        """Get top sources from liked articles."""
        db = self._get_db()
        rows = db.execute("""
            SELECT a.source, COUNT(*) as cnt
            FROM article_feedback f
            JOIN articles a ON a.id = f.article_id
            WHERE f.feedback_type = 'like'
            GROUP BY a.source
            ORDER BY cnt DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [{"source": r[0], "count": r[1]} for r in rows]

    def get_liked_tags(self, limit: int = 20) -> list[dict]:
        """Get top tags from liked articles."""
        db = self._get_db()
        rows = db.execute("""
            SELECT a.tags, COUNT(*) as cnt
            FROM article_feedback f
            JOIN articles a ON a.id = f.article_id
            WHERE f.feedback_type = 'like' AND a.tags != '[]'
            GROUP BY a.tags
            ORDER BY cnt DESC
            LIMIT ?
        """, (limit,)).fetchall()

        # Flatten and count individual tags
        tag_counts: dict[str, int] = {}
        for r in rows:
            tags = json.loads(r[0])
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + r[1]

        return sorted(
            [{"tag": t, "count": c} for t, c in tag_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:limit]

    # ------------------------------------------------------------------
    # Recommendations
    # ------------------------------------------------------------------

    def get_recommended_articles(self, limit: int = 20) -> list[ArticleRecord]:
        """Get recommended articles based on feedback patterns."""
        db = self._get_db()

        # Get liked sources and tags
        liked_sources = [r["source"] for r in self.get_liked_sources(5)]
        liked_tags = [r["tag"] for r in self.get_liked_tags(10)]

        if not liked_sources and not liked_tags:
            return []

        # Get already feedbacked article IDs to exclude
        feedbacked_ids = [
            r[0] for r in db.execute(
                "SELECT DISTINCT article_id FROM article_feedback"
            ).fetchall()
        ]

        conditions = []
        params = []

        if liked_sources:
            ph = ",".join("?" for _ in liked_sources)
            conditions.append(f"a.source IN ({ph})")
            params.extend(liked_sources)

        if liked_tags:
            for tag in liked_tags:
                conditions.append("a.tags LIKE ?")
                params.append(f"%{tag}%")

        if not conditions:
            return []

        # Exclude already feedbacked articles
        exclude_clause = ""
        if feedbacked_ids:
            ph = ",".join("?" for _ in feedbacked_ids)
            exclude_clause = f"AND a.id NOT IN ({ph})"
            params.extend(feedbacked_ids)

        where_clause = " OR ".join(conditions)
        query = f"""
            SELECT a.* FROM articles a
            WHERE ({where_clause}) {exclude_clause}
            ORDER BY a.published DESC
            LIMIT ?
        """
        params.append(limit)

        db.row_factory = sqlite3.Row
        rows = db.execute(query, params).fetchall()
        db.row_factory = None
        return [self._row_to_article(r) for r in rows]

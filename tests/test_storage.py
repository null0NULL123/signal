"""Storage layer tests - covers base, articles, dashboard, feedback, trends."""

from __future__ import annotations

import os
import tempfile

from base import make_entry, make_feed, temp_db
from config import LOCALE
from models import Digest
from storage.knowledge import KnowledgeStorage


# ------------------------------------------------------------------
# Connection lifecycle
# ------------------------------------------------------------------

def test_memory_db():
    """Test with in-memory DB (fast, no cleanup needed)."""
    ks = KnowledgeStorage(db_path=":memory:")
    ks.initialize()

    # Schema created
    db = ks._get_db()
    tables = {r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert {"articles", "digests", "article_feedback"} <= tables

    # Empty state
    assert ks.get_articles(weeks=1) == []
    assert ks.get_feedback_stats() == {"like": 0, "dislike": 0, "bookmark": 0}

    ks.close()


def test_save_and_query():
    with temp_db() as ks:
        feed = make_feed([
            make_entry("Article One", summary="Summary one"),
            make_entry("Article Two", summary="Summary two"),
        ])

        saved = ks.save_articles([feed])
        assert saved == 2

        saved2 = ks.save_articles([feed])
        assert saved2 == 0

        articles = ks.get_articles(weeks=1)
        assert len(articles) == 2
        assert articles[0].title in ("Article One", "Article Two")


def test_batch_exist():
    with temp_db() as ks:
        assert ks.articles_exist([]) == set()

        feed = make_feed([make_entry("X")])
        ks.save_articles([feed])

        h = ks._hash("X", "http://test/x")
        assert h in ks.articles_exist([h])
        assert "nonexistent" not in ks.articles_exist(["nonexistent"])


def test_keyword_search():
    with temp_db() as ks:
        feed = make_feed([
            make_entry("SQLite is great"),
            make_entry("PostgreSQL tips"),
            make_entry("SQLite advanced"),
        ])
        ks.save_articles([feed])

        results = ks.search_by_keywords(["SQLite"])
        assert len(results) == 2
        titles = {r.title for r in results}
        assert "SQLite is great" in titles
        assert "SQLite advanced" in titles


def test_topics():
    with temp_db() as ks:
        # Tags come from articles, not a separate topics table
        e1 = make_entry("Article A")
        e1.tags = ["AI", "LLM"]
        e2 = make_entry("Article B")
        e2.tags = ["AI", "Rust"]
        feed = make_feed([e1, e2])
        ks.save_articles([feed])

        trends = ks.get_topic_trends(months=1)
        assert len(trends) >= 2
        ai_topic = next((t for t in trends if t["topic"] == "ai"), None)
        assert ai_topic is not None
        assert ai_topic["total"] == 2


def test_all_tags():
    with temp_db() as ks:
        assert ks.get_all_tags() == []

        e1 = make_entry("Article A")
        e1.tags = ["AI", "LLM"]
        e2 = make_entry("Article B")
        e2.tags = ["AI", "Rust"]
        feed = make_feed([e1, e2])
        ks.save_articles([feed])

        tags = ks.get_all_tags()
        assert len(tags) == 3
        ai_tag = next(t for t in tags if t["tag"] == "ai")
        assert ai_tag["count"] == 2
        rust_tag = next(t for t in tags if t["tag"] == "rust")
        assert rust_tag["count"] == 1


def test_digest():
    from models import Digest
    with temp_db() as ks:
        d = Digest(content="test digest", article_count=5)
        ks.save_digest(d)

        db = ks._get_db()
        row = db.execute("SELECT content, article_count FROM digests").fetchone()
        assert row[0] == "test digest"
        assert row[1] == 5


def test_trend_context():
    with temp_db() as ks:
        assert ks.generate_trend_context() == ""

        e1 = make_entry("Article A")
        e1.tags = ["AI", "LLM"]
        e2 = make_entry("Article B")
        e2.tags = ["AI", "Rust"]
        feed = make_feed([e1, e2])
        ks.save_articles([feed])

        ctx = ks.generate_trend_context()
        assert LOCALE["trend_rising"] in ctx or LOCALE["trend_frequent"] in ctx


def test_related_context():
    with temp_db() as ks:
        old_feed = make_feed([
            make_entry("Old SQLite article"),
            make_entry("Old Rust article"),
        ])
        ks.save_articles([old_feed])

        current_feed = make_feed([make_entry("New SQLite feature")])
        ctx = ks.generate_related_context([current_feed])
        assert "SQLite" in ctx


def test_feedback():
    with temp_db() as ks:
        feed = make_feed([make_entry("Test Article")])
        ks.save_articles([feed])

        articles = ks.get_articles(weeks=1)
        assert len(articles) == 1
        article_id = articles[0].id

        # Toggle add
        assert ks.toggle_feedback(article_id, "like") is True
        feedback = ks.get_article_feedback(article_id)
        assert feedback == ["like"]

        # Toggle remove
        assert ks.toggle_feedback(article_id, "like") is False
        assert ks.get_article_feedback(article_id) == []

        # Multiple types
        ks.set_feedback(article_id, "like")
        ks.set_feedback(article_id, "bookmark")
        feedback = ks.get_article_feedback(article_id)
        assert set(feedback) == {"like", "bookmark"}

        # Stats
        stats = ks.get_feedback_stats()
        assert stats["like"] == 1
        assert stats["bookmark"] == 1
        assert stats["dislike"] == 0

        # Get feedback articles
        liked = ks.get_feedback_articles("like")
        assert len(liked) == 1
        assert liked[0].title == "Test Article"


TESTS = [
    ("memory db", test_memory_db),
    ("save and query", test_save_and_query),
    ("batch exist", test_batch_exist),
    ("keyword search", test_keyword_search),
    ("topics", test_topics),
    ("all tags", test_all_tags),
    ("digest", test_digest),
    ("trend context", test_trend_context),
    ("related context", test_related_context),
    ("feedback", test_feedback),
]

"""Base storage - connection management, schema, and shared helpers."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import struct
from datetime import datetime, timezone
from pathlib import Path

import sqlite_vec

from config import (
    DEFAULT_DB_PATH,
    DEFAULT_EMBEDDING_DIM,
    EMBEDDING_MAX_INPUT_LENGTH,
    HASH_TRUNCATE_LENGTH,
    get_env,
    get_int,
)
from models import ArticleRecord


class BaseStorage:
    """Base class for storage modules. Manages DB connection and shared helpers."""

    def __init__(self, db_path: str | None = None) -> None:
        self._conn: sqlite3.Connection | None = None
        self._db_path = db_path

    def _get_db(self) -> sqlite3.Connection:
        """Get database connection with sqlite-vec loaded. Reuses connection within a run."""
        if self._conn is not None:
            return self._conn
        db_path = self._db_path or get_env("DB_PATH", DEFAULT_DB_PATH)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(db_path, check_same_thread=False)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=NORMAL")
        db.execute("PRAGMA cache_size=-8000")
        db.execute("PRAGMA temp_store=MEMORY")
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
        self._conn = db
        return db

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def initialize(self) -> None:
        """Initialize database schema and vector table."""
        db = self._get_db()
        # Migrate: add llm_summary column if missing
        try:
            db.execute("ALTER TABLE articles ADD COLUMN llm_summary TEXT")
        except Exception:
            pass  # Column already exists
        db.executescript("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                link TEXT NOT NULL,
                source TEXT NOT NULL,
                published TEXT,
                summary TEXT,
                llm_summary TEXT,
                tags TEXT DEFAULT '[]',
                week TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS digests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                article_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS article_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                feedback_type TEXT NOT NULL CHECK(feedback_type IN ('like', 'dislike', 'bookmark')),
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (article_id) REFERENCES articles(id),
                UNIQUE(article_id, feedback_type)
            );
            CREATE INDEX IF NOT EXISTS idx_articles_week ON articles(week);
            CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
            CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published);
            CREATE INDEX IF NOT EXISTS idx_feedback_article ON article_feedback(article_id);
            CREATE INDEX IF NOT EXISTS idx_feedback_type ON article_feedback(feedback_type);
        """)
        dim = get_int("EMBEDDING_DIM", DEFAULT_EMBEDDING_DIM)
        db.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS article_vec USING vec0(
                article_id INTEGER PRIMARY KEY,
                embedding float[{dim}]
            )
        """)
        db.commit()

    # ------------------------------------------------------------------
    # Hash & time helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hash(title: str, link: str) -> str:
        return hashlib.sha256(f"{title}|{link}".encode()).hexdigest()[:HASH_TRUNCATE_LENGTH]

    @staticmethod
    def _week_id(dt: datetime | None = None) -> str:
        if dt is None:
            dt = datetime.now(timezone.utc)
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"

    @staticmethod
    def _row_to_article(r: sqlite3.Row) -> ArticleRecord:
        return ArticleRecord(
            id=r["id"], hash=r["hash"], title=r["title"], link=r["link"],
            source=r["source"], published=r["published"],
            summary=r["summary"], llm_summary=r["llm_summary"] if "llm_summary" in r.keys() else "",
            tags=json.loads(r["tags"]) if r["tags"] else [],
            week=r["week"], created_at=r["created_at"],
        )

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    def _get_embedding(self, text: str) -> list[float] | None:
        try:
            from openai import OpenAI

            api_key = os.environ.get("EMBEDDING_API_KEY", "")
            base_url = os.environ.get("EMBEDDING_API_BASE_URL", "")
            model = os.environ.get("EMBEDDING_MODEL", "")
            if not (api_key and base_url and model):
                return None
            client = OpenAI(api_key=api_key, base_url=base_url)
            response = client.embeddings.create(model=model, input=text[:EMBEDDING_MAX_INPUT_LENGTH])
            return response.data[0].embedding
        except Exception:
            return None

    @staticmethod
    def _pack_embedding(emb: list[float]) -> bytes:
        """Serialize embedding to compact binary (Float32 array)."""
        return struct.pack(f"{len(emb)}f", *emb)

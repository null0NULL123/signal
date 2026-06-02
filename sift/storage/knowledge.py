"""Knowledge accumulation storage - unified entry point.

Combines article, feedback, trend, and dashboard modules into a single interface.
Uses SQLite + sqlite-vec for structured + vector queries in a single .db file.
"""

from __future__ import annotations

from models import ArticleRecord, Digest, FeedResult

from .articles import ArticleStorage
from .dashboard import DashboardStorage
from .feedback import FeedbackStorage
from .trends import TrendStorage


class KnowledgeStorage(ArticleStorage, FeedbackStorage, TrendStorage, DashboardStorage):
    """SQLite + sqlite-vec storage backend for the knowledge base.

    Inherits all functionality from specialized modules:
    - ArticleStorage: article CRUD, search, and embeddings
    - FeedbackStorage: user feedback and recommendations
    - TrendStorage: topic trend analysis and related context
    - DashboardStorage: stats, digests, and preferences
    """

    pass

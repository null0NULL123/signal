"""Pipeline tests - covers run(), fetch_only(), and error handling."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from base import make_entry, make_feed, make_source, temp_db
from config import DEFAULT_DAYS, DEFAULT_LANGUAGE
from models import Digest, FeedResult
from pipeline import Pipeline, create_source


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _mock_source(*feeds: FeedResult) -> MagicMock:
    """Create a mock source that returns feeds in sequence."""
    mock = MagicMock()
    mock.fetch.side_effect = list(feeds)
    return mock


def _mock_summarizer(content: str = "test", article_count: int = 1, returns_none: bool = False) -> MagicMock:
    """Create a mock summarizer."""
    mock = MagicMock()
    mock.process.return_value = None if returns_none else Digest(content=content, article_count=article_count)
    return mock


def _make_pipeline(storage, sources=None, summarizer=None, channels=None, **kwargs):
    """Helper to create pipeline with common setup."""
    if sources is None:
        sources = [make_source()]
    return Pipeline(
        sources=sources,
        storage=storage,
        channels=channels or [],
        summarize_processor=summarizer,
        **kwargs,
    )


# ------------------------------------------------------------------
# create_source
# ------------------------------------------------------------------

def test_create_source():
    rss = create_source(make_source())
    assert type(rss).__name__ == "RSSSource"

    web = create_source(make_source(url="http://x", source_type="web"))
    assert type(web).__name__ == "WebSource"

    try:
        create_source(make_source(source_type="unknown"))
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


# ------------------------------------------------------------------
# Pipeline init
# ------------------------------------------------------------------

def test_pipeline_init():
    p = Pipeline(sources=[], storage=None)
    assert p.days == DEFAULT_DAYS
    assert p.language == DEFAULT_LANGUAGE
    assert p.channels == []

    p2 = Pipeline(sources=[], storage=None, days=3, language="en")
    assert p2.days == 3
    assert p2.language == "en"


# ------------------------------------------------------------------
# Pipeline.run() - happy path
# ------------------------------------------------------------------

def test_run_full_pipeline():
    """Full pipeline: fetch -> dedup -> store -> summarize -> deliver."""
    with temp_db() as storage:
        feed = make_feed([
            make_entry("Article A", summary="Summary A"),
            make_entry("Article B", summary="Summary B"),
        ])
        source = _mock_source(feed)
        summarizer = _mock_summarizer("# Weekly Digest\n\n- A\n- B", article_count=2)

        channel = MagicMock()
        channel.name = "test"

        p = _make_pipeline(storage, summarizer=summarizer, channels=[channel])
        with patch("pipeline.create_source", return_value=source):
            result = p.run()

        # Result
        assert result is not None
        assert result.content == "# Weekly Digest\n\n- A\n- B"
        assert result.article_count == 2

        # Mock calls
        source.fetch.assert_called_once()
        summarizer.process.assert_called_once()
        channel.send.assert_called_once_with(result)

        # Storage
        assert len(storage.get_articles(weeks=1)) == 2
        assert len(storage.get_digests(limit=1)) == 1


def test_run_multiple_sources():
    """Multiple sources fetch in parallel."""
    with temp_db() as storage:
        def create_for_config(cfg):
            mock = MagicMock()
            if cfg.name == "Source A":
                mock.fetch.return_value = make_feed([make_entry("A1"), make_entry("A2")], source_name="Source A")
            else:
                mock.fetch.return_value = make_feed([make_entry("B1")], source_name="Source B")
            return mock

        summarizer = _mock_summarizer(article_count=3)
        sources = [make_source("Source A", "http://a"), make_source("Source B", "http://b")]
        p = _make_pipeline(storage, sources=sources, summarizer=summarizer)

        with patch("pipeline.create_source", side_effect=create_for_config):
            result = p.run()

        assert result is not None
        assert len(storage.get_articles(weeks=1)) == 3


# ------------------------------------------------------------------
# Pipeline.run() - edge cases
# ------------------------------------------------------------------

def test_run_no_summarizer():
    """Without summarizer: fetch and store only, return None."""
    with temp_db() as storage:
        source = _mock_source(make_feed([make_entry("Article X")]))
        p = _make_pipeline(storage, summarizer=None)
        with patch("pipeline.create_source", return_value=source):
            result = p.run()

        assert result is None
        assert len(storage.get_articles(weeks=1)) == 1


def test_run_summarizer_returns_none():
    """Summarizer returns None (e.g., no articles to summarize)."""
    with temp_db() as storage:
        source = _mock_source(FeedResult(config=make_source(), entries=[]))
        summarizer = _mock_summarizer(returns_none=True)
        p = _make_pipeline(storage, summarizer=summarizer)
        with patch("pipeline.create_source", return_value=source):
            result = p.run()

        assert result is None
        summarizer.process.assert_called_once()


def test_run_channel_failure_continues():
    """Pipeline continues when one channel fails."""
    with temp_db() as storage:
        source = _mock_source(make_feed([make_entry("Test")]))

        failing = MagicMock()
        failing.name = "failing"
        failing.send.side_effect = RuntimeError("Connection failed")

        success = MagicMock()
        success.name = "success"

        summarizer = _mock_summarizer()
        p = _make_pipeline(storage, summarizer=summarizer, channels=[failing, success])
        with patch("pipeline.create_source", return_value=source):
            result = p.run()

        assert result is not None
        failing.send.assert_called_once()
        success.send.assert_called_once()


# ------------------------------------------------------------------
# Pipeline.run() - context injection
# ------------------------------------------------------------------

def test_run_injects_trend_context():
    """Trend context from history is passed to summarizer."""
    with temp_db() as storage:
        # Historical data with tags
        old = make_feed([make_entry("Old AI Article")])
        old.entries[0].tags = ["AI", "LLM"]
        storage.save_articles([old])

        # New data
        new = make_feed([make_entry("New AI Article")])
        new.entries[0].tags = ["AI"]
        source = _mock_source(new)

        summarizer = _mock_summarizer()
        p = _make_pipeline(storage, summarizer=summarizer)
        with patch("pipeline.create_source", return_value=source):
            p.run()

        # Verify context was passed
        call_kwargs = summarizer.process.call_args[1]
        trend_ctx = call_kwargs.get("trend_context", "")
        assert len(trend_ctx) > 0  # Should have context from history


# ------------------------------------------------------------------
# Pipeline.fetch_only()
# ------------------------------------------------------------------

def test_fetch_only():
    """fetch_only: fetch and store without summarizing."""
    with temp_db() as storage:
        source = _mock_source(make_feed([make_entry("Fetch Article")]))
        p = _make_pipeline(storage, summarizer=None)
        with patch("pipeline.create_source", return_value=source):
            results = p.fetch_only()

        assert len(results) == 1
        assert results[0].entries[0].title == "Fetch Article"
        assert len(storage.get_articles(weeks=1)) == 1


def test_fetch_only_dedup():
    """Second fetch of same articles is deduped."""
    with temp_db() as storage:
        feed = make_feed([make_entry("Dedup Test")])
        source = _mock_source(feed, feed)
        p = _make_pipeline(storage, summarizer=None)
        with patch("pipeline.create_source", return_value=source):
            p.fetch_only()
            p.fetch_only()

        assert len(storage.get_articles(weeks=1)) == 1


# ------------------------------------------------------------------
# Disabled source
# ------------------------------------------------------------------

def test_disabled_source_skipped():
    """Disabled sources are not fetched."""
    with temp_db() as storage:
        source = _mock_source(make_feed([make_entry("Enabled")]))

        sources = [
            make_source("Enabled", "http://e", enabled=True),
            make_source("Disabled", "http://d", enabled=False),
        ]
        call_count = 0
        def counting_create(cfg):
            nonlocal call_count
            call_count += 1
            return source

        p = _make_pipeline(storage, sources=sources, summarizer=None)
        with patch("pipeline.create_source", side_effect=counting_create):
            p.fetch_only()

        assert call_count == 1


TESTS = [
    ("create_source", test_create_source),
    ("Pipeline init", test_pipeline_init),
    ("run full pipeline", test_run_full_pipeline),
    ("run multiple sources", test_run_multiple_sources),
    ("run no summarizer", test_run_no_summarizer),
    ("run summarizer returns none", test_run_summarizer_returns_none),
    ("run channel failure continues", test_run_channel_failure_continues),
    ("run injects trend context", test_run_injects_trend_context),
    ("fetch_only", test_fetch_only),
    ("fetch_only dedup", test_fetch_only_dedup),
    ("disabled source skipped", test_disabled_source_skipped),
]

"""Models tests."""

from __future__ import annotations

from base import make_entry, make_feed, make_source
from sift.models import Digest, Entry, FeedResult, SourceConfig


def test_source_config():
    sc = make_source()
    assert sc.name == "Test"
    assert sc.source_type == "rss"
    assert sc.enabled is True
    assert sc.tags == []
    assert sc.metadata == {}


def test_entry():
    e = make_entry("Hello")
    assert e.title == "Hello"
    assert e.summary == ""
    assert e.published is not None


def test_feed_result():
    feed = make_feed([])
    assert feed.ok is True
    assert feed.entries == []

    cfg = make_source()
    r2 = FeedResult(config=cfg, error="fail")
    assert r2.ok is False


def test_digest():
    d = Digest(content="hello", language="zh-CN")
    assert d.content == "hello"
    assert d.article_count == 0


TESTS = [
    ("SourceConfig", test_source_config),
    ("Entry", test_entry),
    ("FeedResult", test_feed_result),
    ("Digest", test_digest),
]

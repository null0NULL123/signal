"""Config module tests."""

from __future__ import annotations

import os

from base import env_vars, temp_file, temp_json
from config import (
    DEFAULT_SOURCE_LANG,
    DEFAULT_SOURCE_TYPE,
    get_env,
    get_float,
    get_int,
    load_env,
    load_sources,
)


def test_get_env():
    with env_vars(_TEST_STR="hello", _TEST_INT="42", _TEST_FLOAT="3.14"):
        assert get_env("_TEST_STR") == "hello"
        assert get_env("_TEST_MISSING", "default") == "default"

        assert get_int("_TEST_INT", 0) == 42
        assert get_int("_TEST_MISSING", 99) == 99

        assert get_float("_TEST_FLOAT", 0.0) == 3.14
        assert get_float("_TEST_MISSING", 1.5) == 1.5


def test_load_env():
    content = "\n".join([
        "# comment",
        "API_BASE_URL=https://test.api.com/v1",
        "API_KEY=test-key",
        "MODEL_NAME=test-model",
        "SMTP_SERVER=smtp.test.com",
        "SMTP_PORT=587",
        "SMTP_SENDER=test@test.com",
        "SMTP_AUTH_CODE=test-code",
        "SMTP_RECEIVER=test@test.com",
        "EXTRA_VAR=extra-value",
    ])

    keys = ["API_BASE_URL", "API_KEY", "MODEL_NAME", "SMTP_SERVER",
            "SMTP_PORT", "SMTP_SENDER", "SMTP_AUTH_CODE", "SMTP_RECEIVER", "EXTRA_VAR"]

    with temp_file(content, suffix=".env") as tmp_path:
        saved = {k: os.environ.pop(k, None) for k in keys}
        try:
            load_env(tmp_path)
            assert os.environ["API_BASE_URL"] == "https://test.api.com/v1"
            assert os.environ["EXTRA_VAR"] == "extra-value"
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v
                else:
                    os.environ.pop(k, None)


def test_load_sources():
    data = [
        {"name": "Test Blog", "url": "https://example.com/rss"},
        {"name": "Web Source", "url": "https://example.com", "source_type": "web", "lang": "zh"},
    ]

    with temp_json(data) as tmp_path:
        sources = load_sources(tmp_path)
        assert len(sources) == 2
        assert sources[0].name == "Test Blog"
        assert sources[0].lang == DEFAULT_SOURCE_LANG
        assert sources[0].source_type == DEFAULT_SOURCE_TYPE
        assert sources[1].source_type == "web"
        assert sources[1].lang == "zh"


TESTS = [
    ("get_env/get_int/get_float", test_get_env),
    ("load_env", test_load_env),
    ("load_sources", test_load_sources),
]

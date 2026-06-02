"""Channels tests."""

from __future__ import annotations

import os
import smtplib
from pathlib import Path

from base import env_vars, temp_dir
from sift.channels.email import EmailChannel
from sift.channels.file import FileChannel
from sift.channels.github_pages import GitHubPagesChannel
from sift.models import Digest

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass


def test_file_channel():
    with temp_dir() as tmpdir:
        ch = FileChannel(output_dir=str(tmpdir))
        assert ch.name == "file"

        d = Digest(content="# Test\nHello world")
        assert ch.send(d) is True

        files = list(tmpdir.glob("*.md"))
        assert len(files) == 1
        assert "sift-" in files[0].name
        assert files[0].read_text() == "# Test\nHello world"


def test_github_pages_channel():
    with temp_dir() as tmpdir:
        with env_vars(GITHUB_PAGES_DIR=str(tmpdir)):
            ch = GitHubPagesChannel()
            assert ch.name == "github_pages"

            d = Digest(content="# Hello\n\nTest content")
            assert ch.send(d) is True

            digests_dir = tmpdir / "digests"
            assert digests_dir.exists()
            html_files = list(digests_dir.glob("*.html"))
            assert len(html_files) == 1
            assert "Hello" in html_files[0].read_text()
            assert "article-page" in html_files[0].read_text()


def test_email_channel():
    """Test EmailChannel initialization and message building (no actual send)."""
    with env_vars(SMTP_SENDER="test@example.com", SMTP_AUTH_CODE="test-password", SMTP_RECEIVER="receiver@example.com"):
        ch = EmailChannel(smtp_server="smtp.example.com", smtp_port=587)
        assert ch.name == "email"
        assert ch.smtp_server == "smtp.example.com"
        assert ch.sender == "test@example.com"
        assert ch.receiver == "receiver@example.com"

        d = Digest(content="# Digest Title\n\n- Article 1\n- Article 2\n\n---\nFooter")
        msg = ch._build_message(d.content)

        assert "Sift" in msg["Subject"]
        assert msg["From"] == "test@example.com"
        assert msg["To"] == "receiver@example.com"

        html_content = None
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html_content = part.get_payload(decode=True).decode()
                break

        assert html_content is not None
        assert "<h1" in html_content
        assert "Article 1" in html_content
        assert "<hr" in html_content


def test_email_send_real():
    """Test SMTP connection and auth only (no actual email sent)."""
    required = ["SMTP_SERVER", "SMTP_SENDER", "SMTP_AUTH_CODE"]
    if not all(os.environ.get(k) for k in required):
        return

    ch = EmailChannel()
    with smtplib.SMTP(ch.smtp_server, ch.smtp_port, timeout=ch._timeout) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(ch.sender, ch.auth_code)


TESTS = [
    ("FileChannel", test_file_channel),
    ("GitHubPagesChannel", test_github_pages_channel),
    ("EmailSend", test_email_send_real),
    ("EmailChannel", test_email_channel),
]

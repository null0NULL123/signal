"""GitHub Pages channel - saves digest as HTML for static site hosting."""

from __future__ import annotations

import os
import re
import logging
from datetime import datetime
from pathlib import Path

from channels.base import BaseChannel
from config import LOCALE, get_env
from models import Digest

log = logging.getLogger("sift")


def _docs_dir() -> Path:
    env_dir = os.environ.get("GITHUB_PAGES_DIR", "")
    return Path(env_dir) if env_dir else Path(__file__).parent.parent / "site"


class GitHubPagesChannel(BaseChannel):
    """Saves digest as a styled HTML page and updates the index."""

    @property
    def name(self) -> str:
        return "github_pages"

    def send(self, digest: Digest) -> bool:
        try:
            digests_dir = _docs_dir() / "digests"
            digests_dir.mkdir(parents=True, exist_ok=True)

            date_str = datetime.now().strftime("%Y-%m-%d")
            filepath = digests_dir / f"{date_str}.html"
            filepath.write_text(self._render_digest(digest, date_str), encoding="utf-8")
            log.info(f"Saved digest page to {filepath}")

            self._update_index(digests_dir)
            return True
        except Exception as e:
            log.error(f"GitHub Pages save failed: {e}")
            return False

    def _render_digest(self, digest: Digest, date_str: str) -> str:
        body = self._md_to_html(digest.content)
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sift - {date_str}</title>
  <link rel="stylesheet" href="../style.css">
</head>
<body>
  <div class="container">
    <header>
      <h1>Sift</h1>
      <p class="date">{date_str} | {LOCALE['email_ai_tag']}</p>
      <nav><a href="../index.html">{LOCALE['pages_back']}</a></nav>
    </header>
    <article>{body}</article>
    <footer><p>{LOCALE['pages_footer']}</p></footer>
  </div>
</body>
</html>"""

    def _update_index(self, digests_dir: Path) -> None:
        docs_dir = digests_dir.parent
        digests = sorted(digests_dir.glob("*.html"), reverse=True)
        entries = [{"date": f.stem, "file": f"digests/{f.name}"} for f in digests]

        items = "\n".join(f'    <li><a href="{e["file"]}">{e["date"]}</a></li>' for e in entries)
        index_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sift - {LOCALE['email_subject']}</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="container">
    <header>
      <h1>Sift</h1>
      <p class="subtitle">{LOCALE['pages_subtitle']}</p>
      <p class="description">{LOCALE['pages_description']}</p>
    </header>
    <main>
      <h2>{LOCALE['pages_history_title']}</h2>
      <ul class="digest-list">
{items}
      </ul>
    </main>
    <footer><p>{LOCALE['pages_footer']} | <a href="{get_env('GITHUB_REPO_URL', '#')}">GitHub</a></p></footer>
  </div>
</body>
</html>"""
        (docs_dir / "index.html").write_text(index_html, encoding="utf-8")
        log.info(f"Updated index with {len(entries)} digests")

    @staticmethod
    def _md_to_html(md_text: str) -> str:
        """Convert markdown to HTML for web page display."""
        lines = md_text.split("\n")
        html_lines = []
        in_list = False

        for line in lines:
            if line.startswith("## "):
                if in_list:
                    html_lines.append("</ul>"); in_list = False
                html_lines.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("### "):
                if in_list:
                    html_lines.append("</ul>"); in_list = False
                html_lines.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith("# "):
                if in_list:
                    html_lines.append("</ul>"); in_list = False
                html_lines.append(f"<h1>{line[2:]}</h1>")
            elif line.strip() == "---":
                if in_list:
                    html_lines.append("</ul>"); in_list = False
                html_lines.append("<hr>")
            else:
                line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
                line = re.sub(r"`([^`]+)`", r"<code>\1</code>", line)
                line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', line)

                if line.startswith("- ") or line.startswith("* "):
                    if not in_list:
                        html_lines.append("<ul>"); in_list = True
                    html_lines.append(f"<li>{line[2:]}</li>")
                elif re.match(r"^\d+\.\s", line):
                    html_lines.append(f"<p class='numbered'>{line}</p>")
                elif line.strip() == "":
                    if in_list:
                        html_lines.append("</ul>"); in_list = False
                    html_lines.append("")
                else:
                    if in_list:
                        html_lines.append("</ul>"); in_list = False
                    html_lines.append(f"<p>{line}</p>")

        if in_list:
            html_lines.append("</ul>")
        return "\n".join(html_lines)

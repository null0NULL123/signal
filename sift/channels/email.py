from __future__ import annotations

import logging
import os
import re
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import LOCALE, get_int
from models import Digest

from .base import BaseChannel

log = logging.getLogger("sift")


class EmailChannel(BaseChannel):
    """Send digest via SMTP email."""

    def __init__(
        self,
        smtp_server: str | None = None,
        smtp_port: int | None = None,
        sender: str | None = None,
        auth_code: str | None = None,
        receiver: str | None = None,
    ) -> None:
        self.smtp_server = smtp_server or os.environ.get("SMTP_SERVER", "")
        self.smtp_port = smtp_port or get_int("SMTP_PORT", 587)
        self.sender = sender or os.environ["SMTP_SENDER"]
        self.auth_code = auth_code or os.environ["SMTP_AUTH_CODE"]
        self.receiver = receiver or os.environ["SMTP_RECEIVER"]
        self._timeout = get_int("EMAIL_SMTP_TIMEOUT", 30)

    @property
    def name(self) -> str:
        return "email"

    def send(self, digest: Digest) -> bool:
        max_retries = get_int("EMAIL_MAX_RETRIES", 3)
        retry_delay = get_int("EMAIL_RETRY_DELAY", 10)
        msg = self._build_message(digest.content)
        payload = msg.as_string()

        for attempt in range(1, max_retries + 1):
            try:
                log.info(f"Sending email (attempt {attempt}/{max_retries})...")
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=self._timeout) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(self.sender, self.auth_code)
                    server.sendmail(self.sender, [self.receiver], payload)
                log.info("Email sent successfully")
                return True
            except (smtplib.SMTPServerDisconnected, TimeoutError, OSError) as e:
                log.warning(f"Attempt {attempt}/{max_retries} failed: {type(e).__name__}: {e}")
                if attempt < max_retries:
                    log.info(f"Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)

        log.error(f"Email sending failed after {max_retries} attempts")
        return False

    def _build_message(self, markdown_text: str) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"{LOCALE['email_subject']} - {datetime.now().strftime('%Y-%m-%d')}"
        msg["From"] = self.sender
        msg["To"] = self.receiver
        msg.attach(MIMEText(markdown_text, "plain", "utf-8"))
        msg.attach(MIMEText(self._md_to_html(markdown_text), "html", "utf-8"))
        return msg

    @staticmethod
    def _md_to_html(md_text: str) -> str:
        """Minimal markdown to HTML conversion for email."""
        lines = md_text.split("\n")
        html_lines = []
        in_list = False

        for line in lines:
            if line.startswith("## "):
                if in_list:
                    html_lines.append("</ul>"); in_list = False
                html_lines.append(f'<h2 style="color:#1a1a2e;font-size:20px;border-bottom:2px solid #e94560;padding-bottom:6px;margin-top:28px">{line[3:]}</h2>')
            elif line.startswith("### "):
                if in_list:
                    html_lines.append("</ul>"); in_list = False
                html_lines.append(f'<h3 style="color:#16213e;font-size:17px;margin-top:20px">{line[4:]}</h3>')
            elif line.startswith("# "):
                if in_list:
                    html_lines.append("</ul>"); in_list = False
                html_lines.append(f'<h1 style="color:#e94560;font-size:22px;margin-top:20px">{line[2:]}</h1>')
            elif line.strip() == "---":
                if in_list:
                    html_lines.append("</ul>"); in_list = False
                html_lines.append('<hr style="border:none;border-top:1px solid #eee;margin:24px 0">')
            else:
                line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
                line = re.sub(r"`([^`]+)`", r'<code style="background:#f0f0f0;padding:2px 5px;border-radius:3px;font-size:13px">\1</code>', line)
                line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" style="color:#0f3460;text-decoration:none;border-bottom:1px solid #0f3460">\1</a>', line)
                line = re.sub(r"(?<!href=\")(?<!\">)(https?://[^\s<>\)\"]+)", r'<a href="\1" style="color:#0f3460;text-decoration:none;border-bottom:1px solid #0f3460">\1</a>', line)

                if line.startswith("- ") or line.startswith("* "):
                    if not in_list:
                        html_lines.append('<ul style="padding-left:20px;margin:8px 0">'); in_list = True
                    html_lines.append(f'<li style="margin-bottom:6px">{line[2:]}</li>')
                elif line.strip() == "":
                    if in_list:
                        html_lines.append("</ul>"); in_list = False
                    html_lines.append("")
                elif line.strip().startswith(("（", "(")):
                    html_lines.append(f'<p style="color:#888;font-size:13px;margin:2px 0 12px 0;font-style:italic">{line}</p>')
                else:
                    if in_list:
                        html_lines.append("</ul>"); in_list = False
                    html_lines.append(f'<p style="margin:8px 0;line-height:1.7">{line}</p>')

        if in_list:
            html_lines.append("</ul>")

        body = "\n".join(html_lines)
        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',sans-serif;max-width:680px;margin:0 auto;padding:24px;color:#333;line-height:1.7;background:#fff">
<div style="text-align:center;margin-bottom:24px">
  <h1 style="color:#1a1a2e;font-size:26px;margin:0 0 8px 0;letter-spacing:1px">{LOCALE['email_subject']}</h1>
  <p style="color:#999;font-size:14px;margin:0">{datetime.now().strftime('%Y-%m-%d')} | {LOCALE['email_ai_tag']}</p>
</div>
<div style="background:#f8f9fa;border-radius:8px;padding:20px;margin-bottom:20px;border-left:4px solid #1a1a2e">
{body}
</div>
<hr style="border:none;border-top:1px solid #eee;margin-top:24px">
<p style="color:#aaa;font-size:12px;text-align:center;margin-top:16px">{LOCALE['email_footer']}</p>
</body>
</html>"""

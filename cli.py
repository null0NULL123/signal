"""Command-line interface for Signal.

Usage::

    python cli.py run [--days 7] [--language zh-CN]
    python cli.py fetch [--days 7]
    python cli.py discover
"""

from __future__ import annotations

import argparse
import logging
import sys

from config import (
    DEFAULT_FEEDS_PATH,
    DEFAULT_PROMPT_NAME,
    load_env,
    load_sources,
    validate_env,
    get_summary_days,
    get_summary_language,
)
from pipeline import Pipeline, create_source

log = logging.getLogger("signal")


def setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cmd_run(args: argparse.Namespace) -> None:
    """Run the full pipeline: fetch -> dedup -> save -> summarize -> deliver."""
    load_env()
    validate_env(include_smtp=not args.no_email)

    from channels.file import FileChannel
    from channels.github_pages import GitHubPagesChannel
    from processors.summarizer import SummarizeProcessor
    from storage.knowledge import KnowledgeStorage

    sources = load_sources(args.feeds)
    if not sources:
        log.error(f"No sources found in {args.feeds}")
        sys.exit(1)

    channels: list = [FileChannel(), GitHubPagesChannel()]
    if not args.no_email:
        from channels.email import EmailChannel
        channels.append(EmailChannel())

    Pipeline(
        sources=sources,
        storage=KnowledgeStorage(),
        channels=channels,
        summarize_processor=SummarizeProcessor(prompt_name=args.profile),
        days=args.days or get_summary_days(),
        language=args.language or get_summary_language(),
    ).run()
    log.info("Done!")


def cmd_fetch(args: argparse.Namespace) -> None:
    """Fetch and store articles only (no summarization, no delivery)."""
    load_env()

    from storage.knowledge import KnowledgeStorage

    sources = load_sources(args.feeds)
    if not sources:
        log.error(f"No sources found in {args.feeds}")
        sys.exit(1)

    results = Pipeline(
        sources=sources,
        storage=KnowledgeStorage(),
        days=args.days or get_summary_days(),
    ).fetch_only()

    total = sum(len(r.entries) for r in results if r.ok)
    errors = [r.config.name for r in results if not r.ok]
    log.info(f"Fetched {total} new articles from {len(results)} sources")
    if errors:
        log.warning(f"Failed sources: {', '.join(errors)}")


def cmd_discover(args: argparse.Namespace) -> None:
    """Discover available sub-sources from configured feeds."""
    from sources.base import BaseSource

    sources = load_sources(args.feeds)
    if not sources:
        log.error(f"No sources found in {args.feeds}")
        sys.exit(1)

    for cfg in sources:
        try:
            src: BaseSource = create_source(cfg)
            discovered = src.discover()
            if discovered:
                log.info(f"{cfg.name}: discovered {len(discovered)} sub-sources")
                for sub in discovered:
                    log.info(f"  - {sub.name} ({sub.url})")
            else:
                log.info(f"{cfg.name}: no sub-sources")
        except Exception as exc:
            log.warning(f"{cfg.name}: discovery failed - {exc}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="signal",
        description="Signal - RSS weekly digest with AI summary and email delivery",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--feeds", default=None, help=f"Path to feeds.json (default: {DEFAULT_FEEDS_PATH})")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    p_run = sub.add_parser("run", help="Full pipeline: fetch + summarize + deliver")
    p_run.add_argument("--days", type=int, default=None, help="Days of articles to fetch")
    p_run.add_argument("--language", default=None, help="Target language for digest")
    p_run.add_argument("--profile", default=None, help=f"Prompt profile name (default: {DEFAULT_PROMPT_NAME})")
    p_run.add_argument("--no-email", action="store_true", help="Skip email delivery (use with GitHub Pages / file output only)")

    p_fetch = sub.add_parser("fetch", help="Fetch and store articles only")
    p_fetch.add_argument("--days", type=int, default=None, help="Days of articles to fetch")

    sub.add_parser("discover", help="Discover sub-sources from configured feeds")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    {"run": cmd_run, "fetch": cmd_fetch, "discover": cmd_discover}[args.command](args)


if __name__ == "__main__":
    main()

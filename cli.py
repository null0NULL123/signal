"""Command-line interface for Signal.

Usage::

    python cli.py run [--days 7] [--language zh-CN]
    python cli.py fetch [--days 7]
    python cli.py discover
    python cli.py space list
    python cli.py space create <name>
    python cli.py space delete <name>
"""

from __future__ import annotations

import argparse
import json
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
from channels.file import FileChannel
from channels.github_pages import GitHubPagesChannel
from pipeline import Pipeline, create_source
from sources.base import BaseSource
from processors.summarizer import SummarizeProcessor
from storage.knowledge import KnowledgeStorage
import workspace as ws

log = logging.getLogger("signal")


def setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _resolve_feeds_path(args: argparse.Namespace) -> str:
    """Resolve feeds path: explicit --feeds > workspace feeds.json > default."""
    if args.feeds:
        return args.feeds
    workspace = getattr(args, "workspace", ws.DEFAULT_WORKSPACE)
    ws_feeds = ws.get_feeds_path(workspace)
    if ws_feeds.exists():
        return str(ws_feeds)
    return DEFAULT_FEEDS_PATH


def _resolve_storage(args: argparse.Namespace) -> KnowledgeStorage:
    """Create KnowledgeStorage for the given workspace."""
    workspace = getattr(args, "workspace", ws.DEFAULT_WORKSPACE)
    db_path = ws.get_db_path(workspace)
    storage = KnowledgeStorage(db_path=db_path)
    return storage


def cmd_run(args: argparse.Namespace) -> None:
    """Run the full pipeline: fetch -> dedup -> save -> summarize -> deliver."""
    load_env()
    validate_env(include_smtp=args.email)

    feeds_path = _resolve_feeds_path(args)
    sources = load_sources(feeds_path)
    if not sources:
        log.error(f"No sources found in {feeds_path}")
        sys.exit(1)

    channels: list = [FileChannel(), GitHubPagesChannel()]
    if args.email:
        from channels.email import EmailChannel
        channels.append(EmailChannel())

    storage = _resolve_storage(args)
    try:
        Pipeline(
            sources=sources,
            storage=storage,
            channels=channels,
            summarize_processor=SummarizeProcessor(prompt_name=args.profile),
            days=args.days or get_summary_days(),
            language=args.language or get_summary_language(),
        ).run()
    finally:
        storage.close()
    log.info("Done!")


def cmd_fetch(args: argparse.Namespace) -> None:
    """Fetch and store articles only (no summarization, no delivery)."""
    load_env()

    feeds_path = _resolve_feeds_path(args)
    sources = load_sources(feeds_path)
    if not sources:
        log.error(f"No sources found in {feeds_path}")
        sys.exit(1)

    storage = _resolve_storage(args)
    try:
        results = Pipeline(
            sources=sources,
            storage=storage,
            days=args.days or get_summary_days(),
        ).fetch_only()
    finally:
        storage.close()

    total = sum(len(r.entries) for r in results if r.ok)
    errors = [r.config.name for r in results if not r.ok]
    log.info(f"Fetched {total} new articles from {len(results)} sources")
    if errors:
        log.warning(f"Failed sources: {', '.join(errors)}")


def cmd_discover(args: argparse.Namespace) -> None:
    """Discover available sub-sources from configured feeds."""
    feeds_path = _resolve_feeds_path(args)
    sources = load_sources(feeds_path)
    if not sources:
        log.error(f"No sources found in {feeds_path}")
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


# ---------------------------------------------------------------------------
# Space management commands
# ---------------------------------------------------------------------------


def cmd_space_list(args: argparse.Namespace) -> None:
    """List all workspaces."""
    workspaces = ws.list_workspaces()
    active = ws.get_active_workspace()
    for name in workspaces:
        marker = " *" if name == active else ""
        feeds_path = ws.get_feeds_path(name)
        count = 0
        if feeds_path.exists():
            try:
                count = len(json.loads(feeds_path.read_text()))
            except (json.JSONDecodeError, OSError):
                pass
        print(f"  {name}{marker}  ({count} sources)")
    if len(workspaces) > 1:
        print("\n* = active workspace")


def cmd_space_create(args: argparse.Namespace) -> None:
    """Create a new workspace."""
    try:
        ws.create_workspace(args.name)
        log.info(f"Workspace '{args.name}' created")
        log.info(f"  Edit feeds: {ws.get_feeds_path(args.name)}")
        log.info(f"  Run with:  python cli.py run --workspace {args.name}")
    except ValueError as e:
        log.error(str(e))
        sys.exit(1)


def cmd_space_delete(args: argparse.Namespace) -> None:
    """Delete a workspace."""
    try:
        if not args.confirm:
            print(f"This will permanently delete workspace '{args.name}' and all its data.")
            answer = input("Continue? [y/N] ").strip().lower()
            if answer != "y":
                print("Cancelled.")
                return
        ws.delete_workspace(args.name)
        log.info(f"Workspace '{args.name}' deleted")
    except ValueError as e:
        log.error(str(e))
        sys.exit(1)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="signal",
        description="Signal - RSS weekly digest with AI summary and email delivery",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--workspace", "-w", default=ws.DEFAULT_WORKSPACE, help=f"Workspace name (default: {ws.DEFAULT_WORKSPACE})")
    parser.add_argument("--feeds", default=None, help=f"Path to feeds.json (default: {DEFAULT_FEEDS_PATH})")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    p_run = sub.add_parser("run", help="Full pipeline: fetch + summarize + deliver")
    p_run.add_argument("--days", type=int, default=None, help="Days of articles to fetch")
    p_run.add_argument("--language", default=None, help="Target language for digest")
    p_run.add_argument("--profile", default=None, help=f"Prompt profile name (default: {DEFAULT_PROMPT_NAME})")
    p_run.add_argument("--email", action="store_true", help="Enable email delivery (requires SMTP config in .env)")

    p_fetch = sub.add_parser("fetch", help="Fetch and store articles only")
    p_fetch.add_argument("--days", type=int, default=None, help="Days of articles to fetch")

    sub.add_parser("discover", help="Discover sub-sources from configured feeds")

    # Space management
    p_space = sub.add_parser("space", help="Manage workspaces")
    space_sub = p_space.add_subparsers(dest="space_command", help="Space commands")

    space_sub.add_parser("list", help="List all workspaces")

    p_create = space_sub.add_parser("create", help="Create a new workspace")
    p_create.add_argument("name", help="Workspace name")

    p_delete = space_sub.add_parser("delete", help="Delete a workspace")
    p_delete.add_argument("name", help="Workspace name")
    p_delete.add_argument("-y", "--confirm", action="store_true", help="Skip confirmation")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    # Set active workspace in environment
    if args.workspace:
        import os
        os.environ["ACTIVE_WORKSPACE"] = args.workspace

    if args.command == "space":
        space_cmds = {
            "list": cmd_space_list,
            "create": cmd_space_create,
            "delete": cmd_space_delete,
        }
        if not args.space_command:
            cmd_space_list(args)
        else:
            space_cmds[args.space_command](args)
    else:
        {"run": cmd_run, "fetch": cmd_fetch, "discover": cmd_discover}[args.command](args)


if __name__ == "__main__":
    main()

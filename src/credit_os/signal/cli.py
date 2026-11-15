"""Command line for Signal: ``python -m credit_os.signal --root <folder> <command>``.

Commands: ``users add``, ``sources propose|approve|pause|list``, ``topics add|list``, ``ingest``,
``serve`` and ``stories``. Limits an operator needs to know:

- Do not run ``ingest`` beside ``serve`` on the same root: ``serve`` runs its own ingest loop, and
  two processes on one root are not prevented (one can hold the write lock for a long while).
- A ``users`` row is created only by ``users add`` and is needed only to react or to hold a writer
  or owner role; any typed name can read, save, follow and join an open group without one.
- ``serve`` holds up to 4 descriptors per stalled request, 64 connections at most: against a
  soft limit of 256 (launchd's default) raise it first with ``ulimit -n``.
- Clients must send the host name in lower case: the service compares the ``Host`` header exactly
  and keeps the configured name in lower case. A browser lower-cases it; curl and urllib send it
  as typed and get 403 otherwise. Start serve with the host name in lower case.
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from credit_os.signal.fetch import FetchRefused, check_address
from credit_os.signal.identity import IdentityError, clean_name
from credit_os.signal.ingest import health, run_due
from credit_os.signal.service import DEFAULT_HOST, DEFAULT_PORT, serve
from credit_os.signal.store import (
    KINDS,
    ROLES,
    StoreError,
    add_user,
    last_check,
    open_db,
    propose_source,
    set_source_state,
    sources,
    utc_text,
)
from credit_os.signal.topics import add_topic, list_topics

_STORIES_SQL = """
SELECT s.id, s.title, s.published_at, src.name AS source_name,
       (SELECT COUNT(DISTINCT d.duplicate_source_id) FROM story_duplicates d
        WHERE d.story_id = s.id) AS folded
FROM stories s JOIN sources src ON src.id = s.source_id
ORDER BY s.published_at DESC, s.id DESC
LIMIT ?
"""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m credit_os.signal")
    parser.add_argument("--root", type=Path, required=True, help="folder holding signal/")
    commands = parser.add_subparsers(dest="command", required=True)

    users = commands.add_parser("users").add_subparsers(dest="action", required=True)
    add = users.add_parser("add")
    add.add_argument("name")
    add.add_argument("--role", choices=ROLES, required=True)

    srcs = commands.add_parser("sources").add_subparsers(dest="action", required=True)
    propose = srcs.add_parser("propose")
    propose.add_argument("name")
    propose.add_argument("--kind", choices=KINDS, required=True)
    propose.add_argument("--url", required=True)
    propose.add_argument("--by", required=True)
    for action in ("approve", "pause"):
        srcs.add_parser(action).add_argument("id", type=int)
    srcs.add_parser("list")

    topics = commands.add_parser("topics").add_subparsers(dest="action", required=True)
    new_topic = topics.add_parser("add")
    new_topic.add_argument("name")
    new_topic.add_argument("--keywords", required=True, help="comma-separated phrases")
    new_topic.add_argument("--kinds", default="", help="comma-separated; empty means every kind")
    new_topic.add_argument("--by", required=True)
    topics.add_parser("list")

    commands.add_parser(
        "ingest",
        help="one ingest pass",
        description="One ingest pass over the approved sources that are due. Do not run ingest "
        "beside serve on the same root: serve runs its own loop and two processes on one root "
        "are not prevented.",
    )

    serving = commands.add_parser(
        "serve",
        help="the feed service and its ingest loop",
        description="The feed service and its ingest loop, until interrupted. Do not run ingest "
        "beside serve on the same root (two processes on one root are not prevented). Each "
        "stalled request holds 4 descriptors, 64 connections at most: under launchd the soft "
        "limit is 256, so raise it with `ulimit -n`. Clients must send the host name in lower "
        "case (a browser does; curl and urllib send it as typed and get 403 otherwise): start "
        "serve with the host name in lower case. A users row is created only by "
        "`users add` and is needed only to react or to hold a writer or owner role.",
    )
    serving.add_argument("--host", default=DEFAULT_HOST)
    serving.add_argument("--port", type=int, default=DEFAULT_PORT)

    stories = commands.add_parser("stories")
    stories.add_argument("--limit", type=_positive_int, default=20)
    return parser


def _stamp(value: datetime | None, missing: str = "") -> str:
    return missing if value is None else value.astimezone(UTC).strftime("%Y-%m-%d %H:%M")


def _list_sources(db: sqlite3.Connection) -> None:
    now = datetime.now(UTC)
    for row in sources(db):
        status = health(db, row["id"], now)
        why = f"  ({status.reason})" if status.state == "failing" else ""
        print(
            f"{row['id']}  {row['state']}  {status.state}  "
            f"{_stamp(status.last_item, 'no items')}  {row['name']}{why}"
        )


def _ingest(db: sqlite3.Connection) -> None:
    names = {row["id"]: row["name"] for row in sources(db)}
    now = datetime.now(UTC)
    results = run_due(db, now)
    for source_id, ok, reason in results:
        state = "ok" if ok else "failed"
        if not ok and _unchecked(db, source_id, now):
            # No check is recorded for a source the lookup cap stopped: the pass ends there and
            # the sources left stay due.
            print(
                f"{names[source_id]}: stopped at the lookup cap: {reason}; later sources stay due"
            )
        else:
            print(f"{names[source_id]}: {state}: {reason}")


def _unchecked(db: sqlite3.Connection, source_id: int, now: datetime) -> bool:
    """True when the source has no check recorded at this pass's time (the lookup cap stopped it)."""
    row = last_check(db, source_id)
    return row is None or row["at"] != utc_text(now)


def _stories(db: sqlite3.Connection, limit: int) -> None:
    for row in db.execute(_STORIES_SQL, (limit,)):
        when = _stamp(datetime.fromisoformat(row["published_at"]))
        folded = f" (+{row['folded']})" if row["folded"] else ""
        print(f"{when}  {row['source_name']}  {row['title']}{folded}")


def _split(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def _topics(db: sqlite3.Connection, args: argparse.Namespace) -> None:
    if args.action == "add":
        by = clean_name(args.by)  # the rule the service applies to a name from a cookie
        add_topic(db, args.name, _split(args.keywords), _split(args.kinds), by)
    else:
        for row in list_topics(db, None):  # every topic, none marked as followed
            print(f"{row['id']}  {row['stories']}  {row['name']}")


def _dispatch(args: argparse.Namespace) -> None:
    db = open_db(args.root)
    try:
        if args.command == "users":
            add_user(db, clean_name(args.name), args.role)
        elif args.command == "sources":
            if args.action == "propose":
                check_address(args.url)
                propose_source(db, args.name, args.kind, args.url, args.by)
            elif args.action == "list":
                _list_sources(db)
            else:
                state = "approved" if args.action == "approve" else "paused"
                set_source_state(db, args.id, state)
        elif args.command == "topics":
            _topics(db, args)
        elif args.command == "ingest":
            _ingest(db)
        else:
            _stories(db, args.limit)
    finally:
        db.close()


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        value = 0
    if value < 1:
        raise argparse.ArgumentTypeError("must be an integer >= 1")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    """Run one command; 2 on a usage error, a store error or a refused address."""
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exit_:
        return exit_.code if isinstance(exit_.code, int) else 2
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if args.command == "serve":
        return _serve(args)
    try:
        _dispatch(args)
    except (StoreError, FetchRefused, IdentityError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


def _serve(args: argparse.Namespace) -> int:
    try:
        args.host.encode("idna")  # what the socket does first; a name it cannot encode fails here
    except UnicodeError as error:  # the only failure `service.serve` does not turn into exit 2
        print(f"cannot listen on {args.host}:{args.port}: {error}", file=sys.stderr)
        return 2
    return serve(args.root, args.host, args.port)

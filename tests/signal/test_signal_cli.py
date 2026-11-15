"""S-14: the command line, called in-process through ``main``. Feeds are recorded bytes; no
command resolves a name (``check_address`` or ``fetch._resolve`` is replaced where a test would
reach one). Expected values are literals."""

import contextlib
import io
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from test_signal_feeds import RSS

from credit_os.signal import cli, fetch
from credit_os.signal.feeds import Entry
from credit_os.signal.fetch import Fetched, FetchRefused, LookupCapRefused
from credit_os.signal.identity import clean_name
from credit_os.signal.store import add_story, open_db, propose_source, role_of

PROPOSE = ("sources", "propose", "Authority", "--kind", "regulator", "--url", "https://a.org/f")


def run(root: Path, *args: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(["--root", str(root), *args])
    return code, out.getvalue(), err.getvalue()


class Clock(datetime):
    @classmethod
    def now(cls, tz: Any = None) -> "Clock":
        return cls(2026, 11, 13, 10, 0, tzinfo=tz)


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "check_address", lambda url: None)


def test_propose_approve_list(tmp_path: Path, offline: None) -> None:
    assert run(tmp_path, *PROPOSE, "--by", "ak")[0] == 0
    code, out, err = run(tmp_path, "sources", "list")
    assert (code, err) == (0, "")
    assert out == "1  proposed  never checked  no items  Authority\n"
    assert run(tmp_path, "sources", "approve", "1")[0] == 0
    assert run(tmp_path, "sources", "list")[1].startswith("1  approved  ")
    assert run(tmp_path, "sources", "pause", "1")[0] == 0
    assert run(tmp_path, "sources", "list")[1].startswith("1  paused  ")


def test_proposing_a_private_address_is_refused(tmp_path: Path) -> None:
    args = ("sources", "propose", "X", "--kind", "news", "--url", "https://127.0.0.1/f")
    code, out, err = run(tmp_path, *args, "--by", "ak")
    assert (code, out) == (2, "")
    assert err.startswith("error: ") and "plain host name" in err
    assert run(tmp_path, "sources", "list")[1] == ""


def test_proposing_a_name_that_resolves_privately_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(fetch, "_resolve", lambda host: ["10.0.0.5"])
    args = ("sources", "propose", "X", "--kind", "news", "--url", "https://feeds.example.org/f")
    code, out, err = run(tmp_path, *args, "--by", "ak")
    assert (code, out) == (2, "") and "public" in err
    assert run(tmp_path, "sources", "list")[1] == ""


def test_an_invalid_role_exits_2(tmp_path: Path) -> None:
    assert run(tmp_path, "users", "add", "X", "--role", "admin")[0] == 2


def test_ingest_and_stories_with_a_recorded_feed(
    tmp_path: Path, offline: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "datetime", Clock)
    monkeypatch.setattr(fetch, "fetch", lambda u, e, m: Fetched(RSS, None, None))
    run(tmp_path, *PROPOSE, "--by", "ak")
    run(tmp_path, "sources", "approve", "1")
    code, out, err = run(tmp_path, "ingest")
    assert (code, out, err) == (0, "Authority: ok: 2 new\n", "")
    assert run(tmp_path, "stories")[1].splitlines() == [
        "2026-11-13 10:00  Authority  No date",
        "2026-11-13 08:00  Authority  Authority opens review",
    ]


def test_a_pass_that_stops_at_the_lookup_cap_prints_the_reason(
    tmp_path: Path, offline: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    def capped(u: str, e: str | None, m: str | None) -> Fetched:
        raise LookupCapRefused("too many lookups are still waiting for an answer")

    monkeypatch.setattr(fetch, "fetch", capped)
    run(tmp_path, *PROPOSE, "--by", "ak")
    run(tmp_path, "sources", "approve", "1")
    code, out, err = run(tmp_path, "ingest")
    assert (code, err) == (0, "")
    assert out == (
        "Authority: stopped at the lookup cap: too many lookups are still waiting for an answer;"
        " later sources stay due\n"
    )
    assert run(tmp_path, "sources", "list")[1].startswith("1  approved  never checked")


def test_sources_list_shows_why_a_source_is_failing(
    tmp_path: Path, offline: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(u: str, e: str | None, m: str | None) -> Fetched:
        raise FetchRefused("server answered HTTP 503")

    monkeypatch.setattr(fetch, "fetch", refuse)
    run(tmp_path, *PROPOSE, "--by", "x")
    run(tmp_path, "sources", "approve", "1")
    assert run(tmp_path, "ingest")[1] == "Authority: failed: server answered HTTP 503\n"
    out = run(tmp_path, "sources", "list")[1]
    assert out.endswith("no items  Authority  (server answered HTTP 503)\n")
    assert "  failing  " in out


def test_the_story_count_of_others_counts_sources_not_links(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    for n in (1, 2):
        propose_source(db, f"S{n}", "news", f"https://s{n}.org/f", "x")
    t = datetime(2026, 11, 13, 9, tzinfo=UTC)
    title = "Authority opens in depth review"
    add_story(db, 1, Entry(title, "https://s1.org/1", t, ""), t)
    add_story(db, 2, Entry(title, "https://s2.org/1", t, ""), t)
    add_story(db, 2, Entry(title, "https://s2.org/2", t, ""), t)
    db.close()
    assert run(tmp_path, "stories")[1] == f"2026-11-13 09:00  S1  {title} (+1)\n"


def test_approving_an_unknown_source_exits_2_with_one_line(tmp_path: Path) -> None:
    assert run(tmp_path, "sources", "approve", "999") == (2, "", "error: no source with id 999\n")


@pytest.mark.parametrize("name", ["", "\u200b \t"])
def test_a_name_that_cleans_to_nothing_is_refused_in_one_line(tmp_path: Path, name: str) -> None:
    result = run(tmp_path, "users", "add", name, "--role", "reader")
    assert result == (2, "", "error: display name is empty\n")


def test_users_add_stores_the_name_the_page_looks_up(tmp_path: Path) -> None:
    assert run(tmp_path, "users", "add", "  B.   Novak ", "--role", "writer")[0] == 0
    db = open_db(tmp_path)
    try:
        assert role_of(db, clean_name("  B.   Novak ")) == "writer"
        assert [row["name"] for row in db.execute("SELECT name FROM users")] == ["B. Novak"]
    finally:
        db.close()


@pytest.mark.parametrize("limit", ["0", "-1", "x"])
def test_the_stories_limit_must_be_a_positive_integer(tmp_path: Path, limit: str) -> None:
    code, out, err = run(tmp_path, "stories", "--limit", limit)
    assert (code, out) == (2, "")
    assert err.splitlines()[-1].endswith("--limit: must be an integer >= 1")


def test_topics_add_and_list_show_every_topic_to_nobody(tmp_path: Path) -> None:
    add = ("topics", "add", "Competition", "--keywords", "merger review, remedy", "--by", "ak")
    assert run(tmp_path, *add)[0] == 0
    db = open_db(tmp_path)
    db.execute("INSERT INTO topic_follows(topic_id, user_name) VALUES(1, 'ak')")
    db.commit()
    db.close()
    assert run(tmp_path, "topics", "list") == (0, "1  0  Competition\n", "")


def test_topics_list_asks_for_all_topics_with_no_user(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[object] = []

    def record(db: object, user: object) -> list[Any]:
        asked.append(user)
        return []

    monkeypatch.setattr(cli, "list_topics", record)
    assert run(tmp_path, "topics", "list")[0] == 0
    assert asked == [None]


def test_topics_add_by_cleans_the_name_like_the_service(tmp_path: Path) -> None:
    args = ("topics", "add", "T", "--keywords", "review", "--by", "  B.   Novak ")
    assert run(tmp_path, *args)[0] == 0
    db = open_db(tmp_path)
    try:
        assert [r["created_by"] for r in db.execute("SELECT created_by FROM topics")] == [
            "B. Novak"
        ]
    finally:
        db.close()


def test_a_topic_with_no_keywords_exits_2_with_one_line(tmp_path: Path) -> None:
    code, out, err = run(tmp_path, "topics", "add", "X", "--keywords", "", "--by", "ak")
    assert (code, out) == (2, "") and len(err.splitlines()) == 1


def test_kinds_with_spaces_after_commas_are_trimmed(tmp_path: Path) -> None:
    args = (
        "topics",
        "add",
        "T",
        "--keywords",
        "review",
        "--kinds",
        "regulator, news",
        "--by",
        "ak",
    )
    assert run(tmp_path, *args)[0] == 0


def test_there_is_no_tick_option(tmp_path: Path) -> None:
    assert run(tmp_path, "serve", "--tick", "1")[0] == 2


def _words(text: str) -> str:
    return " ".join(text.replace("`", "").lower().split())


def test_the_help_and_the_module_docstring_name_the_limits(
    capsys: pytest.CaptureFixture[str],
) -> None:
    for command in ("serve", "ingest"):
        assert cli.main(["--root", "x", command, "--help"]) == 0
    helped = _words(capsys.readouterr().out)
    assert helped.count("do not run ingest beside serve") == 2
    assert "two processes on one root are not prevented" in helped
    assert "4 descriptors" in helped and "ulimit -n" in helped
    assert "users add and is needed only to react or to hold a writer or owner role" in helped
    assert "as clients will spell it" in helped
    doc = _words(cli.__doc__ or "")
    for phrase in (
        "do not run ingest beside serve",
        "two processes on one root are not prevented",
        "4 descriptors per stalled request",
        "ulimit -n",
        "created only by users add and is needed only to react or to hold a writer or owner role",
        "as clients will spell it",
    ):
        assert phrase in doc


def test_python_dash_m_runs_the_command_line(tmp_path: Path) -> None:
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "credit_os.signal",
            "--root",
            str(tmp_path),
            "users",
            "add",
            "",
            "--role",
            "reader",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert (done.returncode, done.stdout, done.stderr) == (2, "", "error: display name is empty\n")

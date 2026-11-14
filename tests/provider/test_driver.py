import json
import logging
from typing import Any

import provider_driver_key as key
import pytest
from fake_client import Fake

from credit_os.provider.driver import CopilotDriver, scrub_raw
from credit_os.provider.events import reply_from_events
from credit_os.provider.redact import Redactor
from credit_os.provider.types import Message, Reply, Request, ToolSpec, Usage


def _complete(driver: CopilotDriver, case: dict[str, Any]) -> Reply:
    messages = tuple(Message(role, text) for role, text in case["messages"])
    request = Request(messages, tuple(ToolSpec(*t) for t in case["tools"]), 1000, case["effort"])
    return driver.complete(request, exchange_id=case["exchange_id"], call_index=case["call_index"])


def _run(given: dict[str, Any]) -> tuple[Reply, Fake, CopilotDriver]:
    case = {**key.DEFAULTS, **given}
    fake = Fake(case)
    driver = CopilotDriver(
        fake.open_client,
        config_id="copilot-sol-medium",
        model=key.MODEL,
        environ=case["environ"],
        home=case["home"],
        clock=fake.clock,
        idle_timeout_s=case["idle"],
        overall_timeout_s=case["overall"],
    )
    if case["before"] == "close":
        driver.close()
    if case["before"] == "same":
        _complete(driver, case)
    fake.steps.clear()
    return _complete(driver, case), fake, driver


@pytest.mark.parametrize(("want", "given"), key.CASES.values(), ids=list(key.CASES))
def test_cases(want: dict[str, Any], given: dict[str, Any]) -> None:
    reply, fake, _ = _run(given)
    case = {**key.DEFAULTS, **given}
    parser = reply_from_events(
        case["script"], model=key.MODEL, redactor=Redactor.from_environ(case["environ"])
    )
    charge = None if reply.billed_usd is None else format(reply.billed_usd, "f")
    usage = None if want["usage"] is None else Usage(*want["usage"])
    fields = (
        reply.kind,
        reply.error_class,
        reply.usage,
        charge,
        reply.started_at,
        reply.finished_at,
    )
    assert fields == (
        *map(want.get, ("kind", "error_class")),
        usage,
        *map(want.get, ("charge", "started", "finished")),
    )
    if "absent" not in want:
        assert reply.message == (
            parser.message if want["message"] is key.PARSER else want["message"]
        )
    assert tuple(fake.steps) == want["calls"]
    assert all(fake.bounds[s] == v for s, v in want.get("bounds", {}).items())
    assert reply.compactions == ()
    _check_turn(reply, want["turn"])
    _check_raw(reply, want, case)


def _check_turn(reply: Reply, turn: Any) -> None:
    t = reply.turn
    calls = (
        tuple((c.call_id, c.name, c.arguments, c.bad_arguments) for c in t.tool_calls) if t else ()
    )
    assert (t and (t.text, calls, t.stop_reason, t.request_id)) == (turn or None)


def _check_raw(reply: Reply, want: dict[str, Any], case: dict[str, Any]) -> None:
    assert type(reply.raw) is (type(None) if want["kind"] == "not_sent" else bytes)
    if reply.raw is not None and "absent" in want:
        shown = (reply.raw.decode() + (reply.message or "")).lower()
        assert not [a for a in want["absent"] if a.lower() in shown]
        assert len(json.loads(reply.raw)) == len(case["script"])


@pytest.mark.parametrize("raw", key.UNREADABLE_RAW)
def test_unreadable_raw_gives_the_placeholder(raw: bytes) -> None:
    assert scrub_raw(raw, str) == key.RAW_PLACEHOLDER


def test_release_failure_is_logged_once_without_its_text(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        _run(key.CASES[key.RELEASE_LOG_CASE][1])
    assert len(caplog.records) == 1
    assert all(t in caplog.text for t in key.RELEASE_LOG_HAS)
    assert not any(t in caplog.text for t in key.RELEASE_LOG_LACKS)


def test_close_releases_the_kept_session_once() -> None:
    reply, fake, driver = _run({"script": key._TURN_SCRIPT})
    fake.steps.clear()
    assert (reply.kind, driver.close(), tuple(fake.steps)) == ("ok", (), key._RELEASE)
    fake.steps.clear()
    assert (driver.close(), fake.steps) == ((), [])

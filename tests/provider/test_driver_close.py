import logging
from dataclasses import astuple
from typing import Any

import provider_driver_close_key as key
import provider_driver_key as base
import pytest
from fake_client import Fake

from credit_os.provider.driver import CopilotDriver
from credit_os.provider.types import Compaction, Message, Request


def _shown(c: Compaction) -> tuple[Any, ...]:
    charge = None if c.billed_usd is None else format(c.billed_usd, "f")
    counts = astuple(c.usage)[:4]
    return (c.event_id, c.outcome, counts, charge, c.supersedes)


@pytest.mark.parametrize("given", key.CASES.values(), ids=list(key.CASES))
def test_cases(given: dict[str, Any], caplog: pytest.LogCaptureFixture) -> None:
    fakes: list[Fake] = []

    def open_client() -> Fake:
        fake = Fake({**base.DEFAULTS, **given["calls"][len(fakes)]})
        fake.now = fakes[-1].now if fakes else fake.now
        fakes.append(fake)
        return fake.open_client()

    d = base.DEFAULTS
    driver = CopilotDriver(
        open_client,
        config_id="copilot-sol-medium",
        model=base.MODEL,
        environ=d["environ"],
        home=d["home"],
        clock=lambda: fakes[-1].now if fakes else base.T0,
        idle_timeout_s=d["idle"],
        overall_timeout_s=d["overall"],
    )
    got: dict[str, Any] = {"replies": [], "closed": []}
    with caplog.at_level(logging.WARNING):
        for call in given["calls"]:
            messages = tuple(Message(role, text) for role, text in d["messages"])
            request = Request(messages, (), 1000, d["effort"])
            reply = driver.complete(request, exchange_id=call["exchange_id"], call_index=0)
            charge = None if reply.billed_usd is None else format(reply.billed_usd, "f")
            usage = None if reply.usage is None else astuple(reply.usage)
            shown = tuple(map(_shown, reply.compactions))
            got["replies"].append((reply.kind, reply.error_class, usage, charge, shown))
        for _ in range(given["closes"]):
            got["closed"].append(tuple(map(_shown, driver.close())))
    want = given["want"]
    assert got["replies"] == want["replies"]
    assert got["closed"] == list(want["closed"])
    has, lacks = want.get("log", ((), ()))
    assert all(w in caplog.text for w in has)
    assert not [w for w in lacks if w in caplog.text]

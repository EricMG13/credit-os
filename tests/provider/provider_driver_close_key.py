"""Answer key for step 1C, PR 3-2: the compactions a reply carries, what close() returns, and the
events a session still holds when it is read at release or at close. Written by the controller
before the code existed; implementers do not edit it. Every value is invented.

A case drives one driver (provider_driver_key's DEFAULTS: environ, home, models, idle, overall)
through its calls in order, then calls close() `closes` times. Each call is call index 0 of its own
exchange, on its own client and session (a fake built from DEFAULTS merged with that call), handed
out by open_client in order; close() reads the kept sessions in the order their replies returned.
`queued` is what that session's queued() returns: read at release when the call's reply is not ok,
else read by close(). `fail` and `takes` work as in provider_driver_key, per call. Times and step
lists are not compared here (provider_driver_key does that).

want["replies"][i] is (kind, error_class, usage, charge, compactions) for call i: usage is the five
counts in Usage's order, charge is format(billed_usd, "f"), and compactions is a tuple of
(event_id, outcome, counts, charge, supersedes) in the reply's order, counts being the four
compaction counts in Usage's order and charge None when unknown. want["closed"][k] is the tuple the
k-th close() returned, in the same form. want["log"], where given, is (words the warnings logged
during the case have, taken together; words none of them has).

The rules the rows encode (coordinator rulings for PR 3-2, 2026-11-14):
- A reply carries the compactions of its call's events. A reply that is not ok also carries those of
  the events its release read from queued(): one list, the call's events then the queued ones, read
  for compactions only; the reply's kind, class, usage and charge come from the call's events alone.
- A queued event that reports spend (`assistant.usage`, or any event whose data holds a field the
  parser reads a count or charge from) is spend the reply does not attribute, and a
  queued() read that times out, raises or does not return a list of events is a read that failed:
  either adds one compaction `driver:release-unread` (failed, no counts, charge None) at the end of
  the reply's. At close() the same, for any kept session, gives one `driver:close-unread` per
  close() call, at the end of what it returns. A leftover event with no figures that is not a
  compaction is dropped and its type logged, never its content.
- A complete supersedes a compaction only within one session: when that session delivered exactly
  one unfinished compaction, the complete's own list holds no start and no other complete, and that
  compaction's id was not withheld. Otherwise it supersedes nothing (None).
- An event_id the driver's redaction would change is withheld: `driver:withheld-<n>`, n counting
  from 1 per driver, outcome failed, no counts, charge None, supersedes None.
- A compaction whose envelope id this driver already delivered is not delivered again. When it is
  not the same compaction (outcome, counts, charge), its read counts as one that failed (the release
  or close entry): controller's reading of ruling 5, since dropping it would drop spend. The
  driver's own ids are never dropped as repeats of one another.
- Unknown spend is None everywhere, never 0.
"""

from typing import Any

from provider_driver_key import _ERROR, _IDLE, _TOKEN, _TURN_SCRIPT, _USAGE, event, said

_FULL = (12, 4, 0, 7, 2)
_CALL_CHARGE = "0.00012300000"  # 12,300,000 x 1E-11
_USED = {"inputTokens": 30, "cacheReadTokens": 20, "cacheWriteTokens": 0, "outputTokens": 5}
_PAID = {**_USED, "copilotUsage": {"totalNanoAiu": 2140500000}}
_C4, _N4 = (30, 20, 0, 5), (None, None, None, None)
_CHARGE = "0.02140500000"  # 2,140,500,000 x 1E-11
CALL: dict[str, Any] = {"script": _TURN_SCRIPT, "queued": [], "fail": {}, "takes": {}}


def _start(i: str) -> dict[str, Any]:
    return {**event(0, "session.compaction_start", conversationTokens=900), "id": i}


def _end(i: str, **used: Any) -> dict[str, Any]:
    data = {"success": True, "compactionTokensUsed": used} if used else {"success": True}
    return {**event(0, "session.compaction_complete", **data), "id": i}


def _done(i: str, charge: str | None = _CHARGE, sup: str | None = None) -> tuple[Any, ...]:
    return (i, "done", _C4, charge, sup)


def _open(i: str) -> tuple[Any, ...]:
    return (i, "unfinished", _N4, None, None)


def _failed(i: str) -> tuple[Any, ...]:
    return (i, "failed", _N4, None, None)


def _ok(*compactions: tuple[Any, ...]) -> tuple[Any, ...]:
    return ("ok", None, _FULL, _CALL_CHARGE, compactions)


def _error(cls: str, *compactions: tuple[Any, ...]) -> tuple[Any, ...]:
    return ("sent_usage", cls, _FULL, _CALL_CHARGE, compactions)


_W1, _W2 = _failed("driver:withheld-1"), _failed("driver:withheld-2")
RELEASE_UNREAD, CLOSE_UNREAD = _failed("driver:release-unread"), _failed("driver:close-unread")
_LATE_SPEND = {**_USAGE, "id": "u7"}  # reports spend after the call ended
_TURN = [_USAGE, said(2, "done"), _IDLE]
_FAILED = [_USAGE, _ERROR]  # the session reports an error: SessionError, figures kept, released
_TOKEN_IDS = [_start(f"{_TOKEN}-1"), _start(f"{_TOKEN}-2")]  # the parser: KeyReflected


def _case(calls: list[dict[str, Any]], replies: list[Any], *closed: Any, **more: Any) -> Any:
    calls = [{**CALL, "exchange_id": f"ex-{n}", **c} for n, c in enumerate(calls)]
    want = {"replies": replies, "closed": closed, **more}
    return {"calls": calls, "closes": len(closed), "want": want}


CASES: dict[str, dict[str, Any]] = {
    # --- what a reply carries
    "a start and its complete in one call are one compaction on the reply": _case(
        [{"script": [_start("s1"), _end("c1", **_PAID), *_TURN]}], [_ok(_done("c1"))], ()
    ),
    "a start left open by an ok call is completed at close, in its session": _case(
        [{"script": [_start("s1"), *_TURN], "queued": [_end("c1", **_PAID)]}],
        [_ok(_open("s1"))],
        (_done("c1", sup="s1"),),
        (),
    ),
    # --- a complete supersedes only a start its own session delivered
    "two sessions, first a then b": _case(
        [
            {"script": [_start("a1"), *_TURN], "queued": [_end("ca", **_PAID)]},
            {"script": [_start("b1"), *_TURN], "queued": [_end("cb", **_USED)]},
        ],
        [_ok(_open("a1")), _ok(_open("b1"))],
        (_done("ca", sup="a1"), _done("cb", None, sup="b1")),
    ),
    "two sessions, first b then a": _case(
        [
            {"script": [_start("b1"), *_TURN], "queued": [_end("cb", **_USED)]},
            {"script": [_start("a1"), *_TURN], "queued": [_end("ca", **_PAID)]},
        ],
        [_ok(_open("b1")), _ok(_open("a1"))],
        (_done("cb", None, sup="b1"), _done("ca", sup="a1")),
    ),
    "a complete from a session that delivered no start leaves another session's open": _case(
        [
            {"queued": [_end("ca", **_PAID)]},
            {"script": [_start("b1"), *_TURN], "queued": [_end("cb", **_USED)]},
        ],
        [_ok(), _ok(_open("b1"))],
        (_done("ca"), _done("cb", None, sup="b1")),
    ),
    # --- linking is conservative: when it cannot be sure, nothing is superseded
    "a complete whose list also holds a start supersedes nothing": _case(
        [{"script": [_start("s1"), *_TURN], "queued": [_start("s2"), _end("c2", **_PAID)]}],
        [_ok(_open("s1"))],
        (_done("c2"),),
    ),
    "two completes in one list supersede nothing": _case(
        [{"script": [_start("s1"), *_TURN], "queued": [_end("c1", **_PAID), _end("c2", **_USED)]}],
        [_ok(_open("s1"))],
        (_done("c1"), _done("c2", None)),
    ),
    "two open starts in a session: a complete supersedes neither": _case(
        [{"script": [_start("s1"), _start("s2"), *_TURN], "queued": [_end("c1", **_PAID)]}],
        [_ok(_open("s1"), _open("s2"))],
        (_done("c1"),),
    ),
    "a start whose id holds the home path is withheld, and nothing supersedes it": _case(
        [{"script": [_start("/home/jane/s1"), *_TURN], "queued": [_end("c1", **_PAID)]}],
        [_ok(_W1)],
        (_done("c1"),),
    ),
    # --- repeats
    "a start already delivered is not delivered again at close": _case(
        [{"script": [_start("s1"), *_TURN], "queued": [_start("s1")]}], [_ok(_open("s1"))], ()
    ),
    "a complete under the id of a start already delivered is spend unknown": _case(
        [{"script": [_start("s1"), *_TURN], "queued": [_end("s1", **_PAID)]}],
        [_ok(_open("s1"))],
        (CLOSE_UNREAD,),
    ),
    "two replies whose release reads fail each carry the release entry": _case(
        [{"script": _FAILED, "queued": "junk"}, {"script": _FAILED, "queued": "junk"}],
        [_error("SessionError", RELEASE_UNREAD), _error("SessionError", RELEASE_UNREAD)],
        (),
    ),
    # --- the release path of a reply that is not ok
    "a complete read at release goes on the reply, paired with the call's start": _case(
        [{"script": [_start("s1"), *_FAILED], "queued": [_end("c1", **_PAID)]}],
        [_error("SessionError", _done("c1"))],
        (),
    ),
    "spend read at release is not the reply's: its figures stay the call's": _case(
        [{"script": _FAILED, "queued": [_LATE_SPEND]}],
        [_error("SessionError", RELEASE_UNREAD)],
        (),
    ),
    "a release read that times out": _case(
        [{"script": _FAILED, "fail": {"queued": "timeout"}}],
        [_error("SessionError", RELEASE_UNREAD)],
        (),
        log=(("queued", "TimeoutError"), ()),
    ),
    "a release read that raises": _case(
        [{"script": _FAILED, "fail": {"queued": ("RuntimeError", "boom")}}],
        [_error("SessionError", RELEASE_UNREAD)],
        (),
        log=(("queued", "RuntimeError"), ("boom",)),
    ),
    "a release read that is not a list": _case(
        [{"script": _FAILED, "queued": "junk"}], [_error("SessionError", RELEASE_UNREAD)], ()
    ),
    "two withheld ids and the release entry on one reply, then the close entry: none dropped": _case(
        [{"script": [*_TOKEN_IDS, *_FAILED], "queued": [_LATE_SPEND]}, {"queued": "junk"}],
        [_error("KeyReflected", _W1, _W2, RELEASE_UNREAD), _ok()],
        (CLOSE_UNREAD,),
    ),
    # --- what close() returns
    "spend a kept session still holds at close": _case(
        [{"queued": [_LATE_SPEND]}], [_ok()], (CLOSE_UNREAD,), log=((), ("12300000",))
    ),
    "a leftover of another type that holds a cost field is spend too": _case(
        [{"queued": [event(7, "model.call_failure", copilotUsage={"totalNanoAiu": 5})]}],
        [_ok()],
        (CLOSE_UNREAD,),
    ),
    "two kept sessions whose reads fail give one close entry": _case(
        [{"fail": {"queued": "timeout"}}, {"queued": ["junk"]}], [_ok(), _ok()], (CLOSE_UNREAD,)
    ),
    "what was pending, then the close entry": _case(
        [{"script": [_start("s1"), *_TURN], "queued": [_end("c1", **_PAID)]}, {"queued": "junk"}],
        [_ok(_open("s1")), _ok()],
        (_done("c1", sup="s1"), CLOSE_UNREAD),
    ),
    "a leftover with no figures and no compaction is dropped and its type logged": _case(
        [{"queued": [said(7, "late")]}], [_ok()], (), log=(("assistant.message",), ("late",))
    ),
}

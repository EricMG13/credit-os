"""The Copilot session driver: one text turn through a `ClientLike`; synchronous, no thread, sleep,
real clock, environment or file read (time is only `clock()`).

Documented fail-open: a release step (abort, queued, disconnect, stop, force_stop) that raises
or times out never changes the reply's kind, class, usage or charge and never stops the later
steps; it is logged once at warning level with the step name and the exception class only, never
its text. A failed `queued` read adds `driver:release-unread` to the reply, or
`driver:close-unread` to the result of close()."""

import json
import logging
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from credit_os.provider.events import (
    _COMPACTION_TYPES,
    _COUNTS,
    _as_events,
    _serialise,
    compactions_from_events,
    reply_from_events,
)
from credit_os.provider.redact import Redactor
from credit_os.provider.session import ClientLike, SessionLike
from credit_os.provider.types import Compaction, Reply, Request, Usage

_log = logging.getLogger(__name__)
_EXCHANGE = re.compile(r"[A-Za-z0-9_-]{1,128}")
_ENDS = ("session.idle", "session.error")
_IDLE_OUT = "no session event within the idle timeout"
_OVERALL_OUT = "the call passed its overall timeout"
_NO_ID = "an exchange id is 1 to 128 of A-Z a-z 0-9 _ -"
_NO_DUPLICATE = "two tools share a name"
_NO_MATCH = "the tool calls reported, offered and invoked differ"
_NO_LOST = "the session went idle with a tool call not invoked"
_NO_PATH = "a tool call id holds a path"
_NO_INDEX = "a call index other than 0 is not supported yet"
_NO_HISTORY = "a first call is system messages, then exactly one user message"
_NO_REUSE = "the exchange is already open or was released"
_NO_KEY = "COPILOT_GITHUB_TOKEN is not set"
_NO_RUNTIME = "COPILOT_CLI_PATH is not set"
_Problem = tuple[str, str, bool]  # (error class, message, whether to abort before release)
_UNREAD = object()  # what a release read gives when queued() failed
_SPEND_FIELDS = ("copilotUsage", "compactionTokensUsed", *(wire for wire, _ in _COUNTS))


def _unread(name: str) -> Compaction:
    return Compaction(Usage(), None, "failed", f"driver:{name}-unread", None)


def _valid(value: object) -> list[Any] | None:
    return None if _serialise(value) is None else _as_events(value)


def _spends(event: dict[str, Any]) -> bool:
    return event["type"] == "assistant.usage" or any(f in event["data"] for f in _SPEND_FIELDS)


def _stray(event: dict[str, Any]) -> bool:
    """A compaction event holding a spend field the parser does not read for it."""
    read = {
        "session.compaction_start": (),
        "session.compaction_complete": ("compactionTokensUsed",),
    }
    return event["type"] in read and any(
        f in event["data"] for f in _SPEND_FIELDS if f not in read[event["type"]]
    )


def _duplicated(request: Request) -> bool:
    names = [t.name for t in request.tools]
    return len(set(names)) != len(names)


def _data(events: list[Any], kind: str) -> list[dict[str, Any]]:
    """The payloads of the dict events of one type (an envelope that is not a dict is skipped)."""
    return [
        e["data"]
        for e in events
        if isinstance(e, dict) and e.get("type") == kind and isinstance(e.get("data"), dict)
    ]


def _ready(events: list[Any], offered: set[str]) -> bool:
    """A call that announces tool calls may end: a usage and a start are read, every announced
    id has a start, and every start of an offered tool has been invoked under the same id."""
    starts = _data(events, "tool.execution_start")
    lists = [d.get("toolRequests") for d in _data(events, "assistant.message")]
    announced = [
        r.get("toolCallId") for t in lists if isinstance(t, list) for r in t if isinstance(r, dict)
    ]
    started = {d.get("toolCallId") for d in starts}
    invoked = {d.get("toolCallId") for d in _data(events, "external_tool.requested")}
    wanted = {d.get("toolCallId") for d in starts if d.get("toolName") in offered}
    return bool(_data(events, "assistant.usage") and starts) and (
        started.issuperset(announced) and invoked.issuperset(wanted)
    )


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True)


def _differ(reply: Reply, invoked: list[dict[str, Any]], offered: set[str]) -> bool:
    """Whether the calls reported, offered and invoked disagree."""
    calls = {c.call_id: c for c in (reply.turn.tool_calls if reply.turn else ())}
    ids = [d.get("toolCallId") for d in invoked]
    if len(set(ids)) != len(ids) or set(ids) != set(calls):
        return True
    if any(c.name not in offered for c in calls.values()):
        return True
    for d in invoked:
        c = calls[d["toolCallId"]]
        sent = json.loads(c.bad_arguments) if c.bad_arguments is not None else c.arguments
        if d.get("toolName") != c.name or _json(d.get("arguments") or {}) != _json(sent or {}):
            return True
    return False


@dataclass
class _Kept:
    """A session held open after an ok reply. `pending` holds the ids of the unfinished
    compactions delivered on that reply (`None` for a withheld one); `invoked` the tool calls
    the runtime asked for in it (toolCallId to requestId)."""

    client: ClientLike
    session: SessionLike
    pending: list[str | None] = field(default_factory=list)
    invoked: dict[str, str] = field(default_factory=dict)


class _Refused(Exception):
    """A call that stops before it is sent: becomes a `not_sent` reply. Args: class, message."""


def _try(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> tuple[Any, Exception | None]:
    """The one catch-all. It hides nothing: the caller makes the failure a reply or a log line."""
    try:
        return fn(*args, **kwargs), None
    except Exception as exc:
        if isinstance(exc, MemoryError):  # not a step's failure: let it propagate
            raise
        return None, exc


def _failure(step: str, exc: Exception) -> str:
    if isinstance(exc, TimeoutError):
        return f"{step} timed out"
    text, unprintable = _try(str, exc)  # a __str__ that raises: the class still tells enough
    return f"{step} failed: {type(exc).__name__}: {'<unprintable>' if unprintable else text}"


def _send_problem(exc: Exception) -> _Problem:
    if isinstance(exc, TimeoutError):
        return "OverallTimeout", _OVERALL_OUT, True
    return "AdapterError", _failure("send", exc), False


def _walk(value: Any, redact: Callable[[str], str]) -> Any:
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [_walk(v, redact) for v in value]
    if isinstance(value, dict):
        return {redact(k): _walk(v, redact) for k, v in value.items()}
    return value


def scrub_raw(raw: bytes, redact: Callable[[str], str]) -> bytes:
    """`raw` with `redact` applied to every string in it, keys included, written with the
    parser's separators. Bytes that cannot be decoded or encoded again give a fixed placeholder,
    never the original."""
    try:
        return json.dumps(_walk(json.loads(raw), redact), separators=(",", ":")).encode("utf-8")
    except (ValueError, RecursionError):  # undecodable or unwritable: the placeholder, not raw
        return b'"[redacted]"'


def _has_figures(reply: Reply) -> bool:
    counts = vars(reply.usage).values() if reply.usage else []
    return reply.billed_usd is not None or any(v is not None for v in counts)


class CopilotDriver:
    """A `Model`. One client and one session per exchange; a call at index 0 may offer tools,
    declared with no handler: the runtime's `external_tool.requested` is the call invoked, and
    the reply carries the tool calls with the session kept (answers are not sent yet). Paths (the home and the runtime
    path) are masked by the one `Redactor` (decision 0012); the driver keeps no path code."""

    def __init__(
        self,
        open_client: Callable[[], ClientLike],
        *,
        config_id: str,
        model: str,
        environ: Mapping[str, str],
        home: str,
        clock: Callable[[], float],
        idle_timeout_s: float = 1800.0,
        overall_timeout_s: float = 1800.0,
        abort_timeout_s: float = 5.0,
        close_read_timeout_s: float = 5.0,
        disconnect_timeout_s: float = 5.0,
        stop_timeout_s: float = 30.0,
        force_stop_timeout_s: float = 5.0,
        settle_s: float = 2.0,
    ) -> None:
        self._open_client, self._model, self._environ = open_client, model, environ
        self._clock, self._idle, self._overall = clock, idle_timeout_s, overall_timeout_s
        self._settle = settle_s
        steps = ("abort", "queued", "disconnect", "stop", "force_stop")
        waits = (abort_timeout_s, close_read_timeout_s, disconnect_timeout_s)
        self._bounds = dict(zip(steps, (*waits, stop_timeout_s, force_stop_timeout_s)))
        self.config_id = config_id
        known = [home, *(p for p in [environ.get("COPILOT_CLI_PATH", "")] if p.strip())]
        self._redactor = Redactor.from_environ(environ, known_paths=known)
        self._text = self._redactor.message
        self._used: set[str] = set()
        self._kept: list[_Kept] = []
        self._seen: dict[str, tuple[Any, ...]] = {}  # envelope id -> outcome, usage, charge
        self._withheld = 0
        self._closed = False

    def complete(self, request: Request, *, exchange_id: str, call_index: int) -> Reply:
        try:
            self._refuse(request, exchange_id, call_index)
            return self._exchange(request, exchange_id)
        except _Refused as refused:
            error_class, text = refused.args
            message = self._text(text)[:500]
            return Reply("not_sent", None, error_class, message, None, None, None, None, None)

    def close(self) -> tuple[Compaction, ...]:
        kept, self._kept = self._kept, []
        out: list[Compaction] = []
        unread = False
        for k in kept:
            left = self._release(k.client, k.session, timed_out=bool(k.invoked))
            found, failed = self._read([], left, k, closing=True)
            out += found
            unread = unread or failed
        self._closed = True
        return tuple(out + [_unread("close")] * unread)

    def _refuse(self, request: Request, exchange_id: str, call_index: int) -> None:
        roles = [m.role for m in request.messages]
        history = roles[-1:] == ["user"] and all(r == "system" for r in roles[:-1])
        env = self._environ
        checks = (
            (self._closed, "AdapterClosed", "the model is closed"),
            (not _EXCHANGE.fullmatch(exchange_id), "InvalidExchangeId", _NO_ID),
            (_duplicated(request), "InvalidToolSpec", _NO_DUPLICATE),
            (call_index != 0, "UnsupportedCall", _NO_INDEX),
            (not history, "HistoryMismatch", _NO_HISTORY),
            (exchange_id in self._used, "ExchangeExists", _NO_REUSE),
            (not env.get("COPILOT_GITHUB_TOKEN", "").strip(), "KeyMissing", _NO_KEY),
            (not env.get("COPILOT_CLI_PATH", "").strip(), "RuntimeMissing", _NO_RUNTIME),
        )
        for refused, error_class, message in checks:
            if refused:
                raise _Refused(error_class, message)
        self._used.add(exchange_id)

    def _left(self, end: float) -> float:
        return max(0.0, end - self._clock())

    def _step(self, name: str, fn: Callable[..., Any], **kwargs: Any) -> Any:
        value, exc = _try(fn, **kwargs)
        if exc is not None:
            raise _Refused("PreSendFailure", _failure(name, exc))
        return value

    def _open(self, request: Request, exchange_id: str, end: float) -> tuple[Any, Any]:
        client = self._step("open_client", self._open_client)
        try:
            self._step("start", client.start, timeout_s=self._left(end))
            models = self._step("list_models", client.list_models, timeout_s=self._left(end))
            self._check_offered(models, request.effort)
            system = "\n\n".join(m.text for m in request.messages[:-1])
            opened: dict[str, Any] = {
                "model": self._model,
                "effort": request.effort,
                "system": system,
            }
            opened |= {"session_id": exchange_id, "tools": request.tools}
            opened["timeout_s"] = self._left(end)
            return client, self._step("open_session", client.open_session, **opened)
        except _Refused:
            self._stop(client)
            raise

    def _check_offered(self, models: object, effort: str) -> None:
        listed = models if isinstance(models, list) else []
        found = [m for m in listed if isinstance(m, dict) and m.get("id") == self._model]
        if not found:
            raise _Refused("ModelUnavailable", f"{self._model} is not offered")
        efforts = found[0].get("supportedReasoningEfforts")
        if not isinstance(efforts, list) or effort not in efforts:
            raise _Refused("EffortUnavailable", f"effort {effort} is not offered for {self._model}")

    def _exchange(self, request: Request, exchange_id: str) -> Reply:
        started = self._clock()
        end = started + self._overall
        client, session = self._open(request, exchange_id, end)
        _, exc = _try(session.send, request.messages[-1].text, timeout_s=self._left(end))
        events: list[Any] = []
        offered = {t.name for t in request.tools}
        problem = (
            self._collect(session, end, events, offered) if exc is None else _send_problem(exc)
        )
        finished = self._clock()
        reply = self._reply(events, problem, offered)
        invoked = _data(events, "external_tool.requested")
        kept = _Kept(client, session)
        left: object = []
        if reply.kind == "ok":
            kept.invoked = {str(d.get("toolCallId")): str(d.get("requestId")) for d in invoked}
            self._kept.append(kept)
        else:
            aborts = bool(problem and problem[2]) or bool(invoked)
            left = self._release(client, session, timed_out=aborts)
        found, failed = self._read(events, left, kept)
        found += [_unread("release")] * failed
        reply = replace(reply, compactions=tuple(found))
        message = reply.message and self._text(reply.message)[:500]
        raw = None if reply.raw is None else scrub_raw(reply.raw, self._text)
        return replace(reply, message=message, raw=raw, started_at=started, finished_at=finished)

    def _collect(
        self, session: SessionLike, end: float, events: list[Any], offered: set[str]
    ) -> _Problem | None:
        settling = False  # the tool-call boundary was met: one more poll, bounded by settle_s
        while (left := self._left(end)) > 0:  # the overall bound is checked before every poll
            wait = min(self._settle if settling else self._idle, left)
            envelope, exc = _try(session.next_event, timeout_s=wait)
            if exc is not None and not isinstance(exc, TimeoutError):
                return "AdapterError", _failure("next_event", exc), True
            if envelope is None:
                return None if settling else self._silent(left)
            events.append(envelope)
            if not isinstance(envelope, dict) or envelope.get("type") in _ENDS:
                return None
            settling = _ready(events, offered)
        return "OverallTimeout", _OVERALL_OUT, True

    def _silent(self, left: float) -> _Problem:
        if left <= self._idle:
            return "OverallTimeout", _OVERALL_OUT, True
        return "IdleTimeout", _IDLE_OUT, True

    def _tool_problem(self, reply: Reply, events: list[Any], offered: set[str]) -> _Problem | None:
        """What the reply's tool calls, the tools offered and the calls invoked say against it."""
        invoked = _data(events, "external_tool.requested")
        last = events[-1] if events else None
        idle = isinstance(last, dict) and last.get("type") == "session.idle"
        started = {
            d.get("toolCallId")
            for d in _data(events, "tool.execution_start")
            if d.get("toolName") in offered
        }
        if idle and started - {d.get("toolCallId") for d in invoked}:
            return "ToolCallLost", _NO_LOST, False
        calls = reply.turn.tool_calls if reply.turn else ()
        ids = [c.call_id for c in calls] + [d.get("toolCallId") for d in invoked]
        if any(self._text(str(i)) != i for i in ids):
            return "ToolCallIdRedacted", _NO_PATH, False
        if _differ(reply, invoked, offered):
            return "ToolCallMismatch", _NO_MATCH, False
        return None

    def _reply(self, events: list[Any], problem: _Problem | None, offered: set[str]) -> Reply:
        reply = reply_from_events(events, model=self._model, redactor=self._redactor)
        sub_agent = any(isinstance(e, dict) and e.get("agentId") is not None for e in events)
        if problem is None and reply.kind == "ok" and sub_agent:
            problem = "SubAgentEvent", "an event came from a sub-agent", False
        if problem is None and reply.kind == "ok":
            problem = self._tool_problem(reply, events, offered)
        if problem is None:
            return reply
        error_class, message, _ = problem
        if not _has_figures(reply):
            return Reply(
                "sent_unknown", None, error_class, message, None, None, reply.raw, None, None
            )
        usage, charge = reply.usage or Usage(), reply.billed_usd
        return Reply("sent_usage", None, error_class, message, usage, charge, reply.raw, None, None)

    def _release(self, client: ClientLike, session: SessionLike, *, timed_out: bool) -> object:
        """The steps in order; what queued() returned, or `_UNREAD` when that step failed."""
        if timed_out:
            self._log_step("abort", session.abort)
        left, read = self._log_step("queued", session.queued)
        self._log_step("disconnect", session.disconnect)
        self._stop(client)
        return left if read else _UNREAD

    def _stop(self, client: ClientLike) -> None:
        if not self._log_step("stop", client.stop)[1]:
            self._log_step("force_stop", client.force_stop)

    def _log_step(self, name: str, fn: Callable[..., Any]) -> tuple[Any, bool]:
        value, exc = _try(fn, timeout_s=self._bounds[name])
        if exc is not None:
            _log.warning("release step %s failed: %s", name, type(exc).__name__)
        return value, exc is None

    def _leftovers(self, left: object) -> tuple[list[Any], bool]:
        """The events a release read gave, and whether the read failed: it did not give a list
        of events, or an event in it reports spend. A leftover that is neither a compaction nor
        spend is dropped and its type logged, never its content."""
        events = None if left is _UNREAD else _valid(left)
        if events is None:
            if left is not _UNREAD:  # a failed step already logged its own line
                _log.warning("the queued read is not a list of events")
            return [], True
        others = [e for e in events if e["type"] not in _COMPACTION_TYPES]
        spend = [self._text(e["type"]) for e in others if _spends(e)]
        for e in others:
            if not _spends(e):
                _log.warning("a leftover event was dropped: %s", self._text(e["type"]))
        if spend:
            _log.warning("the queued read holds spend, event types: %s", ", ".join(spend))
        return events, bool(spend)

    def _read(
        self, base: list[Any], left: object, kept: _Kept, *, closing: bool = False
    ) -> tuple[list[Compaction], bool]:
        """The compactions of the call's events then the leftovers, as delivered, and whether
        the read failed."""
        fresh, failed = self._leftovers(left)
        own = _valid(base)  # the call's own events: unreadable ones cost nothing but the entry
        failed = failed or own is None
        listed = _valid((own or []) + fresh) or []
        kinds = [e["type"] for e in listed]
        strays = [self._text(e["type"]) for e in listed if _stray(e)]
        if strays:
            _log.warning(
                "a compaction event holds unattributed spend, event types: %s", ", ".join(strays)
            )
            failed = True
        alone = kinds.count("session.compaction_complete") == 1 and len(kept.pending) == 1
        link = (
            kept.pending[0]
            if closing and alone and "session.compaction_start" not in kinds
            else None
        )
        out: list[Compaction] = []
        changed = False
        for c in compactions_from_events(listed):
            mark = (c.outcome, c.usage, c.billed_usd)
            if c.event_id in self._seen:
                changed = changed or self._seen[c.event_id] != mark
                continue
            self._seen[c.event_id] = mark
            out.append(self._shaped(c, link, kept.pending))
        if changed:
            _log.warning(
                "a compaction repeats a delivered id with other figures"
                " (call events or queued read)"
            )
        return out, failed or changed

    def _shaped(self, c: Compaction, link: str | None, pending: list[str | None]) -> Compaction:
        """`c` as delivered: withheld when its id would need redacting or starts `driver:` (a fixed
        id of this driver's), linked to the one unfinished compaction its session delivered when
        `link` names it."""
        if c.event_id.startswith("driver:") or self._text(c.event_id) != c.event_id:
            self._withheld += 1
            pending += [None] * (c.outcome == "unfinished")
            return Compaction(Usage(), None, "failed", f"driver:withheld-{self._withheld}", None)
        if c.outcome == "unfinished":
            pending.append(c.event_id)
        elif link:
            pending.clear()
            return replace(c, supersedes=link)
        return c

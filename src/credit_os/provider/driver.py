"""The Copilot session driver: one text turn through a `ClientLike`; synchronous, no thread, sleep,
real clock, environment or file read (time is only `clock()`).

Documented fail-open: a release step (abort, queued, disconnect, stop, force_stop) that raises
never changes the reply or stops the later steps; it is logged once at warning level with the
step name and the exception class only, never its text."""

import json
import logging
import re
from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import Any

from credit_os.provider.events import reply_from_events
from credit_os.provider.redact import Redactor, home_paths
from credit_os.provider.session import ClientLike, SessionLike
from credit_os.provider.types import Compaction, Reply, Request, Usage

_log = logging.getLogger(__name__)
_EXCHANGE = re.compile(r"[A-Za-z0-9_-]{1,128}")
_ENDS = ("session.idle", "session.error")
_IDLE_OUT = "no session event within the idle timeout"
_OVERALL_OUT = "the call passed its overall timeout"
_NO_ID = "an exchange id is 1 to 128 of A-Z a-z 0-9 _ -"
_NO_TOOLS = "tool specifications are not supported yet"
_NO_INDEX = "a call index above 0 is not supported yet"
_NO_HISTORY = "a first call is system messages, then exactly one user message"
_NO_REUSE = "the exchange is already open or was released"
_NO_KEY = "COPILOT_GITHUB_TOKEN is not set"
_NO_RUNTIME = "COPILOT_CLI_PATH is not set"
_Problem = tuple[str, str, bool]  # (error class, message, whether it is a timeout)


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
    return f"{step} failed: {type(exc).__name__}: {exc}"


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


def _path_forms(values: list[str]) -> set[str]:
    forms = set()
    for v in values:
        for s in (v, v.replace("\\", "/"), v.replace("/", "\\")):
            forms |= {c for c in (s, s.lower(), s.upper()) if len(c) > 3}
    return forms


def _has_figures(reply: Reply) -> bool:
    counts = vars(reply.usage).values() if reply.usage else []
    return reply.billed_usd is not None or any(v is not None for v in counts)


class CopilotDriver:
    """A `Model`. One client and one session per exchange. A path seen in mixed case other than
    the as-given, lower and upper forms (with either slash) is caught only where `home_paths`
    recognises it."""

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
    ) -> None:
        self._open_client, self._model, self._environ = open_client, model, environ
        self._clock, self._idle, self._overall = clock, idle_timeout_s, overall_timeout_s
        steps = ("abort", "queued", "disconnect", "stop", "force_stop")
        waits = (abort_timeout_s, close_read_timeout_s, disconnect_timeout_s)
        self._bounds = dict(zip(steps, (*waits, stop_timeout_s, force_stop_timeout_s)))
        self.config_id = config_id
        self._tokens = Redactor.from_environ(environ)
        self._paths = Redactor(_path_forms([home, environ.get("COPILOT_CLI_PATH", "")]))
        self._used: set[str] = set()
        self._kept: list[tuple[ClientLike, SessionLike]] = []
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
        for client, session in kept:
            self._release(client, session, timed_out=False)
        self._closed = True
        return ()

    def _refuse(self, request: Request, exchange_id: str, call_index: int) -> None:
        roles = [m.role for m in request.messages]
        history = roles[-1:] == ["user"] and all(r == "system" for r in roles[:-1])
        env = self._environ
        checks = (
            (self._closed, "AdapterClosed", "the model is closed"),
            (not _EXCHANGE.fullmatch(exchange_id), "InvalidExchangeId", _NO_ID),
            (bool(request.tools), "UnsupportedCall", _NO_TOOLS),
            (call_index > 0, "UnsupportedCall", _NO_INDEX),
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
            opened |= {"session_id": exchange_id, "timeout_s": self._left(end)}
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
        problem = self._collect(session, end, events) if exc is None else _send_problem(exc)
        finished = self._clock()
        reply = self._reply(events, problem)
        if reply.kind == "ok":
            self._kept.append((client, session))
        else:
            self._release(client, session, timed_out=bool(problem and problem[2]))
        message = None if reply.message is None else self._text(reply.message)[:500]
        raw = None if reply.raw is None else scrub_raw(reply.raw, self._text)
        return replace(reply, message=message, raw=raw, started_at=started, finished_at=finished)

    def _collect(self, session: SessionLike, end: float, events: list[Any]) -> _Problem | None:
        while True:
            left = self._left(end)
            envelope, exc = _try(session.next_event, timeout_s=min(self._idle, left))
            if exc is not None and not isinstance(exc, TimeoutError):
                return "AdapterError", _failure("next_event", exc), False
            if envelope is None:
                if left <= self._idle:
                    return "OverallTimeout", _OVERALL_OUT, True
                return "IdleTimeout", _IDLE_OUT, True
            events.append(envelope)
            if not isinstance(envelope, dict) or envelope.get("type") in _ENDS:
                return None

    def _reply(self, events: list[Any], problem: _Problem | None) -> Reply:
        reply = reply_from_events(events, model=self._model, redactor=self._tokens)
        sub_agent = any(isinstance(e, dict) and e.get("agentId") for e in events)
        if problem is None and reply.kind == "ok" and sub_agent:
            problem = "SubAgentEvent", "an event came from a sub-agent", False
        if problem is None:
            return reply
        error_class, message, _ = problem
        if not _has_figures(reply):
            return Reply(
                "sent_unknown", None, error_class, message, None, None, reply.raw, None, None
            )
        usage, charge = reply.usage or Usage(), reply.billed_usd
        return Reply("sent_usage", None, error_class, message, usage, charge, reply.raw, None, None)

    def _release(self, client: ClientLike, session: SessionLike, *, timed_out: bool) -> None:
        if timed_out:
            self._log_step("abort", session.abort)
        self._log_step("queued", session.queued)
        self._log_step("disconnect", session.disconnect)
        self._stop(client)

    def _stop(self, client: ClientLike) -> None:
        if not self._log_step("stop", client.stop):
            self._log_step("force_stop", client.force_stop)

    def _log_step(self, name: str, fn: Callable[..., Any]) -> bool:
        _, exc = _try(fn, timeout_s=self._bounds[name])
        if exc is not None:
            _log.warning("release step %s failed: %s", name, type(exc).__name__)
        return exc is None

    def _text(self, value: str) -> str:
        return home_paths(self._paths.text(self._tokens.text(value)))

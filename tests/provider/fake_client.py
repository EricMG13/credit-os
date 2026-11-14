"""A fake Copilot client and session in one object, driven by a case of `provider_driver_key`.
No thread, no sleep, no real time: the clock is a number the steps advance."""

import builtins
from typing import Any

from provider_driver_key import T0


class Fake:
    def __init__(self, case: dict[str, Any]) -> None:
        self.case, self.now = case, T0
        self.steps: list[str] = []
        self.bounds: dict[str, float] = {}
        self.opened: dict[str, Any] = {}
        self.sent: str | None = None
        self.given: list[float] = []  # every timeout_s given, next_event included
        self.read: list[object] = []  # the envelopes next_event handed over
        self.script: list[object] = list(case["script"])

    def clock(self) -> float:
        return self.now

    def step(self, name: str, timeout_s: float = 0, *, seen: bool = True) -> "Fake":
        self.given.append(timeout_s)
        if seen:
            self.steps.append(name)
            self.bounds[name] = timeout_s
        fail = self.case["fail"].get(name)
        if fail == "timeout":
            self.now += timeout_s
            raise TimeoutError(name)
        if fail:
            raise getattr(builtins, fail[0])(fail[1])
        self.now += self.case["takes"].get(name, 0)
        return self

    def open_client(self) -> "Fake":
        return self.step("open_client")

    def start(self, *, timeout_s: float) -> None:
        self.step("start", timeout_s)

    def list_models(self, *, timeout_s: float) -> object:
        return self.step("list_models", timeout_s).case["models"]

    def open_session(self, *, timeout_s: float, **given: Any) -> "Fake":
        self.opened = given
        return self.step("open_session", timeout_s)

    def send(self, prompt: str, *, timeout_s: float) -> None:
        self.sent = prompt
        self.step("send", timeout_s)

    def queued(self, *, timeout_s: float) -> object:
        return self.step("queued", timeout_s).case["queued"]

    def abort(self, *, timeout_s: float) -> None:
        self.step("abort", timeout_s)

    def disconnect(self, *, timeout_s: float) -> None:
        self.step("disconnect", timeout_s)

    def stop(self, *, timeout_s: float) -> None:
        self.step("stop", timeout_s)

    def force_stop(self, *, timeout_s: float) -> None:
        self.step("force_stop", timeout_s)

    def next_event(self, *, timeout_s: float) -> object | None:
        self.step("next_event", timeout_s, seen=False)
        waited = 0.0
        while self.script and type(self.script[0]) is tuple:
            gap = self.script[0][1]
            if waited + gap >= timeout_s:  # the bound ends inside this tick
                self.script[0] = ("tick", waited + gap - timeout_s)
                break
            waited += gap
            self.script.pop(0)
        else:
            if self.script:
                self.now += waited
                self.read.append(self.script[0])
                return self.script.pop(0)
        self.now += timeout_s
        return None

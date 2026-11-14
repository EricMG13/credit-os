"""What the forecast reader sends back: a refusal to repair, or the method declining."""

from enum import StrEnum


class RefusalKind(StrEnum):
    BLOCK = "block"
    JSON = "json"


class ForecastRefused(Exception):
    """The forecast inputs break a rule; the module is asked to repair them."""

    def __init__(self, kind: RefusalKind, subject: str, message: str) -> None:
        if not isinstance(kind, RefusalKind):
            raise TypeError("kind must be a RefusalKind")
        for name, text in (("subject", subject), ("message", message)):
            if not isinstance(text, str):
                raise TypeError(f"{name} must be a str")
            if not text.strip():
                raise ValueError(f"{name} must not be blank")
        super().__init__(message)
        self.kind = kind
        self.subject = subject
        self.message = message


class ForecastDeclined(Exception):
    """The handoff gives no forecast drivers: the method declines, nothing to repair."""

    def __init__(self, reason: str) -> None:
        text = "the handoff gives no forecast drivers, so no forecast was computed"
        super().__init__(f"{text} ({reason})" if reason else text)
        self.reason = reason

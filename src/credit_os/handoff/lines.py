import re

_TERMINATOR = re.compile(r"\r\n|\n|\r")


def split_lines(text: str) -> tuple[str, ...]:
    """Split on CRLF, LF or lone CR only; drop one leading BOM and the final empty piece."""
    parts = _TERMINATOR.split(text.removeprefix("\ufeff"))
    if parts[-1] == "":
        parts.pop()
    return tuple(parts)


def count_terminators(text: str) -> int:
    """How many line terminators `text` holds, by the same rule as `split_lines`."""
    return len(_TERMINATOR.findall(text))

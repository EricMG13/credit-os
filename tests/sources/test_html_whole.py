"""The line writer, fed in any event order, equals the legacy rule applied to the whole."""

import re

from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.sources.html import _LineText

_ZERO = dict.fromkeys((0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF))


def reference(events: list[tuple[str, ...]]) -> str:
    parts = [
        re.sub(r"\s+", " ", e[1]) if e[0] == "text" else " " if e[0] == "space" else "\n"
        for e in events
    ]
    lines = (re.sub(r"\s+", " ", x.translate(_ZERO)).strip() for x in "".join(parts).split("\n"))
    return "".join(f"{line}\n" for line in lines if line)


_ALPHABET = [
    " ",
    "\n",
    "\t",
    "\N{NO-BREAK SPACE}",
    "\N{LINE SEPARATOR}",
    "\x1c",
    "\N{ZERO WIDTH SPACE}",
    "\N{ZERO WIDTH NON-JOINER}",
    "\N{ZERO WIDTH JOINER}",
    "\N{WORD JOINER}",
    "\N{ZERO WIDTH NO-BREAK SPACE}",
    "a",
    "b",
    "\N{LATIN SMALL LETTER E WITH ACUTE}",
]

_EVENTS = st.lists(
    st.one_of(
        st.tuples(st.just("text"), st.text(alphabet=st.sampled_from(_ALPHABET), max_size=12)),
        st.tuples(st.just("space")),
        st.tuples(st.just("line")),
    ),
    max_size=20,
)


@settings(max_examples=1000)
@given(events=_EVENTS)
def test_line_text_equals_the_whole_rule(events: list[tuple[str, ...]]) -> None:
    lines = _LineText()
    pieces: list[str] = []
    for event in events:
        if event[0] == "text":
            lines.text(event[1])
        elif event[0] == "space":
            lines.space()
        else:
            lines.line_end()
        pieces.extend(lines.take())
    lines.line_end()
    pieces.extend(lines.take())
    assert "".join(pieces) == reference(events)

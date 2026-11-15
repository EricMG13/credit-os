"""Reading in pieces equals reading whole: the line writer, and html_pages against the legacy."""

import html.parser
import random
import re
from collections import Counter
from collections.abc import Sequence

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from credit_os.sources import SourceUnreadable, cut_pages
from credit_os.sources import html as reader
from credit_os.sources.html import BLOCK, HIDDEN, LINE_TAGS, SKIP, VOID, _LineText, html_pages

_ZERO = dict.fromkeys((0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF))
_ZERO_WIDTH = _ZERO


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


# --- html_pages against the legacy converter, on generated documents ---


# The reference: the legacy converter (legacy 8e3954a, html_text.py) fed the whole decoded text.
def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.translate(_ZERO_WIDTH)).strip()


class _Lines(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.stack: list[tuple[str, bool]] = []
        self.open_names: Counter[str] = Counter()  # open tag name -> count, keeps end tags linear
        self.skipping = 0

    def _break(self, tag: str) -> None:
        if tag in LINE_TAGS:
            self.parts.append("\n")
        elif tag in BLOCK:
            self.parts.append(" ")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "body":
            self.handle_endtag("head")  # an unclosed head ends at body
        self._break(tag)
        if tag in VOID:
            return
        hidden = tag in SKIP or any(k == "style" and HIDDEN.search(v or "") for k, v in attrs)
        self.stack.append((tag, hidden))
        self.open_names[tag] += 1
        self.skipping += hidden

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._break(tag)

    def handle_endtag(self, tag: str) -> None:
        self._break(tag)
        if tag in VOID:
            return
        if not self.open_names[tag]:
            return
        while True:
            name, hidden = self.stack.pop()
            self.open_names[name] -= 1
            self.skipping -= hidden
            if name == tag:
                return

    def handle_data(self, data: str) -> None:
        if not self.skipping:
            # Newlines inside text are plain whitespace, never a line break.
            self.parts.append(re.sub(r"\s+", " ", data))


def legacy_text(decoded: str) -> str:
    """The legacy converter's text for decoded HTML fed whole (its decoding and NUL check apart)."""
    parser = _Lines()
    parser.feed(decoded)
    parser.close()
    lines = [line for line in (_normalise(x) for x in "".join(parser.parts).split("\n")) if line]
    return "".join(f"{line}\n" for line in lines)


# The generator of documents: fragments of markup, text, references, comments, declarations and
# raw-text elements, drawn from a source of choices the test supplies for each example.
LONG_REFS = False


class _Draws:
    """The random source of the generator below; the test points it at the example's source."""

    def __init__(self) -> None:
        self.use(random.Random(0))

    def use(self, source: random.Random) -> None:
        self.random = source.random
        self.randint = source.randint
        self.choice = source.choice


rng = _Draws()


def pick(options: Sequence[str]) -> str:
    return rng.choice(options)


# fmt: off
NAMES = ["p", "div", "br", "span", "b", "td", "tr", "table", "li", "ul", "h1", "body", "head", "html", "img",
         "input", "a", "svg", "ix:header", "ix:nonfraction", "P", "DIV", "Span", "noscript", "x-y", "o:p",
         "section", "pre", "hr", "meta", "link", "form", "font"]
RAW = ["script", "style", "textarea", "title", "xmp", "iframe", "noembed", "noframes"]
WORDS = ["Revenue", "rose", "to", "100m", "FY2025", "a", "b", "net", "debt", "x"]
TEXT = [" ", " ", "\n", "\t", "\u00a0", "\u200b", "\ufeff", "\u2060", "\u00e9", "\u0436", "\U0001f600", "<", "< ", "<3",
        "a<b", "&", "& ", "&amp;", "&nbsp;", "&euro;", "&#65;", "&#x41;", "&lt", "&lt;", "&notin;", "&not", "&noti",
        "&#0;", "&#55296;", "&unknown;", "&#", "&#x", "&#;", "&Afr;", "&nGt;", "&amp", ">", "-->", "]]>", "'", '"', "=",
        "\r\n", "\x0c", "\x1c", "\u2028", "\u3000", "/>", "&#1234567", "&#x1F600;"]
ATTRS = ['class="x"', 'style="display:none"', "style='display : none'", 'STYLE="DISPLAY:NONE"', "style=display:none",
         'style="color:red"', 'style="display&colon;none"', 'style="display:&#110;one"', 'style="x', 'title="a>b"',
         "title='>'", "href=x/", "/", "checked", "=", '"', "a=b=c", 'style="display:\nnone"', "style", "style=",
         'style=""', 'data-a="&amp;"', "x='y'", 'style="displaynone"', 'style = "display:none"', "style='display:none",
         'style="display\u00a0:none"', "a='", 'b="',
         'title = "a>b"', "x = 'c>d'", 'title = "a>b"', "x = 'c>d'", 'y= "e>"', "z =\n'>'"]


def digits(maximum: int) -> str:
    return "".join(pick("0123456789") for _ in range(rng.randint(1, maximum)))


def text() -> str:
    if rng.random() < 0.5:
        return pick(WORDS)
    if rng.random() < 0.1:
        longest = 60 if LONG_REFS else 28
        return pick(["&#" + digits(longest), "&#x" + digits(longest), "&#" + digits(longest) + ";",
                     "&#x" + digits(longest) + ";", "&#000000000000000000000065;"])
    return pick(TEXT)


def attrs() -> str:
    out = []
    for _ in range(rng.choice([0, 0, 0, 1, 1, 2, 3, 6])):
        r = rng.random()
        if r < 0.75:
            out.append(pick(ATTRS))
        elif r < 0.85:
            out.append('data-x="' + "".join(pick(["Q", "A", ">", " ", "'", "=", "&amp;"]) for _ in range(rng.randint(0, 90))) + '"')
        elif r < 0.95:
            out.append('style="' + "color:red;" * rng.randint(0, 9) + pick(["display:none", "display: none;", "", "x"]) + '"')
        else:
            out.append("d=" + "".join(pick("Mz0 1,") for _ in range(rng.randint(0, 80))))
    sep = pick([" ", " ", "\n", "  ", "/", "\t"])
    return ("" if not out else pick([" ", " ", "\n", "/"]) + sep.join(out))


def name() -> str:
    r = rng.random()
    if r < 0.9:
        return pick(NAMES)
    if r < 0.95:
        return "n" + "".join(pick("abc-:.") for _ in range(rng.randint(1, 70)))
    return pick(['a"b', "a=b", "a<b", "a&amp;b", "a\u00e9", "a'"])


def start_tag() -> str:
    return "<" + name() + attrs() + pick([">", ">", ">", ">", "/>", " >", " / >", " />", "", "/ >"])


def end_tag() -> str:
    return pick(["</" + name() + ">"] * 6 + ["</" + name() + " >", "</" + name() + attrs() + ">", "</" + name() + attrs() + ">", "</" + name() + "\n>",
                "</>", "</ x>", "</3>", "</" + name(), "</"])


def comment() -> str:
    body = " ".join(pick(WORDS + ["<p>", "</div>", "--", "-", ">", "<!--", "--!", "]]>"]) for _ in range(rng.randint(0, 12)))
    return pick(["<!-- " + body + " -->"] * 5 + ["<!---->", "<!-->", "<!--->", "<!-- " + body + " --!>", "<!-- " + body,
                "<!--[if IE]>" + body + "<![endif]-->", "<!--" + body + "--", "<!--" + body + "-"])


def declaration() -> str:
    body = " ".join(pick(WORDS + ['"a>b"', "'", "[", "]", "]]", "<", "--"]) for _ in range(rng.randint(0, 12)))
    return pick(["<!DOCTYPE html>", "<!doctype html " + body + ">", "<![CDATA[" + body + "]]>", "<![if x]>", "<![endif]>",
                 "<!" + body + ">", "<?xml version='1.0'?>", "<?" + body + ">", "<?" + body + "?>", "<!", "<?", "<![CDATA[" + body,
                 "<![" + body + ">", "<!DOCTYPE " + body, "<!ELEMENT " + body + ">", "<![CDATA[]]>"])


def raw_element() -> str:
    element = pick(RAW)
    body = "".join(pick(WORDS + [" ", " ", "<", "</", "</" + element[:-1], "</p>", "<p>", "&amp;", "&", "&a", "&#65;", "<!--", "-->",
                                 "</" + element + "x", "\n", "\U0001f600", "&noti", "&#1234567"]) for _ in range(rng.randint(0, 40)))
    close = pick(["</" + element + ">"] * 5 + ["</" + element.upper() + " >", "</" + element + " x='>'>", "", "</" + element + "\n>",
                 "</" + element + "/>", "</" + element + attrs() + ">"])
    return "<" + element + attrs() + ">" + body + close


def document() -> str:
    parts = []
    for _ in range(rng.randint(3, 40)):
        r = rng.random()
        if r < 0.40: parts.append(text())
        elif r < 0.65: parts.append(start_tag())
        elif r < 0.80: parts.append(end_tag())
        elif r < 0.87: parts.append(comment())
        elif r < 0.93: parts.append(declaration())
        else: parts.append(raw_element())
    if rng.random() < 0.02:
        parts.insert(rng.randint(0, len(parts)), "<plaintext>")
    return "".join(parts)

# fmt: on


_SETTINGS = [
    pytest.param((1, 34, 35, 23), id="1-34-35-23"),
    pytest.param((5, 34, 39, 23), id="5-34-39-23"),
    pytest.param((64, 64, 128, 23), id="64-64-128-23"),
]


def _reasons_of_long_tags() -> set[str]:
    parsed = reader.PARSED_CHARACTERS
    return {
        f"a tag name longer than {parsed:,} characters",
        f"a style attribute longer than {parsed:,} characters that is not plain ASCII",
    }


# Design 4.10 row 6: "&#" and 32 decimal digits, or "&#x" and 32 hexadecimal digits, in the bytes.
# The generator can reach it by joining a reference of 28 digits to the letters of the next text.
_LONG_REFERENCE = re.compile(rb"&#(?:[0-9]{32}|[xX][0-9a-fA-F]{32})")


def _check(raw: bytes, whole: str, size: int, refusals: set[str]) -> None:
    if _LONG_REFERENCE.search(raw):
        with pytest.raises(SourceUnreadable) as caught:
            html_pages("f.html", raw)
        assert str(caught.value) == "f.html: a character reference of 32 or more digits"
        return
    try:
        result = html_pages("f.html", raw)
    except SourceUnreadable as error:
        assert str(error).removeprefix("f.html: ") in refusals
        return
    assert [page.text for page in result.pages] == list(cut_pages(whole, size))


@pytest.mark.parametrize("setting", _SETTINGS)
@settings(max_examples=300, deadline=None)
@example(source=random.Random(10167))
@given(source=st.randoms(use_true_random=False))
def test_small_pieces_equal_whole(
    setting: tuple[int, int, int, int], source: random.Random
) -> None:
    rng.use(source)
    raw = document().encode("utf-8")
    whole = legacy_text(raw.decode("utf-8-sig"))
    piece, held, parsed, page = setting
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(reader, "PIECE_BYTES", piece)
        patch.setattr(reader, "HELD_CHARACTERS", held)
        patch.setattr(reader, "PARSED_CHARACTERS", parsed)
        patch.setattr(reader, "PAGE_CHARACTERS", page)
        refusals = _reasons_of_long_tags()
        if whole == "":
            refusals.add("has no visible text")
        _check(raw, whole, page, refusals)


@settings(max_examples=300, deadline=None)
@example(source=random.Random(10167))
@given(source=st.randoms(use_true_random=False))
def test_real_constants_equal_whole(source: random.Random) -> None:
    rng.use(source)
    raw = document().encode("utf-8")
    whole = legacy_text(raw.decode("utf-8-sig"))
    _check(raw, whole, 3_000, {"has no visible text"} if whole == "" else set())

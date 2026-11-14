"""R24: the memory of parse_feed on hostile bodies within MAX_BYTES, measured with tracemalloc.

The shapes are the worst inputs of the reviewer's probe (``r24_memory.py``). Each runs at full
MAX_BYTES, or at a stated reduced size with a proportionally reduced ceiling where the shape
takes seconds. Every ceiling is far under what the shape cost before the fix and holds only if
the cause is gone: a node per element, a qualified name per element, one html.parser tag with a
million attributes, one string object per character.
"""

import gc
import tracemalloc
from collections.abc import Callable

import pytest

from credit_os.signal.feeds import MAX_BYTES, FeedError, parse_feed

MiB = 1024 * 1024
CEILING = 64 * MiB

_HEAD = b'<rss version="2.0"><channel><item><title>t</title><link>https://e.org/a</link>'
_TAIL = b"</item></channel></rss>"
_D0, _D1 = _HEAD + b"<description>", b"</description>" + _TAIL
_C0, _C1 = _HEAD + b"<description><![CDATA[", b"]]></description>" + _TAIL
_ATOM0 = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><link href="https://e.org/a"/>'
_ATOM1 = b"</entry></feed>"
_LETTER = "ж".encode()  # a 2-byte letter: one new str object per character


def _fill(pre: bytes, unit: bytes, post: bytes, size: int) -> bytes:
    return pre + unit * ((size - len(pre) - len(post)) // len(unit)) + post


def _uri_fills_body(size: int) -> bytes:
    pre, mid, post = _D0 + b'<d xmlns="u:', b'">', b"</d>" + _D1
    body = b"<a/>" * 100
    return pre + b"x" * (size - len(pre) - len(mid) - len(post) - len(body)) + mid + body + post


def _uri_and_count_grow(size: int) -> bytes:
    n = size // 128
    return _D0 + b'<d xmlns="u:' + b"x" * (n - 2) + b'">' + b"<a/>" * n + b"</d>" + _D1


def _items(unit: bytes) -> Callable[[int], bytes]:
    return lambda s: _fill(b'<rss version="2.0"><channel>', unit, b"</channel></rss>", s)


_URI256 = b"u:" + b"x" * 254

CASES: dict[str, Callable[[int], bytes]] = {
    "html one tag with a million attributes": lambda s: _fill(_C0 + b"<a ", b"b ", b">" + _C1, s),
    "html unclosed tag with attributes": lambda s: _fill(_C0 + b"<a ", b"b=c ", _C1, s),
    "html unclosed comment": lambda s: _fill(_C0 + b"<!--", b"x", _C1, s),
    "html angle brackets": lambda s: _fill(_C0, b"<", _C1, s),
    "html block tags": lambda s: _fill(_C0, b"<p>", _C1, s),
    "atom html title, one tag with a million attributes": lambda s: _fill(
        _ATOM0 + b'<title type="html"><![CDATA[<a ', b"b ", b">T]]></title>" + _ATOM1, s
    ),
    "atom html summary, one tag with a million attributes": lambda s: _fill(
        _ATOM0 + b'<title>T</title><summary type="html"><![CDATA[<a ',
        b"b ",
        b">T]]></summary>" + _ATOM1,
        s,
    ),
    "atom xhtml summary of small elements": lambda s: _fill(
        _ATOM0
        + b'<title>T</title><summary type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml">',
        b"<a/>",
        b"</div></summary>" + _ATOM1,
        s,
    ),
    "small elements": lambda s: _fill(_D0, b"<a/>", _D1, s),
    "small elements in the Atom namespace": lambda s: _fill(
        _ATOM0 + b"<title>T</title><summary>", b"<a/>", b"</summary>" + _ATOM1, s
    ),
    "small elements in a 256-character namespace": lambda s: _fill(
        _D0 + b'<d xmlns="' + _URI256 + b'">', b"<a/>", b"</d>" + _D1, s
    ),
    "100 elements in a namespace that fills the body": _uri_fills_body,
    "namespace URI and element count both grow": _uri_and_count_grow,
    "namespaced attribute on every element": lambda s: _fill(
        _D0 + b'<d xmlns:p="u:x">', b'<a p:b=""/>', b"</d>" + _D1, s
    ),
    "empty items": _items(b"<item/>"),
    "items with an empty title": _items(b"<item><title/></item>"),
    "readable items": _items(b"<item><title>t</title><link>https://e.org/a</link></item>"),
    "distinct element names": lambda s: _fill(_D0, b"<n/>", _D1, s),
    "one element with the most attributes": lambda s: _fill(_D0 + b"<e", b' a=""', b"/>" + _D1, s),
    "title of 2-byte letters": lambda s: _fill(
        b'<rss version="2.0"><channel><item><link>https://e.org/a</link><title>',
        _LETTER,
        b"</title>" + _TAIL,
        s,
    ),
    "description of 2-byte letters": lambda s: _fill(_D0, _LETTER, _D1, s),
    "text split by comments": lambda s: _fill(_D0, _LETTER + b"<!---->", _D1, s),
}


def _peak(body: bytes) -> tuple[int, object]:
    gc.collect()
    tracemalloc.start()
    try:
        try:
            result: object = parse_feed(body)
        except FeedError as exc:
            result = exc
        return tracemalloc.get_traced_memory()[1], result
    finally:
        tracemalloc.stop()


@pytest.mark.parametrize("name", list(CASES))
def test_the_peak_memory_of_a_hostile_body_stays_under_the_ceiling(name: str) -> None:
    body = CASES[name](MAX_BYTES)
    assert len(body) <= MAX_BYTES
    peak, result = _peak(body)
    assert isinstance(result, list | FeedError)
    assert peak < CEILING, f"{name}: {peak / MiB:.1f} MiB"


def test_a_genuine_feed_of_1000_xhtml_entries_of_100_elements_is_read_whole() -> None:
    content = "".join(f"<p>w{i}</p>" for i in range(100))
    entry = (
        '<entry><title>Entry {n}</title><link href="https://e.org/{n}"/>'
        '<summary type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml">{c}</div></summary>'
        "</entry>"
    )
    body = (
        '<feed xmlns="http://www.w3.org/2005/Atom">'
        + "".join(entry.format(n=n, c=content) for n in range(1000))
        + "</feed>"
    ).encode()
    assert len(body) <= MAX_BYTES
    peak, result = _peak(body)
    assert isinstance(result, list)
    assert [e.title for e in result] == [f"Entry {n}" for n in range(1000)]
    assert all(e.summary.startswith("w0 w1 w2") for e in result)
    assert peak < CEILING

"""R24: the peak memory of parse_feed on hostile bodies, measured with tracemalloc.

Every case builds a body of at most MAX_BYTES, parses it and asserts two things: the peak stays
under CEILING, and the outcome is the one the case names. A case either reads its feed (a list)
or is refused with the message of the constant that refuses it (``REFUSED``); a body that fails
for another reason, malformed XML for one, measures nothing and fails the test. The shapes are
the worst bodies found by review: a node per element, a name per element or attribute (pyexpat
keeps every distinct name for the whole parse, and a namespace URI in each name if it expands
them), one html.parser tag with a million attributes, one string object per character. The last
test reads a large genuine feed whole.
"""

import gc
import tracemalloc
from collections.abc import Callable

import pytest

from credit_os.signal.feeds import (
    MAX_ATTRIBUTES,
    MAX_BYTES,
    MAX_ELEMENTS,
    MAX_NAMESPACE_CHARS,
    FeedError,
    parse_feed,
)

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


def _numbered(pre: bytes, unit: Callable[[int], bytes], post: bytes, size: int) -> bytes:
    """``pre``, ``unit(0)``, ``unit(1)`` ... as many as fit in ``size`` bytes, then ``post``."""
    parts, room, n = [pre], size - len(pre) - len(post), 0
    while len(piece := unit(n)) <= room:
        parts.append(piece)
        room -= len(piece)
        n += 1
    return b"".join([*parts, post])


def _attribute_elements(
    uri: bytes, per_element: int, count: int | None = None, size: int = MAX_BYTES
) -> bytes:
    """Elements of ``per_element`` attributes, all names different, in namespace ``uri``.

    ``count`` elements, or as many as fit in ``size`` bytes.
    """

    def element(n: int) -> bytes:
        names = (b' p:a%d=""' % (n * per_element + k) for k in range(per_element))
        return b"<x" + b"".join(names) + b"/>"

    pre, post = _D0 + b'<d xmlns:p="' + uri + b'">', b"</d>" + _D1
    if count is None:
        return _numbered(pre, element, post, size)
    return pre + b"".join(map(element, range(count))) + post


def _namespace(chars: int, unit: str = "u") -> bytes:
    return ("u:" + unit * (chars - 2)).encode()


def _distinct_elements(uri: bytes, count: int) -> bytes:
    pre, post = _D0 + b'<d xmlns:p="' + uri + b'">', b"</d>" + _D1
    return pre + b"".join(b"<p:e%d/>" % n for n in range(count)) + post


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
    "distinct element names": lambda s: _numbered(_D0, lambda n: b"<n%d/>" % n, _D1, s),
    "one element with the most attributes": lambda s: _numbered(
        _D0 + b"<e", lambda n: b' a%d=""' % n, b"/>" + _D1, s
    ),
    "namespace declarations on one element, all prefixes different": lambda s: _numbered(
        _D0 + b"<d", lambda n: b' xmlns:p%d="u"' % n, b"/>" + _D1, s
    ),
    "256 distinct attributes on each element, 1 KiB namespace, half the body": lambda s: (
        _attribute_elements(_namespace(1024), 256, size=s // 2)
    ),
    "256 distinct attributes on each element, namespace at the limit, half the body": lambda s: (
        _attribute_elements(_namespace(MAX_NAMESPACE_CHARS), 256, size=s // 2)
    ),
    "256 distinct attributes on each element, 1 KiB namespace, whole body": lambda s: (
        _attribute_elements(_namespace(1024), 256, size=s)
    ),
    "namespace of 64 Ki characters, 6 elements of 256 distinct attributes": lambda s: (
        _attribute_elements(_namespace(65536), 256, 6)
    ),
    "namespace of 1 Mi characters, one element of 48 attributes": lambda s: _attribute_elements(
        _namespace(1048576), 48, 1
    ),
    "namespace of 16 Ki astral characters, 1000 distinct elements": lambda s: _distinct_elements(
        _namespace(16384, "\U0001f600"), 1000
    ),
    "namespace of 64 Ki astral characters, 266 elements": lambda s: _distinct_elements(
        _namespace(65536, "\U0001f600"), 266
    ),
    "title of 2-byte letters": lambda s: _fill(
        b'<rss version="2.0"><channel><item><link>https://e.org/a</link><title>',
        _LETTER,
        b"</title>" + _TAIL,
        s,
    ),
    "description of 2-byte letters": lambda s: _fill(_D0, _LETTER, _D1, s),
    "text split by comments": lambda s: _fill(_D0, _LETTER + b"<!---->", _D1, s),
}


_TOO_MANY_ELEMENTS = f"feed has more than {MAX_ELEMENTS} elements"
_TOO_MANY_ATTRIBUTES = f"feed has an element with more than {MAX_ATTRIBUTES} attributes"
_LONG_NAMES = "feed element names are too long"  # MAX_NAME_CHARS
_LONG_NAMESPACE = f"feed has a namespace URI of more than {MAX_NAMESPACE_CHARS} characters"
# The cases that are refused, with the message of the constant that refuses them.
REFUSED = {
    "atom xhtml summary of small elements": _TOO_MANY_ELEMENTS,
    "small elements": _TOO_MANY_ELEMENTS,
    "small elements in the Atom namespace": _TOO_MANY_ELEMENTS,
    "small elements in a 256-character namespace": _TOO_MANY_ELEMENTS,
    "100 elements in a namespace that fills the body": _LONG_NAMESPACE,
    "namespace URI and element count both grow": _LONG_NAMESPACE,
    "empty items": _TOO_MANY_ELEMENTS,
    "distinct element names": _LONG_NAMES,
    "one element with the most attributes": _LONG_NAMES,
    "namespace declarations on one element, all prefixes different": _LONG_NAMES,
    "256 distinct attributes on each element, 1 KiB namespace, whole body": _LONG_NAMES,
    "namespace of 64 Ki characters, 6 elements of 256 distinct attributes": _LONG_NAMESPACE,
    "namespace of 1 Mi characters, one element of 48 attributes": _LONG_NAMESPACE,
    "namespace of 16 Ki astral characters, 1000 distinct elements": _LONG_NAMESPACE,
    "namespace of 64 Ki astral characters, 266 elements": _LONG_NAMESPACE,
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
    if name in REFUSED:
        assert isinstance(result, FeedError)
        assert str(result) == REFUSED[name]
    else:
        assert isinstance(result, list), result
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

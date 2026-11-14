import time
from array import array
from collections.abc import Callable
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import cast
from xml.parsers import expat

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.signal.feeds import (
    MAX_ATTRIBUTES,
    MAX_BYTES,
    MAX_ELEMENTS,
    MAX_NAME_CHARS,
    MAX_NAMESPACE_CHARS,
    Entry,
    FeedError,
    _new_parser,
    _Node,
    _TreeBuilder,
    parse_feed,
)

_DTD_REFUSAL = "^feed declares a DTD or entities$"

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Authority opens review</title><link>https://example.org/a</link>
<pubDate>Fri, 13 Nov 2026 09:00:00 +0100</pubDate>
<description>&lt;p&gt;Phase&amp;nbsp;two   begins &amp;amp; ends.&lt;/p&gt;</description></item>
<item><title></title><link>https://example.org/b</link></item>
<item><title>Bad link</title><link>javascript:alert(1)</link></item>
<item><title>No date</title><link>https://example.org/c</link></item>
</channel></rss>"""

ATOM = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Rating action</title>
<link rel="self" href="https://example.org/self"/><link href="https://example.org/r"/>
<updated>2026-11-12T18:30:00Z</updated><summary>Downgrade.</summary></entry></feed>"""


def test_rss_entries() -> None:
    got = parse_feed(RSS)
    assert [e.title for e in got] == ["Authority opens review", "No date"]
    assert got[0].link == "https://example.org/a"
    assert got[0].published == datetime(2026, 11, 13, 8, 0, tzinfo=UTC)
    assert got[0].summary == "Phase two begins & ends."  # the non-breaking space collapses too
    assert got[1].published is None


def test_atom_entry() -> None:
    (e,) = parse_feed(ATOM)
    assert (e.title, e.link, e.summary) == ("Rating action", "https://example.org/r", "Downgrade.")
    assert e.published == datetime(2026, 11, 12, 18, 30, tzinfo=UTC)


def test_summary_is_cut_to_300_on_a_word_boundary() -> None:
    body = RSS.replace(
        b"&lt;p&gt;Phase&amp;nbsp;two   begins &amp;amp; ends.&lt;/p&gt;", b"word " * 100
    )
    s = parse_feed(body)[0].summary
    assert len(s) <= 300 and s.endswith("word") and s == " ".join(["word"] * 60)


@pytest.mark.parametrize(
    "body",
    [
        b'<?xml version="1.0"?><!DOCTYPE rss [<!ENTITY a "b">]><rss/>',
    ],
)
def test_dtd_or_entities_are_refused(body: bytes) -> None:
    with pytest.raises(FeedError, match=_DTD_REFUSAL):
        parse_feed(body)


def test_a_lower_case_doctype_is_not_xml_and_is_refused_as_such() -> None:
    # R19: no byte search, so the parser alone reads it: "<!doctype" is not a declaration.
    with pytest.raises(FeedError, match="^feed is not valid XML$"):
        parse_feed(b"<!doctype rss><rss/>")


@pytest.mark.parametrize("body", [b"not xml", b"<html><body/></html>", b""])
def test_non_feeds_are_refused(body: bytes) -> None:
    with pytest.raises(FeedError):
        parse_feed(body)


def _rss(item: str, head: str = "") -> bytes:
    return (f'{head}<rss version="2.0"><channel><item>{item}</item></channel></rss>').encode()


@pytest.mark.parametrize("bom", [True, False])
def test_utf16_dtd_is_refused_by_the_parser(bom: bool) -> None:
    text = (
        '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE rss [<!ENTITY x "INJECTED">]>'
        '<rss version="2.0"><channel><item><title>&x;</title>'
        "<link>https://e.org/a</link></item></channel></rss>"
    )
    body = text.encode("utf-16") if bom else text.encode("utf-16-le")
    with pytest.raises(FeedError, match=_DTD_REFUSAL):
        parse_feed(body)


@pytest.mark.parametrize(
    "item",
    [
        "<pubDate>Fri, 31 Dec 9999 23:59:59 -0100</pubDate>",
        "<pubDate>0001-01-01T00:00:00+01:00</pubDate>",
        "<pubDate>9999-12-31T23:59:59-01:00</pubDate>",
    ],
)
def test_out_of_range_dates_give_none(item: str) -> None:
    (e,) = parse_feed(_rss("<title>t</title><link>https://e.org/a</link>" + item))
    assert e.published is None


def test_atom_out_of_range_date_gives_none() -> None:
    body = ATOM.replace(b"2026-11-12T18:30:00Z", b"9999-12-31T23:59:59-01:00")
    assert parse_feed(body)[0].published is None


@pytest.mark.parametrize("enc", ["shift_jis", "no-such-enc"])
def test_bad_encoding_declarations_are_feed_errors(enc: str) -> None:
    body = f'<?xml version="1.0" encoding="{enc}"?><rss version="2.0"><channel/></rss>'
    with pytest.raises(FeedError, match="encoding"):
        parse_feed(body.encode())


def test_nested_title_and_xhtml_text_are_read() -> None:
    (e,) = parse_feed(
        _rss(
            '<title><a href="https://e.org/a">Linked <b>head</b></a></title>'
            "<link>https://e.org/a</link>"
        )
    )
    assert e.title == "Linked head"
    atom = (
        b'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:x="http://www.w3.org/1999/xhtml">'
        b'<entry><title type="xhtml"><x:div>Rated <x:b>down</x:b></x:div></title>'
        b'<link href="https://e.org/r"/><summary type="xhtml"><x:div>Cut.</x:div></summary>'
        b"</entry></feed>"
    )
    (a,) = parse_feed(atom)
    assert (a.title, a.summary) == ("Rated down", "Cut.")


def test_script_and_style_text_is_dropped_from_summary() -> None:
    desc = "&lt;style&gt;p{color:red}&lt;/style&gt;&lt;script&gt;evil()&lt;/script&gt;Kept"
    (e,) = parse_feed(
        _rss(f"<title>t</title><link>https://e.org/a</link><description>{desc}</description>")
    )
    assert e.summary == "Kept"


def test_iso_date_in_rss_is_accepted() -> None:
    (e,) = parse_feed(
        _rss("<title>t</title><link>https://e.org/a</link><pubDate>2026-11-12T18:30:00Z</pubDate>")
    )
    assert e.published == datetime(2026, 11, 12, 18, 30, tzinfo=UTC)


def test_entity_at_the_boundary_is_not_cut_mid_entity() -> None:
    desc = "a " * 149 + "&amp;&amp; tail"  # the first '&' decodes to character 299
    (e,) = parse_feed(
        _rss(f"<title>t</title><link>https://e.org/a</link><description>{desc}</description>")
    )
    assert "&amp" not in e.summary and "&&" in e.summary and len(e.summary) <= 300


def test_entries_with_malformed_links_are_skipped() -> None:
    links = [
        "https://example.org:abc/x",
        "https://[::1/x",
        "http://example.org:99999/x",
        "https:///x",
        "https://example.org/good",
    ]
    items = "".join(
        f"<item><title>Story {i}</title><link>{u}</link></item>" for i, u in enumerate(links)
    )
    body = f"<rss version='2.0'><channel>{items}</channel></rss>".encode()
    assert [e.link for e in parse_feed(body)] == ["https://example.org/good"]


# --- new: the parser is expat, called directly; document type and entities are refused ---

_LINK = "<link>https://e.org/a</link>"
_LAUGHS = (
    '<!DOCTYPE rss [<!ENTITY a "lol"><!ENTITY b "&a;&a;&a;&a;"><!ENTITY c "&b;&b;&b;&b;">'
    '<!ENTITY d "&c;&c;&c;&c;">]>'
)


def test_doctype_feed_is_refused() -> None:
    body = b'<!DOCTYPE rss SYSTEM "http://e.org/rss.dtd">' + _rss(f"<title>t</title>{_LINK}")
    with pytest.raises(FeedError, match=_DTD_REFUSAL):
        parse_feed(body)


def test_internal_entity_expansion_is_refused_not_expanded() -> None:
    body = _rss(f"<title>&d;</title>{_LINK}", head=_LAUGHS)
    with pytest.raises(FeedError, match=_DTD_REFUSAL):
        parse_feed(body)


def test_external_entity_is_refused() -> None:
    head = '<!DOCTYPE rss [<!ENTITY x SYSTEM "file:///etc/hostname">]>'
    with pytest.raises(FeedError, match=_DTD_REFUSAL):
        parse_feed(_rss(f"<title>&x;</title>{_LINK}", head=head))


@pytest.mark.parametrize("codec", ["utf-16", "utf-16-le", "utf-16-be"])
@pytest.mark.parametrize(
    "head",
    [
        _LAUGHS,
        '<!DOCTYPE rss [<!ENTITY x SYSTEM "file:///etc/hostname">]>',
        '<!DOCTYPE rss PUBLIC "-//X//EN" "http://e.org/x.dtd">',
        '<!DOCTYPE rss [<!ENTITY % p "<!ELEMENT a ANY>"> %p;]>',
        '<!DOCTYPE rss [<!NOTATION n SYSTEM "x"><!ENTITY u SYSTEM "u.gif" NDATA n>]>',
        '<!DOCTYPE rss [<!NOTATION n SYSTEM "x">]>',
    ],
)
def test_wide_encoded_dtds_are_refused_by_the_parser(codec: str, head: str) -> None:
    text = '<?xml version="1.0" encoding="UTF-16"?>' + head
    text += '<rss version="2.0"><channel><item><title>t</title>' + _LINK + "</item></channel></rss>"
    with pytest.raises(FeedError, match=_DTD_REFUSAL):
        parse_feed(text.encode(codec))


def test_doctype_text_inside_a_comment_or_cdata_is_read() -> None:
    # R19: only a real declaration is refused, not the text "<!DOCTYPE" in a comment or CDATA.
    for inner in ("<!-- <!DOCTYPE x> -->", "<![CDATA[<!ENTITY y 'z'>]]>"):
        (e,) = parse_feed(_rss(f"<title>t</title>{_LINK}{inner}"))
        assert e.title == "t"
    page_item = f"<title>t</title>{_LINK}<description><![CDATA[<!DOCTYPE html><p>Page</p>]]>"
    (page,) = parse_feed(_rss(page_item + "</description>"))
    assert page.summary == "Page"


def test_prefixed_elements_do_not_stand_in_for_plain_ones() -> None:
    body = (
        b'<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"'
        b' xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><item>'
        b"<atom:link>https://e.org/wrong</atom:link><dc:title>wrong</dc:title>"
        b"<title>Right</title><link>https://e.org/right</link></item>"
        b"<item><atom:title>only prefixed</atom:title><link>https://e.org/x</link></item>"
        b"</channel></rss>"
    )
    (e,) = parse_feed(body)
    assert (e.title, e.link) == ("Right", "https://e.org/right")


def test_atom_with_a_prefix_instead_of_a_default_namespace() -> None:
    body = (
        b'<a:feed xmlns:a="http://www.w3.org/2005/Atom"><a:entry><a:title>Prefixed</a:title>'
        b'<a:link href=" https://e.org/p "/><a:published>2026-11-12T18:30:00+01:00</a:published>'
        b"<a:summary>S</a:summary></a:entry></a:feed>"
    )
    (e,) = parse_feed(body)
    assert (e.title, e.link, e.summary) == ("Prefixed", "https://e.org/p", "S")
    assert e.published == datetime(2026, 11, 12, 17, 30, tzinfo=UTC)


_ATOM_URI = "http://www.w3.org/2005/Atom"
_ENTRY = '<link href="https://e.org/{n}"/>'


def _atom(inner: str, attrs: str = "") -> bytes:
    return f'<feed xmlns="{_ATOM_URI}"{attrs}>{inner}</feed>'.encode()


def test_a_prefix_rebound_inside_an_element_applies_from_that_element() -> None:
    body = _atom(
        '<entry xmlns:a="urn:other"><a:title>no</a:title><title>First</title>'
        + _ENTRY.format(n="1")
        + "</entry><entry><a:title>Second</a:title><a:link href='https://e.org/2'/></entry>",
        f' xmlns:a="{_ATOM_URI}"',
    )
    assert [(e.title, e.link) for e in parse_feed(body)] == [
        ("First", "https://e.org/1"),
        ("Second", "https://e.org/2"),
    ]


def test_a_title_link_or_entry_in_a_foreign_namespace_is_never_the_feeds() -> None:
    body = _atom(
        '<o:entry><o:title>no</o:title><o:link href="https://e.org/no"/></o:entry>'
        '<entry><o:title>no</o:title><title xmlns="urn:other">no</title>'
        '<title>Yes</title><o:link href="https://e.org/no"/><link xmlns="urn:other" href="https://e.org/no2"/>'
        '<link href="https://e.org/yes"/></entry>'
        '<entry xmlns="urn:other"><title>no</title><link href="https://e.org/no3"/></entry>',
        ' xmlns:o="urn:other"',
    )
    assert [(e.title, e.link) for e in parse_feed(body)] == [("Yes", "https://e.org/yes")]


def test_an_empty_default_namespace_undeclares_the_default() -> None:
    inner = "<title>T</title>" + _ENTRY.format(n="1")
    assert parse_feed(_atom(f'<entry xmlns="">{inner}</entry>')) == []
    assert len(parse_feed(_atom(f"<entry>{inner}</entry>"))) == 1


def test_an_attribute_without_a_prefix_is_in_no_namespace() -> None:
    # The default namespace does not reach attributes, so rel and href are read as written.
    body = _atom(
        "<entry><title>T</title>"
        '<link rel="enclosure" href="https://e.org/no"/><link href="https://e.org/yes"/></entry>'
    )
    assert [e.link for e in parse_feed(body)] == ["https://e.org/yes"]


def test_namespace_declarations_are_not_attributes() -> None:
    declarations = "".join(f' xmlns:p{n}="urn:{n}"' for n in range(MAX_ATTRIBUTES + 40))
    plain = "".join(f' a{n}=""' for n in range(MAX_ATTRIBUTES))
    body = _atom("<entry><title>T</title>" + _ENTRY.format(n="1") + "</entry>", declarations)
    assert len(parse_feed(body)) == 1
    body = _atom(f"<x{declarations}{plain}/>")
    assert parse_feed(body) == []
    with pytest.raises(FeedError, match=f"more than {MAX_ATTRIBUTES} attributes"):
        parse_feed(_atom(f'<x{declarations}{plain} one-more=""/>'))


@pytest.mark.parametrize(
    "inner",
    [
        "<q:x/>",  # unbound element prefix
        '<x q:a=""/>',  # unbound attribute prefix
        '<x xmlns:p="u"/><p:y/>',  # a prefix is unbound once its element closes
        '<x xmlns:p="u" xmlns:q="u" p:a="" q:a=""/>',  # one expanded name twice
        '<x xmlns:p=""/>',  # a prefix cannot be bound to nothing
        '<x xmlns:xml="urn:other"/>',
        '<x xmlns:xmlns="urn:x"/>',
        '<x xmlns:p="http://www.w3.org/XML/1998/namespace"/>',
        '<x xmlns="http://www.w3.org/2000/xmlns/"/>',
        "<:x/>",
        "<x:/>",
        '<x xmlns:x="u"><x:y:z/></x>',
        '<x xmlns:x="u"><x:1/></x>',
        '<x :a=""/>',
    ],
)
def test_a_name_expat_would_refuse_in_namespace_mode_is_refused(inner: str) -> None:
    with pytest.raises(FeedError, match="not valid XML"):
        parse_feed(_atom(inner))


def test_the_xml_prefix_is_always_bound() -> None:
    body = _atom(
        '<entry xml:lang="en"><xml:note/><title xml:space="preserve">T</title>'
        + _ENTRY.format(n="1")
        + '</entry><x xmlns:xml="http://www.w3.org/XML/1998/namespace"/>',
        ' xml:base="http://e.org/"',
    )
    assert [e.title for e in parse_feed(body)] == ["T"]


def test_a_namespace_uri_is_refused_beyond_the_limit() -> None:
    at_limit = "u:" + "x" * (MAX_NAMESPACE_CHARS - 2)

    def rss(attr: str, uri: str) -> bytes:
        return f'<rss version="2.0" {attr}="{uri}"><channel/></rss>'.encode()

    assert parse_feed(rss("xmlns:p", at_limit)) == []
    for attr in ("xmlns:p", "xmlns"):
        with pytest.raises(FeedError, match=f"more than {MAX_NAMESPACE_CHARS} characters"):
            parse_feed(rss(attr, at_limit + "x"))


# --- the namespace rules against expat's own: the reader treats the same elements as its own ---

# Children are drawn from the names the reader looks for below their parent, so that generated
# documents are often feeds; the declarations and prefixes are what vary.
_BELOW = {
    "": ("rss", "feed"),
    "rss": ("channel", "x"),
    "channel": ("item", "x"),
    "item": ("title", "link", "x"),
    "feed": ("entry", "x"),
    "entry": ("title", "link", "x"),
}
_URIS = (None, None, "", _ATOM_URI, _ATOM_URI, "urn:other")
_ATTRIBUTES = ('rel="alternate"', 'href="https://e.org/x"', 'xml:lang="en"', 'a:rel="x"', 'b:y=""')
_Element = tuple[str, str | None, tuple[str | None, ...], tuple[str, ...], tuple[object, ...]]


@st.composite
def _element(draw: st.DrawFn, parent: str = "", depth: int = 0) -> _Element:
    local = draw(st.sampled_from(_BELOW.get(parent, ("x", "title"))))
    prefix = draw(st.sampled_from((None, None, "a", "b")))
    declared = tuple(draw(st.sampled_from(_URIS)) for _ in range(3))  # xmlns, xmlns:a, xmlns:b
    attrs = tuple(draw(st.lists(st.sampled_from(_ATTRIBUTES), unique=True, max_size=3)))
    count = draw(st.integers(0, 3)) if depth < 4 else 0
    children = tuple(draw(_element(local, depth + 1)) for _ in range(count))
    return local, prefix, declared, attrs, children


def _render(element: _Element) -> str:
    local, prefix, declared, attrs, children = element
    names = ("xmlns", "xmlns:a", "xmlns:b")
    declarations = [
        f'{n}="{uri}"' for n, uri in zip(names, declared, strict=True) if uri is not None
    ]
    name = f"{prefix}:{local}" if prefix else local
    inner = "".join(_render(cast(_Element, child)) for child in children)
    return f"<{' '.join([name, *declarations, *attrs])}>{inner}</{name}>"


def _expected_kind(parent: str | None, name: str, seen: set[str]) -> str | None:
    """What the reader should make of ``name`` below ``parent``, from expat's "uri}local" names."""
    atom = f"{_ATOM_URI}}}"
    if parent == "document":
        return {"rss": "rss", f"{atom}feed": "feed"}.get(name, "other")
    below = {
        "rss": {"channel": "channel"},
        "channel": {"item": "item"},
        "feed": {f"{atom}entry": "entry"},
        "item": dict.fromkeys(("title", "link", "pubDate", "description"), "field"),
        "entry": dict.fromkeys(
            (f"{atom}{k}" for k in ("published", "updated", "title", "summary")), "field"
        ),
    }
    kind = below.get(parent or "", {}).get(name)
    if kind == "field":
        if name in seen:  # the first of two fields of a name wins
            return None
        seen.add(name)
    return kind


def _expat_kinds(body: bytes) -> list[str | None] | None:
    """Per element, in document order, what the reader should make of it; None if refused."""
    kinds: list[str | None] = []
    stack: list[tuple[str | None, set[str]]] = [("document", set())]

    def start(name: str, attrs: dict[str, str]) -> None:
        parent, seen = stack[-1]
        kind = _expected_kind(parent, name, seen)
        kinds.append(kind)
        stack.append((kind, set()))

    parser = expat.ParserCreate(namespace_separator="}")
    parser.StartElementHandler = start
    parser.EndElementHandler = lambda name: stack.pop()
    try:
        parser.Parse(body, True)
    except expat.ExpatError:
        return None
    return kinds


def _reader_kinds(body: bytes) -> list[str | None] | None:
    """Per element, what the tree builder made of it (a node's kind, "field", or None)."""
    builder = _TreeBuilder()
    kinds: list[str | None] = []

    def start(name: str, attrs: dict[str, str]) -> None:
        builder.start(name, attrs)
        kept = builder._open[-1]  # the smallest seam: what _enter returned for this element
        kinds.append(kept.kind if isinstance(kept, _Node) else "field" if kept else None)

    parser = _new_parser(builder)
    parser.StartElementHandler = start
    try:
        parser.Parse(body, True)
    except FeedError:
        return None
    return kinds


@settings(max_examples=400, deadline=None)
@given(_element())
def test_the_reader_treats_the_elements_expat_namespace_mode_names_as_the_feeds_as_its_own(
    document: _Element,
) -> None:
    body = _render(document).encode()
    assert _reader_kinds(body) == _expat_kinds(body)


@pytest.mark.parametrize(
    "body",
    [
        b'<feed xmlns="http://example.org/other"><entry/></feed>',
        b'<rss xmlns="http://example.org/other" version="2.0"><channel/></rss>',
        b'<x:rss xmlns:x="http://example.org/other"><channel/></x:rss>',
    ],
)
def test_feed_elements_in_the_wrong_namespace_are_refused(body: bytes) -> None:
    with pytest.raises(FeedError, match="neither an RSS 2.0 nor an Atom"):
        parse_feed(body)


def test_atom_link_rel_alternate_and_missing_href() -> None:
    body = (
        b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>T</title>'
        b'<link rel="enclosure" href="https://e.org/enc"/>'
        b'<link rel="alternate" href="https://e.org/alt"/></entry>'
        b"<entry><title>No link</title><link/></entry></feed>"
    )
    (e,) = parse_feed(body)
    assert e.link == "https://e.org/alt"


def test_cdata_is_literal_text() -> None:
    body = _rss(
        "<title><![CDATA[A &amp; B <i>x</i>]]></title>"
        + _LINK
        + "<description><![CDATA[<p>Bold <b>word</b> &amp; more</p>]]></description>"
    )
    (e,) = parse_feed(body)
    assert e.title == "A &amp; B <i>x</i>"  # CDATA is not decoded, and a title is not HTML
    assert e.summary == "Bold word & more"


def test_mixed_content_comments_and_processing_instructions() -> None:
    body = _rss("<title>Pre <b>mid</b> post<!-- hidden -->tail<?pi ignored?>end</title>" + _LINK)
    (e,) = parse_feed(body)
    assert e.title == "Pre mid posttailend"


def test_text_split_around_references_is_joined() -> None:
    body = _rss("<title>a&amp;b&lt;c&#x41;&#66;d</title>" + _LINK)
    (e,) = parse_feed(body)
    assert e.title == "a&b<cABd"


def test_character_references_decode_once_in_a_title_and_twice_in_a_summary() -> None:
    body = _rss(
        "<title>x &#38; y &amp;#38; z</title>"
        + _LINK
        + "<description>&amp;#38; &amp;amp; &amp;#x41; &#38;amp;</description>"
    )
    (e,) = parse_feed(body)
    assert e.title == "x & y &#38; z"
    assert e.summary == "& & A &"


def test_utf8_byte_order_mark_is_skipped() -> None:
    (e,) = parse_feed(b"\xef\xbb\xbf" + _rss("<title>Bom</title>" + _LINK))
    assert e.title == "Bom"


def test_utf16_byte_order_mark_feed_is_read() -> None:
    text = (
        '<?xml version="1.0" encoding="UTF-16"?>' + _rss("<title>Wide é</title>" + _LINK).decode()
    )
    (e,) = parse_feed(text.encode("utf-16"))
    assert e.title == "Wide é"


def test_encoding_declared_in_the_prolog_is_used() -> None:
    head = '<?xml version="1.0" encoding="ISO-8859-1"?>'
    body = (head + _rss("<title>Caf\xe9 \xfc</title>" + _LINK).decode()).encode("latin-1")
    (e,) = parse_feed(body)
    assert e.title == "Caf\xe9 \xfc"


def test_multibyte_text_with_a_utf8_declaration() -> None:
    head = '<?xml version="1.0" encoding="utf-8"?>'
    body = (head + _rss("<title>Café 日本</title>" + _LINK).decode()).encode()
    (e,) = parse_feed(body)
    assert e.title == "Café 日本"


@pytest.mark.parametrize(
    "body",
    [
        b'<rss version="2.0"><channel><item><title>\xff\xfe</title></item></channel></rss>',
        (
            b'<?xml version="1.0" encoding="utf-8"?><rss><channel><item><title>\xc3</title>'
            b"</item></channel></rss>"
        ),
        b"\xff\xff\xff",
    ],
)
def test_invalid_utf8_is_refused(body: bytes) -> None:
    with pytest.raises(FeedError, match="not valid XML"):
        parse_feed(body)


def test_latin1_bytes_under_a_utf8_declaration_are_refused() -> None:
    body = b'<?xml version="1.0" encoding="utf-8"?><rss><channel>\xe9</channel></rss>'
    with pytest.raises(FeedError, match="not valid XML"):
        parse_feed(body)


@pytest.mark.parametrize(
    "body",
    [
        b'<rss version="2.0"><channel><item><title>t</title></channel></rss>',  # mismatched
        b'<rss version="2.0"><channel>',  # truncated
        b'<rss version="2.0"><channel/></rss><rss/>',  # two roots
        b'<rss version="2.0"><channel/></rss>junk',  # trailing text
        b'<rss version="2.0"><channel><item><title>&nbsp;</title></item></channel></rss>',
        b'<rss version="2.0"><channel><item><link a="1" a="2"/></item></channel></rss>',
        b'<rss version="2.0"><channel><item><title>a < b</title></item></channel></rss>',
        b"<rss:x/>",  # undeclared prefix
        b"<?xml version='1.0'?>",  # no element
    ],
)
def test_malformed_xml_is_refused(body: bytes) -> None:
    with pytest.raises(FeedError, match="not valid XML"):
        parse_feed(body)


def test_very_deep_nesting_is_refused() -> None:
    title = "<b>" * 5000 + "deep" + "</b>" * 5000
    with pytest.raises(FeedError, match="deeper than 64"):
        parse_feed(_rss(f"<title>{title}</title>" + _LINK))


def test_items_keep_feed_order_across_channels() -> None:
    body = (
        b'<rss version="2.0"><channel><item><title>One</title><link>https://e.org/1</link></item>'
        b"</channel><channel><item><title>Two</title><link>https://e.org/2</link></item>"
        b"</channel><item><title>Stray</title><link>https://e.org/3</link></item></rss>"
    )
    assert [e.title for e in parse_feed(body)] == ["One", "Two"]


@pytest.mark.parametrize(
    "head",
    [
        '<!DOCTYPE rss [<!ENTITY % p "<!ELEMENT a ANY>"> %p;]>',
        '<!DOCTYPE rss [<!ENTITY % p SYSTEM "http://e.org/p.ent"> %p;]>',
        '<!DOCTYPE rss [<!ENTITY u SYSTEM "u.gif" NDATA n>]>',
        '<!DOCTYPE rss [<!NOTATION n SYSTEM "x">]>',
        '<!DOCTYPE rss [<!NOTATION n PUBLIC "-//X//EN">]>',
    ],
)
def test_parameter_unparsed_and_notation_declarations_are_refused(head: str) -> None:
    with pytest.raises(FeedError, match=_DTD_REFUSAL):
        parse_feed(_rss("<title>t</title>" + _LINK, head=head))


def test_ten_thousand_levels_of_nesting_are_refused_within_the_bound() -> None:
    depth = 10_000
    start = time.perf_counter()
    inner = "<b>" * depth + "deep" + "</b>" * depth
    with pytest.raises(FeedError, match="deeper than 64"):
        parse_feed(_rss(f"<title>{inner}</title>" + _LINK))
    stray = b'<rss version="2.0">' + b"<a>" * depth + b"</a>" * depth + b"</rss>"
    with pytest.raises(FeedError, match="deeper than 64"):
        parse_feed(stray)
    assert time.perf_counter() - start < 10.0


def test_a_very_long_attribute_returns_within_the_bound() -> None:
    start = time.perf_counter()
    href = "https://e.org/" + "a" * 1_900_000
    body = (
        '<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>T</title>'
        f'<link href="{href}"/></entry></feed>'
    ).encode()
    assert parse_feed(body) == []
    assert time.perf_counter() - start < 10.0


# --- review batch (S-3a): rulings R7 to R10 and the task review's Lows ---


def _link_body(link: str, title: str = "t") -> bytes:
    return _rss(f"<title>{title}</title><link>{link}</link>")


@pytest.mark.parametrize(
    "link",
    [
        "https://evil.example\\@www.reuters.com/markets/x",
        "https://evil.example\\\\@www.reuters.com/x",
        "https://www.reuters.com@evil.example/x",
        "https://user:pass@e.org/x",
        "https://%65vil.example/x",
        "https://\uff45vil.example/x",
        "https://e.org\u3002evil.example/x",
        "https://e.org\\x",
    ],
)
def test_links_with_a_backslash_userinfo_percent_or_non_ascii_authority_are_unusable(
    link: str,
) -> None:
    assert parse_feed(_link_body(link)) == []


def test_at_percent_and_backslash_after_the_authority_are_allowed() -> None:
    link = "https://e.org/a%20b?q=a@b#c\\d"
    assert [e.link for e in parse_feed(_link_body(link))] == [link]


def test_a_link_of_2048_characters_is_usable_and_2049_is_not() -> None:
    pad = "a" * (2048 - len("https://e.org/"))
    assert [e.link for e in parse_feed(_link_body("https://e.org/" + pad))] == [
        "https://e.org/" + pad
    ]
    assert parse_feed(_link_body("https://e.org/" + pad + "a")) == []


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Moody\u2019s cuts \u202eDCBA\u202c outlook", "Moody\u2019s cuts DCBA outlook"),
        ("Fitch&#x200b; affirms", "Fitch affirms"),
        ("a&#x7f;b", "ab"),
        ("a&#x9b;b", "ab"),
        ("&#x2066;x&#x2069;", "x"),
        ("a\tb\nc", "a b c"),
    ],
)
def test_titles_drop_control_and_format_characters_and_keep_whitespace_breaks(
    raw: str, expected: str
) -> None:
    (e,) = parse_feed(_link_body("https://e.org/a", raw))
    assert e.title == expected


def test_a_title_of_only_format_characters_leaves_no_entry() -> None:
    assert parse_feed(_link_body("https://e.org/a", "&#x200b;&#x202e;")) == []


def test_titles_are_cut_to_500_characters() -> None:
    (exact,) = parse_feed(_link_body("https://e.org/a", "w" * 500))
    (over,) = parse_feed(_link_body("https://e.org/a", "w" * 501))
    assert exact.title == "w" * 500
    assert over.title == "w" * 500


_PAD_HEAD = b'<rss version="2.0"><channel><item><title>t</title><link>https://e.org/a</link>'
_PAD_TAIL = b"</item></channel></rss>"


def _padded(size: int) -> bytes:
    filler = size - len(_PAD_HEAD) - len(_PAD_TAIL) - len(b"<!---->")
    return _PAD_HEAD + b"<!--" + b"x" * filler + b"-->" + _PAD_TAIL


def test_a_body_of_exactly_two_mebibytes_is_read_and_one_byte_more_is_refused() -> None:
    assert MAX_BYTES == 2 * 1024 * 1024
    at_cap = _padded(2 * 1024 * 1024)
    assert len(at_cap) == 2 * 1024 * 1024
    assert [e.title for e in parse_feed(at_cap)] == ["t"]
    with pytest.raises(FeedError, match="larger than 2 MiB"):
        parse_feed(_padded(2 * 1024 * 1024 + 1))


def test_the_size_cap_is_checked_before_any_parsing() -> None:
    with pytest.raises(FeedError, match="larger than 2 MiB"):
        parse_feed(b"x" * (2 * 1024 * 1024 + 1))


def _nested(levels: int, closed: bool = True) -> bytes:
    inner = b"<a>" * (levels - 1)
    tail = b"</a>" * (levels - 1) + b"</rss>" if closed else b""
    return b'<rss version="2.0">' + inner + tail


def test_nesting_of_64_elements_is_read_and_65_is_refused() -> None:
    assert parse_feed(_nested(64)) == []
    with pytest.raises(FeedError, match="deeper than 64"):
        parse_feed(_nested(65))


def test_the_depth_limit_acts_when_the_65th_level_opens() -> None:
    with pytest.raises(FeedError, match="deeper than 64"):
        parse_feed(_nested(65, closed=False))
    with pytest.raises(FeedError, match="not valid XML"):
        parse_feed(_nested(64, closed=False))


def test_text_from_the_feed_in_an_error_message_is_cut_to_120_characters() -> None:
    prefix = "feed uses an unsupported text encoding ("
    body = f'<?xml version="1.0" encoding="{"A" * 5000}"?><rss version="2.0"/>'
    with pytest.raises(FeedError) as caught:
        parse_feed(body.encode())
    message = str(caught.value)
    assert message.startswith(prefix)
    assert message.endswith(")")
    assert len(message.removeprefix(prefix).removesuffix(")")) == 120


@pytest.mark.parametrize(
    ("name", "args"),
    [
        ("StartDoctypeDeclHandler", ("rss", None, None, 0)),
        ("EntityDeclHandler", ("x", 0, "v", None, None, None, None)),
        ("ExternalEntityRefHandler", ("ctx", None, "sys", None)),
        ("UnparsedEntityDeclHandler", ("u", None, "u.gif", None, "n")),
        ("NotationDeclHandler", ("n", None, "x", None)),
    ],
)
def test_each_refusal_handler_the_parser_installs_refuses_on_its_own(
    name: str, args: tuple[object, ...]
) -> None:
    handler = getattr(_new_parser(_TreeBuilder()), name)
    with pytest.raises(FeedError, match=_DTD_REFUSAL):
        handler(*args)


@pytest.mark.parametrize(
    "body",
    [
        b"<?xml version='1.0'?>",
        b"<!-- only a comment -->",
        b"<?pi only?>",
        b'<rss version="2.0"/><rss version="2.0"/>',
    ],
)
def test_no_root_and_a_second_root_are_refused_as_invalid_xml(body: bytes) -> None:
    with pytest.raises(FeedError, match="^feed is not valid XML$"):
        parse_feed(body)


def test_items_and_entries_are_taken_only_from_a_channel_and_from_the_feed() -> None:
    link = "<link>https://e.org/a</link>"
    rss = f'<rss version="2.0"><x><item><title>t</title>{link}</item></x></rss>'.encode()
    atom = (
        b'<feed xmlns="http://www.w3.org/2005/Atom"><x><entry><title>t</title>'
        b'<link href="https://e.org/a"/></entry></x></feed>'
    )
    assert parse_feed(rss) == []
    assert parse_feed(atom) == []


def test_a_channel_image_and_an_atom_source_are_not_entries() -> None:
    rss = (
        b'<rss version="2.0"><channel><image><title>Logo</title><link>https://e.org/i</link>'
        b"</image><item><title>Real</title><link>https://e.org/r</link></item></channel></rss>"
    )
    atom = (
        b'<feed xmlns="http://www.w3.org/2005/Atom"><source><title>Logo</title>'
        b'<link href="https://e.org/i"/></source><entry><title>Real</title>'
        b'<link href="https://e.org/r"/></entry></feed>'
    )
    assert [e.title for e in parse_feed(rss)] == ["Real"]
    assert [e.title for e in parse_feed(atom)] == ["Real"]


def test_the_first_of_two_titles_wins() -> None:
    (e,) = parse_feed(_rss("<title>First</title><title>Second</title>" + _LINK))
    assert e.title == "First"


def test_atom_published_takes_priority_over_updated() -> None:
    body = (
        b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>T</title>'
        b'<link href="https://e.org/a"/><updated>2026-11-12T18:30:00Z</updated>'
        b"<published>2026-11-01T08:00:00Z</published></entry></feed>"
    )
    (e,) = parse_feed(body)
    assert e.published == datetime(2026, 11, 1, 8, 0, tzinfo=UTC)


# --- whole-branch review (S-3a), R17: block-level elements do not fuse in a summary ---


def _summary_of(description: str) -> str:
    item = (
        "<title>t</title><link>https://e.org/a</link>"
        f"<description><![CDATA[{description}]]></description>"
    )
    (e,) = parse_feed(_rss(item))
    return e.summary


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        (
            "London, 13 November 2026<br/><br/>Example Ratings has downgraded Issuer SA to BB+.",
            "London, 13 November 2026 Example Ratings has downgraded Issuer SA to BB+.",
        ),
        (
            "<h2>Rating action</h2><p>Outlook revised to negative</p>",
            "Rating action Outlook revised to negative",
        ),
        (
            "<ul><li>Covenant breach</li><li>Liquidity shortfall</li></ul>",
            "Covenant breach Liquidity shortfall",
        ),
        (
            (
                "<table><tr><th>Year</th><th>Leverage</th></tr>"
                "<tr><td>2026</td><td>5.2x</td></tr></table>"
            ),
            "Year Leverage 2026 5.2x",
        ),
        (
            "<p>Breaches reported in the year: 4</p><p>5 further cases are under review.</p>",
            "Breaches reported in the year: 4 5 further cases are under review.",
        ),
        (
            (
                '<div class="body"><p>Consultation on liquidity reporting</p></div>'
                '<div class="date">13 November 2026</div>'
            ),
            "Consultation on liquidity reporting 13 November 2026",
        ),
        (
            (
                "<section>One</section><article>Two</article><figure>Three</figure>"
                "<figcaption>Four</figcaption><dl><dt>Five</dt><dd>Six</dd></dl>"
            ),
            "One Two Three Four Five Six",
        ),
        # controls: inline tags and blocks already separated by white space
        (
            "<p>Phase <b>two</b> of H<sub>2</sub>O and <b>B</b>old begins.</p>",
            "Phase two of H2O and Bold begins.",
        ),
        ("<p>First paragraph.</p>\n<p>Second paragraph.</p>", "First paragraph. Second paragraph."),
    ],
)
def test_block_level_elements_do_not_fuse_in_a_summary(description: str, expected: str) -> None:
    assert _summary_of(description) == expected


@pytest.mark.parametrize(
    "tag",
    [
        *("p", "br", "div", "li", "ul", "ol", "dl", "dt", "dd", "table", "tr", "td", "th"),
        *("thead", "tbody", "tfoot", "caption", "h1", "h2", "h3", "h4", "h5", "h6"),
        *("blockquote", "pre", "hr", "section", "article", "header", "footer", "figure"),
        "figcaption",
    ],
)
def test_every_block_level_tag_separates_the_text_around_it(tag: str) -> None:
    assert _summary_of(f"before<{tag}>inside</{tag}>after") == "before inside after"


@pytest.mark.parametrize("tag", ["b", "i", "span", "a", "sub", "em", "code"])
def test_inline_tags_do_not_separate_the_text_around_them(tag: str) -> None:
    assert _summary_of(f"before<{tag}>inside</{tag}>after") == "beforeinsideafter"


# --- whole-branch review (S-3a), second batch: R18, R20, R7b, R8b and the test-strength gaps ---

_ATOM_HEAD = b'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:x="http://www.w3.org/1999/xhtml">'


def _atom_one(title: str, summary: str = "") -> Entry:
    body = (
        f'{_ATOM_HEAD.decode()}<entry>{title}<link href="https://e.org/a"/>{summary}</entry></feed>'
    ).encode()
    (e,) = parse_feed(body)
    return e


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("<title>R&amp;D &lt;b&gt;x&lt;/b&gt;</title>", "R&D <b>x</b>"),
        ('<title type="text">R&amp;D &lt;b&gt;x&lt;/b&gt;</title>', "R&D <b>x</b>"),
        (
            (
                '<title type="html">Moody&amp;#8217;s cuts Issuer &amp;amp; Co '
                "&lt;em&gt;now&lt;/em&gt;</title>"
            ),
            "Moody\u2019s cuts Issuer & Co now",
        ),
        (
            '<title type="xhtml"><x:div>Rated <x:b>down</x:b> &amp;amp; out</x:div></title>',
            "Rated down &amp; out",
        ),
        ('<title type="xhtml"><x:p>One</x:p><x:p>Two</x:p></title>', "One Two"),
    ],
)
def test_atom_title_type_decides_whether_it_is_markup(title: str, expected: str) -> None:
    assert _atom_one(title).title == expected


@pytest.mark.parametrize(
    ("summary", "expected"),
    [
        (
            '<summary type="text">Margin &lt;5% &amp;amp; falling; see &lt;Table 2&gt;</summary>',
            "Margin <5% &amp; falling; see <Table 2>",
        ),
        ("<summary>Margin &lt;5% &amp; falling</summary>", "Margin <5% & falling"),
        (
            '<summary type="html">Leverage &lt;b&gt;high&lt;/b&gt; &amp;amp; rising</summary>',
            "Leverage high & rising",
        ),
        (
            (
                '<summary type="xhtml"><x:div><x:p>Outlook negative</x:p>'
                "<x:p>Liquidity short</x:p></x:div></summary>"
            ),
            "Outlook negative Liquidity short",
        ),
    ],
)
def test_atom_summary_type_decides_whether_it_is_markup(summary: str, expected: str) -> None:
    assert _atom_one("<title>T</title>", summary).summary == expected


@pytest.mark.parametrize("method", ["goahead", "close"])
def test_a_failure_inside_the_html_stripper_is_a_feed_error(
    monkeypatch: pytest.MonkeyPatch, method: str
) -> None:
    """R20. Real standard libraries before the 2025 fixes raise AssertionError from html.parser
    on some markup; the installed one does not, so this test makes ``HTMLParser.goahead`` (which
    reading text calls) or ``HTMLParser.close`` raise it.
    """

    def failing(self: HTMLParser, *args: str) -> None:
        raise AssertionError("unexpected parser state")

    monkeypatch.setattr(HTMLParser, method, failing)
    body = _rss(f"<title>t</title>{_LINK}<description>text</description>")
    with pytest.raises(FeedError, match="^feed text could not be read$"):
        parse_feed(body)


@pytest.mark.parametrize(
    "link",
    [
        "https://127.0.0.1/x",
        "https://0x7f.1/x",
        "https://0x7f.0.0.1/x",
        "https://0177.0.0.1/x",
        "https://2130706433/x",
        "https://1.2.3.4.5/x",
        "https://[::1]:8443/x",
        "https://[::ffff:127.0.0.1]/x",
        "https://localhost/x",
        "https://intranet/x",
        "https://e.org./x",
        "https://.e.org/x",
        "https://e..org/x",
        "https://e.org evil/x",
        "https://e_x.org/x",
        "https://e.org^x/",
        "https://[v1.x]/",
    ],
)
def test_a_link_host_must_be_a_dns_name(link: str) -> None:
    assert parse_feed(_link_body(link)) == []


@pytest.mark.parametrize(
    "link",
    [
        "https://e.org/x",
        "https://news.example.co.uk:8443/x?q=1",
        "https://xn--bcher-kva.example/x",
        "https://my-site.example/x",
        "https://e.org2/x",
        "https://1.example/x",
        "HTTPS://E.ORG/x",
        "https://e.org/\u00fcbersicht",
    ],
)
def test_a_dns_name_host_is_usable(link: str) -> None:
    assert [e.link for e in parse_feed(_link_body(link))] == [link]


def test_a_link_with_port_zero_is_unusable() -> None:
    assert parse_feed(_link_body("https://e.org:0/x")) == []


def test_a_link_on_its_own_lines_is_read() -> None:
    body = _rss("<title>t</title><link>\n   https://e.org/a\n</link>")
    assert [e.link for e in parse_feed(body)] == ["https://e.org/a"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Outlook &#x202e;evitagen&#x202c; a&#x200b;b c", "Outlook evitagen ab c"),
        ("Outlook \u202eevitagen\u202c a\u200bb c\x9bd\x7fe", "Outlook evitagen ab cde"),
    ],
)
def test_summaries_drop_control_and_format_characters(raw: str, expected: str) -> None:
    assert _summary_of(raw) == expected


def test_a_summary_keeps_tab_and_newline_as_breaks() -> None:
    assert _summary_of("a\tb\nc") == "a b c"


def test_a_title_is_stripped_again_after_the_500_character_cut() -> None:
    (e,) = parse_feed(_link_body("https://e.org/a", "w" * 499 + " next"))
    assert e.title == "w" * 499


def test_atom_titles_drop_control_and_format_characters() -> None:
    assert _atom_one("<title>Rated &#x202e;DCBA&#x202c; down</title>").title == "Rated DCBA down"


def test_a_date_with_no_zone_is_read_as_utc() -> None:
    (rss,) = parse_feed(
        _rss("<title>t</title>" + _LINK + "<pubDate>Fri, 13 Nov 2026 09:00:00</pubDate>")
    )
    assert rss.published == datetime(2026, 11, 13, 9, 0, tzinfo=UTC)
    atom = _atom_one("<title>T</title><updated>2026-11-12T18:30:00</updated>")
    assert atom.published == datetime(2026, 11, 12, 18, 30, tzinfo=UTC)


_TZSET: Callable[[], None] | None = getattr(time, "tzset", None)


@pytest.mark.skipif(_TZSET is None, reason="the local zone cannot be set here")
def test_a_date_with_no_zone_is_utc_whatever_the_local_zone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _TZSET is not None
    monkeypatch.setenv("TZ", "Asia/Tokyo")
    _TZSET()
    try:
        (e,) = parse_feed(
            _rss("<title>t</title>" + _LINK + "<pubDate>2026-11-12T18:30:00</pubDate>")
        )
    finally:
        monkeypatch.undo()
        _TZSET()
    assert e.published == datetime(2026, 11, 12, 18, 30, tzinfo=UTC)


def test_a_summary_of_300_characters_is_kept_and_301_are_cut() -> None:
    assert _summary_of("x" * 300) == "x" * 300
    assert _summary_of("x" * 301) == "x" * 300
    # With a space inside, a 300-character summary ends a word and is kept whole (L-3: a `<`
    # for `<=` at the boundary would cut its last word); one character more is cut at the space.
    spaced = "x" * 149 + " " + "y" * 150
    assert len(spaced) == 300
    assert _summary_of(spaced) == spaced
    assert _summary_of(spaced + "z") == "x" * 149


# --- S-3a re-review: R7b amended, R18 amended, R26 and the 300-character boundary ---


@pytest.mark.parametrize(
    "host",
    [
        "1.2.3.0x7f",
        "127.0.0.0x1",
        "0x7f.0.0.0x1",
        "0x7f.0x0.0x0.0x1",
        "10.0.0.0X1",
        "192.168.0.0x1",
        "1.2.3.0x",
        "e.0x",
        "e.0xff",
        "169.254.169.0xfe",
    ],
)
def test_a_host_whose_last_label_is_a_hex_number_is_unusable(host: str) -> None:
    # A browser reads such a host as an IPv4 address ("127.0.0.0x1" is 127.0.0.1).
    assert parse_feed(_link_body(f"http://{host}/x")) == []


@pytest.mark.parametrize("host", ["a.1e3", "1.2.3.7f", "e.ff", "e.0x7g", "e.x7f", "1.2.3.f"])
def test_a_last_label_that_only_looks_like_a_number_is_a_name(host: str) -> None:
    # A browser reads these as names, so they stay usable.
    assert [e.link for e in parse_feed(_link_body(f"http://{host}/x"))] == [f"http://{host}/x"]


_XHTML_DIV = 'xmlns="http://www.w3.org/1999/xhtml"'


@pytest.mark.parametrize(
    ("inner", "expected"),
    [
        ("A <xmp>&lt;b&gt; &amp;amp; B</xmp> C", "A <b> &amp; B C"),
        ("A <iframe>&lt;b&gt;</iframe> C", "A <b> C"),
        ("A <noembed>&lt;i&gt;</noembed> C", "A <i> C"),
        ("A <noframes>&lt;i&gt;</noframes> C", "A <i> C"),
        ("A <plaintext>B</plaintext> C", "A B C"),
        ("A <_x>B</_x> C", "A B C"),
        ("A <a.b>B</a.b> C", "A B C"),
        ("A <m:b xmlns:m='urn:m'>B</m:b> C", "A B C"),
        ('A <a href="javascript:x" title="T">B</a> C', "A B C"),
        ("A <él>B</él> C", "A B C"),
        ("A <script>SCRIPT</script>B", "A B"),
        ("A <style>p{}</style>B", "A B"),
        ("<p>A</p><P>B</P><x:div xmlns:x='urn:x'>C</x:div>", "A B C"),
    ],
)
def test_xhtml_is_rebuilt_from_known_tags_only(inner: str, expected: str) -> None:
    summary = f'<summary type="xhtml"><div {_XHTML_DIV}>{inner}</div></summary>'
    assert _atom_one("<title>T</title>", summary).summary == expected


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("not bytes", id="str"),
        pytest.param("", id="empty str"),
        pytest.param("x" * (MAX_BYTES + 1), id="str over the cap"),
        pytest.param(None, id="None"),
        pytest.param([b"x"], id="list"),
        pytest.param(7, id="int"),
    ],
)
def test_a_body_that_is_not_bytes_is_a_type_error_before_the_size_check(body: object) -> None:
    with pytest.raises(TypeError, match="body must be bytes"):
        parse_feed(cast(bytes, body))


@pytest.mark.parametrize("kind", [bytearray, memoryview])
def test_a_bytes_like_body_is_read_like_bytes(kind: type) -> None:
    # The predecessor's byte search accepted any bytes-like body; so does the port.
    assert parse_feed(cast(bytes, kind(RSS))) == parse_feed(RSS)


# --- R24: what the tree keeps, what is refused, and what is cut before it is cleaned ---


def _flat(count: int) -> bytes:
    return b'<rss version="2.0">' + b"<a/>" * (count - 1) + b"</rss>"


def test_a_feed_of_exactly_the_most_elements_is_read_and_one_more_is_refused() -> None:
    assert parse_feed(_flat(MAX_ELEMENTS)) == []
    with pytest.raises(FeedError, match=f"more than {MAX_ELEMENTS} elements"):
        parse_feed(_flat(MAX_ELEMENTS + 1))


def test_an_element_with_the_most_attributes_is_read_and_one_more_is_refused() -> None:
    def feed(count: int) -> bytes:
        attrs = "".join(f' a{i}="x"' for i in range(count))
        return f'<rss version="2.0"><channel{attrs}/></rss>'.encode()

    assert parse_feed(feed(MAX_ATTRIBUTES)) == []
    with pytest.raises(FeedError, match=f"more than {MAX_ATTRIBUTES} attributes"):
        parse_feed(feed(MAX_ATTRIBUTES + 1))


def test_element_and_attribute_names_are_refused_once_their_total_length_passes_the_bound() -> None:
    name = "n" * 100
    attrs = "".join(f' {name[:-4]}{k:04}=""' for k in range(200))  # 200 names of 100 characters

    def elements(count: int) -> bytes:
        return f'<rss version="2.0"><d>{f"<{name}/>" * count}</d></rss>'.encode()

    def with_attributes(count: int) -> bytes:
        return f'<rss version="2.0"><d>{f"<a{attrs}/>" * count}</d></rss>'.encode()

    fits = MAX_NAME_CHARS // len(name) - 4
    assert parse_feed(elements(fits)) == []
    with pytest.raises(FeedError, match="element names are too long"):
        parse_feed(elements(fits + 8))
    fits = (MAX_NAME_CHARS - 20) // (1 + 200 * len(name))  # 52 elements of 20,001 characters
    assert parse_feed(with_attributes(fits)) == []
    with pytest.raises(FeedError, match="element names are too long"):
        parse_feed(with_attributes(fits + 1))


def test_elements_inside_a_field_are_counted() -> None:
    inner = "<b>x</b>" * (MAX_ELEMENTS // 8 + 1)
    with pytest.raises(FeedError, match="more than"):
        parse_feed(_rss(f"<title>t</title>{_LINK}<description>{inner * 8}</description>"))


def test_text_outside_the_fields_that_are_read_is_not_kept() -> None:
    body = _rss(
        f"<title>t</title>{_LINK}<guid>g</guid><category><title>c</title></category>"
        "<description>d</description>"
    )
    (e,) = parse_feed(body)
    assert (e.title, e.summary) == ("t", "d")


def test_text_is_read_after_any_amount_of_markup() -> None:
    assert _summary_of("Lead " + "<i></i>" * 100_000 + "late") == "Lead late"
    assert _summary_of("<i></i>" * 100_000 + "late") == "late"
    assert _summary_of("<pre>" + "word " * 40_000 + "</pre>").startswith("word word word")
    assert _summary_of("<p>" + "word " * 40_000 + "</p>").startswith("word word word")


def test_a_summary_after_a_leading_data_image_is_read() -> None:
    image = '<img src="data:image/png;base64,' + "iVBORw0K" * 20_000 + '"/>'
    assert (
        _summary_of(image + "<p>The committee held the rate.</p>") == "The committee held the rate."
    )
    style = "<style>" + "p{margin:0}" * 20_000 + "</style>"
    assert _summary_of(style + "<p>Rate held.</p>") == "Rate held."


# --- R37/R38: dates and links are read to their limits, a memoryview must be bytes ---

_DATE = "Fri, 13 Nov 2026 09:00:00 GMT"  # 29 characters


def _published(date: str) -> datetime | None:
    (e,) = parse_feed(_rss(f"<title>t</title>{_LINK}<pubDate>{date}</pubDate>"))
    return e.published


def test_a_date_longer_than_the_limit_is_no_date() -> None:
    at_limit = _DATE + " x" * 113 + "y"
    assert len(at_limit) == 256
    assert _published(at_limit) == datetime(2026, 11, 13, 9, 0, tzinfo=UTC)
    assert _published(at_limit + "y") is None
    assert _published(" " * 300 + at_limit + " " * 300) == datetime(2026, 11, 13, 9, 0, tzinfo=UTC)


def test_an_atom_date_is_read_without_its_blanks_and_none_when_too_long() -> None:
    def updated(text: str) -> datetime | None:
        return _atom_one("<title>T</title>", f"<updated>{text}</updated>").published

    stamp = "2026-11-13T09:00:00Z"
    assert updated(" " * 300 + stamp + " " * 300) == datetime(2026, 11, 13, 9, 0, tzinfo=UTC)
    assert updated(stamp + " " * 300 + "x") is None


def test_a_link_is_read_with_blanks_at_its_ends_and_cut_by_its_limit() -> None:
    def rss_links(link: str) -> list[str]:
        return [e.link for e in parse_feed(_rss(f"<title>t</title><link>{link}</link>"))]

    def atom_links(href: str) -> list[str]:
        body = f'{_ATOM_HEAD.decode()}<entry><title>T</title><link href="{href}"/></entry></feed>'
        return [e.link for e in parse_feed(body.encode())]

    for links in (rss_links, atom_links):
        assert links(" " * 5000 + "https://e.org/a" + " " * 5000) == ["https://e.org/a"]
        assert links("https://e.org/" + "a" * 2034) == ["https://e.org/" + "a" * 2034]
        assert links("https://e.org/" + "a" * 2035) == []
        assert links("https://e.org/a" + " " * 5000 + "x") == []


def test_a_memoryview_that_is_not_contiguous_bytes_is_a_type_error() -> None:
    """A2 (R31 point 4): a contiguous view of anything but bytes is refused, not read."""
    padded = RSS + b" " * (-len(RSS) % 4)
    for view in (memoryview(padded).cast("H"), memoryview(padded).cast("c")):
        with pytest.raises(TypeError, match="contiguous bytes"):
            parse_feed(cast(bytes, view))


def test_a_memoryview_of_four_byte_items_is_a_type_error() -> None:
    padded = RSS + b" " * (-len(RSS) % 4)
    with pytest.raises(TypeError, match="contiguous bytes"):
        parse_feed(cast(bytes, memoryview(array("I", padded))))


def test_a_body_that_is_not_contiguous_bytes_is_refused() -> None:
    with pytest.raises(TypeError, match="contiguous"):
        parse_feed(cast(bytes, memoryview(RSS + RSS)[::2]))
    # a contiguous memoryview of bytes in any shape is read like its bytes
    padded = RSS + b" " * (-len(RSS) % 2)
    two_d = memoryview(padded).cast("B", [2, len(padded) // 2])
    assert parse_feed(cast(bytes, two_d)) == parse_feed(RSS)


# --- R37/R38: html.parser is driven in pieces and holds at most MAX_HELD_CHARS ---


def test_an_over_long_tag_is_one_space() -> None:
    assert _summary_of("x<a " + "b " * 3000 + ">y") == "x y"
    assert _summary_of('x<a title="' + "q" * 5000 + '">y') == "x y"
    assert _summary_of("x<a>y") == "xy"
    assert _summary_of("x</a " + "b " * 3000 + ">y") == "x y"


def test_a_construct_open_at_the_end_drops_the_rest() -> None:
    assert _summary_of("Keep <a " + "b " * 3000 + "lost") == "Keep"
    assert _summary_of("Keep <!--" + "x" * 5000) == "Keep"


def test_a_held_comment_or_cdata_section_ends_at_its_own_end() -> None:
    assert _summary_of("<!--" + "a>b " * 1000 + "-->Visible") == "Visible"
    # the section holds "]]>", which a CDATA block of the feed can only carry split in two
    section = "<![CDATA[" + "q>q " * 1000 + "]]>Visible"
    assert _summary_of(section.replace("]]>", "]]]]><![CDATA[>")) == "Visible"


def test_a_long_tag_with_a_quoted_bracket_keeps_the_text_after_it() -> None:
    tag = '<a title="' + "x" * 3000 + '>y" href="z">Link text</a> rest'
    assert _summary_of(tag) == "Link text rest"


def test_a_tag_open_past_the_held_limit_ends_at_the_next_bracket_even_in_a_quoted_value() -> None:
    """R38, accepted: a quoted ">" ends a tag that html.parser could not finish in 4,096
    characters; the rest of the tag then reads as text, and no tag is made of what is cut."""
    tag = '<a title="' + "x" * 5000 + '>y" href="z">Link text</a> rest'
    assert _summary_of(tag) == 'y" href="z">Link text rest'


def test_cutting_a_construct_out_cannot_join_the_pieces_into_markup() -> None:
    assert _summary_of("x<scr<b " + "c " * 3000 + ">ipt>y") == "x ipt>y"
    assert _summary_of("<scr" + "<i " + "j " * 3000 + ">ipt>alert(1)</script>") == "ipt>alert(1)"


def test_long_element_content_is_read_up_to_its_end_tag() -> None:
    assert _summary_of("<textarea>" + "w " * 5000 + "</textarea>after") == "w " * 149 + "w"
    assert _summary_of("<style>" + "p{x:y}" * 3000 + "</style><p>Visible</p>") == "Visible"
    script = "<script>" + "var a=1;" * 2000 + "</script>Visible words here"
    assert _summary_of(script) == "Visible words here"
    assert _summary_of("<title>" + "y" * 2045 + "</TITLE >after") == "y" * 300


def test_references_are_decoded_across_feed_steps() -> None:
    assert _summary_of("&amp;" * 5000) == "&" * 300
    assert _summary_of("w&notin; " * 3000) == "w\u2209 " * 99 + "w\u2209"
    assert _summary_of("&#1078;" * 3000 + " end") == "\u0436" * 300
    # text that ends at a reference html.parser waits to see whole is read in pieces too
    assert _summary_of("&a" * 3000) == "&a" * 150


def test_a_reference_of_more_digits_than_int_reads_does_not_escape() -> None:
    """N1 (R38): such a reference reads as U+FFFD then its digits, as one cut at a feed boundary."""
    assert _summary_of("&#" + "1" * 5000 + ";") == "\ufffd" + "1" * 299
    title = _atom_one('<title type="html">&amp;#' + "1" * 5000 + ";</title>").title
    assert title.startswith("\ufffd111")


def test_the_stripper_stops_once_the_summary_is_full(monkeypatch: pytest.MonkeyPatch) -> None:
    held: list[int] = []
    goahead = HTMLParser.goahead

    def counting(self: HTMLParser, end: bool) -> None:
        held.append(len(self.rawdata))
        goahead(self, end)

    monkeypatch.setattr(HTMLParser, "goahead", counting)
    assert _summary_of("word " * 400_000) == "word " * 59 + "word"
    assert len(held) <= 3
    assert max(held) <= 4096  # html.parser never reads more than a held part and one step


def test_an_rss_description_with_blanks_at_its_ends_is_read_as_stripped() -> None:
    assert _summary_of("</\n") == "</"
    assert _summary_of("\n  Lead <b>x</b> \n ") == "Lead x"


class _WholeText(HTMLParser):
    """The oracle: html.parser reading a whole description at once, with the reader's block rule."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.skip = self.skip or tag == "script"
        if tag in ("p", "br"):
            self.out.append(" ")

    def handle_endtag(self, tag: str) -> None:
        self.skip = self.skip and tag != "script"
        if tag in ("p", "br"):
            self.out.append(" ")

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.out.append(data)


_FIELD_PIECES = st.sampled_from(
    ["word", "x ", " ", "<p>", "</p>", "<b>", "</b>", "&amp;", "&lt;", "&#1078;", "&notin;"]
    + ["&a", "<br/>", "<!-- c -->", "<script>s</script>", '<a href="q>r">', "</a>", "&", "\n"]
    + ["<textarea>t</textarea>", "<", ">", "\u0436", "<![CDATA[ k>l ]]>"]
)


@settings(max_examples=150, deadline=None, derandomize=True)
@given(st.lists(_FIELD_PIECES, min_size=300, max_size=1500).map("".join))
def test_a_description_read_in_pieces_is_what_html_parser_reads_of_the_whole(text: str) -> None:
    """Fields past one step (2,048 characters) with no construct held over the limit: the
    reader gives what html.parser gives of the whole text, folded and cut by hand here."""
    whole = _WholeText()
    whole.feed(text)
    whole.close()
    folded = " ".join("".join(whole.out).split())
    head = folded[:301]
    if len(head) <= 300:
        expected = head
    elif " " not in head:
        expected = head[:300]
    else:
        expected = head.rsplit(" ", 1)[0].rstrip()
    assert _summary_of(text.replace("]]>", "]]]]><![CDATA[>")) == expected

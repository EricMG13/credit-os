import time
from datetime import UTC, datetime

import pytest

from credit_os.signal.feeds import FeedError, parse_feed

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
        b"<!doctype rss><rss/>",
    ],
)
def test_dtd_or_entities_are_refused(body: bytes) -> None:
    with pytest.raises(FeedError, match="DTD or entities"):
        parse_feed(body)


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
    with pytest.raises(FeedError, match="DTD or entities"):
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
    with pytest.raises(FeedError, match="DTD or entities"):
        parse_feed(body)


def test_internal_entity_expansion_is_refused_not_expanded() -> None:
    body = _rss(f"<title>&d;</title>{_LINK}", head=_LAUGHS)
    with pytest.raises(FeedError, match="DTD or entities"):
        parse_feed(body)


def test_external_entity_is_refused() -> None:
    head = '<!DOCTYPE rss [<!ENTITY x SYSTEM "file:///etc/hostname">]>'
    with pytest.raises(FeedError, match="DTD or entities"):
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
    with pytest.raises(FeedError, match="DTD or entities"):
        parse_feed(text.encode(codec))


def test_doctype_text_inside_a_comment_or_cdata_is_still_refused() -> None:
    # The predecessor refuses any "<!DOCTYPE" or "<!ENTITY" byte sequence; so does the port.
    for inner in ("<!-- <!DOCTYPE x> -->", "<![CDATA[<!ENTITY y 'z'>]]>"):
        with pytest.raises(FeedError, match="DTD or entities"):
            parse_feed(_rss(f"<title>t</title>{_LINK}{inner}"))


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


def test_very_deep_nesting_is_read_without_recursion() -> None:
    depth = 5000
    title = "<b>" * depth + "deep" + "</b>" * depth
    (e,) = parse_feed(_rss(f"<title>{title}</title>" + _LINK))
    assert e.title == "deep"


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
    with pytest.raises(FeedError, match="DTD or entities"):
        parse_feed(_rss("<title>t</title>" + _LINK, head=head))


def test_ten_thousand_levels_of_nesting_return_within_the_bound() -> None:
    depth = 10_000
    start = time.perf_counter()
    inner = "<b>" * depth + "deep" + "</b>" * depth
    (e,) = parse_feed(_rss(f"<title>{inner}</title>" + _LINK))
    assert e.title == "deep"
    stray = b'<rss version="2.0">' + b"<a>" * depth + b"</a>" * depth + b"</rss>"
    assert parse_feed(stray) == []
    assert time.perf_counter() - start < 10.0


def test_a_very_long_attribute_returns_within_the_bound() -> None:
    start = time.perf_counter()
    href = "https://e.org/" + "a" * 5_000_000
    body = (
        '<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>T</title>'
        f'<link href="{href}"/></entry></feed>'
    ).encode()
    (e,) = parse_feed(body)
    assert e.link == href
    assert time.perf_counter() - start < 10.0

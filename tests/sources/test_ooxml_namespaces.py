"""The namespace binding of `Package.parse`, held against expat's own namespace mode.

The answer key is expat with a namespace separator: on each of 1,000 generated parts it either
reads the part, naming every element and attribute `uri}local` in order, or refuses it. The shape
binds namespaces itself (expat runs with no separator), so it must read the same parts with the
same names in the same order, and refuse every part the key refuses. Written by the controller
from the fourth round's plan (1D PR 3b-2); the implementer does not edit it.
"""

import io
import random
import zipfile
from xml.parsers import expat

from credit_os.sources.errors import SourceUnreadable
from credit_os.sources.ooxml import Package

SEED = 20261114
CASES = 1_000
CJK = "\N{CJK UNIFIED IDEOGRAPH-4E00}"
XML_NAME = "http://www.w3.org/XML/1998/namespace"
XMLNS_NAME = "http://www.w3.org/2000/xmlns/"
PREFIXES = ["p", "p", "q", "q", "r", "xml", "xmlns", "XMLNS", "p.q", "1p", "-p", CJK, ""]
LOCALS = ["a", "b", "k", "_k", CJK, "1b", "-k", ".k"]
LOCALS += ["\N{MIDDLE DOT}k", "\N{COMBINING GRAVE ACCENT}k", "\N{ARABIC-INDIC DIGIT ZERO}"]
URIS = ["u", "u", "v", "v", "w", "", XML_NAME, XMLNS_NAME, "x}y", "a b"]
URIS += ["\N{LINEAR B SYLLABLE B008 A}", "HTTP://www.w3.org/XML/1998/namespace", "a&amp;b"]
TARGETS = ["pi", "pi", "p:i", ":i", "xml-s"]

Event = tuple[object, ...]


def _name(rng: random.Random) -> str:
    shape = rng.choices(["plain", "prefixed", "odd"], weights=[6, 5, 0.25])[0]
    if shape == "plain":
        return rng.choice(LOCALS[:5] if rng.random() < 0.97 else LOCALS)
    if shape == "prefixed":
        local = rng.choice(LOCALS[:5] if rng.random() < 0.96 else LOCALS)
        prefix = rng.choice(PREFIXES[:4] if rng.random() < 0.96 else PREFIXES)
        return f"{prefix}:{local}"
    return rng.choice(["a:b:c", ":a", "a:", "p:a:b"])


def _start_tag(rng: random.Random, depth: int) -> tuple[str, str]:
    tag = _name(rng)
    pairs: list[str] = []
    if depth == 0 and rng.random() < 0.8:
        pairs += ['xmlns:p="u"', f'xmlns:q="{rng.choice(["u", "v"])}"']
    if rng.random() < 0.3:
        pairs.append(f'xmlns="{rng.choice(["u", "v", "w", ""])}"')
    if rng.random() < 0.15:
        pairs += ['p:k="1"', 'q:k="2"']
    for _ in range(rng.choice([0, 0, 0, 1, 1, 2])):
        prefix = rng.choice(PREFIXES[:5] if rng.random() < 0.93 else PREFIXES)
        key = "xmlns" if prefix == "" else f"xmlns:{prefix}"
        uri = rng.choice(URIS[:5] if rng.random() < 0.93 else URIS)
        pairs.append(f'{key}="{uri}"')
    for _ in range(rng.choice([0, 1, 1, 2, 3])):
        pairs.append(f'{_name(rng)}="1"')
    rng.shuffle(pairs)
    return tag, "<" + " ".join([tag, *pairs])


def _element(rng: random.Random, depth: int) -> str:
    tag, head = _start_tag(rng, depth)
    if depth >= 3 or rng.random() < 0.4:
        return head + "/>"
    inner: list[str] = []
    for _ in range(rng.choice([0, 1, 2, 3])):
        roll = rng.random()
        if roll < 0.06:
            inner.append(f"<?{rng.choice(TARGETS)} d?>")
        elif roll < 0.2:
            inner.append("t")
        else:
            inner.append(_element(rng, depth + 1))
    return head + ">" + "".join(inner) + f"</{tag}>"


class _Seen:
    """Both readers write here: element starts with their attributes in order, and ends."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    def start(self, name: str, attributes: dict[str, str]) -> None:
        self.events.append(("start", name, list(attributes.items())))

    def end(self, name: str) -> None:
        self.events.append(("end", name))

    def text(self, data: str) -> None:
        del data


def _by_expat(text: str) -> list[Event] | None:
    """The key: expat's namespace mode, or None when it refuses the part."""
    seen = _Seen()
    parser = expat.ParserCreate(None, "}")
    parser.buffer_text = True
    parser.StartElementHandler = seen.start
    parser.EndElementHandler = seen.end
    try:
        parser.Parse(text, True)
    except expat.ExpatError:
        return None
    return seen.events


def _by_package(data: bytes) -> list[Event] | None:
    """The code under test, given the part in a deflated zip; None when it refuses."""
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("xl/a.xml", data)
    seen = _Seen()
    try:
        Package("b.xlsx", archive.getvalue()).parse("xl/a.xml", seen)
    except SourceUnreadable:
        return None
    return seen.events


def test_namespaces_are_bound_as_expat_binds_them() -> None:
    rng = random.Random(SEED)
    read = refused = 0
    problems: list[str] = []
    for case in range(CASES):
        text = _element(rng, 0)
        data = text.encode()
        assert len(data) < 4_096
        expected = _by_expat(text)
        actual = _by_package(data)
        if expected is None:
            refused += 1
            if actual is not None:
                problems.append(f"{case}: expat refuses, the package reads: {text!a}")
        else:
            read += 1
            if actual != expected:
                problems.append(f"{case}: {actual!a} != {expected!a}: {text!a}")
    assert problems == [], f"{len(problems)} of {CASES} differ; first: {problems[:3]}"
    assert read >= 250, read
    assert refused >= 250, refused

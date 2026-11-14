"""Redaction tests, compared with the controller's answer key (provider_redaction_key)."""

import ast
from pathlib import Path

import provider_redaction_key as key
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.provider import canned, events, redact
from credit_os.provider.redact import Redactor, home_paths


@pytest.mark.parametrize(("values", "text", "expected"), key.REDACT_TEXT)
def test_text_rows(values: tuple[str, ...], text: str, expected: str) -> None:
    assert Redactor(values).text(text) == expected


@pytest.mark.parametrize(("values", "text", "expected"), key.REDACT_TEXT)
def test_bytes_rows(values: tuple[str, ...], text: str, expected: str) -> None:
    assert Redactor(values).bytes_(text.encode()) == expected.encode()


@pytest.mark.parametrize(
    ("values", "text", "expected"), [row for row in key.REDACT_TEXT if any(row[0])]
)
def test_no_exact_value_survives_a_change(
    values: tuple[str, ...], text: str, expected: str
) -> None:
    out = Redactor(values).text(text)
    assert all(v not in out for v in values if v)


@pytest.mark.parametrize(("environ", "text", "expected"), key.REDACT_ENVIRON)
def test_environ_rows(environ: dict[str, str], text: str, expected: str) -> None:
    assert Redactor.from_environ(environ).text(text) == expected


@pytest.mark.parametrize(("text", "expected"), key.HOME_PATHS)
def test_home_paths_rows(text: str, expected: str) -> None:
    assert home_paths(text) == expected


# Mutation rows, expected values written by hand: the key does not pin these forms.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("/Users/Jane  Doe/x", "<home>/x"),
        ("C:\\Users\\Jane Doe: next", "<home>: next"),
        ("msg\\r/home/jane/x", "msg\\r<home>/x"),
        ("msg\\t/home/jane/x", "msg\\t<home>/x"),
        ("msg\\n\\\\fs01\\share\\Users\\jane\\x", "msg\\n<home>\\x"),
        ("C:\\Users\\Mary  O'Brien\\x", "<home>\\x"),
        ("\\\\home\\x\\Users\\ y", "<home>"),
        # A written-out escaped apostrophe is part of the name, not a separator.
        ("""'open "C:\\\\Users\\\\Pat O\\'Hara Jones" failed'""", """'open "<home>" failed'"""),
        (
            """'\\'open "C:\\\\\\\\Users\\\\\\\\Pat O\\\\\\'Hara Jones" failed\\''""",
            """'\\'open "<home>" failed\\''""",
        ),
        ("""open "C:/Users/Pat O\\'Hara Jones" failed""", 'open "<home>" failed'),
        (
            """'open "\\\\\\\\srv\\\\share\\\\Users\\\\Pat O\\'Hara Jones" failed'""",
            """'open "\\\\<home>" failed'""",
        ),
        (
            """'open "\\\\\\\\?\\\\UNC\\\\srv\\\\share\\\\Users\\\\Pat O\\'Hara Jones" failed'""",
            """'open "\\\\<home>" failed'""",
        ),
        ("open /mnt/c/Users/Pat O\\'Hara Jones failed", "open <home>"),
        # A real separator still ends the name (same as the base's output).
        ("C:\\Users\\mary\\Documents\\x", "<home>\\Documents\\x"),
    ],
)
def test_home_paths_mutation_rows(text: str, expected: str) -> None:
    assert home_paths(text) == expected


def test_lone_surrogate_value_does_not_raise_and_its_encodable_forms_match() -> None:
    redactor = Redactor(["ab\ud800cd-4711"])
    assert redactor.text("x ab\ud800cd-4711 y") == "x [redacted] y"
    assert redactor.bytes_(rb'x "ab\ud800cd-4711" y') == b'x "[redacted]" y'
    assert redactor.bytes_(b"x ab-4711 y") == b"x ab-4711 y"


def test_json_forms_unescaped_non_ascii_twice_escaped_matches() -> None:
    redactor = Redactor(['p\u00e4"x-4711'])
    assert redactor.text('"p\u00e4\\\\\\"x-4711"') == '"[redacted]"'
    assert redactor.bytes_('"p\u00e4\\\\\\"x-4711"'.encode()) == b'"[redacted]"'


def test_three_levels_of_escaping_are_not_matched() -> None:
    assert Redactor(['a"b-4711']).text(r"a\\\\\\\"b-4711") == r"a\\\\\\\"b-4711"


def test_empty_redactors_leave_text_unchanged() -> None:
    assert Redactor().text("x") == "x"
    assert Redactor.from_environ({}).text("x") == "x"


@pytest.mark.parametrize("file", [redact.__file__, canned.__file__, events.__file__])
def test_module_does_not_import_os(file: str | None) -> None:
    tree = ast.parse(Path(str(file)).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] not in ("os", "copilot") for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in ("os", "copilot")


_VALUES = st.text(min_size=4).filter(lambda v: "[" not in v and "]" not in v and v not in key.MARK)


@given(t=st.text(), v=_VALUES)
def test_exact_value_never_survives(t: str, v: str) -> None:
    assert v not in Redactor([v]).text(t + v + t)
    assert v.encode() not in Redactor([v]).bytes_((t + v + t).encode())


_NAME_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'().-_&éüßøÖ漢"
_PREFIXES = (
    "C:\\Users\\",
    "c:/users/",
    "C:\\\\Users\\\\",
    "D:\\Users/",
    "\\\\fs01\\share\\Users\\",
    "\\\\?\\UNC\\srv\\share\\Users\\",
    "\\\\?\\C:\\Users\\",
    "/mnt/c/Users/",
    "file:///C:/Users/",
    "/home/",
    "/Users/",
    "/var/home/",
    "file:///home/",
)
_LEADS = ("", " ", "cwd: ", "'", '"', "(", "<", "[", "msg\\n", '{"cwd": "')
_TAILS = (
    "",
    "/x",
    "\\x",
    "\\\\x",
    "\\AppData\\x.js",
    "'",
    '"',
    "' set",
    ",",
    ";",
    ":",
    ": next",
    ")",
    ">",
    ".",
    ". Next",
    " retry",
    "  more words",
    "\n",
    "\r\nnext",
    "\\n",
    '\'s "x"',
    ")\\n",
    " C:\\Users\\Zed Q\\x",
    " D:/Users/Zed",
    " /home/zed/x",
    " \\\\srv\\share\\Users\\zed",
    "C:\\Users\\b",
)


@settings(max_examples=1000, deadline=None)
@given(
    lead=st.sampled_from(_LEADS),
    prefix=st.sampled_from(_PREFIXES),
    words=st.lists(st.text(_NAME_CHARS, min_size=1, max_size=8), min_size=1, max_size=4),
    seps=st.lists(st.sampled_from([" ", "  ", "   "]), min_size=3, max_size=3),
    tail=st.sampled_from(_TAILS),
)
def test_no_word_of_a_home_name_survives(
    lead: str, prefix: str, words: list[str], seps: list[str], tail: str
) -> None:
    name = words[0] + "".join(s + w for s, w in zip(seps, words[1:], strict=False))
    out = home_paths(lead + prefix + name + tail).replace("<home>", "\x00")
    kept = [
        w for w in words if len(w) > 1 and w not in lead + prefix and w not in tail and w in out
    ]
    assert kept == []

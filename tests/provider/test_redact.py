"""Redaction tests, compared with the controller's answer key (provider_redaction_key)."""

import ast
import json
from collections.abc import Callable
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
        # JSON of a repr: exactly two backslashes before the apostrophe.
        ("""'open "C:\\\\Users\\\\Pat O\\\\'Hara Jones" failed'""", """'open "<home>" failed'"""),
        # A UNC host that starts with an apostrophe begins the next home path; its user goes too.
        (
            "C:\\Users\\mary\\'s \\\\'srv\\share\\Users\\bob smith\\x",
            "<home><home>\\x",
        ),
        # The same, with the second head under var/home.
        (
            "C:\\Users\\mary\\'s \\\\'srv\\share\\var\\home\\bob smith\\x",
            "<home><home>\\x",
        ),
        # A UNC head under a root folder begins the next home path; it goes too.
        ("C:\\Users\\mary\\'s \\\\'srv\\share\\root\\x", "<home><home>\\x"),
        # A drive head inside the name after the run begins its own home path.
        ("C:\\Users\\mary\\'s D:/Users/x \\\\h/s/Users/bob", "<home>"),
        ("C:\\Users\\mary\\'s D:\\Users\\bob", "<home>"),
        # Without the written-out apostrophe: the base's output.
        ("C:\\Users\\mary D:\\Users\\bob", "<home>:<home>"),
        # POSIX heads: a backslash in the name takes the rest of the line (main's rule).
        ("/home/\\:x", "<home>"),
        ("/Users\\\\:y", "<home>"),
        ("/var/home/\\:z", "<home>"),
        # A real separator still ends the name (same as the base's output).
        ("C:\\Users\\mary\\Documents\\x", "<home>\\Documents\\x"),
    ],
)
def test_home_paths_mutation_rows(text: str, expected: str) -> None:
    assert home_paths(text) == expected


# A UNC home whose leading separators are forward slashes (a Windows form: the Windows name
# rule and the escaped-apostrophe rule apply). Expected values by hand.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("//srv/share/Users/Bo Lu", "<home>"),
        ("//?/UNC/srv/share/Users/Bo Lu", "<home>"),
        ('open "//srv/share/Users/Bo Lu" failed', 'open "<home>" failed'),
        ("//srv//share//Users//Bo Lu", "<home>"),
        ("//?//UNC//srv//share//Users//Bo Lu", "<home>"),
        ("//srv/share/USERS/Bo Lu", "<home>"),
        ("//srv/share/var/home/Bo Lu", "<home>"),
        ("//srv/share/root", "<home>"),
        ("//srv/share/Users/Bo Lu/x", "<home>/x"),
        ("//srv/share/Users/Bo Lu: next", "<home>: next"),
        ('open "//srv/share/Users/Pat O\\\'Hara Jones" failed', 'open "<home>" failed'),
        # Mixed leading separators.
        ("\\/srv/share/Users/Bo Lu/x", "<home>/x"),
        ("/\\srv\\share\\Users\\Bo Lu\\x", "<home>\\x"),
        # Straight after a written-out "\n".
        ("msg\\n//srv/share/Users/Bo Lu/x", "msg\\n<home>/x"),
        # A UNC file URL is a UNC path: it fails closed (the "file:" prefix stays).
        ("file://srv/share/Users/x", "file:<home>"),
        # A protocol-relative URL after a quote cannot be told from a UNC path: it fails closed.
        ('<script src="//cdn.example.com/a/home/b">', '<script src="<home>">'),
    ],
)
def test_forward_slash_unc_rows(text: str, expected: str) -> None:
    assert home_paths(text) == expected


# Not UNC paths: the output is the base's (52adbcac) output, recorded before the change.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://example.com/a/Users/jane/p", "https://example.com/a/Users/jane/p"),
        ("https://srv/share/Users/jane/p", "https://srv/share/Users/jane/p"),
        ("ftp://srv/share/home/jane", "ftp://srv/share/home/jane"),
        ("file:///home/jane/x.txt", "file://<home>/x.txt"),
        ("file:///C:/Users/Jane Doe/x", "file:///<home>/x"),
        ("/home/jane//x", "<home>//x"),
        ("/a//b/Users/c", "/a//b/Users/c"),
        ("x//srv/share/Users/y", "x//srv/share/Users/y"),
        ("// see /Users/jane", "// see <home>"),
    ],
)
def test_forward_slash_unc_leaves_non_unc_unchanged(text: str, expected: str) -> None:
    assert home_paths(text) == expected


# The forward-slash UNC form's own pattern must never hide a Windows head the base finds: where its
# separator run swallows the start of a second head, the union still redacts the second head's name.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('open "//h/s/Users/\\Users\\Pat O\\\'Hara Jones" failed', 'open "<home>" failed'),
        ("//h/s/Users/\\\\v\\s\\Users\\Pat O\\'Hara Jones", "<home>"),
        ("//h/s/Users//mnt/c/Users/Pat O\\'Hara Jones", "<home>"),
        ("/\\h/s/USERS\\\\var\\home\\Pat O\\'Hara Jones", "<home>"),
        ("//h/s/home\\\\Users\\Pat O\\'Hara Jones", "<home>"),
    ],
)
def test_forward_slash_unc_never_hides_a_second_head(text: str, expected: str) -> None:
    assert home_paths(text) == expected


# A UNC file URL with an empty authority (four or more slashes after "file:"), any case, straight
# after a written-out "\n"; "file" must be the whole scheme.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("file:////srv/share/Users/Bo Lu/x.txt", "file:<home>/x.txt"),
        ("file://///srv/share/Users/Bo Lu/x.txt", "file:<home>/x.txt"),
        ('open "file:////srv/share/Users/Bo Lu" failed', 'open "file:<home>" failed'),
        ("file:////srv/share/home/Bo Lu", "file:<home>"),
        ("FILE://srv/share/Users/Bo Lu", "FILE:<home>"),
        ("File://srv/share/Users/Bo Lu", "File:<home>"),
        ("msg\\nfile://srv/share/Users/Bo Lu", "msg\\nfile:<home>"),
        # Not the whole scheme, or a POSIX file path: unchanged from the base.
        ("vscode-file://vscode-app/c:/Users/Bo/x", "vscode-file://vscode-app/<home>/x"),
        ("x-file://srv/share/Users/Bo", "x-file://srv/share/Users/Bo"),
        ("my.file://srv/share/home/Bo", "my.file://srv/share/home/Bo"),
        ("file:///srv/share/Users/Bo", "file:///srv/share/Users/Bo"),
    ],
)
def test_forward_slash_unc_file_urls(text: str, expected: str) -> None:
    assert home_paths(text) == expected


# The written-out forms of a forward-slash-led UNC home (repr, JSON of repr) and the mixed leads.
@pytest.mark.parametrize(
    "head",
    [
        "//srv/share/Users/",
        "\\/srv/share/Users/",
        "/\\srv\\share\\Users\\",
        "//srv\\share\\Users\\",
    ],
)
@pytest.mark.parametrize(
    ("wrap", "expected"),
    [
        (lambda s: s, 'open "<home>" failed'),
        (repr, "'open \"<home>\" failed'"),
        (lambda s: json.dumps(repr(s)), '"\'open \\"<home>\\" failed\'"'),
        (lambda s: repr(repr(s)), "'\\'open \"<home>\" failed\\''"),
    ],
)
def test_forward_slash_unc_written_out_forms(
    head: str, wrap: Callable[[str], str], expected: str
) -> None:
    assert home_paths(wrap(f'open "{head}Pat O\'Hara Jones" failed')) == expected


# A home folder needs a separator before it: a share that merely ends in "home" or "root" is not one.
@pytest.mark.parametrize(
    "text",
    [
        "//fileserver/sharedhome/docs/plan.txt",
        "//h/myroot",
        '<script src="//cdn.example.com/ahome/b.js">',
        "//h/sUsers/x",
        "file://srv/sharedhome/docs",
    ],
)
def test_forward_slash_unc_home_folder_needs_a_separator(text: str) -> None:
    assert home_paths(text) == text


def test_home_path_is_the_bases_pattern() -> None:
    # the base's (52adbcac) compiled pattern, verbatim: the forward-slash form has its own pattern
    base = (
        r"(?:(?<![\w.-])|(?<=\\[nrt])(?=[A-Za-z]:|\\\\|/))"
        r"(?:(?P<win>(?:[A-Za-z]:|\\\\(?:\?[\\/]+UNC[\\/]+)?[^\s\\/]+[\\/]+[^\s\\/]+|/mnt/[A-Za-z])"
        r"[\\/]+|\\)|/)"
        r"(?:(?i:users|home|var[\\/]+home)(?(win)[\\/]++|[\\/]+)"
        r"(?(win)(?!\\*\\\\(?:\?[\\/]+UNC[\\/]+)?[^\s\\/]+[\\/]+[^\s\\/]+[\\/]+"
        r"(?:(?i:users|home|var[\\/]+home)[\\/]|root(?![^\s\\/:*?\"'<>|(),;])))"
        r"(?:\\+(?=')|[^\\/<>:\"|?*\r\n])|(?:[^/:\\\r\n]|\\[^\r\n]*))+"
        r"|root(?![^\s\\/:*?\"'<>|(),;]))"
    )
    assert redact._HOME_PATH.pattern == base


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


def test_home_path_plain_is_mains_pattern() -> None:
    # main's compiled pattern at 54073086, verbatim: the fail-closed floor must not drift silently.
    base = (
        r"(?:(?<![\w.-])|(?<=\\[nrt])(?=[A-Za-z]:|\\\\|/))"
        r"(?:(?P<win>(?:[A-Za-z]:|\\\\(?:\?[\\/]+UNC[\\/]+)?[^\s\\/]+[\\/]+[^\s\\/]+|/mnt/[A-Za-z])"
        r"[\\/]+|\\)|/)"
        r"(?:(?i:users|home|var[\\/]+home)[\\/]+(?(win)[^\\/<>:\"|?*\r\n]|(?:[^/:\\\r\n]|\\[^\r\n]*))+"
        r"|root(?![^\s\\/:*?\"'<>|(),;]))"
    )
    assert redact._HOME_PATH_PLAIN.pattern == base


# A Users, home or var/home folder inside a path is a home too (owner ruling, 2026-11-14): under a
# drive, a UNC share (either slash, short or long-path), /mnt/<drive>/, or the rest of a path whose
# start already matched as a home. The span is the separator before the folder, the folder, its
# separators and the user name. Expected values by hand.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # (a) under a drive, either slash
        ("D:\\data\\Users\\bob smith\\x", "D:\\data<home>\\x"),
        ("D:/data/Users/bob smith/x", "D:/data<home>/x"),
        # (b) under a UNC share: backslash, forward slash, long-path
        ("\\\\srv\\share\\data\\Users\\bob smith\\x", "\\\\srv\\share\\data<home>\\x"),
        (
            "\\\\?\\UNC\\srv\\share\\data\\Users\\bob smith\\x",
            "\\\\?\\UNC\\srv\\share\\data<home>\\x",
        ),
        ("//srv/share/data/Users/bob smith/x", "//srv/share/data<home>/x"),
        ("//?/UNC/srv/share/data/Users/bob smith/x", "//?/UNC/srv/share/data<home>/x"),
        # (c) under /mnt/<drive>/
        ("/mnt/c/data/Users/bob smith/x", "/mnt/c/data<home>/x"),
        # (d) the rest of a path whose start already matched as a home
        ("C:\\Users\\mary\\backup\\Users\\bob smith\\x", "<home>\\backup<home>\\x"),
        ("C:/Users/mary/backup/Users/bob smith/x", "<home>/backup<home>/x"),
        ("/home/jane/backup/home/bob/x", "<home>/backup<home>/x"),
        ("//srv/share/Users/mary/backup/Users/bob smith/x", "<home>/backup<home>/x"),
        # several nested homes on one path
        ("D:\\data\\Users\\bob\\more\\home\\al smith\\y", "D:\\data<home>\\more<home>\\y"),
        ("/home/jane/backup/home/bob/x/home/al/y", "<home>/backup<home>/x<home>/y"),
        # var/home, mixed case
        ("D:\\data\\var\\home\\bob\\x", "D:\\data<home>\\x"),
        ("/home/jane/backup/var/home/bob/x", "<home>/backup<home>/x"),
        ("D:/data/USERS/bob smith", "D:/data<home>"),
        ("D:\\data\\hOmE\\bob", "D:\\data<home>"),
        # a Windows name with spaces runs to the line's end; reserved characters end it
        ("D:\\data\\Users\\bob smith and more", "D:\\data<home>"),
        ("D:\\a\\Users\\b: next", "D:\\a<home>: next"),
        # a written-out escaped apostrophe stays in a Windows name
        ("D:\\data\\Users\\Pat O\\'Hara Jones\\x", "D:\\data<home>\\x"),
        # repr-escaped separators
        ("D:\\\\data\\\\Users\\\\bob smith\\\\x", "D:\\\\data<home>\\\\x"),
        ("D:\\a\nD:\\b\\Users\\bob", "D:\\a\nD:\\b<home>"),
        ("D:\\a\\n\\Users\\bob", "D:\\a\\n<home>"),
        # a name runs through spaces as before, but the reach ended at its first space: a folder
        # after that space is not looked for. A drive later on the line has its own reach.
        ("D:\\a\\Users\\bob C:\\b\\home\\carol", "D:\\a<home>:\\b<home>"),
        ("D:\\data\\Users\\bob smith\\home\\al\\x", "D:\\data<home>\\home\\al\\x"),
        ("/home/jane/a/home/bob smith/home/al", "<home>/a<home>/home/al"),
        # a drive with doubled slashes is still a drive path
        ("C://srv/share/Users/bob", "C://srv/share<home>"),
        # a POSIX name ends at "/", a backslash in it takes the rest of the line
        ("/home/jane/backup/home/bob smith/x", "<home>/backup<home>/x"),
        ("/home/jane/backup/home/b\\ob/x", "<home>/backup<home>"),
        # /root is a home, so the rest of its path is searched; a root folder inside has no form
        ("/root/backup/home/bob/x", "<home>/backup<home>/x"),
        # a straight drive or share folder is the old rule's, unchanged
        ("D:\\Users\\bob\\x", "<home>\\x"),
        # the user name of one nested home can be the folder of the next: both go, and the two
        # overlapping spans (the first's folder and name, the second's folder and name) render as
        # one "<home>"
        ("D:\\data\\home\\users\\jdoeq\\x", "D:\\data<home>\\x"),
        ("D:/data/home/users/jdoeq/x", "D:/data<home>/x"),
        ("\\\\srv\\share\\data\\home\\users\\jdoeq\\x", "\\\\srv\\share\\data<home>\\x"),
        ("//srv/share/data/home/users/jdoeq/x", "//srv/share/data<home>/x"),
        ("/mnt/c/data/home/users/jdoeq/x", "/mnt/c/data<home>/x"),
        ("D:\\data\\Users\\home\\bobq", "D:\\data<home>"),
        ("C:\\Users\\home\\Users\\bobq\\x", "<home>\\x"),
        ("/home/jane/backup/home/users/jdoeq/x", "<home>/backup<home>/x"),
        # rule (c) with backslashes
        ("/mnt/c\\data\\Users\\bob", "/mnt/c\\data<home>"),
        # a folder word as the user name at the top level under each of (a) to (d)
        ("D:\\Users\\home\\x", "<home>"),
        ("\\\\srv\\share\\Users\\users\\x", "<home>"),
        ("/mnt/c/Users/home/x", "<home>"),
        ("C:\\Users\\mary\\backup\\Users\\home\\x", "<home>\\backup<home>"),
        ("/home/jane/backup/home/Users/x", "<home>/backup<home>"),
    ],
)
def test_nested_home_rows(text: str, expected: str) -> None:
    assert home_paths(text) == expected


# Not changed: URLs with a scheme, bare relative paths, POSIX absolute paths that are not under a
# matched home, whole-segment near-misses, root. Outputs recorded from the base before the change.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://example.com/a/Users/jane/p", "https://example.com/a/Users/jane/p"),
        ("path=a/Users/bob/x", "path=a/Users/bob/x"),
        ("docs/home/bob", "docs/home/bob"),
        ("foo\\Users\\bob\\x", "foo\\Users\\bob\\x"),
        ("/srv/data/home/bob", "/srv/data/home/bob"),
        ("/a//b/Users/c", "/a//b/Users/c"),
        ("file:///home/jane/x.txt", "file://<home>/x.txt"),
        ("D:\\data\\myUsers\\x", "D:\\data\\myUsers\\x"),
        ("D:\\data\\homework\\x", "D:\\data\\homework\\x"),
        ("D:\\data\\Users2\\x", "D:\\data\\Users2\\x"),
        ("D:\\data\\root\\x", "D:\\data\\root\\x"),
        ("/home/jane/backup/homework/x", "<home>/backup/homework/x"),
        ("D:\\data\\Users\\", "D:\\data\\Users\\"),
        # the reach ends at the first whitespace: a folder past a space is not looked for
        ("D:\\my data\\Users\\bob", "D:\\my data\\Users\\bob"),
        ("D:\\a then foo/Users/bob", "D:\\a then foo/Users/bob"),
        ("D:\\a\tUsers\\bob", "D:\\a\tUsers\\bob"),
        (
            "Saved to D:\\reports. See docs/home/bobq for details",
            "Saved to D:\\reports. See docs/home/bobq for details",
        ),
        (
            "Wrote C:\\tmp\\out.txt; then read ../home/bobq/notes",
            "Wrote C:\\tmp\\out.txt; then read ../home/bobq/notes",
        ),
        ("['D:\\\\x', 'b/home/cq']", "['D:\\\\x', 'b/home/cq']"),
        # the POSIX rest of a home reaches to the first whitespace too
        ("/home/jane/x and docs/home/bobq", "<home>/x and docs/home/bobq"),
        # a character Windows reserves ends the reach: this relative path is not under the drive
        ('D:\\a" then foo/Users/bob', 'D:\\a" then foo/Users/bob'),
    ],
)
def test_nested_home_leaves_other_shapes_unchanged(text: str, expected: str) -> None:
    assert home_paths(text) == expected

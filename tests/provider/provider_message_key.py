"""Answer key for step 1C, PR 2h: `Redactor.message`, redaction by known paths (decision 0012).
Written by the controller before the code existed; implementers do not edit it. Every value is
invented. Expected values are written by hand from 0012's rules, never from the code under test.

The contract (0012, with the controller's readings marked):
- `Redactor(exact_values=(), *, known_paths=())` and `Redactor.from_environ(environ, *,
  known_paths=())`. `text` and `bytes_` stay keys-only. A known path is stripped of surrounding
  whitespace and trailing separators (reading); one with no folder name left raises ValueError.
- `message(text)` finds, on the unmasked text, the spans of keys (as `text` does), of each known
  path and of the net (`home_paths`, frozen), and masks their union once: a merged span holding any
  path span (known or net) becomes `<home>`, one holding only key spans `[redacted]` (reading).
- A known path is matched whole, and its last two folders under any lead (a path with one folder
  is matched whole only: reading), with no left or right boundary. Each character as written, as
  `\\uXXXX` or `\\xXX` (either hex case, one to eight backslashes, its UTF-8 bytes included),
  percent-encoded (the percent itself up to twice), in NFC or NFD; any letter case (no case map
  that changes length). Each separator is any run of up to 16 of `/`, `\\`, `%2F`, `%5C`, the
  percent of the last two also encoded up to twice (reading: a separator is a character too).
- Not guaranteed, and pinned here as the net alone gives it: another user's home; 8.3 short names;
  a case map that changes length; a bare user name; a value split across strings; octal, HTML or
  base64; the text of an ok reply.
"""

import json
import unicodedata
import urllib.parse
from collections.abc import Callable

B = "\\"  # one backslash
_GH = "ghp_" + "A" * 36  # a GitHub token shape, built from parts
H1 = "C:\\Users\\M\u00e9lanie"  # under Users: the net sees its head too
H2 = "D:\\Profiles\\M\u00e9lanie"  # outside Users: only the known path finds it
_MUL = "C:\\Users\\M\u00fcller"
_RT = "/opt/acme/bin/copilot"

# (exact values, known paths, text, expected message)
MESSAGE: tuple[tuple[tuple[str, ...], tuple[str, ...], str, str], ...] = (
    # --- H2 in every encoding 0012 lists
    ((), (H2,), "x D:\\Profiles\\M\u00e9lanie\\proj", "x <home>\\proj"),
    ((), (H2,), "d:\\profiles\\M\\u00e9lanie\\x", "<home>\\x"),
    (
        (),
        (H2,),
        "D:" + B * 2 + "Profiles" + B * 2 + "M\\u00E9lanie" + B * 2 + "x",
        "<home>" + B * 2 + "x",
    ),
    (
        (),
        (H2,),
        "D:" + B * 4 + "Profiles" + B * 4 + "M" + B * 2 + "u00e9lanie" + B * 4 + "x",
        "<home>" + B * 4 + "x",
    ),
    ((), (H2,), "D:" + B * 16 + "Profiles" + B * 16 + "M" + B * 8 + "u00e9lanie", "<home>"),
    ((), (H2,), "D:\\Profiles\\M\\xE9lanie\\x", "<home>\\x"),
    ((), (H2,), "D:\\Profiles\\M\\xc3\\xa9lanie\\x", "<home>\\x"),
    (
        (),
        (H2,),
        "D:" + B * 2 + "Profiles" + B * 2 + "M" + B * 2 + "xc3" + B * 2 + "xa9lanie",
        "<home>",
    ),
    ((), (H2,), "D%3A%5CProfiles%5CM%C3%A9lanie%5Cx", "<home>%5Cx"),
    ((), (H2,), "d%253a%255cprofiles%255cm%25c3%25a9lanie", "<home>"),
    ((), (H2,), "D:\\Profiles\\Me\u0301lanie\\x", "<home>\\x"),
    ((), (H2,), "D:" + B * 2 + "Profiles" + B * 2 + "Me\\u0301lanie", "<home>"),
    ((), (H2,), "D:/\\/Profiles\\\\//M\u00e9lanie/x", "<home>/x"),
    ((), (H2,), "d:\\PROFILES\\m\u00c9LANIE\\x", "<home>\\x"),
    ((), (H2,), "xD:\\Profiles\\M\u00e9laniey", "x<home>y"),
    # --- its last two folders under any lead
    ((), (H2,), "E:\\old\\Profiles\\M\u00e9lanie\\x", "E:\\old\\<home>\\x"),
    ((), (H2,), "/mnt/d/Profiles/M\u00e9lanie/x", "/mnt/d/<home>/x"),
    ((), (H2,), "file:///srv/Profiles%2FM%C3%A9lanie", "file:///srv/<home>"),
    ((), (H2,), "\\Profiles\\M\u00e9lanie", "\\<home>"),
    # --- a POSIX home outside the net's folders; a path with one folder is matched whole only
    ((), ("/srv/people/jane",), "cannot open /srv/people/jane/x", "cannot open <home>/x"),
    ((), ("/srv/people/jane",), "/backup/people/jane/x", "/backup/<home>/x"),
    ((), ("/ann",), "see /ann/x, not annual", "see <home>/x, not annual"),
    # --- a known path given with padding and a trailing separator
    ((), (" D:/Profiles/Jane Roe/ \n",), "D:\\Profiles\\Jane Roe\\x", "<home>\\x"),
    # --- the runtime path is a known path too
    ((), (H2, _RT), "spawn /opt/acme/bin/copilot failed", "spawn <home> failed"),
    # --- the review's leftovers on the driver branch
    (
        (),
        (_MUL,),
        "C:" + B * 2 + "Users" + B * 2 + "M\\u00FCller" + B * 2 + "proj",
        "<home>" + B * 2 + "proj",
    ),
    ((), ("D:\\Profiles\\alice",), "d:/profiles/Alice/x", "<home>/x"),
    # --- one union: spans found on the unmasked text (finding 3 on main, and in the driver)
    ((), (H1,), "c:\\Users\\M\\u00e9lanie\\x", "<home>\\x"),
    (
        (),
        ("D:\\Data\\Users\\M\u00fcller",),
        "/home/build or D:"
        + B * 2
        + "Data"
        + B * 2
        + "Users"
        + B * 2
        + "M\\u00fcller"
        + B * 2
        + "proj",
        "<home>" + B * 2 + "proj",
    ),
    ((), (H1,), "C:\\Users\\M\u00e9lanie\\" + _GH + "\\x", "<home>\\[redacted]\\x"),
    (("lanieQ7",), (H2,), "D:\\Profiles\\M\u00e9lanieQ7x", "<home>x"),
    (("Q7Q7Q7",), (H2,), "D:\\Profiles\\M\u00e9lanieQ7Q7Q7", "<home>[redacted]"),
    ((), (), "bad " + _GH + " in C:\\Users\\bob\\x", "bad [redacted] in <home>\\x"),
    # --- not guaranteed: pinned as the net alone gives it
    ((), (H2,), "C:\\Users\\bob\\x", "<home>\\x"),
    ((), (H2,), "D:\\Profiles\\bob\\x", "D:\\Profiles\\bob\\x"),
    ((), (H2,), "D:\\Profiles\\MLANIE~1\\x", "D:\\Profiles\\MLANIE~1\\x"),
    ((), ("D:\\Profiles\\Strau\u00df",), "D:\\PROFILES\\STRAUSS\\x", "D:\\PROFILES\\STRAUSS\\x"),
    ((), (H2,), "M\u00e9lanie wrote this", "M\u00e9lanie wrote this"),
    ((), (H2,), '["D:\\Profiles", "M\u00e9lanie"]', '["D:\\Profiles", "M\u00e9lanie"]'),
    ((), (H2,), "D:\\Profiles\\M\\351lanie", "D:\\Profiles\\M\\351lanie"),
    ((), (H2,), "D:\\Profiles\\M&#233;lanie", "D:\\Profiles\\M&#233;lanie"),
    ((), (H2,), "RDpcUHJvZmlsZXNcTcOpbGFuaWU=", "RDpcUHJvZmlsZXNcTcOpbGFuaWU="),
)

# Known paths with no folder name: Redactor(known_paths=(p,)) raises ValueError.
REFUSED: tuple[str, ...] = ("", "/", "C:\\", " / ", "\\\\")

# The frozen net, two rows the whole-branch review of #187 found no test held (`_nested_spans`
# mutants 12 and 21): (text, home_paths(text)).
NET: tuple[tuple[str, str], ...] = (
    ("\\Users\\bob\\home\\alice\\x", "<home><home>\\x"),
    ("C:\\Users\\bob\\x D:\\data\\Users\\alice\\y", "<home>\\x D:\\data<home>\\y"),
)

_USAGE = {"model": "gpt-6-sol", "finishReason": "stop", "inputTokens": 1, "outputTokens": 1}
_EVENT_USAGE: dict[str, object] = {"id": "u1", "type": "assistant.usage", "data": _USAGE}


def _error(text: str) -> list[dict[str, object]]:
    return [
        _EVENT_USAGE,
        {"id": "x1", "type": "session.error", "data": {"errorType": "x", "message": text}},
    ]


# Through the parser: (known paths, events, which field, expected). "message" is Reply.message;
# "text" is Reply.turn.text. Masking precedes the 500-character cut.
EVENTS: tuple[tuple[tuple[str, ...], list[dict[str, object]], str, str], ...] = (
    (
        (H2,),
        _error("cannot open D:\\Profiles\\M\u00e9lanie\\proj"),
        "message",
        "x: cannot open <home>\\proj",
    ),
    ((H2,), _error("y" * 490 + H2 + "\\tail"), "message", "x: " + "y" * 490 + "<home>\\"),
    (
        (H2,),
        [
            _EVENT_USAGE,
            {
                "id": "m1",
                "type": "assistant.message",
                "data": {"content": "see " + H2, "messageId": "m1"},
            },
        ],
        "text",
        "see D:\\Profiles\\M\u00e9lanie",
    ),
)

# Time: message() on each text, known paths (H2, _RT), at most SECONDS each (inputs <= 10^5).
SECONDS = 1.0
TIMING: tuple[tuple[str, str], ...] = (
    ("backslashes", B * 100_000),
    ("escapes", "\\u00e9" * 16_000),
    ("percents", "%25" * 33_000),
    ("a matched head then a separator run", "D:\\Profiles" + B * 99_000),
    ("the known path repeated", (H2 + " ") * 4_500),
)


# The property test's encoders, from the standard library only (never the production builder).
def _json(s: str) -> str:
    return json.dumps(s)[1:-1]


def _json_raw(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)[1:-1]


def _ascii(s: str) -> str:
    return ascii(s)[1:-1]


def _utf8(s: str) -> str:
    return ascii(s.encode("utf-8"))[2:-1]


def _quote(s: str) -> str:
    return urllib.parse.quote(s, safe="")


def _nfd(s: str) -> str:
    return unicodedata.normalize("NFD", s)


ENCODERS: dict[str, Callable[[str], str]] = {
    "json": _json,
    "json_raw": _json_raw,
    "ascii": _ascii,
    "utf8": _utf8,
    "quote": _quote,
    "nfd": _nfd,
    "swapcase": str.swapcase,
}
# Chains inside 0012's guarantee, applied left to right to a whole occurrence (lead and tail kept
# out). With separator runs of 1 or 2 before encoding, no run passes 16 and no escape 8 backslashes.
CHAINS: tuple[tuple[str, ...], ...] = (
    (),
    ("json",),
    ("json", "json"),
    ("json", "json", "json"),
    ("json_raw", "json"),
    ("ascii",),
    ("ascii", "json"),
    ("utf8",),
    ("utf8", "json"),
    ("quote",),
    ("quote", "quote"),
    ("nfd",),
    ("nfd", "json"),
    ("nfd", "quote"),
    ("swapcase",),
    ("json", "swapcase"),
    ("quote", "swapcase"),
    ("utf8", "swapcase"),
)
# Folder-name characters for generated paths: every one keeps its length under swapcase.
NAME_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._- \u00e9\u00fc\u00f1\u00f8\u00c9\u00dc\u5f20\u4f1f"
LEADS: tuple[str, ...] = (
    "",
    "x ",
    "/home/build or ",
    "E:\\old\\",
    "file:///",
    "\\\\srv\\share\\",
    "/mnt/c/",
)
TAILS: tuple[str, ...] = ("", "\\proj", "/x", " y", "\\")

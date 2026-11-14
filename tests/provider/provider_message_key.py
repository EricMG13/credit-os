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
  Case applies before the encoding, and a character's case forms are every character
  `re.IGNORECASE` holds the same letter, final sigma included (owner, 2026-11-14).
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
_ELISE = "D:\\Profiles\\\u00c9lise"
_PJ, _PF, _JO = "D:\\Profiles\\%5cjane", "D:\\Profiles\\%2Fjane", "/srv/people/%252Fjo"
_PE, _PFE, _PD = (
    "D:\\Profiles\\%5c\u00e9lise",
    "/srv/people/%2F\u00e9lise",
    "/srv/people/%252Fj\u00f6rg",
)
_JP = "D:" + B * 2 + "Profiles" + B * 2  # D:\Profiles\ as JSON writes it
_NIKOS = "D:\\Profiles\\\u039d\u0399\u039a\u039f\u03a3"  # ends in a capital sigma
_ODOS = "/srv/\u039f\u0394\u039f\u03a3/\u0391\u0398\u0397\u039d\u0391"
_ODOS_UTF8 = (
    "\\xce\\xbf\\xce\\xb4\\xce\\xbf\\xcf\\x82/\\xce\\xb1\\xce\\xb8\\xce\\xb7\\xce\\xbd\\xce\\xb1"
)

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
    # --- review round 1: case applies before the encoding (owner and coordinator, 2026-11-14)
    (
        (),
        (_ELISE,),
        "open d:" + B * 2 + "profiles" + B * 2 + "\\u00e9lise" + B + "x",
        "open <home>\\x",
    ),
    ((), (_ELISE,), "open d:" + B * 2 + "profiles" + B * 2 + "\\xe9lise\\x", "open <home>\\x"),
    ((), (_ELISE,), "open d:" + B * 2 + "profiles" + B * 2 + "\\xc3\\xa9lise\\x", "open <home>\\x"),
    ((), (_ELISE,), "open d%3A%5Cprofiles%5C%C3%A9lise\\x", "open <home>\\x"),
    ((), (H2,), "D:" + B * 2 + "PROFILES" + B * 2 + "M\\u00c9LANIE", "<home>"),
    ((), ("C:\\Users\\\u00c9lodie",), "c%3A%5Cusers%5C%C3%A9lodie", "<home>"),
    # --- review round 1: NFC and NFD of the whole name; UTF-8 bytes as \\uXXXX; padding inside
    ((), ("D:\\Profiles\\\uf900ab",), "x D:\\Profiles\\\uf900ab\\y", "x <home>\\y"),
    ((), ("D:\\Profiles\\\uf900ab",), "x D:\\Profiles\\\u8c48ab", "x <home>"),
    ((), ("D:\\Profiles\\F\u00e9\u0329mi",), "D:\\Profiles\\Fe\u0329\u0301mi\\x", "<home>\\x"),
    ((), (H2,), "D:" + B * 2 + "Profiles" + B * 2 + "M\\u00c3\\u00a9lanie", "<home>"),
    ((), ("D:/Profiles/Jane/ /",), "D:\\Profiles\\Jane\\x", "<home>\\x"),
    # --- audit N1 and N3, sweep D1: a name led by a separator token, then percent-encoded
    (
        (),
        ("D:\\Profiles\\Irm\u00e3",),
        "D:" + B * 2 + "Profiles" + B * 2 + "Irm\\xc3\\xa3",
        "<home>",
    ),
    ((), ("D:\\Profiles\\X5",), "D:" + B * 2 + "Profiles" + B * 2 + "\\x585", "<home>"),
    ((), (_PJ,), "x D%3A%5CProfiles%5C%255cjane y", "x <home> y"),
    ((), (_PJ,), "x Profiles%5C%255cjane y", "x <home> y"),
    ((), (_PF,), "x D:\\Profiles\\%2Fjane y", "x <home> y"),
    ((), (_PF,), "x D%253A%255CProfiles%255C%25252Fjane y", "x <home> y"),
    ((), (_PF,), "x Profiles%255C%25252Fjane y", "x <home> y"),
    ((), (_JO,), "x people/%252Fjo y", "x <home> y"),
    ((), (_JO,), "x %2Fsrv%2Fpeople%2F%25252Fjo y", "x <home> y"),
    ((), (_JO,), "x people%2F%25252Fjo y", "x <home> y"),
    # --- whole-branch review M1: what no test held (a non-BMP pair, %25 twice, _SHARED, prefixes)
    ((), ("D:\\Profiles\\\U00020000ko",), "x " + _JP + "\\ud840\\udc00ko y", "x <home> y"),
    ((), ("D:\\Profiles\\ko\U0001f600",), "x " + _JP + "ko\\uD83D\\uDE00 y", "x <home> y"),
    ((), ("D:\\Profiles\\MAX",), "x D:\\Profiles\\MAX y", "x <home> y"),
    ((), ("/srv/people/%25252Fjo",), "x /srv/people/%25252Fjo y", "x <home> y"),
    ((), ("/srv/people/%25252Fjo",), "x people/%25252Fjo y", "x <home> y"),
    ((), ("\\\\?\\vol\\jane",), "x E:\\old\\vol\\jane y", "x E:\\old\\<home> y"),
    ((), (H2,), "x D%25253A%25255CProfiles%25255CM%2525C3%2525A9lanie y", "x <home> y"),
    ((), (_ELISE,), "x D:%5CProfiles%5C\\u00e9lise y", "x <home> y"),
    ((), (_ELISE,), "x D:%255CProfiles%255C\\xe9lise y", "x <home> y"),
    ((), (_ELISE,), "x D:%25255CProfiles%25255C\\u00c9lise y", "x <home> y"),
    ((), ("\\\\srv\\share\\team\\jane",), "x \\\\srv\\share\\team\\jane y", "x <home> y"),
    ((), ("D:\\Profiles\\\udc80x",), "x D:\\Profiles\\\udc80x y", "x <home> y"),
    # --- whole-branch review L1: a token-led name whose next character is escaped
    ((), (_PE,), "x " + _JP + "%5c\\u00e9lise y", "x <home> y"),
    ((), (_PE,), "x " + _JP + "%5c\\xc3\\xa9lise y", "x <home> y"),
    ((), (_PE,), "x D:\\Profiles\\%5c\\u00e9lise y", "x <home> y"),
    ((), (_PE,), "x E:\\old\\Profiles\\%5c\\u00e9lise y", "x E:\\old\\<home> y"),
    ((), (_PE,), "x D:\\Profiles\\%5C\\u00C9LISE y", "x <home> y"),
    ((), (_PFE,), "x people/%2f\\xc3\\xa9lise y", "x <home> y"),
    ((), (_PD,), "x /srv/people/%252F\\u006a\\u00f6rg y", "x <home> y"),
    ((), (_PE,), "x D:\\Profiles\\%5c" + B * 3 + "u00e9lise y", "x <home> y"),
    # --- whole-branch review L2 (owner: inside): every letter re.IGNORECASE holds the same
    (
        (),
        (_NIKOS,),
        "x d:" + B * 2 + "profiles" + B * 2 + "\\u03bd\\u03b9\\u03ba\\u03bf\\u03c2 y",
        "x <home> y",
    ),
    ((), (_NIKOS,), "x d%3A%5CpROFILES%5C%CE%BD%CE%B9%CE%BA%CE%BF%CF%82 y", "x <home> y"),
    ((), (_ODOS,), "x /srv/" + _ODOS_UTF8 + " y", "x <home> y"),
    ((), ("D:\\Profiles\\Jens",), "x " + _JP + "Jen\\u017f y", "x <home> y"),
    ((), ("D:\\Profiles\\Kai",), "x D%3A%5CProfiles%5C%E2%84%AAai y", "x <home> y"),
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
REFUSED: tuple[str, ...] = (
    "",
    "/",
    "C:\\",
    " / ",
    "\\\\",
    "\\\\?\\",
    "\\\\?\\C:\\",
    "\\\\.\\",
    "\\\\.\\C:\\",
    "//./",
)  # a long-path prefix is no folder

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
PEAK_BYTES = 20_000_000  # tracemalloc peak of building a Redactor's case table, any known paths
TIMING: tuple[tuple[str, str], ...] = (
    ("backslashes", B * 100_000),
    ("escapes", "\\u00e9" * 16_000),
    ("percents", "%25" * 33_000),
    ("a matched head then a separator run", "D:\\Profiles" + B * 99_000),
    ("the known path repeated", (H2 + " ") * 4_500),
)


def _near_miss(folders: tuple[str, ...], run: int) -> str:
    """Each folder after the first starts with its first character as a \\x escape after a run of
    backslashes, and the last character is wrong: every split of a run is tried if parsing is not
    linear (task review round 1, M1)."""
    rest = "".join(B * run + f"x{ord(f[0]):02x}" + f[1:] for f in folders[1:])
    return ("C:" + B * run + folders[0] + rest)[:-1] + "Q"


_EIGHT = tuple(c * 3 for c in "abcdefgh")
_DEEP = "C:\\" + "\\".join(_EIGHT)  # an 8-folder known path
_RT_WIN = "C:\\Users\\jane\\AppData\\Local\\Programs\\copilot\\bin\\copilot.exe"
# message() is linear in the text for fixed known paths (coordinator, 2026-11-14): (label, known
# paths, text), each at most SECONDS. Inputs at most 10^5 characters.
TIMING_PATHS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("near-miss, 8 folders, once", (_DEEP,), _near_miss(_EIGHT, 16)),
    ("near-miss, 8 folders, repeated", (_DEEP,), (_near_miss(_EIGHT, 16) * 600)[:100_000]),
    (
        "near-miss, runtime path, repeated",
        (_RT_WIN,),
        (_near_miss(tuple(_RT_WIN.split("\\")[1:]), 8) * 400)[:100_000],
    ),
    (
        "backslashes, UNC and POSIX non-ASCII",
        ("\\\\srv\\\u00e9share\\Users\\bob", "/home/j\u00f6rg"),
        B * 100_000,
    ),
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
    ("swapcase", "json"),
    ("swapcase", "ascii"),
    ("swapcase", "utf8"),
    ("swapcase", "quote"),
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

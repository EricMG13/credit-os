"""`Redactor.message` tests, compared with the controller's answer key (provider_message_key)."""

import subprocess
import sys
import time
from pathlib import Path

import provider_message_key as key
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from credit_os.provider.events import reply_from_events
from credit_os.provider.redact import Redactor, home_paths


@pytest.mark.parametrize(("exact", "known", "text", "expected"), key.MESSAGE)
def test_message_rows(
    exact: tuple[str, ...], known: tuple[str, ...], text: str, expected: str
) -> None:
    assert Redactor(exact, known_paths=known).message(text) == expected


@pytest.mark.parametrize("path", key.REFUSED)
def test_a_path_with_no_folder_is_refused(path: str) -> None:
    with pytest.raises(ValueError, match="folder"):
        Redactor(known_paths=(path,))
    with pytest.raises(ValueError, match="folder"):
        Redactor.from_environ({}, known_paths=(path,))


@pytest.mark.parametrize(("text", "expected"), key.NET)
def test_net_rows(text: str, expected: str) -> None:
    assert home_paths(text) == expected


@pytest.mark.parametrize(("known", "events", "field", "expected"), key.EVENTS)
def test_event_rows(
    known: tuple[str, ...], events: list[dict[str, object]], field: str, expected: str
) -> None:
    reply = reply_from_events(events, model="gpt-6-sol", redactor=Redactor(known_paths=known))
    got = reply.message if field == "message" else reply.turn.text if reply.turn else None
    assert got == expected


def test_text_stays_keys_only() -> None:
    redactor = Redactor(known_paths=(key.H2,))
    assert redactor.text("D:\\Profiles\\M\u00e9lanie") == "D:\\Profiles\\M\u00e9lanie"
    assert redactor.bytes_(b"D:\\Profiles") == b"D:\\Profiles"


@pytest.mark.parametrize(("label", "text"), key.TIMING, ids=[row[0] for row in key.TIMING])
def test_message_time(label: str, text: str, capsys: pytest.CaptureFixture[str]) -> None:
    redactor = Redactor(known_paths=(key.H2, key._RT))
    start = time.perf_counter()
    redactor.message(text)
    seconds = time.perf_counter() - start
    with capsys.disabled():
        print(f"\nTIMING {label}: {seconds:.3f} s")
    assert seconds <= key.SECONDS


@pytest.mark.parametrize(
    ("label", "known", "text"), key.TIMING_PATHS, ids=[row[0] for row in key.TIMING_PATHS]
)
def test_message_time_by_path(
    label: str, known: tuple[str, ...], text: str, capsys: pytest.CaptureFixture[str]
) -> None:
    redactor = Redactor(known_paths=known)
    start = time.perf_counter()
    redactor.message(text)
    seconds = time.perf_counter() - start
    with capsys.disabled():
        print(f"\nTIMING {label}: {seconds:.3f} s")
    assert seconds <= key.SECONDS


_NAME = st.text(alphabet=key.NAME_ALPHABET, min_size=3, max_size=12).filter(
    lambda n: n == n.strip()
)
# (the known path's root text, the root's segments, whether a separator leads them)
_ROOTS = [(f"{d}:\\", [f"{d}:"], False) for d in "CDEFGHIJKLMNOPQRSTUVWXYZ"] + [
    ("\\\\srv\\share\\", ["srv", "share"], True),
    ("/", [], True),
]
_RUN = st.lists(st.sampled_from("/\\"), min_size=1, max_size=2).map("".join)


def _chain(chain: tuple[str, ...], value: str) -> str:
    for name in chain:
        value = key.ENCODERS[name](value)
    return value


def _joined(segments: list[str], runs: list[str], leading: bool) -> str:
    seps = iter(runs)
    return (next(seps) if leading else "") + "".join(
        seg + (next(seps) if i < len(segments) - 1 else "") for i, seg in enumerate(segments)
    )


@settings(max_examples=1000, deadline=None)
@given(
    root=st.sampled_from(_ROOTS),
    names=st.lists(_NAME, min_size=2, max_size=4),
    runs=st.lists(_RUN, min_size=8, max_size=8),
    whole=st.booleans(),
    chain=st.sampled_from(key.CHAINS),
    lead=st.sampled_from(key.LEADS),
    tail=st.sampled_from(key.TAILS),
)
def test_known_path_in_every_encoding(
    root: tuple[str, list[str], bool],
    names: list[str],
    runs: list[str],
    whole: bool,
    chain: tuple[str, ...],
    lead: str,
    tail: str,
) -> None:
    text_root, segments, leading = root
    known = text_root + "\\".join(names)
    last = names[-2:]
    occurrence = _joined(segments + names, runs, leading) if whole else _joined(last, runs, False)
    text = lead + _chain(chain, occurrence) + tail
    out = Redactor(known_paths=(known,)).message(text).lower()
    for name in last:
        encoded = _chain(chain, name).lower()
        assume(encoded not in (lead + tail + "<home>[redacted]").lower())
        assert encoded not in out


_HEADS = ("C:\\Users\\", "/home/", "\\\\srv\\share\\Users\\", "/mnt/c/Users/")
_AROUND = st.text(alphabet="0123456789 .,;!()_-", max_size=12)


@settings(max_examples=1000, deadline=None)
@given(
    head=st.sampled_from(_HEADS),
    name=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=5, max_size=7),
    before=_AROUND,
    after=_AROUND,
    shape=st.sampled_from(["ghp_", "github_pat_", "sk-or-"]),
    body=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", min_size=40, max_size=40),
    keyed=st.booleans(),
)
def test_message_masks_what_either_pass_masks(
    head: str, name: str, before: str, after: str, shape: str, body: str, keyed: bool
) -> None:
    secret = shape + body
    text = before + head + name + "\\" + (secret + after if keyed else after)
    out = Redactor(known_paths=(key.H2,)).message(text)
    if name in text and name not in home_paths(text):
        assume(name not in "<home>[redacted]")
        assert name not in out
    if keyed and secret not in Redactor().text(text):
        assert secret not in out


_BUILD_PROBE = """
import sys, tracemalloc
sys.path.insert(0, sys.argv[1])
import provider_message_key as key
from credit_os.provider.redact import Redactor

events = 0
def counter(frame, event, arg):
    global events
    if event in ("call", "c_call"):
        events += 1

tracemalloc.start()
sys.setprofile(counter)
Redactor(known_paths=(key._RT_WIN,))
sys.setprofile(None)
print(tracemalloc.get_traced_memory()[1], events)
"""


def test_the_first_build_with_known_paths_stays_within_memory_and_event_bounds() -> None:
    """One subprocess, one build: its case forms come from no per-code-point table."""
    here = str(Path(__file__).parent)
    done = subprocess.run(
        [sys.executable, "-c", _BUILD_PROBE, here],
        capture_output=True,
        text=True,
        check=True,
    )
    peak, events = (int(n) for n in done.stdout.split())
    assert peak <= key.PEAK_BYTES
    assert events <= key.BUILD_EVENTS

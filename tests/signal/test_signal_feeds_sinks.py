"""R37: the sinks a feed field's text goes into as it arrives, checked against hand-written text.

A sink is given a field in pieces of any size and must give what the whole text would: the
pieces' boundaries change nothing. Expected values are written out here, not computed with the
production helpers.
"""

import random

import pytest

from credit_os.signal.feeds import _Fold, _Head


def _pieces(text: str, size: int) -> list[str]:
    return [text[start : start + size] for start in range(0, len(text), size)] or [""]


def test_folding_equals_the_whole_text_folded_then_cut() -> None:
    # What each piece leaves in the text: format and control characters vanish, other white
    # space becomes a space.
    left = {
        "a": "a",
        "b": "b",
        "\u0436": "\u0436",
        " ": " ",
        "\n": " ",
        "\t": " ",
        "\u200b": "",
        "\x07": "",
        "\u00a0": " ",
        "\x1c": " ",
        "word": "word",
    }
    rnd = random.Random(7)
    for size in (0, 1, 7, 90, 4095, 4096, 4097, 9000, 20000):
        chosen = [rnd.choice(list(left)) for _ in range(size)]
        text = "".join(chosen)
        expected = " ".join("".join(left[piece] for piece in chosen).split())
        for limit in (1, 5, 301, 500, 100_000):
            for step in (1, 7, 4096, size + 1):
                fold = _Fold(limit)
                for piece in _pieces(text, step):
                    fold.add(piece)
                assert fold.value() == expected[:limit], (size, limit, step)


def test_a_word_longer_than_the_limit_is_cut_without_reading_the_rest() -> None:
    fold = _Fold(500)
    for _ in range(250):
        fold.add("w" * 4000)
    assert fold.full
    assert fold.value() == "w" * 500
    spaced = _Fold(10)
    spaced.add(" " * 10_000 + "a b")
    assert spaced.value() == "a b"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", ""),
        ("   ", ""),
        (" abc ", "abc"),
        ("abcde", "abcde"),
        ("abcdef", ""),
        ("  abcde  ", "abcde"),
        ("abc de", ""),
        (" a b ", "a b"),
        ("ab  \n", "ab"),
        ("\n\tab", "ab"),
        (" a b c", "a b c"),
    ],
)
def test_a_head_is_the_stripped_text_or_nothing_when_that_is_over_the_limit(
    text: str, expected: str
) -> None:
    for step in (1, 2, 3, len(text) + 1):
        head = _Head(5)
        for piece in _pieces(text, step):
            head.add(piece)
        assert head.value() == expected, step
    assert _Head.of(text, 5) == expected


def test_a_head_reads_blanks_by_the_million_and_keeps_only_the_limit() -> None:
    assert _Head.of(" " * 1_000_000 + "ab" + " " * 1_000_000, 2048) == "ab"
    assert _Head.of("x" * 1_000_000, 2048) == ""
    assert _Head.of("x" * 2048 + " " * 1_000_000, 2048) == "x" * 2048
    assert _Head.of("x" * 2048 + " " * 1_000_000 + "y", 2048) == ""

import dataclasses
import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Any

import provider_canned_key as key
import pytest

from credit_os.provider.canned import RecordingError, RecordingMissing, canned_model
from credit_os.provider.types import Message, Model, Reply, Request

RECORDING = Path(__file__).parent / "recordings" / "canned.jsonl"
REQUEST = Request((Message("user", "x"),), (), 10, "medium")
CP1_1 = ("cp1-synthetic", 1)


def _ask(model: Model, at: tuple[str, int]) -> Reply:
    return model.complete(REQUEST, exchange_id=at[0], call_index=at[1])


def _file(tmp_path: Path, *lines: dict[str, Any] | str) -> Path:
    path = tmp_path / "rec.jsonl"
    path.write_text("\n".join(x if isinstance(x, str) else json.dumps(x) for x in lines) + "\n")
    return path


@pytest.mark.parametrize("at", list(key.CANNED_REPLIES))
def test_recorded_replies_match_key(at: tuple[str, int]) -> None:
    model = canned_model("copilot-sol-medium", RECORDING)
    assert dataclasses.asdict(_ask(model, at)) == key.CANNED_REPLIES[at]


@pytest.mark.parametrize(("at", "text"), list(key.CANNED_BILLED_TEXT.items()))
def test_billed_digits(at: tuple[str, int], text: str) -> None:
    assert str(_ask(canned_model("c", RECORDING), at).billed_usd) == text


def test_tool_argument_keeps_decimal_digits() -> None:
    turn = _ask(canned_model("c", RECORDING), CP1_1).turn
    assert turn is not None
    scale = turn.tool_calls[0].arguments["scale"]
    assert isinstance(scale, Decimal)
    assert str(scale) == key.CANNED_SCALE_TEXT


@pytest.mark.parametrize(("at", "texts"), list(key.CANNED_COMPACTION_BILLED_TEXT.items()))
def test_compaction_charges(at: tuple[str, int], texts: tuple[str | None, ...]) -> None:
    reply = _ask(canned_model("c", RECORDING), at)
    assert (
        tuple(None if c.billed_usd is None else str(c.billed_usd) for c in reply.compactions)
        == texts
    )


def test_missing_count_is_not_zero() -> None:
    usage = _ask(canned_model("c", RECORDING), CP1_1).usage
    assert usage is not None
    assert usage.cached_read_tokens == 0
    assert usage.input_tokens is None


@pytest.mark.parametrize("at", key.CANNED_MISSING)
def test_missing_request_raises(at: tuple[str, int]) -> None:
    with pytest.raises(RecordingMissing) as caught:
        _ask(canned_model("c", RECORDING), at)
    assert (caught.value.exchange_id, caught.value.call_index) == at
    assert at[0] in str(caught.value)
    assert str(at[1]) in str(caught.value)


@pytest.mark.parametrize("line", key.CANNED_BAD_LINES)
def test_bad_lines_refused(tmp_path: Path, line: dict[str, Any] | str) -> None:
    with pytest.raises(RecordingError, match="line 1"):
        canned_model("c", _file(tmp_path, line))


@pytest.mark.parametrize("line", key.CANNED_GOOD_LINES)
def test_good_lines_accepted(tmp_path: Path, line: dict[str, Any]) -> None:
    reply = _ask(canned_model("c", _file(tmp_path, line)), ("e", 0))
    assert (reply.raw, reply.started_at, reply.finished_at) == (None, None, None)


def test_good_line_details(tmp_path: Path) -> None:
    bad = _ask(canned_model("c", _file(tmp_path, key.CANNED_GOOD_LINES[2])), ("e", 0))
    assert bad.turn is not None
    assert bad.turn.tool_calls[0].bad_arguments == "[1]"
    two = _ask(canned_model("c", _file(tmp_path, key.CANNED_GOOD_LINES[3])), ("e", 0))
    assert [c.billed_usd for c in two.compactions] == [Decimal("0.0240831"), None]


def test_duplicate_refused_at_second_line(tmp_path: Path) -> None:
    with pytest.raises(RecordingError, match="line 2"):
        canned_model("c", _file(tmp_path, *key.CANNED_DUPLICATE))


def test_blank_lines_count(tmp_path: Path) -> None:
    with pytest.raises(RecordingError, match=r"rec\.jsonl line 2: "):
        canned_model("c", _file(tmp_path, "", "{not json"))


def test_unreadable_paths(tmp_path: Path) -> None:
    for path in (tmp_path / "absent.jsonl", tmp_path):
        with pytest.raises(RecordingError, match=rf"{path.name}: unreadable: \w+"):
            canned_model("c", path)


def test_not_utf8_refused(tmp_path: Path) -> None:
    path = tmp_path / "rec.jsonl"
    path.write_bytes(b"\xff\n")
    with pytest.raises(RecordingError, match=r"rec\.jsonl: unreadable: UnicodeDecodeError"):
        canned_model("c", path)


class _NoEnvironment:
    def __getitem__(self, name: str) -> str:
        raise AssertionError("environment read")

    def __getattr__(self, name: str) -> object:
        raise AssertionError("environment read")


def test_reads_no_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as patched:
        patched.setattr(os, "environ", _NoEnvironment())
        assert _ask(canned_model("c", RECORDING), CP1_1).kind == "ok"


def test_config_close_and_repeat() -> None:
    model = canned_model("copilot-sol-medium", RECORDING)
    first = _ask(model, CP1_1)
    assert model.config_id == "copilot-sol-medium"
    model.close()
    assert _ask(model, CP1_1) is first

"""The data.js writer, compared with the controller's answer key byte for byte."""

import hashlib
import importlib.util
import json
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType, ModuleType
from typing import cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from credit_os.delivery import writer
from credit_os.delivery.errors import DeliveryRefused

KEY_PATH = Path(__file__).with_name("delivery_writer_key.py")
EXPECTED = Path(__file__).with_name("expected") / "writer"
PREFIX = b"window.CREDIT_OS_DATA = JSON.parse("
SUFFIX = b");\n"


def load_key() -> ModuleType:
    """Import the answer key by path, without touching sys.path."""
    spec = importlib.util.spec_from_file_location("delivery_writer_key", KEY_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {KEY_PATH}")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


KEY = load_key()
CASES: dict[str, tuple[object, object, object]] = KEY.CASES
REFUSED: dict[str, object] = KEY.REFUSED
REFUSED_KEYS: dict[str, dict[object, object]] = KEY.REFUSED_KEYS
RUNS0: object = KEY.RUNS0
SIZES: tuple[tuple[int, bool], ...] = KEY.SIZES
NAMES = sorted(CASES)


@pytest.mark.parametrize("name", NAMES, ids=NAMES)
def test_case_bytes_equal_expected_file(name: str) -> None:
    expected = (EXPECTED / name).read_bytes()
    assert writer.data_js(writer.envelope(*CASES[name])) == expected


@pytest.mark.parametrize("name", NAMES, ids=NAMES)
def test_expected_file_hash_equals_key(name: str) -> None:
    assert hashlib.sha256((EXPECTED / name).read_bytes()).hexdigest() == KEY.SHA256[name]


def test_every_expected_file_has_a_case() -> None:
    assert sorted(p.name for p in EXPECTED.glob("*.js")) == NAMES


@pytest.mark.parametrize("name", NAMES, ids=NAMES)
def test_same_input_twice_gives_same_bytes(name: str) -> None:
    first = writer.data_js(writer.envelope(*CASES[name]))
    assert writer.data_js(writer.envelope(*CASES[name])) == first


def test_envelope_member_order_and_no_run_or_signal() -> None:
    value = writer.envelope(1, 2, 3)
    assert list(value) == ["schema", "issuers", "library", "model"]
    assert value["schema"] == "credit-os-data/1"


@pytest.mark.parametrize("name", sorted(REFUSED), ids=sorted(REFUSED))
def test_refused_value(name: str) -> None:
    value = REFUSED[name]
    with pytest.raises(DeliveryRefused) as caught:
        writer.data_js(writer.envelope((), {"x": value}, {"runs": ()}))
    assert type(caught.value) is DeliveryRefused
    message = str(caught.value)
    if name == "float":
        assert "float" in message
    assert repr(value) not in message
    assert str(value) not in message


@pytest.mark.parametrize("name", sorted(REFUSED_KEYS), ids=sorted(REFUSED_KEYS))
def test_refused_key(name: str) -> None:
    members = REFUSED_KEYS[name]
    with pytest.raises(DeliveryRefused) as caught:
        writer.data_js(writer.envelope((), members, {"runs": ()}))
    assert type(caught.value) is DeliveryRefused
    assert all(repr(k) not in str(caught.value) for k in members)


def test_refusal_never_names_a_key_or_value() -> None:
    marker = "marker-" + "zq" * 8
    with pytest.raises(DeliveryRefused) as caught:
        writer.data_js(writer.envelope((), {marker: 1.5}, {"runs": ()}))
    assert marker not in str(caught.value)
    assert "1.5" not in str(caught.value)


@pytest.mark.parametrize("size,allowed", SIZES, ids=[str(s) for s, _ in SIZES])
def test_check_size(size: int, allowed: bool) -> None:
    if allowed:
        assert cast(Callable[[int], object], writer.check_size)(size) is None
        return
    with pytest.raises(DeliveryRefused) as caught:
        writer.check_size(size)
    assert "16777216" in str(caught.value)
    assert str(size) in str(caught.value)


def test_max_bytes_equals_key() -> None:
    assert writer.MAX_BYTES == KEY.MAX_BYTES == 16 * 1024 * 1024


def test_data_js_applies_the_size_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(writer, "MAX_BYTES", 10)
    with pytest.raises(DeliveryRefused):
        writer.data_js(writer.envelope((), {}, RUNS0))


def test_decimal_is_written_by_json_number() -> None:
    body = writer.data_js(writer.envelope((), {"d": Decimal("12.340")}, RUNS0))
    assert b'\\"d\\":12.34' in body


@pytest.mark.parametrize("raw", ["a b", "é", "\U0001f600", "<", "\x1f", "\x7f"])
def test_output_is_ascii(raw: str) -> None:
    body = writer.data_js(writer.envelope((), {"t": raw}, RUNS0))
    assert body.isascii()
    assert b"<" not in body


def test_mapping_other_than_dict_is_accepted() -> None:
    a = writer.data_js(writer.envelope((), MappingProxyType({"k": 1}), RUNS0))
    b = writer.data_js(writer.envelope((), {"k": 1}, RUNS0))
    assert a == b


def read_back(body: bytes) -> dict[str, object]:
    assert body.startswith(PREFIX)
    assert body.endswith(SUFFIX)
    inner = json.loads(body[len(PREFIX) : -len(SUFFIX)].decode("ascii"))
    assert isinstance(inner, str)
    return cast(dict[str, object], json.loads(inner))


def normal(value: object) -> object:
    if isinstance(value, (list, tuple)):
        return [normal(v) for v in value]
    if isinstance(value, dict):
        return {k: normal(v) for k, v in value.items()}
    return value


TEXT = st.text(alphabet=st.characters(exclude_categories=["Cs"]), max_size=12)
LEAVES = st.one_of(
    TEXT,
    st.booleans(),
    st.none(),
    st.integers(min_value=-(2**53 - 1), max_value=2**53 - 1),
)
VALUES: st.SearchStrategy[object] = st.recursive(
    LEAVES,
    lambda inner: st.one_of(
        st.lists(inner, max_size=4),
        st.lists(inner, max_size=4).map(tuple),
        st.dictionaries(TEXT, inner, max_size=4),
    ),
    max_leaves=12,
)


@given(VALUES)
def test_round_trip(value: object) -> None:
    body = writer.data_js(writer.envelope((), {"v": value}, RUNS0))
    assert body.isascii()
    assert b"<" not in body
    assert read_back(body)["library"] == {"v": normal(value)}

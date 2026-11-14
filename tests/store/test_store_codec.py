from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest
import store_codec_key as key
from hypothesis import given
from hypothesis import strategies as st

from credit_os.store import codec
from credit_os.store.codec import (
    detail_from_text,
    detail_to_text,
    money_from_text,
    money_to_text,
    time_from_text,
    time_to_text,
)
from credit_os.store.errors import StoreCorrupt, StoreRefused

Call = Callable[[Any], object]
_DISTINCTIVE = "QXZJ-distinctive-" * 40
_REFUSALS: tuple[tuple[Call, tuple[object, ...], type[Exception]], ...] = (
    (money_to_text, key.MONEY_WRITE_REFUSED, StoreRefused),
    (money_from_text, key.MONEY_READ_REFUSED, StoreCorrupt),
    (time_to_text, key.TIME_WRITE_REFUSED, StoreRefused),
    (time_from_text, key.TIME_READ_REFUSED, StoreCorrupt),
    (detail_to_text, key.DETAIL_WRITE_REFUSED, StoreRefused),
    (detail_from_text, key.DETAIL_READ_REFUSED, StoreCorrupt),
)
_CASES = [(c, v, e) for c, values, e in _REFUSALS for v in values]
_CASES += [(detail_from_text, v, StoreCorrupt) for v in ("[" * 100_000, "9" * 5_000)]
_NAIVE = next(v for v in key.TIME_WRITE_REFUSED if isinstance(v, datetime) and v.tzinfo is None)
_BAD_OFFSET = next(
    v
    for v in key.TIME_WRITE_REFUSED
    if isinstance(v, datetime)
    and isinstance(v.tzinfo, key.OddZone)
    and v.tzinfo.utcoffset(None) == timedelta(hours=24)
)
_LONG = Decimal("1" * 63 + ".5")  # 64 digits, but 65 characters of text
_COLLIDE = {"\ud800": 1, "\\ud800": 2}  # the same key once escaped
_CASES += [(detail_to_text, _COLLIDE, StoreRefused), (money_to_text, _LONG, StoreRefused)]
_MESSAGES: tuple[tuple[Call, Any, str], ...] = (
    (money_to_text, Decimal("NaN"), "money must be finite"),
    (money_to_text, Decimal(-1), "money must be unsigned"),
    (time_to_text, _NAIVE, "time must be timezone-aware"),
    (
        money_to_text,
        Decimal("1E+64"),
        "money has more than 64 digits or an exponent outside -62..63",
    ),
    (
        money_to_text,
        Decimal("1E-63"),
        "money has more than 64 digits or an exponent outside -62..63",
    ),
    (
        money_to_text,
        Decimal("1" * 65),
        "money has more than 64 digits or an exponent outside -62..63",
    ),
    (
        money_from_text,
        "1" * (key.MONEY_TEXT_MAXIMUM + 1),
        "stored money is longer than 64 characters (str)",
    ),
    (money_to_text, _LONG, "money text is longer than 64 characters"),
    (time_to_text, _BAD_OFFSET, "time zone offset is not valid"),
    (detail_to_text, {"n": 2**63}, "detail int is outside 64 signed bits"),
    (time_to_text, 1e18, "time is outside years 0001 to 9999 or not a number"),
    (time_from_text, "2026-02-30T00:00:00.000000Z", "stored time names no real instant"),
    (detail_to_text, {"a": 1.5}, "detail values must be str, int or None, got float"),
    (detail_to_text, {1: "x"}, "detail keys must be str, got int"),
    (detail_to_text, _COLLIDE, "detail keys collide after escaping"),
    (detail_from_text, b"{}", "stored detail is not text (bytes)"),
)


@pytest.mark.parametrize(("call", "value", "error"), _CASES)
def test_codec_refuses_what_the_key_lists(call: Call, value: Any, error: type[Exception]) -> None:
    with pytest.raises(error) as caught:
        call(value)
    assert type(caught.value) is error
    assert error is StoreCorrupt or isinstance(caught.value, ValueError)


_WRITTEN: list[tuple[Call, Any, str]] = [(money_to_text, v, t) for v, t in key.MONEY_WRITTEN]
_WRITTEN += [(time_to_text, v, t) for v, t in key.TIME_WRITTEN]
_WRITTEN += [(detail_to_text, v, t) for v, t in key.DETAIL_WRITTEN]
_WRITTEN += [(detail_to_text, *key.DETAIL_MAPPING_PROXY)]


@pytest.mark.parametrize(("call", "value", "text"), _WRITTEN)
def test_values_are_written_as_the_keys_text(call: Call, value: Any, text: str) -> None:
    assert call(value) == text
    assert call is not time_to_text or len(text) == key.TIME_TEXT_LENGTH


@pytest.mark.parametrize(("stored", "shown"), key.MONEY_READ)
def test_money_read_keeps_digits_and_exponent(stored: str, shown: str) -> None:
    result = money_from_text(stored)
    assert type(result) is Decimal and str(result) == shown


@pytest.mark.parametrize(("stored", "instant"), key.TIME_READ)
def test_time_read_gives_aware_utc(stored: str, instant: datetime) -> None:
    result = time_from_text(stored)
    assert result == instant
    assert result is not None and result.utcoffset() == timedelta(0)


@pytest.mark.parametrize(
    ("detail", "text"), [row for row in key.DETAIL_WRITTEN if "ud800" not in row[1]]
)
def test_detail_written_text_reads_back_equal(
    detail: dict[str, str | int | None], text: str
) -> None:
    assert detail_from_text(text) == detail


def test_money_subclass_that_lies_about_its_sign_is_refused() -> None:
    class Lying(Decimal):
        def is_signed(self) -> bool:
            return False

    with pytest.raises(StoreRefused):
        money_to_text(Lying("-1"))


def test_detail_lone_surrogate_reads_back_escaped() -> None:
    text, expected = key.DETAIL_LONE_SURROGATE_READ
    assert detail_from_text(text) == expected


def test_none_passes_through_and_zero_is_not_none() -> None:
    assert (money_to_text(None), money_from_text(None)) == (None, None)
    assert (time_to_text(None), time_from_text(None)) == (None, None)
    assert money_to_text(Decimal(0)) == "0"
    assert time_to_text(0.0) == "1970-01-01T00:00:00.000000Z"


@pytest.mark.parametrize("call", [call for call, _, _ in _REFUSALS])
@pytest.mark.parametrize("value", [_DISTINCTIVE, b"QXZJ"])
def test_refusal_message_names_the_type_not_the_value(call: Call, value: Any) -> None:
    with pytest.raises((StoreRefused, StoreCorrupt)) as caught:
        call(value)
    assert "QXZJ" not in str(caught.value)
    assert type(value).__name__ in str(caught.value)


@pytest.mark.parametrize(("call", "value", "message"), _MESSAGES)
def test_error_message_names_the_rule_broken(call: Call, value: Any, message: str) -> None:
    with pytest.raises((StoreRefused, StoreCorrupt)) as caught:
        call(value)
    assert str(caught.value) == message


_MONEY = st.builds(
    lambda digits, exponent: Decimal((0, digits, exponent)),
    st.lists(st.integers(0, 9), min_size=1, max_size=40).map(tuple),
    st.integers(-30, 20),
)
_ZONES = st.timedeltas(timedelta(hours=-23, minutes=-59), timedelta(hours=23, minutes=59))
_MOMENTS = st.datetimes(
    datetime(2, 1, 1, tzinfo=UTC).replace(tzinfo=None),
    datetime(9998, 12, 31, tzinfo=UTC).replace(tzinfo=None),
    timezones=st.builds(timezone, _ZONES),
)
_CHARS = st.characters(exclude_categories=["Cs"])
_DETAIL = st.dictionaries(
    st.text(_CHARS),
    st.one_of(
        st.text(_CHARS),
        st.integers(key.DETAIL_INT_MINIMUM, key.DETAIL_INT_MAXIMUM),
        st.none(),
    ),
    max_size=6,
)


@given(_MONEY)
def test_money_round_trips_and_re_encodes_the_same(value: Decimal) -> None:
    text = money_to_text(value)
    back = money_from_text(text)
    assert back == value and money_to_text(back) == text


@given(_MOMENTS, _MOMENTS)
def test_time_round_trips_and_its_text_orders_as_the_instants(a: datetime, b: datetime) -> None:
    ta, tb = time_to_text(a), time_to_text(b)
    assert ta is not None and tb is not None and time_from_text(ta) == a
    assert (a < b) == (ta < tb)
    assert (a == b) == (ta == tb)


@given(_DETAIL, st.randoms(use_true_random=False))
def test_detail_text_ignores_insertion_order_and_round_trips(
    detail: dict[str, str | int | None], random: Any
) -> None:
    items = list(detail.items())
    random.shuffle(items)
    text = detail_to_text(detail)
    assert detail_to_text(dict(items)) == text
    assert detail_from_text(text) == detail


def test_money_size_checks_run_before_the_text_is_built(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_format(*_: object) -> str:
        raise RuntimeError("format called before the size checks")

    monkeypatch.setattr(codec, "format", no_format, raising=False)
    for huge in ("1E+1000000", "1E-1000000", "0E+1000000", "1" * 65):
        with pytest.raises(StoreRefused):
            money_to_text(Decimal(huge))


def test_money_written_texts_respect_the_maximum_and_reach_it() -> None:
    lengths = [len(text) for _, text in key.MONEY_WRITTEN]
    assert max(lengths) == key.MONEY_TEXT_MAXIMUM

"""The wording layer of delivery, compared row by row with the controller's answer key."""

import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from credit_os.delivery import wording
from credit_os.delivery.errors import DeliveryRefused

ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "src" / "credit_os" / "delivery" / "wording.json"
KEY: dict[str, Any] = json.loads(
    (Path(__file__).parent / "expected" / "wording.json").read_text(encoding="utf-8")
)
W = wording.load_wording()


def ids_of(rows: list[Any]) -> list[str]:
    return [str(r["id"]) if isinstance(r, dict) else str(i) for i, r in enumerate(rows)]


def test_package_file_loads_and_matches_key_hash() -> None:
    match = re.search(r"sha256 ([0-9a-f]{64})", KEY["about"])
    assert match is not None
    assert hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest() == match.group(1)
    assert wording.load_wording(SOURCE_PATH.read_bytes()).not_recorded == W.not_recorded


@pytest.mark.parametrize("row", KEY["fill"], ids=ids_of(KEY["fill"]))
def test_fill(row: list[Any]) -> None:
    entry, values, expected = row
    assert W.fill(entry, values) == expected


@pytest.mark.parametrize("row", KEY["fill_generated"], ids=ids_of(KEY["fill_generated"]))
def test_fill_generated(row: dict[str, Any]) -> None:
    value = row["fill"] * row["count"]
    got = W.fill(row["entry"], {row["name"]: value})
    assert got == row["prefix"] + value + row["suffix"]


@pytest.mark.parametrize("row", KEY["fill_refused"], ids=ids_of(KEY["fill_refused"]))
def test_fill_refused(row: dict[str, Any]) -> None:
    with pytest.raises(DeliveryRefused):
        W.fill(row["entry"], row["values"])


@pytest.mark.parametrize("row", KEY["dates"], ids=ids_of(KEY["dates"]))
def test_dates(row: list[str]) -> None:
    iso, shown, month_year = row
    assert W.display_date(iso) == shown
    assert W.month_year(iso) == month_year


@pytest.mark.parametrize(
    "iso", KEY["dates_refused"], ids=[str(i) for i in range(len(KEY["dates_refused"]))]
)
def test_dates_refused(iso: str) -> None:
    with pytest.raises(DeliveryRefused):
        W.display_date(iso)
    with pytest.raises(DeliveryRefused):
        W.month_year(iso)


def test_non_str_date_is_type_error() -> None:
    for bad in (None, 20260101, b"2026-01-01"):
        with pytest.raises(TypeError):
            W.display_date(cast(str, bad))
        with pytest.raises(TypeError):
            W.month_year(cast(str, bad))


def test_not_recorded() -> None:
    assert W.not_recorded == KEY["not_recorded"]


@pytest.mark.parametrize("row", KEY["states"], ids=ids_of(KEY["states"]))
def test_states(row: list[str | None]) -> None:
    status, reason, word = row
    assert W.state_word(cast(str, status), reason) == word


@pytest.mark.parametrize("row", KEY["states_refused"], ids=ids_of(KEY["states_refused"]))
def test_states_refused(row: list[str | None]) -> None:
    with pytest.raises(DeliveryRefused) as caught:
        W.state_word(cast(str, row[0]), row[1])
    assert str(row[0]) in str(caught.value)


def test_bands() -> None:
    assert list(W.measures) == list(KEY["bands"])
    for key, expected in KEY["bands"].items():
        measure = W.measures[key]
        assert measure.name == expected["name"]
        got = [(b.label, b.min, b.max) for b in measure.bands]
        want = [
            (
                label,
                None if low is None else Decimal(low),
                None if high is None else Decimal(high),
            )
            for label, low, high in expected["bands"]
        ]
        assert got == want


@pytest.mark.parametrize("row", KEY["load_refused"], ids=ids_of(KEY["load_refused"]))
def test_load_refused(row: dict[str, str]) -> None:
    text = SOURCE_PATH.read_text(encoding="utf-8")
    assert text.count(row["old"]) == 1
    data = text.replace(row["old"], row["new"]).encode("utf-8")
    with pytest.raises(DeliveryRefused):
        wording.load_wording(data)


def test_load_refused_not_json_and_not_object() -> None:
    for data in (b"", b"[]", b"{", b"1"):
        with pytest.raises(DeliveryRefused):
            wording.load_wording(data)


@given(st.text())
def test_any_value_comes_back_verbatim(value: str) -> None:
    got = W.fill("changes.none.text", {"issuer_name": value})
    assert got == (
        "This is the first report on " + value + ". What changed will appear here "
        "after the next run."
    )

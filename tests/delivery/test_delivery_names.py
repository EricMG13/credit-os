"""The naming layer of delivery, compared row by row with the controller's answer key."""

import importlib.util
import re
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest
from hypothesis import given
from hypothesis import strategies as st

from credit_os.delivery import names
from credit_os.delivery.errors import DeliveryRefused

KEY_PATH = Path(__file__).with_name("delivery_names_key.py")


def load_key() -> ModuleType:
    """Import the answer key by path, without touching sys.path."""
    spec = importlib.util.spec_from_file_location("delivery_names_key", KEY_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {KEY_PATH}")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


KEY = load_key()
D1: str = KEY.D1


def idx(rows: tuple[object, ...]) -> list[str]:
    return [str(i) for i in range(len(rows))]


def test_modules_equal_key() -> None:
    assert tuple(tuple(m) for m in names.MODULES) == KEY.MODULES


def test_slug_rules() -> None:
    slugs = [m.slug for m in names.MODULES]
    for slug in slugs:
        assert re.fullmatch(r"[a-z0-9-]{1,64}", slug)
        assert not slug.startswith("-")
        assert not slug.endswith("-")
        assert slug not in KEY.WINDOWS_RESERVED
    assert len({s.casefold() for s in slugs}) == len(slugs)


@pytest.mark.parametrize("code,slug,name", KEY.MODULES, ids=[c for c, _, _ in KEY.MODULES])
def test_module_lookup(code: str, slug: str, name: str) -> None:
    found = names.module(code)
    assert (found.code, found.slug, found.name) == (code, slug, name)


@pytest.mark.parametrize("code", KEY.UNKNOWN_CODES, ids=idx(KEY.UNKNOWN_CODES))
def test_unknown_code_refused(code: str) -> None:
    with pytest.raises(DeliveryRefused):
        names.module(code)


@pytest.mark.parametrize("text", KEY.IDS_ACCEPTED, ids=idx(KEY.IDS_ACCEPTED))
def test_id_accepted(text: str) -> None:
    assert names.check_id(text) == text


@pytest.mark.parametrize("text", KEY.IDS_REFUSED, ids=idx(KEY.IDS_REFUSED))
def test_id_refused(text: str) -> None:
    with pytest.raises(DeliveryRefused):
        names.check_id(text)


def test_id_wrong_type() -> None:
    check: Callable[..., object] = names.check_id
    with pytest.raises(TypeError):
        check(5)


@pytest.mark.parametrize("issuer,run,delivery,expected", KEY.FOLDERS, ids=idx(KEY.FOLDERS))
def test_folder(issuer: str, run: str, delivery: str, expected: str) -> None:
    assert names.folder(issuer, run, delivery) == expected


@pytest.mark.parametrize("delivery", KEY.DELIVERIES_REFUSED, ids=idx(KEY.DELIVERIES_REFUSED))
def test_folder_refuses_delivery(delivery: str) -> None:
    with pytest.raises(DeliveryRefused):
        names.folder("nbg", "r-0001", delivery)


def test_folder_refuses_bad_ids() -> None:
    with pytest.raises(DeliveryRefused):
        names.folder("..", "r", D1)
    with pytest.raises(DeliveryRefused):
        names.folder("a", "b/c", D1)


@pytest.mark.parametrize("segments,expected", KEY.HASH_ADDRESSES, ids=idx(KEY.HASH_ADDRESSES))
def test_hash_address(segments: tuple[str, ...], expected: str) -> None:
    assert names.hash_address(*segments) == expected


@pytest.mark.parametrize("segments", KEY.HASH_REFUSED, ids=idx(KEY.HASH_REFUSED))
def test_hash_address_refused(segments: tuple[str, ...]) -> None:
    with pytest.raises(DeliveryRefused):
        names.hash_address(*segments)


@pytest.mark.parametrize("issuer,run,expected", KEY.FORECAST_HREFS, ids=idx(KEY.FORECAST_HREFS))
def test_forecast_href(issuer: str, run: str, expected: str) -> None:
    assert names.forecast_href(issuer, run) == expected


@pytest.mark.parametrize("issuer,run,delivery,expected", KEY.ARCHIVES, ids=idx(KEY.ARCHIVES))
def test_archive_name(issuer: str, run: str, delivery: str, expected: str) -> None:
    assert names.archive_name(issuer, run, delivery) == expected


@pytest.mark.parametrize(
    "issuer,run,delivery,code,expected", KEY.MODULE_DOWNLOADS, ids=idx(KEY.MODULE_DOWNLOADS)
)
def test_module_download(issuer: str, run: str, delivery: str, code: str, expected: str) -> None:
    assert names.module_download(issuer, run, delivery, code) == expected


def test_module_download_unknown_code() -> None:
    with pytest.raises(DeliveryRefused):
        names.module_download("nbg", "r-0001", D1, "CP-9")


@pytest.mark.parametrize("href", KEY.PATHS_ACCEPTED, ids=idx(KEY.PATHS_ACCEPTED))
def test_path_accepted(href: str) -> None:
    assert names.check_relative_path(href) == href


@pytest.mark.parametrize("href", KEY.PATHS_REFUSED, ids=idx(KEY.PATHS_REFUSED))
def test_path_refused(href: str) -> None:
    with pytest.raises(DeliveryRefused):
        names.check_relative_path(href)


def test_path_wrong_type() -> None:
    check: Callable[..., object] = names.check_relative_path
    with pytest.raises(TypeError):
        check(5)


ABSOLUTE = (
    "/Users/someone/Documents/lib/x.md",
    "C:\\Users\\someone\\lib\\x.md",
    "C:/Users/someone/lib/x.md",
    "\\\\server\\someone\\x.md",
    "file:///C:/Users/someone/x.md",
)
LEAKY_CALLS: dict[str, Callable[[str], object]] = {
    "check_relative_path": names.check_relative_path,
    "check_id": names.check_id,
    "hash_address": lambda v: names.hash_address("library", v),
    "folder_delivery": lambda v: names.folder("nbg", "r-0001", v),
    "folder_issuer": lambda v: names.folder(v, "r-0001", D1),
    "folder_run": lambda v: names.folder("nbg", v, D1),
    "module": names.module,
    "forecast_href": lambda v: names.forecast_href(v, "r-0001"),
    "archive_name": lambda v: names.archive_name(v, "r-0001", D1),
    "module_download_code": lambda v: names.module_download("nbg", "r-0001", D1, v),
    "module_download_delivery": lambda v: names.module_download("nbg", "r-0001", v, "CP-8"),
}


@pytest.mark.parametrize("label", list(LEAKY_CALLS), ids=list(LEAKY_CALLS))
@pytest.mark.parametrize("value", ABSOLUTE, ids=idx(ABSOLUTE))
def test_refusal_message_holds_no_input(label: str, value: str) -> None:
    with pytest.raises(DeliveryRefused) as info:
        LEAKY_CALLS[label](value)
    message = str(info.value)
    for banned in (value, "Users", "someone", "C:", "server", "file:"):
        assert banned not in message


ID_TEXT = st.text(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-",
    min_size=1,
    max_size=128,
)


@given(ID_TEXT, ID_TEXT)
def test_ids_build_valid_names(issuer: str, run: str) -> None:
    if issuer in (".", "..") or run in (".", ".."):
        return
    assert re.fullmatch(r"[0-9a-f]{20}", names.folder(issuer, run, D1))
    assert names.check_relative_path(names.archive_name(issuer, run, D1)) == names.archive_name(
        issuer, run, D1
    )
    assert names.hash_address("library", issuer, run, "overview").startswith("#/")


@given(st.text())
def test_check_id_total(text: str) -> None:
    try:
        assert names.check_id(text) == text
    except DeliveryRefused:
        pass


@given(st.text())
def test_check_relative_path_total(text: str) -> None:
    try:
        assert names.check_relative_path(text) == text
    except DeliveryRefused:
        pass

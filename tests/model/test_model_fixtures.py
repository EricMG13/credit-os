"""The synthetic model fixtures: their hashes, folder contents and forecast blocks."""

import hashlib
import re
from pathlib import Path

import pytest

from credit_os.handoff.document import parse
from credit_os.model.inputs import ForecastInputs, read_inputs
from credit_os.model.refusals import ForecastRefused, RefusalKind

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "model"
NAMES = (
    "foundation.md",
    "foundation-thousands.md",
    "foundation-eur.md",
    "forward-model.md",
    "forward-model-thousands.md",
)
LINE = re.compile(r"^([0-9a-f]{64}) {2}(\S.*)$")


def _sums(folder: Path) -> list[tuple[str, str]]:
    text = (folder / "SHA256SUMS").read_bytes().decode("ascii")
    assert text.endswith("\n")
    rows = []
    for line in text.split("\n")[:-1]:
        found = LINE.fullmatch(line)
        assert found is not None, f"bad SHA256SUMS line: {line!r}"
        rows.append((found.group(2), found.group(1)))
    return rows


def check_sums_form(folder: Path) -> None:
    assert [name for name, _ in _sums(folder)] == list(NAMES)


def check_hashes(folder: Path) -> None:
    for name, digest in _sums(folder):
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest, name


def check_entries(folder: Path) -> None:
    found = sorted(entry.name for entry in folder.iterdir())
    assert found == sorted((*NAMES, "SHA256SUMS", ".gitattributes"))


def test_sums_file_form() -> None:
    check_sums_form(FIXTURES)


def test_every_file_matches_its_hash() -> None:
    check_hashes(FIXTURES)


def test_folder_holds_only_the_fixtures() -> None:
    check_entries(FIXTURES)


def test_gitattributes_exact() -> None:
    expected = b"*.md -text\nSHA256SUMS text eol=lf\n"
    assert (FIXTURES / ".gitattributes").read_bytes() == expected


@pytest.mark.parametrize("name", NAMES)
def test_parses_and_is_ascii(name: str) -> None:
    data = (FIXTURES / name).read_bytes()
    data.decode("ascii")
    parse(data)


def _read(name: str) -> tuple[ForecastInputs, dict[str, str]]:
    return read_inputs(parse((FIXTURES / name).read_bytes()))


@pytest.mark.parametrize(
    ("name", "scale", "stated"),
    [
        ("foundation.md", 1, 0),
        ("forward-model.md", 1, 0),
        ("foundation-thousands.md", 1000, 16),
        ("forward-model-thousands.md", 1000, 19),
    ],
)
def test_forecast_blocks(name: str, scale: int, stated: int) -> None:
    inputs, stated_map = _read(name)
    assert inputs.scale == scale
    assert inputs.currency == "USD"
    assert len(stated_map) == stated


@pytest.mark.parametrize(
    ("thousands", "millions"),
    [
        ("foundation-thousands.md", "foundation.md"),
        ("forward-model-thousands.md", "forward-model.md"),
    ],
)
def test_thousands_equal_millions_except_scale(thousands: str, millions: str) -> None:
    scaled = _read(thousands)[0].model_dump(mode="json")
    plain = _read(millions)[0].model_dump(mode="json")
    assert scaled.pop("scale") == 1000
    assert plain.pop("scale") == 1
    assert scaled == plain


def test_eur_foundation_has_no_forecast_block() -> None:
    with pytest.raises(ForecastRefused) as caught:
        _read("foundation-eur.md")
    assert caught.value.kind is RefusalKind.BLOCK


@pytest.mark.parametrize("name", ["forward-model.md", "forward-model-thousands.md"])
def test_forward_model_states_facilities_and_cases(name: str) -> None:
    inputs = _read(name)[0]
    assert inputs.facilities
    assert inputs.upside_drivers is not None
    assert inputs.downside_drivers is not None


@pytest.mark.parametrize("name", ["foundation.md", "foundation-thousands.md"])
def test_foundation_states_no_cases(name: str) -> None:
    inputs = _read(name)[0]
    assert inputs.downside_shock is None
    assert inputs.upside_drivers is None
    assert inputs.downside_drivers is None
    assert inputs.facilities is None


def _copy(tmp_path: Path) -> Path:
    folder = tmp_path / "model"
    folder.mkdir()
    for entry in FIXTURES.iterdir():
        (folder / entry.name).write_bytes(entry.read_bytes())
    return folder


def test_a_changed_byte_is_caught(tmp_path: Path) -> None:
    folder = _copy(tmp_path)
    target = folder / "foundation.md"
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(AssertionError):
        check_hashes(folder)


def test_an_extra_file_is_caught(tmp_path: Path) -> None:
    folder = _copy(tmp_path)
    (folder / "extra.md").write_bytes(b"x")
    with pytest.raises(AssertionError, match="extra.md"):
        check_entries(folder)


def test_a_crlf_sums_file_is_caught(tmp_path: Path) -> None:
    folder = _copy(tmp_path)
    sums = folder / "SHA256SUMS"
    sums.write_bytes(sums.read_bytes().replace(b"\n", b"\r\n"))
    with pytest.raises(AssertionError):
        check_sums_form(folder)

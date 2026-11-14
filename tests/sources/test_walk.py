"""The folder walk: pins, skipped rows and refusals."""

import errno
import os
import sys
import tempfile
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

import credit_os.sources.walk as walk_module
from credit_os import sources
from credit_os.sources import (
    PinnedFolder,
    Skipped,
    SourceKind,
    SourcePin,
    SourceRefused,
    SourceTooLarge,
    SourceUnreadable,
    pin_folder,
    refuse_case_collisions,
)
from credit_os.sources.files import read_capped, source_path

FIXTURE: dict[str, bytes] = {
    "annual-report.pdf": b"%PDF-1.4\n%synthetic\n",
    "data/table.csv": b"period,revenue\nFY2025,100\n",
    "memo.docx": b"PK\x03\x04synthetic-docx",
    "model.xlsx": b"PK\x03\x04synthetic-xlsx",
    "notes/Summary.MD": b"# Synthetic summary\n",
    "notes/filing.html": b"<html><body><p>Synthetic filing.</p></body></html>\n",
    "page.htm": b"<p>x</p>\n",
    "readme.txt": b"Synthetic note.\n",
    ".cache/x.txt": b"cached\n",
    ".hidden.txt": b"hidden\n",
    "_drafts/old.pdf": b"%PDF-1.4\n",
    "image.png": b"\x89PNG\r\n\x1a\n",
    "noext": b"no suffix\n",
    "notes/_scratch.txt": b"scratch\n",
    "notes/archive.zip": b"PK\x03\x04",
    "~$memo.docx": b"lock",
}
README = b"Synthetic note.\n"
README_SHA = "4157540c50a21d8eccdd85cc071e37f2b23dd35525473b1b671044125dd44f42"
SYMLINK_REASON = "symbolic link"
LINKED = "is or passes through a symbolic link"
SEGMENT = "segment starts or ends with a space or ends with a dot"

EXPECTED_PINS = (
    (
        "annual-report.pdf",
        "83decc79ecc2b3f1cd8e01f34991efb870e07e9ec43d48bf0df25e7dd488afd2",
        20,
        SourceKind.PDF,
    ),
    (
        "data/table.csv",
        "2e21223b3346488da9b43cbb41c8dfa74e56d5f075025c8b0429502dc75d88b0",
        26,
        SourceKind.CSV,
    ),
    (
        "memo.docx",
        "a4ccfb55208c2ddf1440efd9c4d886d84250d714cff1e827ea9d9e19e57378ea",
        18,
        SourceKind.DOCX,
    ),
    (
        "model.xlsx",
        "171501c07a0313baef18ed2a59b5e2b744fbd166b7f45809981d63e408099deb",
        18,
        SourceKind.XLSX,
    ),
    (
        "notes/Summary.MD",
        "04ea7b2f63af5c6457d14027f28e4120caadfd2281daa5bddffbcef621bfde29",
        20,
        SourceKind.TEXT,
    ),
    (
        "notes/filing.html",
        "5a7098a94ea17556df46d90f5f335b6c303d318d24996c74ba6f1ee068cdfd4d",
        51,
        SourceKind.HTML,
    ),
    (
        "page.htm",
        "4e29150f4b637511bc7b0cb3bf626d63ce65a89e045f33ff39bd9ce68737741e",
        9,
        SourceKind.HTML,
    ),
    ("readme.txt", README_SHA, 16, SourceKind.TEXT),
)
EXPECTED_SKIPPED = (
    (".cache/", "hidden name"),
    (".hidden.txt", "hidden name"),
    ("_drafts/", "excluded name"),
    ("image.png", "unsupported suffix"),
    ("noext", "unsupported suffix"),
    ("notes/_scratch.txt", "excluded name"),
    ("notes/archive.zip", "unsupported suffix"),
    ("~$memo.docx", "excluded name"),
)


def _write(folder: Path, files: dict[str, bytes]) -> Path:
    for name, raw in files.items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return folder


def _symlink(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except NotImplementedError:
        pytest.skip("this platform cannot create symbolic links")
    except OSError as error:
        if getattr(error, "winerror", None) == 1314:
            pytest.skip("this account cannot create symbolic links")
        raise


def _skipped(*rows: tuple[str, str]) -> tuple[Skipped, ...]:
    return tuple(Skipped(name=name, reason=reason) for name, reason in rows)


def _pin_tuples(result: PinnedFolder) -> tuple[tuple[str, str, int, SourceKind], ...]:
    return tuple((p.name, p.sha256, p.size_bytes, p.kind) for p in result.pins)


def _refusal(folder: Path, exc: type[Exception] = SourceRefused) -> str:
    with pytest.raises(exc) as caught:
        pin_folder(folder)
    return str(caught.value)


def test_fixture_folder(tmp_path: Path) -> None:
    result = pin_folder(_write(tmp_path, FIXTURE))
    assert _pin_tuples(result) == EXPECTED_PINS
    assert result.skipped == _skipped(*EXPECTED_SKIPPED)


@pytest.mark.parametrize(
    ("name", "reason"),
    [(".x.png", "hidden name"), ("_x.png", "excluded name"), ("~$x.png", "excluded name")],
)
def test_precedence(tmp_path: Path, name: str, reason: str) -> None:
    result = pin_folder(_write(tmp_path, {name: b"x"}))
    assert result == PinnedFolder(pins=(), skipped=_skipped((name, reason)))


def test_nested_folders(tmp_path: Path) -> None:
    files = {
        "a/b/c/deep.txt": README,
        "a/b/_skip/x.txt": b"x",
        "a/b/c/pic.png": b"x",
        "_r\u00e9sum\u00e9/x.txt": b"x",
        "r\u00e9sum\u00e9.png": b"x",
    }
    result = pin_folder(_write(tmp_path, files))
    assert result.pins == (
        SourcePin(name="a/b/c/deep.txt", sha256=README_SHA, size_bytes=16, kind=SourceKind.TEXT),
    )
    assert result.skipped == _skipped(
        ("_r\u00e9sum\u00e9/", "excluded name"),
        ("a/b/_skip/", "excluded name"),
        ("a/b/c/pic.png", "unsupported suffix"),
        ("r\u00e9sum\u00e9.png", "unsupported suffix"),
    )


def test_not_a_folder(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    assert _refusal(missing) == f"{missing}: not a folder"
    path = _write(tmp_path, {"file.txt": README}) / "file.txt"
    assert _refusal(path) == f"{path}: not a folder"
    empty = tmp_path / "empty"
    empty.mkdir()
    assert pin_folder(empty) == PinnedFolder(pins=(), skipped=())


def test_over_the_cap(tmp_path: Path) -> None:
    _write(tmp_path, {"readme.txt": README})
    with (tmp_path / "big.txt").open("wb") as handle:
        handle.truncate(52428801)
    assert (
        _refusal(tmp_path, SourceTooLarge) == f"{tmp_path / 'big.txt'}: larger than 52428800 bytes"
    )


@pytest.mark.parametrize(
    ("name", "raw", "message"),
    [
        ("fake.pdf", b"not a pdf\n", "fake.pdf: does not start with %PDF-"),
        ("fake.xlsx", b"plain", "fake.xlsx: does not start with a zip signature"),
        ("binary.txt", b"%PDF-1.4\n", "binary.txt: starts with a PDF signature"),
        ("zip.csv", b"PK\x03\x04", "zip.csv: starts with a zip signature"),
    ],
)
def test_wrong_kind(tmp_path: Path, name: str, raw: bytes, message: str) -> None:
    _write(tmp_path, {name: raw})
    assert _refusal(tmp_path, SourceUnreadable) == message


def test_collisions() -> None:
    cases = [
        (
            ["notes/Filing.html", "a.txt", "notes/filing.html"],
            "notes/Filing.html and notes/filing.html differ only by case",
        ),
        (["a.txt", "a.txt"], "a.txt is listed twice"),
        (["STRASSE.txt", "straße.txt"], "STRASSE.txt and straße.txt differ only by case"),
        (
            ["r\u00e9sum\u00e9.txt", "re\u0301sume\u0301.txt"],
            "re\u0301sume\u0301.txt and r\u00e9sum\u00e9.txt differ only by case or Unicode form",
        ),
        (
            ["\u0124\u0331.txt", "\u0125\u0331.txt"],
            "\u0124\u0331.txt and \u0125\u0331.txt differ only by case",
        ),
        (
            ["\u015a.txt", "\u017f\u0301.txt"],
            "\u015a.txt and \u017f\u0301.txt differ only by case or Unicode form",
        ),
        (
            ["\u1fb3\u0301.txt", "\u1fb4.txt"],
            "\u1fb3\u0301.txt and \u1fb4.txt differ only by case or Unicode form",
        ),
        (
            ["A" * 130 + ".txt", "a" * 130 + ".txt"],
            "A" * 120 + "… and " + "a" * 120 + "… differ only by case",
        ),
    ]
    for names, message in cases:
        with pytest.raises(SourceRefused) as caught:
            refuse_case_collisions(names)
        assert str(caught.value) == message
    refuse_case_collisions(["a.txt", "b.txt"])
    refuse_case_collisions([])


def _pin(name: str) -> SourcePin:
    return SourcePin(name=name, sha256=README_SHA, size_bytes=16, kind=SourceKind.TEXT)


def test_container_rules() -> None:
    with pytest.raises(ValidationError):
        PinnedFolder(pins=(_pin("Readme.txt"), _pin("readme.txt")), skipped=())
    with pytest.raises(ValidationError):
        PinnedFolder(pins=(_pin("readme.txt"), _pin("readme.txt")), skipped=())
    forged = SourcePin.model_construct(
        name="../x.txt", sha256="NOT-HEX", size_bytes=-5, kind=SourceKind.TEXT
    )
    with pytest.raises(ValidationError):
        PinnedFolder(pins=(forged,), skipped=())


def test_case_collision_on_disk(tmp_path: Path) -> None:
    (tmp_path / "Probe").write_bytes(b"x")
    if (tmp_path / "probe").exists():
        pytest.skip("volume is not case-sensitive")
    folder = _write(tmp_path / "f", {"Readme.txt": README, "readme.txt": README})
    assert _refusal(folder) == "Readme.txt and readme.txt differ only by case"


def test_unicode_forms_on_disk(tmp_path: Path) -> None:
    names = ["re\u0301sume\u0301.txt", "r\u00e9sum\u00e9.txt"]
    _write(tmp_path, {name: README for name in names})
    if len(os.listdir(tmp_path)) < 2:
        pytest.skip("volume does not keep both Unicode forms")
    assert _refusal(tmp_path) == f"{names[0]} and {names[1]} differ only by case or Unicode form"


def test_stored_name_as_listed(tmp_path: Path) -> None:
    decomposed = "re\u0301sume\u0301.txt"
    _write(tmp_path, {decomposed: README})
    if os.listdir(tmp_path) != [decomposed]:
        pytest.skip("volume rewrites names")
    assert [p.name for p in pin_folder(tmp_path).pins] == [decomposed]


def _readme_and_outside(tmp_path: Path, outside_files: dict[str, bytes]) -> tuple[Path, Path]:
    folder = _write(tmp_path / "f", {"readme.txt": README})
    return folder, _write(tmp_path / "outside", outside_files)


def test_links(tmp_path: Path) -> None:
    folder, outside = _readme_and_outside(tmp_path, {"secret.txt": b"secret\n"})
    for name in ("link.txt", ".x", "_x"):
        _symlink(folder / name, folder / "readme.txt")
    _symlink(folder / "linkdir", outside)
    result = pin_folder(folder)
    assert [p.name for p in result.pins] == ["readme.txt"]
    assert result.skipped == _skipped(
        (".x", SYMLINK_REASON),
        ("_x", SYMLINK_REASON),
        ("link.txt", SYMLINK_REASON),
        ("linkdir", SYMLINK_REASON),
    )


def test_linked_directory_is_not_entered(tmp_path: Path) -> None:
    folder, outside = _readme_and_outside(tmp_path, {"filing.html": FIXTURE["notes/filing.html"]})
    _symlink(folder / "notes", outside)
    result = pin_folder(folder)
    assert [p.name for p in result.pins] == ["readme.txt"]
    assert result.skipped == _skipped(("notes", SYMLINK_REASON))


@pytest.mark.skipif(sys.platform != "win32", reason="junctions exist on Windows only")
def test_junction(tmp_path: Path) -> None:
    if sys.platform == "win32":
        import _winapi

        folder, outside = _readme_and_outside(tmp_path, {"secret.txt": b"secret\n"})
        _winapi.CreateJunction(str(outside), str(folder / "joined"))
        assert (folder / "joined").is_junction()
        result = pin_folder(folder)
        assert [p.name for p in result.pins] == ["readme.txt"]
        assert result.skipped == _skipped(("joined", SYMLINK_REASON))


def test_swap_between_scan_and_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    folder = _write(
        tmp_path / "f", {"readme.txt": README, "notes/filing.html": FIXTURE["notes/filing.html"]}
    )
    outside = _write(tmp_path / "outside", {"filing.html": FIXTURE["notes/filing.html"]})
    real_source_path = source_path
    real_read = read_capped
    swapped: list[str] = []
    reads: list[Path] = []

    def swapping(root: Path, name: str) -> Path:
        if name == "notes/filing.html" and not swapped:
            swapped.append(name)
            (root / "notes").rename(root / "notes-away")
            _symlink(root / "notes", outside)
        return real_source_path(root, name)

    def counting(path: Path) -> bytes:
        reads.append(path)
        return real_read(path)

    monkeypatch.setattr(walk_module, "source_path", swapping)
    monkeypatch.setattr(walk_module, "read_capped", counting)
    assert _refusal(folder) == f"notes/filing.html: {LINKED}"
    assert swapped == ["notes/filing.html"]
    assert folder / "notes" / "filing.html" not in reads


def test_fifo(tmp_path: Path) -> None:
    if not hasattr(os, "mkfifo"):
        pytest.skip("os.mkfifo is not available on this platform")
    _write(tmp_path, {"readme.txt": README})
    os.mkfifo(tmp_path / "pipe.txt")
    os.mkfifo(tmp_path / "_pipe")
    result = pin_folder(tmp_path)
    assert [p.name for p in result.pins] == ["readme.txt"]
    assert result.skipped == _skipped(
        ("_pipe", "excluded name"), ("pipe.txt", "not a regular file")
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows cannot hold this name")
def test_backslash_name(tmp_path: Path) -> None:
    _write(tmp_path, {"a\\b.txt": README})
    assert _refusal(tmp_path) == "'a\\\\b.txt': forbidden character U+005C"
    assert _refusal(_write(tmp_path / "k", {"bad\r.pdf": b"not a pdf\n"})) == (
        "'bad\\r.pdf': forbidden character U+000D"
    )


def test_bidi_name_is_written_with_escapes(tmp_path: Path) -> None:
    result = pin_folder(_write(tmp_path, {"readme.txt": README, "evil\u202egnp.png": b"x"}))
    assert [p.name for p in result.pins] == ["readme.txt"]
    assert result.skipped == _skipped(("evil\\u202egnp.png", "unsupported suffix"))
    assert PinnedFolder.model_validate_json(result.model_dump_json()) == result


def test_slash_lookalike_name_is_written_with_escapes(tmp_path: Path) -> None:
    result = pin_folder(_write(tmp_path, {"readme.txt": README, "a\u2215b.png": b"x"}))
    assert [p.name for p in result.pins] == ["readme.txt"]
    assert result.skipped == _skipped(("a\\u2215b.png", "unsupported suffix"))
    assert PinnedFolder.model_validate_json(result.model_dump_json()) == result


@pytest.mark.skipif(sys.platform == "win32", reason="Windows cannot hold this name")
def test_control_names_are_written_with_escapes(tmp_path: Path) -> None:
    files = {
        "readme.txt": README,
        "Icon\r": b"x",
        "a\\b.png": b"x",
        ".x\r": b"x",
    }
    result = pin_folder(_write(tmp_path, files))
    assert [p.name for p in result.pins] == ["readme.txt"]
    assert result.skipped == _skipped(
        (".x\\r", "hidden name"),
        ("Icon\\r", "unsupported suffix"),
        ("a\\\\b.png", "unsupported suffix"),
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows normalises or cannot hold these names")
@pytest.mark.parametrize(
    ("directory", "files", "message"),
    [
        ("bad\rdir", {"x.png": b"x"}, "'bad\\rdir': forbidden character U+000D"),
        ("notes.", {"x.png": b"x"}, "'notes.': " + SEGMENT),
        ("notes ", {}, "'notes ': " + SEGMENT),
        ("ok/sub ", {"x.png": b"x"}, "'ok/sub ': " + SEGMENT),
    ],
)
def test_entered_directory_with_a_bad_name_refuses(
    tmp_path: Path, directory: str, files: dict[str, bytes], message: str
) -> None:
    folder = _write(tmp_path, {f"{directory}/{name}": raw for name, raw in files.items()})
    (folder / directory).mkdir(parents=True, exist_ok=True)
    assert _refusal(folder) == message


@pytest.mark.skipif(sys.platform == "win32", reason="Windows cannot hold this name")
def test_hidden_directory_with_a_bad_name_is_skipped(tmp_path: Path) -> None:
    result = pin_folder(_write(tmp_path, {"readme.txt": README, ".x\r/a.txt": b"x"}))
    assert [p.name for p in result.pins] == ["readme.txt"]
    assert result.skipped == _skipped((".x\\r/", "hidden name"))


def test_bad_name_file_refuses_on_every_platform(tmp_path: Path) -> None:
    folder = _write(tmp_path, {"readme.txt": README, "evil\u202e.txt": b"x"})
    assert _refusal(folder) == "'evil\\u202e.txt': forbidden character U+202E"


def test_bad_name_directory_refuses_before_it_is_listed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = _write(tmp_path, {"readme.txt": README, "bad\u202edir/x.png": b"x"})
    real_scandir = os.scandir
    listed: list[str] = []

    def recording(path: str | Path) -> object:
        listed.append(os.fspath(path))
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", recording)
    assert _refusal(folder) == "'bad\\u202edir': forbidden character U+202E"
    assert listed
    assert not any(path.endswith("bad\u202edir") for path in listed)


def test_hidden_bad_name_directory_is_skipped_on_every_platform(tmp_path: Path) -> None:
    result = pin_folder(_write(tmp_path, {"readme.txt": README, ".h\u202e/a.txt": b"x"}))
    assert [p.name for p in result.pins] == ["readme.txt"]
    assert result.skipped == _skipped((".h\\u202e/", "hidden name"))


def _non_utf8(folder: Path, suffix: bytes) -> None:
    _write(folder, {"readme.txt": README})
    try:
        with open(os.fsencode(folder) + b"/bad\xff" + suffix, "wb") as handle:
            handle.write(b"x")
    except OSError:
        pytest.skip("volume refuses a non-UTF-8 name")


@pytest.mark.skipif(sys.platform == "win32", reason="Windows cannot hold this name")
def test_non_utf8_names(tmp_path: Path) -> None:
    _non_utf8(tmp_path / "png", b".png")
    result = pin_folder(tmp_path / "png")
    assert [p.name for p in result.pins] == ["readme.txt"]
    assert result.skipped == _skipped(("bad\\udcff.png", "unsupported suffix"))
    assert PinnedFolder.model_validate_json(result.model_dump_json()) == result
    _non_utf8(tmp_path / "txt", b".txt")
    assert _refusal(tmp_path / "txt") == "'bad\\udcff.txt': forbidden character U+DCFF"


def test_listing_failure_is_typed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    folder = _write(tmp_path, {"readme.txt": README})
    failure = OSError(errno.EACCES, "synthetic")

    def fail(path: object) -> object:
        raise failure

    monkeypatch.setattr(os, "scandir", fail)
    with pytest.raises(SourceUnreadable) as caught:
        pin_folder(folder)
    assert str(caught.value) == f"{folder}: cannot list (synthetic)"
    assert caught.value.__cause__ is failure


@pytest.mark.parametrize("code", [errno.EACCES, errno.ENAMETOOLONG])
def test_folder_test_failure_is_typed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    failure = OSError(code, "synthetic")

    def fail(self: Path) -> bool:
        raise failure

    monkeypatch.setattr(Path, "is_dir", fail)
    with pytest.raises(SourceRefused) as caught:
        pin_folder(tmp_path)
    assert str(caught.value) == f"{tmp_path}: not a folder"
    assert caught.value.__cause__ is failure


def test_listing_failure_without_strerror(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(path: object) -> object:
        raise OSError("text")

    monkeypatch.setattr(os, "scandir", fail)
    assert _refusal(tmp_path, SourceUnreadable) == f"{tmp_path}: cannot list (text)"


_ENTRY_FAILURE = OSError(errno.EACCES, "synthetic")


class BrokenEntry:
    name = "x.txt"

    def is_symlink(self) -> bool:
        raise _ENTRY_FAILURE


def test_entry_failure_is_typed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    failure = _ENTRY_FAILURE
    monkeypatch.setattr(walk_module, "_listing", lambda *args: [BrokenEntry()])
    with pytest.raises(SourceUnreadable) as caught:
        pin_folder(tmp_path)
    assert str(caught.value) == f"{tmp_path}: cannot list (synthetic)"
    assert caught.value.__cause__ is failure


def test_nested_entry_failure_names_the_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = _write(tmp_path, {"readme.txt": README})
    (folder / "sub").mkdir()
    real = walk_module._listing

    def listing(folder: Path, directory: Path, prefix: str) -> list[object]:
        if prefix == "sub/":
            return [BrokenEntry()]
        return list(real(folder, directory, prefix))

    monkeypatch.setattr(walk_module, "_listing", listing)
    with pytest.raises(SourceUnreadable) as caught:
        pin_folder(folder)
    assert str(caught.value) == f"{folder / 'sub'}: cannot list (synthetic)"
    assert caught.value.__cause__ is _ENTRY_FAILURE


@pytest.mark.parametrize(
    ("directory", "exc", "message"),
    [
        ("locked", SourceUnreadable, "{folder}/locked: cannot list ({reason})"),
        ("evil\x1b[2J", SourceRefused, "'evil\\x1b[2J': forbidden character U+001B"),
    ],
)
def test_unlistable_directory(
    tmp_path: Path, directory: str, exc: type[Exception], message: str
) -> None:
    if sys.platform == "win32":
        pytest.skip("Windows: chmod does not deny listing, or the name cannot exist")
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("root ignores directory permissions")
    folder = _write(tmp_path, {"readme.txt": README})
    locked = folder / directory
    locked.mkdir()
    locked.chmod(0o000)
    try:
        try:
            os.listdir(locked)
        except PermissionError:
            pass
        else:
            pytest.skip("chmod does not deny listing here")
        raised = _refusal(folder, exc)
    finally:
        locked.chmod(0o700)
    assert raised == message.format(folder=folder, reason=os.strerror(errno.EACCES))


def test_public_surface() -> None:
    expected = [
        "MAX_BYTES",
        "PinnedFolder",
        "SUFFIX_KINDS",
        "Skipped",
        "SourceChanged",
        "SourceError",
        "SourceKind",
        "SourcePin",
        "SourceRefused",
        "SourceTooLarge",
        "SourceUnreadable",
        "check_kind",
        "kind_of",
        "pin_folder",
        "read_capped",
        "read_pinned",
        "refuse_case_collisions",
        "source_path",
        "validate_name",
    ]
    assert sorted(sources.__all__) == expected
    assert all(hasattr(sources, name) for name in expected)


# --- property test: expected outcomes come from the drawn choices only ---

_PREFIX_REASON: dict[str, str | None] = {
    "": None,
    ".": "hidden name",
    "_": "excluded name",
    "~$": "excluded name",
}
_ACCEPTED: dict[str, tuple[SourceKind, bytes]] = {
    ".pdf": (SourceKind.PDF, b"%PDF-1.4\n"),
    ".htm": (SourceKind.HTML, b"<p>x</p>\n"),
    ".html": (SourceKind.HTML, b"<p>x</p>\n"),
    ".docx": (SourceKind.DOCX, b"PK\x03\x04x"),
    ".txt": (SourceKind.TEXT, b"text\n"),
    ".md": (SourceKind.TEXT, b"# text\n"),
    ".xlsx": (SourceKind.XLSX, b"PK\x03\x04x"),
    ".csv": (SourceKind.CSV, b"a,b\n"),
}
_RESERVED = {"con", "prn", "aux", "nul"} | {f"{d}{i}" for d in ("com", "lpt") for i in range(10)}
_stems = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=6).filter(
    lambda stem: stem not in _RESERVED
)


_Drawn = tuple[dict[str, bytes], list[tuple[str, SourceKind]], list[tuple[str, str]], list[str]]


@st.composite
def _folders(draw: st.DrawFn) -> _Drawn:
    stems = draw(st.lists(_stems, min_size=2, max_size=8, unique_by=str.casefold))
    dir_stem, file_stems = stems[0], stems[1:]
    use_dir = draw(st.booleans())
    dir_prefix = draw(st.sampled_from(list(_PREFIX_REASON)))
    dir_name = dir_prefix + dir_stem
    dir_reason = _PREFIX_REASON[dir_prefix]
    files: dict[str, bytes] = {}
    pinned: list[tuple[str, SourceKind]] = []
    skipped: list[tuple[str, str]] = []
    covered: list[str] = []
    for stem in file_stems:
        prefix = draw(st.sampled_from(list(_PREFIX_REASON)))
        accepted = draw(st.booleans())
        if accepted:
            suffix = draw(st.sampled_from(list(_ACCEPTED)))
            suffix = "".join(draw(st.sampled_from((c.lower(), c.upper()))) for c in suffix)
            kind, raw = _ACCEPTED[suffix.lower()]
        else:
            suffix, raw = draw(st.sampled_from((".png", ".zip", ""))), b"x"
        inside = use_dir and draw(st.booleans())
        name = (dir_name + "/" if inside else "") + prefix + stem + suffix
        files[name] = raw
        if inside and dir_reason is not None:
            if not covered:
                skipped.append((dir_name + "/", dir_reason))
            covered.append(name)
        elif (prefix_reason := _PREFIX_REASON[prefix]) is not None:
            skipped.append((name, prefix_reason))
        elif accepted:
            pinned.append((name, kind))
        else:
            skipped.append((name, "unsupported suffix"))
    return files, sorted(pinned), sorted(skipped), covered


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(_folders())
def test_every_file_is_accounted_for_once(drawn: _Drawn) -> None:
    files, expected_pins, expected_skipped, covered = drawn
    with tempfile.TemporaryDirectory() as root:
        result = pin_folder(_write(Path(root), files))
    assert [(p.name, p.kind) for p in result.pins] == expected_pins
    assert result.skipped == _skipped(*expected_skipped)
    pinned = {p.name for p in result.pins}
    rows = {s.name for s in result.skipped}
    for name in files:
        homes = [name in pinned, name in rows, name in covered]
        assert sum(homes) == 1
        if name in covered:
            assert any(name.startswith(row) for row in rows if row.endswith("/"))

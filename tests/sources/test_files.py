"""Capped, pinned reads of issuer source files."""

import errno
import os
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from credit_os.sources.errors import SourceChanged, SourceRefused, SourceTooLarge, SourceUnreadable
from credit_os.sources.files import MAX_BYTES, read_capped, read_pinned, source_path
from credit_os.sources.pins import SourceKind, SourcePin

FIXTURES: dict[str, tuple[bytes, str, SourceKind]] = {
    "annual-report.pdf": (
        b"%PDF-1.4\n%synthetic\n",
        "83decc79ecc2b3f1cd8e01f34991efb870e07e9ec43d48bf0df25e7dd488afd2",
        SourceKind.PDF,
    ),
    "readme.txt": (
        b"Synthetic note.\n",
        "4157540c50a21d8eccdd85cc071e37f2b23dd35525473b1b671044125dd44f42",
        SourceKind.TEXT,
    ),
    "notes/filing.html": (
        b"<html><body><p>Synthetic filing.</p></body></html>\n",
        "5a7098a94ea17556df46d90f5f335b6c303d318d24996c74ba6f1ee068cdfd4d",
        SourceKind.HTML,
    ),
}


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    for name, (raw, _, _) in FIXTURES.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return tmp_path


def _pin(name: str) -> SourcePin:
    raw, digest, kind = FIXTURES[name]
    return SourcePin(name=name, sha256=digest, size_bytes=len(raw), kind=kind)


def _symlink(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("this platform or account cannot create symbolic links")


def test_max_bytes_literal() -> None:
    assert MAX_BYTES == 52428800


@pytest.mark.parametrize("name", list(FIXTURES))
def test_read_capped_returns_bytes(folder: Path, name: str) -> None:
    assert read_capped(folder / name) == FIXTURES[name][0]


def test_read_capped_exactly_max(tmp_path: Path) -> None:
    path = tmp_path / "big.txt"
    with path.open("wb") as handle:
        handle.truncate(MAX_BYTES)
    assert len(read_capped(path)) == MAX_BYTES


def test_read_capped_over_max(tmp_path: Path) -> None:
    path = tmp_path / "big.txt"
    with path.open("wb") as handle:
        handle.truncate(MAX_BYTES + 1)
    with pytest.raises(SourceTooLarge) as caught:
        read_capped(path)
    assert str(caught.value) == f"{path}: larger than 52428800 bytes"


def test_read_capped_grew_after_stat(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "grows.txt"
    with path.open("wb") as handle:
        handle.truncate(MAX_BYTES + 1)
    real_fstat = os.fstat

    def small_fstat(fd: int) -> os.stat_result:
        real = real_fstat(fd)
        values = list(real)
        values[6] = 0  # st_size
        return os.stat_result(values)

    monkeypatch.setattr(os, "fstat", small_fstat)
    with pytest.raises(SourceTooLarge) as caught:
        read_capped(path)
    assert str(caught.value) == f"{path}: larger than 52428800 bytes"


def test_read_capped_missing(tmp_path: Path) -> None:
    path = tmp_path / "missing.txt"
    with pytest.raises(SourceUnreadable) as caught:
        read_capped(path)
    assert not isinstance(caught.value, SourceTooLarge)
    assert str(caught.value) == f"{path}: cannot open ({os.strerror(errno.ENOENT)})"


def test_read_capped_directory(tmp_path: Path) -> None:
    with pytest.raises(SourceUnreadable) as caught:
        read_capped(tmp_path)
    if sys.platform != "win32":
        assert str(caught.value) == f"{tmp_path}: not a regular file"


def test_read_capped_fifo(tmp_path: Path) -> None:
    if not hasattr(os, "mkfifo"):
        pytest.skip("os.mkfifo is not available on this platform")
    path = tmp_path / "pipe.txt"
    os.mkfifo(path)
    with pytest.raises(SourceUnreadable) as caught:
        read_capped(path)
    assert str(caught.value) == f"{path}: not a regular file"


def test_read_capped_symlink(folder: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
    if not hasattr(os, "O_NOFOLLOW"):
        pytest.skip("os.O_NOFOLLOW is not available on this platform")
    link = tmp_path_factory.mktemp("links") / "link.txt"
    _symlink(link, folder / "readme.txt")
    with pytest.raises(SourceUnreadable):
        read_capped(link)


def test_source_path_nested(folder: Path) -> None:
    assert source_path(folder, "notes/filing.html") == folder.resolve() / "notes" / "filing.html"


def test_source_path_bad_name(folder: Path) -> None:
    with pytest.raises(SourceRefused) as caught:
        source_path(folder, "../outside.txt")
    assert str(caught.value) == "'../outside.txt': empty or dot segment"


def test_source_path_missing_folder(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    with pytest.raises(SourceRefused) as caught:
        source_path(missing, "a.txt")
    assert str(caught.value) == f"{missing}: not a folder"


def test_source_path_folder_is_file(folder: Path) -> None:
    not_folder = folder / "readme.txt"
    with pytest.raises(SourceRefused) as caught:
        source_path(not_folder, "a.txt")
    assert str(caught.value) == f"{not_folder}: not a folder"


def test_source_path_symlink_escape(folder: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
    outside = tmp_path_factory.mktemp("outside") / "secret.txt"
    outside.write_bytes(b"secret\n")
    _symlink(folder / "inside.txt", outside)
    with pytest.raises(SourceRefused) as caught:
        source_path(folder, "inside.txt")
    assert str(caught.value) == "inside.txt: leaves the source folder"


@pytest.mark.parametrize("name", list(FIXTURES))
def test_read_pinned_returns_bytes(folder: Path, name: str) -> None:
    assert read_pinned(folder, _pin(name)) == FIXTURES[name][0]


def test_read_pinned_changed_content(folder: Path) -> None:
    (folder / "readme.txt").write_bytes(b"Synthetic NOTE.\n")
    with pytest.raises(SourceChanged) as caught:
        read_pinned(folder, _pin("readme.txt"))
    assert str(caught.value) == "readme.txt: content differs from the pin"


def test_read_pinned_wrong_size(folder: Path) -> None:
    pin = SourcePin(
        name="readme.txt", sha256=FIXTURES["readme.txt"][1], size_bytes=17, kind=SourceKind.TEXT
    )
    with pytest.raises(SourceChanged) as caught:
        read_pinned(folder, pin)
    assert str(caught.value) == "readme.txt: content differs from the pin"


def test_read_pinned_kind_mismatch(folder: Path) -> None:
    (folder / "fake.pdf").write_bytes(b"not a pdf\n")
    pin = SourcePin(
        name="fake.pdf",
        sha256="c52fa72b5f4be9a86cd7bf69559025bae760a974e1c9d998e33d6981993df412",
        size_bytes=10,
        kind=SourceKind.PDF,
    )
    with pytest.raises(SourceUnreadable) as caught:
        read_pinned(folder, pin)
    assert str(caught.value) == "fake.pdf: does not start with %PDF-"


def test_read_pinned_missing(folder: Path) -> None:
    pin = SourcePin(name="missing.txt", sha256="0" * 64, size_bytes=1, kind=SourceKind.TEXT)
    with pytest.raises(SourceUnreadable):
        read_pinned(folder, pin)


def test_read_capped_embedded_null(tmp_path: Path) -> None:
    path = tmp_path / "a\x00b"
    with pytest.raises(SourceUnreadable) as caught:
        read_capped(path)
    if sys.platform != "win32":
        assert str(caught.value) == f"{path}: cannot open (open: embedded null character in path)"


def _eio(*_args: object) -> object:
    raise OSError(errno.EIO, "synthetic")


def test_read_capped_fstat_error(folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "fstat", _eio)
    path = folder / "readme.txt"
    with pytest.raises(SourceUnreadable) as caught:
        read_capped(path)
    assert str(caught.value) == f"{path}: cannot read (synthetic)"


def test_read_capped_read_error(folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "read", _eio)
    path = folder / "readme.txt"
    with pytest.raises(SourceUnreadable) as caught:
        read_capped(path)
    assert str(caught.value) == f"{path}: cannot read (synthetic)"


def test_read_capped_size_check_before_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "big.txt"
    with path.open("wb") as handle:
        handle.truncate(MAX_BYTES + 1)

    def fail(*_args: object) -> bytes:
        pytest.fail("os.read was called before the size check")

    monkeypatch.setattr(os, "read", fail)
    with pytest.raises(SourceTooLarge):
        read_capped(path)


def test_read_capped_short_reads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw = b"0123456789abcdefghij"
    path = tmp_path / "twenty.txt"
    path.write_bytes(raw)
    real_read = os.read
    monkeypatch.setattr(os, "read", lambda fd, n: real_read(fd, min(n, 7)))
    assert read_capped(path) == raw


def _closes(monkeypatch: pytest.MonkeyPatch) -> tuple[list[int], list[int]]:
    opened: list[int] = []
    closed: list[int] = []
    real_open, real_close = os.open, os.close

    def record_open(path: Path, flags: int) -> int:
        fd = real_open(path, flags)
        opened.append(fd)
        return fd

    def record_close(fd: int) -> None:
        closed.append(fd)
        real_close(fd)

    monkeypatch.setattr(os, "open", record_open)
    monkeypatch.setattr(os, "close", record_close)
    return opened, closed


def _patch_fstat_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "fstat", _eio)


def _patch_read_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "read", _eio)


@pytest.mark.parametrize(
    "scenario",
    ["success", "directory", "too_large", "fstat_fails", "read_fails"],
)
def test_read_capped_closes_descriptor_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scenario: str
) -> None:
    if scenario == "directory" and sys.platform == "win32":
        pytest.skip("a directory cannot be opened as a file on Windows")
    path = tmp_path / "f.txt"
    path.write_bytes(b"Synthetic note.\n")
    if scenario == "directory":
        path = tmp_path
    if scenario == "too_large":
        with path.open("wb") as handle:
            handle.truncate(MAX_BYTES + 1)
    patches: dict[str, Callable[[pytest.MonkeyPatch], None]] = {
        "fstat_fails": _patch_fstat_fail,
        "read_fails": _patch_read_fail,
    }
    opened, closed = _closes(monkeypatch)
    if scenario in patches:
        patches[scenario](monkeypatch)
    try:
        read_capped(path)
    except SourceUnreadable:
        assert scenario != "success"
    else:
        assert scenario == "success"
    assert len(opened) == 1
    assert closed == opened


def test_source_path_self_loop(folder: Path) -> None:
    _symlink(folder / "loop.txt", folder / "loop.txt")
    with pytest.raises(SourceRefused) as caught:
        source_path(folder, "loop.txt")
    assert str(caught.value) == "loop.txt: cannot be resolved"


def test_source_path_two_link_loop(folder: Path) -> None:
    _symlink(folder / "a.txt", folder / "b.txt")
    _symlink(folder / "b.txt", folder / "a.txt")
    with pytest.raises(SourceRefused) as caught:
        source_path(folder, "a.txt")
    assert str(caught.value) == "a.txt: cannot be resolved"


def test_source_path_directory_loop(folder: Path) -> None:
    _symlink(folder / "loopdir", folder / "loopdir")
    with pytest.raises(SourceRefused) as caught:
        source_path(folder, "loopdir/x.txt")
    assert str(caught.value) == "loopdir/x.txt: cannot be resolved"


def test_source_path_folder_loop(tmp_path: Path) -> None:
    ring = tmp_path / "ring"
    _symlink(ring, ring)
    with pytest.raises(SourceRefused) as caught:
        source_path(ring, "a.txt")
    assert str(caught.value) == f"{ring}: not a folder"


def test_read_pinned_self_link(folder: Path) -> None:
    (folder / "readme.txt").unlink()
    _symlink(folder / "readme.txt", folder / "readme.txt")
    with pytest.raises(SourceRefused) as caught:
        read_pinned(folder, _pin("readme.txt"))
    assert str(caught.value) == "readme.txt: cannot be resolved"


def test_read_capped_bounds_each_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "endless.txt"
    path.write_bytes(b"x")
    returned = 0
    requests: list[tuple[int, int]] = []

    def endless_read(_fd: int, size: int) -> bytes:
        nonlocal returned
        requests.append((size, MAX_BYTES + 1 - returned))
        chunk = min(size, 1024 * 1024)
        returned += chunk
        return bytes(chunk)

    monkeypatch.setattr(os, "read", endless_read)
    with pytest.raises(SourceTooLarge) as caught:
        read_capped(path)
    assert str(caught.value) == f"{path}: larger than 52428800 bytes"
    assert returned == MAX_BYTES + 1
    assert all(size == allowed for size, allowed in requests)


def test_source_path_unsearchable_parent(tmp_path: Path) -> None:
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("root ignores directory permissions")
    locked = tmp_path / "locked"
    folder = locked / "issuer"
    folder.mkdir(parents=True)
    (folder / "readme.txt").write_bytes(FIXTURES["readme.txt"][0])
    locked.chmod(0o600)
    try:
        try:
            os.stat(folder)
        except PermissionError:
            pass
        else:
            pytest.skip("chmod does not deny search here")
        with pytest.raises(SourceRefused) as from_path:
            source_path(folder, "readme.txt")
        with pytest.raises(SourceRefused) as from_pin:
            read_pinned(folder, _pin("readme.txt"))
    finally:
        locked.chmod(0o700)
    assert str(from_path.value) == f"{folder}: not a folder"
    assert str(from_pin.value) == f"{folder}: not a folder"


def test_source_path_name_too_long(tmp_path: Path) -> None:
    folder = tmp_path / ("x" * 300)
    with pytest.raises(SourceRefused) as caught:
        source_path(folder, "readme.txt")
    assert str(caught.value) == f"{folder}: not a folder"


CUT = "a" * 120 + "\u2026"
LONG = "a" * 130 + ".txt"


def test_source_path_long_name_self_loop(folder: Path) -> None:
    _symlink(folder / LONG, folder / LONG)
    with pytest.raises(SourceRefused) as caught:
        source_path(folder, LONG)
    assert str(caught.value) == CUT + ": cannot be resolved"


def test_source_path_long_name_escape(
    folder: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    outside = tmp_path_factory.mktemp("outside") / "secret.txt"
    outside.write_bytes(b"secret\n")
    _symlink(folder / LONG, outside)
    with pytest.raises(SourceRefused) as caught:
        source_path(folder, LONG)
    assert str(caught.value) == CUT + ": leaves the source folder"


def test_read_pinned_long_name_changed_content(folder: Path) -> None:
    (folder / LONG).write_bytes(b"other bytes\n")
    pin = SourcePin(
        name=LONG, sha256=FIXTURES["readme.txt"][1], size_bytes=16, kind=SourceKind.TEXT
    )
    with pytest.raises(SourceChanged) as caught:
        read_pinned(folder, pin)
    assert str(caught.value) == CUT + ": content differs from the pin"

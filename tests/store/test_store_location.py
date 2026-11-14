import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import store_location_key as key

from credit_os.store import errors, location
from credit_os.store.errors import StoreCorrupt, StoreRefused, StoreUnusable

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="POSIX modes and links")
BOTH: list[Callable[[Path], Path]] = [location.prepare, location.locate]
HEADER = b"SQLite format 3\x00" + b"\x00" * 84  # exactly 100 bytes, format versions 0


def _header(version_18: int = 1, version_19: int = 1) -> bytes:
    data = bytearray(HEADER)
    data[18], data[19] = version_18, version_19
    return bytes(data)


def _state(folder: Path) -> Path:
    return folder / key.STATE_FILE_NAME


def _both_raise(error: type[Exception], folder: Any) -> None:
    for call in BOTH:
        with pytest.raises(error):
            call(folder)


def test_the_state_file_name_is_the_keys() -> None:
    assert location.STATE_FILE_NAME == key.STATE_FILE_NAME


@pytest.mark.parametrize("text", key.REFUSED_FOLDER_TEXTS, ids=repr)
def test_refused_folder_texts_create_nothing(
    text: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _both_raise(StoreRefused, Path(text))
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("name", key.REFUSED_FOLDER_NAMES, ids=["nul", "surrogate"])
def test_unholdable_folder_names_are_refused(name: str, tmp_path: Path) -> None:
    _both_raise(StoreRefused, tmp_path / name)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("value", key.REFUSED_FOLDER_VALUES, ids=repr)
def test_a_folder_that_is_not_a_path_is_refused(value: object, tmp_path: Path) -> None:
    _both_raise(StoreRefused, value)


def test_a_folder_that_resolves_to_a_network_path_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "resolve", lambda self, strict=False: Path("//server/share/x"))
    _both_raise(StoreRefused, tmp_path / "state")
    assert list(tmp_path.iterdir()) == []


def test_prepare_creates_folder_and_file_and_returns_the_resolved_path(tmp_path: Path) -> None:
    folder = tmp_path / "a" / "b" / "state"
    path = location.prepare(folder)
    assert path == _state(folder).resolve()
    assert path.is_file()
    assert path.stat().st_size == 0
    assert location.prepare(folder) == path


@posix_only
def test_every_created_folder_is_0700_and_the_file_0600_under_umask_zero(tmp_path: Path) -> None:
    old = os.umask(0)
    try:
        location.prepare(tmp_path / "a" / "b" / "state")
    finally:
        os.umask(old)
    for folder in (tmp_path / "a", tmp_path / "a" / "b", tmp_path / "a" / "b" / "state"):
        assert folder.stat().st_mode & 0o777 == key.FOLDER_MODE
    assert _state(tmp_path / "a" / "b" / "state").stat().st_mode & 0o777 == key.FILE_MODE


@posix_only
def test_existing_folder_and_file_modes_are_left_as_found(tmp_path: Path) -> None:
    location.prepare(tmp_path)
    tmp_path.chmod(0o755)
    _state(tmp_path).chmod(0o644)
    location.prepare(tmp_path)
    assert tmp_path.stat().st_mode & 0o777 == 0o755
    assert _state(tmp_path).stat().st_mode & 0o777 == 0o644


def test_a_folder_that_is_a_file_or_a_state_file_that_is_a_directory_is_refused(
    tmp_path: Path,
) -> None:
    (tmp_path / "a").write_bytes(b"x")
    _both_raise(StoreRefused, tmp_path / "a")
    _state(tmp_path).mkdir()
    _both_raise(StoreRefused, tmp_path)


@posix_only
def test_a_symbolic_link_as_folder_or_state_file_is_refused(tmp_path: Path) -> None:
    real = tmp_path / "real"
    location.prepare(real)
    os.symlink(real, tmp_path / "link", target_is_directory=True)
    _both_raise(StoreRefused, tmp_path / "link")
    (tmp_path / "state").mkdir()
    os.symlink(_state(real), _state(tmp_path / "state"))
    _both_raise(StoreRefused, tmp_path / "state")


def test_locate_creates_nothing_and_refuses_a_missing_folder_or_file(tmp_path: Path) -> None:
    for folder in (tmp_path / "missing", tmp_path):
        with pytest.raises(StoreUnusable):
            location.locate(folder)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("content", key.TOO_SHORT_FILES, ids=lambda c: f"{len(c)}-bytes")
def test_a_file_of_1_to_99_bytes_is_corrupt_and_unchanged(content: bytes, tmp_path: Path) -> None:
    _state(tmp_path).write_bytes(content)
    for call in BOTH:
        with pytest.raises(getattr(errors, key.TOO_SHORT_ERROR)):
            call(tmp_path)
    assert _state(tmp_path).read_bytes() == content
    assert issubclass(StoreCorrupt, getattr(errors, key.TOO_SHORT_ERROR))


def test_an_empty_file_is_new_for_the_writer_and_refused_by_the_reader(tmp_path: Path) -> None:
    _state(tmp_path).touch()
    location.prepare(tmp_path)
    with pytest.raises(getattr(errors, key.EMPTY_FILE_READER_ERROR)):
        location.locate(tmp_path)


@posix_only
@pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() == 0, reason="root can write")
@pytest.mark.parametrize(("target", "mode"), [("file", 0o400), ("folder", 0o500)])
def test_a_folder_or_file_this_process_cannot_write_is_unusable(
    target: str, mode: int, tmp_path: Path
) -> None:
    _state(tmp_path).write_bytes(HEADER)
    path = _state(tmp_path) if target == "file" else tmp_path
    path.chmod(mode)
    try:
        with pytest.raises(StoreUnusable):
            location.prepare(tmp_path)
    finally:
        path.chmod(0o700)


@pytest.mark.parametrize("offset", key.HEADER_VERSION_OFFSETS)
def test_a_write_ahead_header_is_refused_by_locate_without_touching_the_folder(
    offset: int, tmp_path: Path
) -> None:
    content = bytearray(HEADER)
    content[offset] = key.HEADER_WRITE_AHEAD
    _state(tmp_path).write_bytes(content)
    with pytest.raises(getattr(errors, key.WRITE_AHEAD_READER_ERROR)):
        location.locate(tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == [key.STATE_FILE_NAME]
    assert _state(tmp_path).read_bytes() == content


def test_a_rollback_journal_header_is_located(tmp_path: Path) -> None:
    _state(tmp_path).write_bytes(_header(key.HEADER_ROLLBACK, key.HEADER_ROLLBACK))
    assert location.locate(tmp_path) == _state(tmp_path).resolve()


def test_an_os_error_is_unusable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: Any, **kwargs: Any) -> int:
        raise PermissionError("denied")

    monkeypatch.setattr(os, "open", denied)
    with pytest.raises(StoreUnusable):
        location.prepare(tmp_path)


@posix_only
def test_a_symbolic_link_loop_as_folder_or_parent_is_refused_and_creates_nothing(
    tmp_path: Path,
) -> None:
    os.symlink(tmp_path / "loop", tmp_path / "loop")
    for folder in (tmp_path / "loop", tmp_path / "loop" / "state"):
        _both_raise(StoreRefused, folder)
    assert [p.name for p in tmp_path.iterdir()] == ["loop"]


@posix_only
@pytest.mark.parametrize("mask", [0o277, 0o777], ids=["277", "777"])
def test_the_modes_do_not_depend_on_the_umask(mask: int, tmp_path: Path) -> None:
    folder = tmp_path / "a" / "state"
    old = os.umask(mask)
    try:
        location.prepare(folder)
    finally:
        os.umask(old)
    for made in (tmp_path / "a", folder):
        assert made.stat().st_mode & 0o777 == key.FOLDER_MODE
    assert _state(folder).stat().st_mode & 0o777 == key.FILE_MODE
    assert location.prepare(folder) == _state(folder).resolve()


def test_a_directory_at_the_state_file_path_is_refused_without_opening_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _state(tmp_path).mkdir()

    def forbidden(*args: Any, **kwargs: Any) -> int:
        raise AssertionError("os.open must not be called")

    monkeypatch.setattr(os, "open", forbidden)
    with pytest.raises(StoreRefused):
        location.prepare(tmp_path)


def test_locate_refuses_a_file_with_a_wal_beside_it_and_touches_nothing(tmp_path: Path) -> None:
    _state(tmp_path).write_bytes(_header())
    wal = tmp_path / (key.STATE_FILE_NAME + "-wal")
    wal.write_bytes(b"frames")
    with pytest.raises(StoreUnusable):
        location.locate(tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == [key.STATE_FILE_NAME, wal.name]
    assert (_state(tmp_path).read_bytes(), wal.read_bytes()) == (_header(), b"frames")
    assert location.prepare(tmp_path) == _state(tmp_path).resolve()


def test_the_header_is_the_keys_100_bytes() -> None:
    assert len(HEADER) == key.SQLITE_HEADER_BYTES


@pytest.mark.skipif(sys.platform != "win32", reason="junctions exist only on Windows")
def test_a_junction_as_folder_is_refused(tmp_path: Path) -> None:
    if sys.platform == "win32":
        import _winapi

        (tmp_path / "real").mkdir()
        _winapi.CreateJunction(str(tmp_path / "real"), str(tmp_path / "joined"))
        assert (tmp_path / "joined").is_junction()
        _both_raise(StoreRefused, tmp_path / "joined")


@posix_only
def test_losing_the_creation_race_leaves_the_other_files_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _state(tmp_path).write_bytes(b"")
    _state(tmp_path).chmod(0o644)
    monkeypatch.setattr(location, "_exists", lambda path: False)  # the file appears after lstat
    location.prepare(tmp_path)
    assert _state(tmp_path).stat().st_mode & 0o777 == 0o644

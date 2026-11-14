"""Where the run-state file lives and what may be opened: path rules, creation and the checks on
an existing file that run before SQLite sees it. No SQLite here."""

import os
import stat
from pathlib import Path

from credit_os.store.errors import StoreCorrupt, StoreRefused, StoreUnusable, safe_text

STATE_FILE_NAME = "run-state.sqlite3"
_HEADER_BYTES = 100
_WRITE_AHEAD = 2  # file format version in header bytes 18 and 19
_CREATE_FLAGS = (
    os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
)


def _network_text(path: Path) -> bool:
    return str(path).startswith(("\\\\", "//"))


def _check_argument(folder: object) -> Path:
    if not isinstance(folder, Path) or not folder.is_absolute() or _network_text(folder):
        raise StoreRefused("the store folder must be an absolute local path")
    if "\x00" in str(folder):
        raise StoreRefused("the store folder name holds a NUL byte")
    try:
        os.fsencode(folder)
        str(folder).encode("utf-8")
        resolved = folder.resolve()
    except ValueError as error:  # includes UnicodeEncodeError
        raise StoreRefused("the store folder name cannot be held by the file system") from error
    except RuntimeError as error:  # a symbolic-link loop, on the Python versions that say so
        raise StoreRefused("the store folder is a symbolic-link loop") from error
    except OSError as error:
        raise StoreUnusable(
            f"the store folder cannot be resolved: {safe_text(str(error))}"
        ) from error
    if _network_text(resolved):
        raise StoreRefused("the store folder resolves to a network or device path")
    return folder


def _is_link(path: Path) -> bool:
    return path.is_symlink() or path.is_junction()


def _check_folder(folder: Path) -> bool:
    """True for a real directory, False when absent; a link or a non-directory is refused."""
    if _is_link(folder):
        raise StoreRefused("the store folder is a link")
    if folder.exists() and not folder.is_dir():
        raise StoreRefused("the store folder is not a directory")
    return folder.exists()


def _make_folder(folder: Path) -> None:
    missing = []
    for candidate in (folder, *folder.parents):
        if candidate.exists():
            break
        missing.append(candidate)
    for candidate in reversed(missing):  # one by one: parents get 0o700 too
        candidate.mkdir(mode=0o700, exist_ok=True)
        candidate.chmod(0o700)  # the umask may have narrowed the mode
    _check_folder(folder)


def _exists(path: Path) -> bool:
    """True when anything is at the path, a dangling link included; no link is followed."""
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    return True


def _check_file(path: Path) -> int:
    """The size of the state file; a link, a non-regular file or a 1 to 99 byte file is refused."""
    try:
        info = path.lstat()
    except FileNotFoundError as error:
        raise StoreUnusable("the state file is missing") from error
    if stat.S_ISLNK(info.st_mode) or _is_link(path) or not stat.S_ISREG(info.st_mode):
        raise StoreRefused("the state file is not a regular file")
    if 0 < info.st_size < _HEADER_BYTES:
        raise StoreCorrupt("the state file is too short to be a database")
    return info.st_size


def _create_file(path: Path) -> None:
    """Create the state file 0o600 whatever the umask; a file already there is left alone."""
    try:
        descriptor = os.open(path, _CREATE_FLAGS, 0o600)
    except FileExistsError:
        return  # made by another process first: checked by the caller
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(descriptor, 0o600)
        else:
            path.chmod(0o600)
    finally:
        os.close(descriptor)


def prepare(folder: Path) -> Path:
    """Check and create the folder and file for the writer; return the state file's path.

    "A refusal creates nothing" binds the argument rules only: folders this call made before a
    later rule refused are left in place."""
    _check_argument(folder)
    path = folder / STATE_FILE_NAME
    try:
        if not _check_folder(folder):
            _make_folder(folder)
        if not _exists(path):  # anything there, even a directory, goes to the file rule
            _create_file(path)
        _check_file(path)
        if not (os.access(folder, os.W_OK) and os.access(path, os.W_OK)):
            raise StoreUnusable("the store folder or file is not writable by this process")
        return path.resolve()
    except OSError as error:
        raise StoreUnusable(f"the store path cannot be used: {safe_text(str(error))}") from error


def locate(folder: Path) -> Path:
    """Check the folder and file for a reader, creating nothing; return the state file's path."""
    _check_argument(folder)
    path = folder / STATE_FILE_NAME
    try:
        if not _check_folder(folder):
            raise StoreUnusable("the store folder is missing")
        if _check_file(path) == 0:
            raise StoreUnusable("the state file is empty")
        if _exists(path.with_name(STATE_FILE_NAME + "-wal")):
            raise StoreUnusable("a write-ahead log sits beside the state file")
        with path.open("rb") as handle:
            header = handle.read(_HEADER_BYTES)
        if _WRITE_AHEAD in header[18:20]:
            raise StoreUnusable("the state file is in write-ahead mode")
        return path.resolve()
    except OSError as error:
        raise StoreUnusable(f"the store path cannot be used: {safe_text(str(error))}") from error

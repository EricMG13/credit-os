"""Capped reads of source files through one descriptor, and pinned reads."""

import hashlib
import os
import stat
from pathlib import Path

from credit_os.sources.errors import (
    SourceChanged,
    SourceRefused,
    SourceTooLarge,
    SourceUnreadable,
    reason_of,
    shown_name,
)
from credit_os.sources.pins import SourcePin, check_kind, validate_name

MAX_BYTES = 50 * 1024 * 1024

_HAS_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)

_OPEN_FLAGS = os.O_RDONLY
for _flag in ("O_BINARY", "O_NONBLOCK", "O_CLOEXEC", "O_NOFOLLOW"):
    _OPEN_FLAGS |= getattr(os, _flag, 0)


def read_capped(path: Path) -> bytes:
    """Read a regular file of at most MAX_BYTES bytes through a single descriptor."""
    try:
        # No O_NOFOLLOW here (Windows), so the open would follow a final link. This test
        # and the open are two steps, the same stated limit as the link walk in
        # source_path: a link swapped in between them is not closed here.
        if not _HAS_NOFOLLOW and (path.is_symlink() or path.is_junction()):
            raise SourceUnreadable(f"{path}: is a symbolic link")
        fd = os.open(path, _OPEN_FLAGS)
    except (OSError, ValueError) as error:
        raise SourceUnreadable(f"{path}: cannot open ({reason_of(error)})") from error
    try:
        raw = _read_descriptor(fd, path)
    except BaseException as first:
        # Whatever the read raised (any exception) propagates unchanged in type and message.
        # A failure of the close is not swallowed: it is recorded on that error as a note.
        try:
            os.close(fd)
        except OSError as closing:
            first.add_note(f"{path}: close also failed ({reason_of(closing)})")
        raise
    try:
        os.close(fd)
    except OSError as error:
        raise SourceUnreadable(f"{path}: cannot read ({reason_of(error)})") from error
    return raw


def _read_descriptor(fd: int, path: Path) -> bytes:
    """Check the open descriptor is a regular file within the cap, then read all of it."""
    try:
        info = os.fstat(fd)
    except OSError as error:
        raise SourceUnreadable(f"{path}: cannot read ({reason_of(error)})") from error
    if not stat.S_ISREG(info.st_mode):
        raise SourceUnreadable(f"{path}: not a regular file")
    if info.st_size > MAX_BYTES:
        raise SourceTooLarge(f"{path}: larger than {MAX_BYTES} bytes")
    raw = bytearray()
    while len(raw) <= MAX_BYTES:
        try:
            chunk = os.read(fd, MAX_BYTES + 1 - len(raw))
        except OSError as error:
            raise SourceUnreadable(f"{path}: cannot read ({reason_of(error)})") from error
        if not chunk:
            break
        raw += chunk
    if len(raw) > MAX_BYTES:
        raise SourceTooLarge(f"{path}: larger than {MAX_BYTES} bytes")
    return bytes(raw)


def source_path(folder: Path, name: str) -> Path:
    """Resolve a validated source name inside the folder, refusing any escape."""
    validate_name(name)
    try:
        root = folder.resolve(strict=True)
        is_folder = root.is_dir()
    except (OSError, RuntimeError, ValueError) as error:
        raise SourceRefused(f"{folder}: not a folder") from error
    if not is_folder:
        raise SourceRefused(f"{folder}: not a folder")
    # The check and the later open are two steps: a link swapped in between them is not
    # closed here. When an existing pin is read, its size and SHA-256 guard the content; when a
    # pin is created no digest exists yet, and that gap is an accepted limit (see pin_folder).
    # The resolve and containment check below the walk stay as the second guard for that case.
    walked = root
    for segment in name.split("/"):
        walked = walked / segment
        try:
            linked = walked.is_symlink() or walked.is_junction()
        except OSError as error:
            raise SourceRefused(f"{shown_name(name)}: cannot be resolved") from error
        if linked:
            raise SourceRefused(f"{shown_name(name)}: is or passes through a symbolic link")
    try:
        candidate = (root / name).resolve()
    except (OSError, RuntimeError) as error:
        raise SourceRefused(f"{shown_name(name)}: cannot be resolved") from error
    if not candidate.is_relative_to(root):
        raise SourceRefused(f"{shown_name(name)}: leaves the source folder")
    return candidate


def read_pinned(folder: Path, pin: SourcePin) -> bytes:
    """Read the pinned file, refusing bytes that differ from the pin or contradict its kind."""
    raw = read_capped(source_path(folder, pin.name))
    if len(raw) != pin.size_bytes or hashlib.sha256(raw).hexdigest() != pin.sha256:
        raise SourceChanged(f"{shown_name(pin.name)}: content differs from the pin")
    check_kind(pin.name, pin.kind, raw)
    return raw

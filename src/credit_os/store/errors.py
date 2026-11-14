"""Typed errors of the store layer and the mapping from a SQLite error to them."""

import sqlite3

_BUSY_CODES = frozenset({5, 6})  # SQLITE_BUSY, SQLITE_LOCKED
_CONFLICT_CODES = frozenset({19})  # SQLITE_CONSTRAINT
_CORRUPT_CODES = frozenset({11, 26})  # SQLITE_CORRUPT, SQLITE_NOTADB
_PRIMARY_CODE_MASK = 0xFF


class StoreError(Exception):
    """Base of every store error.

    A message may hold an absolute path taken from an operating-system error's text
    (`location.prepare` and `location.locate` put `safe_text(str(error))` of an `OSError` into a
    `StoreUnusable`), and so the user's home folder name. Text a caller hands the store to keep
    (C3: a source error's text, its absolute path and notes) is stored whole. A caller that shows,
    logs or stores a store error's message passes it through `credit_os.provider.redact.home_paths`
    first, or shows only the error's class name."""


class StoreRefused(StoreError, ValueError):
    """Bad input from the caller."""


class StoreBusy(StoreError):
    """The lock was not obtained."""


class StoreConflict(StoreError):
    """A constraint or state rule refused the write."""


class StoreCorrupt(StoreError):
    """What is stored cannot be trusted."""


class StoreUnusable(StoreError):
    """The file or library cannot be used."""


def safe_text(text: str) -> str:
    """Return the text with each lone surrogate as its backslash escape; nothing else changes."""
    if not isinstance(text, str):
        raise StoreRefused(f"text must be str, got {type(text).__name__}")
    return text.encode("utf-8", "backslashreplace").decode("utf-8")


def store_error(error: sqlite3.Error, doing: str) -> StoreError:
    """Return (not raise) the store error for the error's SQLite primary result code."""
    message = f"{doing}: {safe_text(str(error))}"
    code = getattr(error, "sqlite_errorcode", None)
    primary = code & _PRIMARY_CODE_MASK if isinstance(code, int) else None
    if primary in _BUSY_CODES:
        return StoreBusy(message)
    if primary in _CONFLICT_CODES:
        return StoreConflict(message)
    if primary in _CORRUPT_CODES:
        return StoreCorrupt(message)
    return StoreUnusable(message)

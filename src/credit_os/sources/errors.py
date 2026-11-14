"""Typed errors of the sources layer; each message names the file and the reason."""


class SourceError(Exception):
    """Base of every sources error."""


class SourceRefused(SourceError, ValueError):
    """A name, path or folder rule refused the source."""


class SourceUnreadable(SourceError):
    """The file cannot be opened or read, or its content does not match its kind."""


class SourceTooLarge(SourceUnreadable):
    """The file is larger than the byte cap."""


class SourceChanged(SourceError):
    """The file's bytes no longer match the pin."""

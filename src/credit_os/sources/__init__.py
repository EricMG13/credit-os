"""Pin and read issuer source files."""

from credit_os.sources.errors import (
    SourceChanged,
    SourceError,
    SourceRefused,
    SourceTooLarge,
    SourceUnreadable,
)
from credit_os.sources.files import MAX_BYTES, read_capped, read_pinned, source_path
from credit_os.sources.pages import Page, SourcePages, cut_pages
from credit_os.sources.pins import (
    SUFFIX_KINDS,
    SourceKind,
    SourcePin,
    check_kind,
    kind_of,
    validate_name,
)
from credit_os.sources.text import csv_pages, text_pages
from credit_os.sources.walk import PinnedFolder, Skipped, pin_folder, refuse_case_collisions

__all__ = [
    "MAX_BYTES",
    "SUFFIX_KINDS",
    "Page",
    "PinnedFolder",
    "Skipped",
    "SourceChanged",
    "SourceError",
    "SourceKind",
    "SourcePages",
    "SourcePin",
    "SourceRefused",
    "SourceTooLarge",
    "SourceUnreadable",
    "check_kind",
    "csv_pages",
    "cut_pages",
    "kind_of",
    "pin_folder",
    "read_capped",
    "read_pinned",
    "refuse_case_collisions",
    "source_path",
    "text_pages",
    "validate_name",
]

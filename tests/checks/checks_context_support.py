"""Shared loading for the checks tests: a CheckContext from a key's context fields.

A plain module, imported by its bare name as `tests/provider` does; a conftest cannot be imported.
"""

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from credit_os.checks.findings import CheckContext
from credit_os.sources.pins import SourceKind, SourcePin, kind_of

HANDOFFS = Path(__file__).resolve().parents[1] / "fixtures" / "handoffs"
_DIGEST = re.compile(r"\{d:(.)(!?)\}")
_FIELDS = ("kind", "pins", "other_sources", "required_registers")


def expand_digests(text: str) -> str:
    def one(found: re.Match[str]) -> str:
        return found.group(1) * 63 + "0" if found.group(2) else found.group(1) * 64

    return _DIGEST.sub(one, text)


def _kind(name: str) -> SourceKind:
    kind = kind_of(name)
    if kind is None:
        raise ValueError(f"a pin in a key names no accepted kind of file: {name!r}")
    return kind


def build_context(base: Mapping[str, Any], case: Mapping[str, Any]) -> CheckContext:
    """A context from `base`, overridden field by field by `case`."""
    fields = {**base, **{name: case[name] for name in _FIELDS if name in case}}
    if "pins" in fields:
        fields["pins"] = tuple(
            SourcePin(name=name, sha256=expand_digests(digest), size_bytes=1, kind=_kind(name))
            for name, digest in fields["pins"]
        )
    return CheckContext(**fields)

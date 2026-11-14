"""Shared loading for the checks tests: a CheckContext from a key's context fields.

A plain module, imported by its bare name as `tests/provider` does; a conftest cannot be imported.
"""

import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from credit_os.checks.findings import CheckContext
from credit_os.handoff.document import HandoffDocument, parse
from credit_os.sources.pins import SourceKind, SourcePin, kind_of

HANDOFFS = Path(__file__).resolve().parents[1] / "fixtures" / "handoffs"
_DIGEST = re.compile(r"\{d:(.)(!?)\}")
_FIELDS = tuple(CheckContext.model_fields)
# What a key's case holds besides context fields: the text it builds and what it expects.
_KEY_ONLY = (
    "name",
    "findings",
    "front",
    "tail",
    "sources",
    "expect",
    "reason",
    "reason_has",
    "columns",
    "reason_lacks",
)


def expand_digests(text: str) -> str:
    def one(found: re.Match[str]) -> str:
        return found.group(1) * 63 + "0" if found.group(2) else found.group(1) * 64

    return _DIGEST.sub(one, text)


def _documents(
    fields: Mapping[str, str], read: Callable[[str], bytes]
) -> dict[str, HandoffDocument]:
    return {code: parse(read(value)) for code, value in fields.items()}


def _fixture_bytes(path: str) -> bytes:
    return (HANDOFFS / path).read_bytes()


def _text_bytes(text: str) -> bytes:
    return text.encode("utf-8")


def _kind(name: str) -> SourceKind:
    kind = kind_of(name)
    if kind is None:
        raise ValueError(f"a pin in a key names no accepted kind of file: {name!r}")
    return kind


def build_context(
    base: Mapping[str, Any], case: Mapping[str, Any], accepted_is_text: bool = False
) -> CheckContext:
    """A context from `base`, overridden field by field by `case`.

    A name in either that is neither a context field nor a key-only name is an error.
    """
    for name in (*base, *case):
        if name not in _FIELDS and name not in _KEY_ONLY:
            raise ValueError(f"a key's context names an unknown field: {name!r}")
    fields = {**base, **{name: case[name] for name in _FIELDS if name in case}}
    if "pins" in fields:
        fields["pins"] = tuple(
            SourcePin(name=name, sha256=expand_digests(digest), size_bytes=1, kind=_kind(name))
            for name, digest in fields["pins"]
        )
    if "upstream" in fields:
        fields["upstream"] = _documents(fields["upstream"], _fixture_bytes)
    if "accepted" in fields:
        fields["accepted"] = _documents(
            fields["accepted"], _text_bytes if accepted_is_text else _fixture_bytes
        )
    return CheckContext(**fields)

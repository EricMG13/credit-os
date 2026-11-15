"""Shared loading for the checks tests: a CheckContext from a key's context fields.

A plain module, imported by its bare name as `tests/provider` does; a conftest cannot be imported.
"""

import re
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

from credit_os.checks.findings import CheckContext, Finding
from credit_os.handoff.document import HandoffDocument, parse
from credit_os.sources.pins import SourceKind, SourcePin, kind_of

HANDOFFS = Path(__file__).resolve().parents[1] / "fixtures" / "handoffs"
_DIGEST = re.compile(r"\{d:(.)(!?)\}")
_FIELDS = tuple(CheckContext.model_fields)
_HELD_CHECKS = frozenset(("figure.not-held", "figure.mismatch"))


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


def _kind(name: str) -> SourceKind:
    kind = kind_of(name)
    if kind is None:
        raise ValueError(f"a pin in a key names no accepted kind of file: {name!r}")
    return kind


def build_context(
    base: Mapping[str, Any], case: Mapping[str, Any], key_only: tuple[str, ...] = ()
) -> CheckContext:
    """A context from `base`, overridden field by field by `case`.

    `key_only` is what the calling test module reads of its key besides context fields (the text
    it builds, what it expects). A name in either mapping that is neither is an error, so a key
    line the test never reads cannot sit unnoticed.
    """
    unknown = sorted({name for name in (*base, *case) if name not in _FIELDS + key_only})
    if unknown:
        raise ValueError(f"a key's context names unknown fields: {unknown!r}")
    fields = {**base, **{name: case[name] for name in _FIELDS if name in case}}
    if "pins" in fields:
        fields["pins"] = tuple(
            SourcePin(name=name, sha256=expand_digests(digest), size_bytes=1, kind=_kind(name))
            for name, digest in fields["pins"]
        )
    if "upstream" in fields:
        fields["upstream"] = _documents(fields["upstream"], _fixture_bytes)
    if "accepted" in fields:
        fields["accepted"] = _documents(fields["accepted"], _fixture_bytes)
    return CheckContext(**fields)


def without_held(findings: Iterable[Finding]) -> list[Finding]:
    """`findings` without `figure.not-held` and `figure.mismatch` (ruling R63).

    The old keys' cases hold no held text, so those two checks would report every passage figure; the
    held checks are keyed by `held.json` and by `fixtures.json` over whole documents. Every other
    check stays compared whole and in order.
    """
    return [finding for finding in findings if finding.check not in _HELD_CHECKS]

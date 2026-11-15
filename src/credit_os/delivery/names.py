"""Names and addresses for the issuer library, built from fixed words only.

Every `#/` address and download name delivery writes is built here, from fixed words, ids checked
against one grammar, a module slug from one fixed table and a hashed folder: never from handoff
text, a source name or a raw id used as a path segment. The download folder is per issuer, run and
delivery (ruling R20). Which delivery of a run the library shows is not decided here. Nothing here
touches the file system.
"""

import hashlib
import re
from typing import NamedTuple

from credit_os.delivery.errors import DeliveryRefused


class Module(NamedTuple):
    """One analytical module: its code, its frozen slug and its display name."""

    code: str
    slug: str
    name: str


# Display names are the predecessor's MODULE_NAMES at legacy 8e3954a, in its order. Slugs are
# frozen (ruling R22): a slug change breaks saved links.
MODULES: tuple[Module, ...] = (
    Module("CP-0", "source-readiness", "Source readiness"),
    Module("CP-1A", "business-and-governance", "Business & governance"),
    Module("CP-DR", "research-questions", "Research questions"),
    Module("CP-1", "financial-foundation", "Financial foundation"),
    Module("CP-1B", "earnings-changes", "Earnings changes"),
    Module("CP-L10", "short-credit-snapshot", "Short credit snapshot"),
    Module("CP-1D", "earnings-quality", "Earnings quality"),
    Module("CP-1C", "peer-benchmark", "Peer benchmark"),
    Module("CP-2D", "liquidity", "Liquidity"),
    Module("CP-3C", "refinancing-and-lme", "Refinancing & LME"),
    Module("CP-2", "fundamental-credit", "Fundamental credit"),
    Module("CP-2A", "downside", "Downside"),
    Module("CP-2G", "forward-credit-model", "Forward credit model"),
    Module("CP-2E", "rates-fx-and-hedging", "Rates, FX & hedging"),
    Module("CP-2H", "ratings-and-triggers", "Ratings & triggers"),
    Module("CP-4", "legal-and-covenants", "Legal & covenants"),
    Module("CP-4A", "covenant-capacity", "Covenant capacity"),
    Module("CP-4B", "structural-priority", "Structural priority"),
    Module("CP-4D", "intercreditor-control", "Intercreditor control"),
    Module("CP-4C", "recovery-and-fulcrum", "Recovery & fulcrum"),
    Module("CP-3", "security-selection", "Security selection"),
    Module("CP-3D", "market-implied-risk", "Market-implied risk"),
    Module("CP-6", "committee-decision", "Committee decision"),
    Module("CP-5", "evidence-validation", "Evidence validation"),
    Module("CP-8", "changes-since-the-last-run", "Changes since the last run"),
)

_BY_CODE = {m.code: m for m in MODULES}
_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")
_DELIVERY = re.compile(r"[0-9a-f]{64}")
_SEGMENT = re.compile(r"(?:[A-Za-z0-9._~@+=,-]|%[0-9A-Fa-f]{2})+")
_ESCAPES = re.compile(r"(?:%[0-9A-Fa-f]{2})+")


def _refuse(rule: str) -> DeliveryRefused:
    """A refusal naming only the rule: no part of the input is ever echoed."""
    return DeliveryRefused(rule)


def module(code: str) -> Module:
    """Return the module with exactly this code."""
    found = _BY_CODE.get(code)
    if found is None:
        raise _refuse("unknown module code")
    return found


def check_id(text: str) -> str:
    """Return an id unchanged when it fits the id grammar."""
    if not isinstance(text, str):
        raise TypeError("id must be a str")
    if _ID.fullmatch(text) is None or text in (".", ".."):
        raise _refuse("id outside [A-Za-z0-9._-]{1,128}, or . or ..")
    return text


def folder(issuer: str, run: str, delivery: str) -> str:
    """Return the 20 hex characters naming one delivery of one run of one issuer."""
    check_id(issuer)
    check_id(run)
    if not isinstance(delivery, str) or _DELIVERY.fullmatch(delivery) is None:
        raise _refuse("delivery is not 64 lower-case hex characters")
    return hashlib.sha256(f"{issuer}/{run}/{delivery}".encode()).hexdigest()[:20]


def hash_address(*segments: str) -> str:
    """Return `#/` and the segments joined by `/`; every segment is a checked id."""
    if not segments:
        raise DeliveryRefused("address needs at least one segment")
    return "#/" + "/".join(check_id(s) for s in segments)


def forecast_href(issuer: str, run: str) -> str:
    """Return the address of a run's forecast page."""
    return hash_address("model", issuer, run, "forecast")


def archive_name(issuer: str, run: str, delivery: str) -> str:
    """Return the relative name of a delivery's handoff archive."""
    return check_relative_path(f"downloads/{folder(issuer, run, delivery)}/handoffs.zip")


def module_download(issuer: str, run: str, delivery: str, code: str) -> str:
    """Return the relative name of one module's handoff download."""
    slug = module(code).slug
    return check_relative_path(f"downloads/{folder(issuer, run, delivery)}/{slug}.md")


def _decode_escapes(segment: str, number: int) -> str:
    def one(match: re.Match[str]) -> str:
        try:
            return bytes.fromhex(match.group().replace("%", "")).decode("utf-8")
        except UnicodeDecodeError:
            raise _refuse(f"path segment {number}: escape is not strict UTF-8") from None

    return _ESCAPES.sub(one, segment)


def check_relative_path(href: str) -> str:
    """Return a relative path unchanged when every segment is safe (C6, C12)."""
    if not isinstance(href, str):
        raise TypeError("path must be a str")
    if not href:
        raise _refuse("path is empty")
    for number, segment in enumerate(href.split("/"), start=1):
        if _SEGMENT.fullmatch(segment) is None:
            raise _refuse(f"path segment {number}: empty or outside the allowed characters")
        decoded = _decode_escapes(segment, number)
        if segment in (".", "..") or decoded in (".", ".."):
            raise _refuse(f"path segment {number}: dot segment")
        if "/" in decoded or "\\" in decoded or "\x00" in decoded:
            raise _refuse(f"path segment {number}: decodes to a separator or NUL")
    return href

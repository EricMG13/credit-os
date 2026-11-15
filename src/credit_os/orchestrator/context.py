"""The run context file: one loader, with the guards and the shape (decision D24).

`load_context` is the only way to get a `RunContext`. Numbers stay text in the models; `amount`
turns one into a `Decimal`, and the empty text is missing, never zero.

Over 1 MiB, over 5,000 JSON values or with a key over 64 characters, a file is refused cheaply;
a real form at the predecessor's row maxima holds about 1,400 values, a margin of over three.
"""

import json
import re
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

PathwayId = Literal[
    "credit_snapshot",
    "earnings_update",
    "relative_value",
    "covenant_refinancing",
    "distressed_restructuring",
    "portfolio_decision",
    "short_snapshot",
    "lite_credit_assessment",
]
RunType = Literal["primary", "secondary", "research", "earnings"]
CaseKind = Literal["public", "private", "synthetic"]
PeerSource = Literal["cp_dr_public", "user_list", "user_comps", "none"]
Basis = Literal["auto", "public_comps", "precedents", "blend", "issuer_trading", "user_multiple"]
EbitdaBasis = Literal["LTM", "NTM"]
LegalDocuments = Literal["executed", "draft", "none"]
IssueClassification = Literal["", "investment_grade", "high_yield"]
QuoteKind = Literal["observed", "indicative_talk"]
RatingScope = Literal["issuer", "facility"]
Cp3Mode = Literal[
    "", "clo_screening", "single_name_rv", "capital_structure_rv", "watchlist_monitoring"
]

SCHEMA = "context/1"
MAX_DEPTH = 32
MAX_BYTES = 1048576
MAX_VALUES = 5000
MAX_KEY = 64
_SEPARATORS = ("\u0085", " ", " ")
_AMOUNT = re.compile(r"-?[0-9]+(\.[0-9]+)?", re.ASCII)


class ContextRefused(ValueError):
    """The context file is refused; each problem reads `<json path>: <message>`."""

    def __init__(self, problems: tuple[str, ...]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True, allow_inf_nan=False)


class RunSettings(_Model):
    run_type: RunType
    pathway: PathwayId
    case_kind: CaseKind
    as_of: str
    current_period: str
    prior_period: str
    reporting_currency: str
    cutoff: str = ""


class Identity(_Model):
    issuer_name: str
    issuer_id: str
    issue_classification: IssueClassification = ""
    borrower_name: str
    parent_name: str
    guarantors: tuple[str, ...]
    aliases: tuple[str, ...]
    listed_equity: bool
    ticker: str
    sector: str
    country: str
    sponsor: str


class DealTerm(_Model):
    facility_id: str
    instrument: str
    currency: str
    size_m: str
    tenor_years: str
    talk_spread_bps_low: str
    talk_spread_bps_high: str
    talk_oid_low: str
    talk_oid_high: str
    floor_pct: str
    coupon_pct: str = ""
    margin_bps: str = ""
    maturity: str = ""
    call_protection: str
    use_of_proceeds: str
    as_of: str
    provider: str


class Quote(_Model):
    facility_id: str
    kind: QuoteKind
    bid: str
    ask: str
    price: str
    yield_pct: str
    spread_bps: str
    as_of: str
    provider: str


class Rating(_Model):
    agency: str
    scope: RatingScope
    rating: str
    outlook: str
    as_of: str


class IssuerMarket(_Model):
    market_cap_m: str
    net_debt_m: str
    ev_m: str
    ebitda_basis: EbitdaBasis
    as_of: str
    source: str


class PeerRow(_Model):
    name: str
    ticker: str
    ev_m: str
    ebitda_m: str
    as_of: str
    source: str


class Precedent(_Model):
    target: str
    acquirer: str
    date: str
    ev_m: str
    ebitda_m: str
    source: str


class UserMultiple(_Model):
    value: str
    basis: EbitdaBasis
    rationale: str


class Valuation(_Model):
    peer_source: PeerSource
    basis: Basis
    issuer_market: IssuerMarket
    peers: tuple[PeerRow, ...]
    precedents: tuple[Precedent, ...]
    user_multiple: UserMultiple


class Cp2aScenario(_Model):
    ebitda_decline_pct: str
    interest_increase_pct: str


class Cp2aPins(_Model):
    scenarios: tuple[Cp2aScenario, ...]
    rationale: str


class Cp2dPins(_Model):
    horizon_months: str
    minimum_cash_m: str
    rationale: str


class Cp2ePins(_Model):
    rate_shocks_bps: tuple[str, ...]
    fx_shocks_pct: tuple[str, ...]
    hedge_ratio_pct: str
    rationale: str


class Cp3cPins(_Model):
    repricing_bps: str
    rationale: str


class Cp3dPins(_Model):
    recovery_pct: str
    rationale: str


class Cp4cPins(_Model):
    ev_multiple: str
    rationale: str


class Assumptions(_Model):
    cp2a: Cp2aPins | None
    cp2d: Cp2dPins | None
    cp2e: Cp2ePins | None
    cp3c: Cp3cPins | None
    cp3d: Cp3dPins | None
    cp4c: Cp4cPins | None


class Attachments(_Model):
    portfolio_workbook: bool
    prior_case: bool
    management_bridge: bool
    legal_documents: LegalDocuments


class ResearchQuestion(_Model):
    text: str
    focus_module: str


class ModuleOptions(_Model):
    cp3_mode: Cp3Mode = ""
    cp6_deep_debate: bool = False


class RunContext(_Model):
    run: RunSettings
    identity: Identity
    deal_terms: tuple[DealTerm, ...]
    quotes: tuple[Quote, ...]
    ratings: tuple[Rating, ...]
    valuation: Valuation
    assumptions: Assumptions
    attachments: Attachments
    research_questions: tuple[ResearchQuestion, ...]
    module_options: ModuleOptions = ModuleOptions()


def amount(text: str) -> Decimal | None:
    """The number in `text`; the empty text is missing (`None`), never zero."""
    if text == "":
        return None
    if _AMOUNT.fullmatch(text) is None:
        raise ValueError(f"not a plain decimal number: {text!r}")
    return Decimal(text)


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for name, value in pairs:
        if name in seen:
            raise ContextRefused((f"$: duplicate key {name!r}",))
        seen[name] = value
    return seen


def _no_constant(name: str) -> Any:
    raise ContextRefused((f"$: {name} is not valid JSON",))


def _parse(raw: bytes) -> Any:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ContextRefused((f"$: not valid UTF-8 ({error.reason})",)) from None
    try:
        return json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_no_constant)
    except ContextRefused:
        raise
    except json.JSONDecodeError as error:
        raise ContextRefused((f"$: not valid JSON ({error.msg} at line {error.lineno})",)) from None
    except (ValueError, RecursionError) as error:
        raise ContextRefused((f"$: not valid JSON ({type(error).__name__})",)) from None


def _too_deep(root: Any) -> bool:
    stack: list[tuple[Any, int]] = [(root, 1)]
    while stack:
        node, level = stack.pop()
        if isinstance(node, (dict, list)):
            if level > MAX_DEPTH:
                return True
            children = node.values() if isinstance(node, dict) else node
            stack.extend((child, level + 1) for child in children)
    return False


def _value_count(root: Any) -> tuple[int, int]:
    """The JSON values `root` holds (objects, arrays, scalars; keys excluded), the longest key."""
    stack = [root]
    count = longest = 0
    while stack:
        node = stack.pop()
        count += 1
        if isinstance(node, dict):
            longest = max([longest, *map(len, node)])
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return count, longest


def _join(path: tuple[str | int, ...]) -> str:
    text = ""
    for step in path:
        text += f"[{step}]" if isinstance(step, int) else (f".{step}" if text else step)
    return text or "$"


def _children(node: Any, path: tuple[str | int, ...]) -> list[tuple[Any, tuple[str | int, ...]]]:
    """The children of an object (key order) or array (index order), last first for a stack."""
    if isinstance(node, dict):
        return [(v, (*path, k)) for k, v in reversed(node.items())]
    if isinstance(node, list):
        return [(v, (*path, i)) for i, v in reversed(list(enumerate(node)))]
    return []


def _separator_problems(root: Any) -> list[str]:
    found: list[str] = []
    stack: list[tuple[Any, tuple[str | int, ...]]] = [(root, ())]
    while stack:
        node, path = stack.pop()
        if isinstance(node, str) and any(mark in node for mark in _SEPARATORS):
            found.append(f"{_join(path)}: contains a line separator (U+0085, U+2028 or U+2029).")
        stack.extend(_children(node, path))
    return found


def load_context(raw: bytes) -> RunContext:
    """Parse and check a context file; raise `ContextRefused` with every problem found."""
    if len(raw) > MAX_BYTES:
        raise ContextRefused((f"$: larger than {MAX_BYTES} bytes.",))
    obj = _parse(raw)
    if not isinstance(obj, dict):
        raise ContextRefused(("$: the top level must be an object.",))
    if _too_deep(obj):
        raise ContextRefused((f"$: nested too deeply (more than {MAX_DEPTH} levels).",))
    values, longest = _value_count(obj)
    if values > MAX_VALUES:
        raise ContextRefused((f"$: too many values (more than {MAX_VALUES}).",))
    if longest > MAX_KEY:
        raise ContextRefused((f"$: a key is longer than {MAX_KEY} characters.",))
    problems: list[str] = []
    if obj.pop("schema", None) != SCHEMA:
        problems.append(f"schema: must be '{SCHEMA}'.")
    problems.extend(_separator_problems(obj))
    context: RunContext | None = None
    try:
        context = RunContext.model_validate_json(json.dumps(obj, ensure_ascii=False))
    except ValidationError as error:
        problems.extend(f"{_join(tuple(e['loc']))}: {e['msg']}" for e in error.errors())
    if problems or context is None:
        raise ContextRefused(tuple(problems))
    return context

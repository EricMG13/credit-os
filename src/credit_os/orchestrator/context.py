"""The run context file: one loader, with the guards and the shape (decision D24).

`load_context` is the only way to get a `RunContext`. Numbers stay text in the models; `amount`
turns one into a `Decimal`, and the empty text is missing, never zero.

Over 1 MiB, over 5,000 JSON values or with a key over 64 characters, a file is refused cheaply;
a real form at the predecessor's row maxima holds about 1,400 values, a margin of over three.
"""

import dataclasses
import datetime as dt
import json
import re
from collections.abc import Callable
from decimal import Decimal
from itertools import pairwise
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
_NUM = r"\d+(\.\d+)?"
_SNUM = r"-?\d+(\.\d+)?"
_INT = r"-?\d+"
_PERIOD = r"(q[1-4]|h[12]|fy)-(\d{4})"
_SLUG = r"[a-z0-9][a-z0-9-]*"
_DATE = r"\d{4}-\d{2}-\d{2}"
_CURRENCY = r"[A-Z]{3}"
_MAX_SCEN, _MAX_Q = 4, 10


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


@dataclasses.dataclass(frozen=True)
class Limit:
    """One pinned assumption's value limits: the single copy the reader uses."""

    req: bool = False
    whole: bool = False
    places: int | None = None
    low: str | None = None
    low_excl: str | None = None
    high: str | None = None
    high_excl: str | None = None


# Keyed "<module>.<field>"; a shock list's limit is the limit of each of its items.
ASSUMPTION_LIMITS: dict[str, Limit] = {
    "cp2a.ebitda_decline_pct": Limit(req=True, places=2, low="0", high="100"),
    "cp2a.interest_increase_pct": Limit(req=True, places=2, low="0", high="100"),
    "cp2d.horizon_months": Limit(req=True, whole=True, low="1", high="60"),
    "cp2d.minimum_cash_m": Limit(req=True, low="0"),
    "cp2e.rate_shocks_bps": Limit(req=True, whole=True, low="1", high="1000"),
    "cp2e.fx_shocks_pct": Limit(req=True, whole=True, low="1", high="50"),
    "cp2e.hedge_ratio_pct": Limit(places=2, low="0", high="100"),
    "cp3c.repricing_bps": Limit(req=True, whole=True, low="0", high="1000"),
    "cp3d.recovery_pct": Limit(req=True, places=2, low="0", high_excl="100"),
    "cp4c.ev_multiple": Limit(req=True, places=2, low_excl="0", high="99.99"),
}


def _match(pattern: str, value: str) -> bool:
    """ASCII-only, whole-string match (no widened `\\d`, no trailing-newline allowance)."""
    return re.fullmatch(pattern, value, re.ASCII) is not None


def _valid_date(value: str) -> bool:
    if not _match(_DATE, value):
        return False
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _period_key(value: str) -> tuple[str, int, int] | None:
    m = re.fullmatch(_PERIOD, value, re.ASCII)
    if m is None:
        return None
    return m[1][0], 0 if m[1] == "fy" else int(m[1][1]), int(m[2])


def _num_message(value: str, signed: bool, limit: Limit) -> str:
    """Why `value` is not an allowed number under `limit`, or the empty text; compares as Decimal."""
    if "," in value:
        return "no thousands separators; write 1250, not 1,250."
    if not _match(_SNUM if signed else _NUM, value):
        return "enter a plain number such as 1250 or 99.5."
    if limit.whole and not _match(_INT, value):
        return "enter a whole number."
    if limit.places is not None and len(value.partition(".")[2]) > limit.places:
        return f"use at most {limit.places} decimal places."
    x = Decimal(value)
    checks: tuple[tuple[str | None, Callable[[Decimal, Decimal], bool], str], ...] = (
        (limit.low, lambda a, b: a < b, "must be {} or more."),
        (limit.low_excl, lambda a, b: a <= b, "must be above {}."),
        (limit.high, lambda a, b: a > b, "must be {} or less."),
        (limit.high_excl, lambda a, b: a >= b, "must be below {}."),
    )
    for bound, failed, template in checks:
        if bound is not None and failed(x, Decimal(bound)):
            return template.format(bound)
    return ""


class _Rules:
    """The value rules over a well-shaped context; collects every problem."""

    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.problems: list[str] = []
        self.as_of = ctx.run.as_of

    def bad(self, path: str, message: str) -> None:
        self.problems.append(f"{path}: {message}")

    def text(self, path: str, value: str, req: bool = False, cell: bool = False) -> None:
        """`cell`: shown in a dossier table cell (a research question), so refused if it breaks one."""
        if req and not value.strip():
            self.bad(path, "required.")
        if cell and ("|" in value or "\n" in value or "\r" in value):
            self.bad(
                path,
                "contains a pipe character, a line feed or a carriage return, "
                "which a dossier table cell cannot hold.",
            )
        elif cell and "<<<" in value:
            self.bad(path, "contains <<<, which a dossier block cannot show.")

    def number(self, path: str, value: str, limit: Limit) -> None:
        if value == "":
            if limit.req:
                self.bad(path, "required.")
            return
        message = _num_message(value, False, limit)
        if message:
            self.bad(path, message)

    def limited(self, path: str, value: str, key: str) -> None:
        self.number(path, value, ASSUMPTION_LIMITS[key])

    def date(self, path: str, value: str, req: bool = False, after: bool = False) -> None:
        if value == "":
            if req:
                self.bad(path, "required.")
            return
        if not _valid_date(value):
            self.bad(path, "enter a date as YYYY-MM-DD.")
        elif after and _valid_date(self.as_of) and value > self.as_of:
            self.bad(
                path,
                f"is after the run as-of date ({self.as_of}); sources dated after it are refused.",
            )

    def currency(self, path: str, value: str, req: bool = False) -> None:
        if value == "":
            if req:
                self.bad(path, "required.")
        elif not _match(_CURRENCY, value):
            self.bad(path, "use three uppercase letters, such as USD.")

    def shocks(self, path: str, items: tuple[str, ...], key: str) -> None:
        limit = ASSUMPTION_LIMITS[key]
        if not items and limit.req:
            self.bad(path, "required.")
        if len(items) > 3:
            self.bad(path, "give at most 3 values.")
        messages = [_num_message(item, False, limit) for item in items]
        for item, message in zip(items, messages, strict=True):
            if message:
                self.bad(path, f'"{item}": {message}')
        if not any(messages) and any(Decimal(a) >= Decimal(b) for a, b in pairwise(items)):
            self.bad(path, "values must increase.")

    def run_section(self) -> None:
        run = self.ctx.run
        self.date("run.as_of", run.as_of, req=True)
        self.date("run.cutoff", run.cutoff, after=True)
        earnings = run.run_type == "earnings"
        for name in ("current_period", "prior_period"):
            value = getattr(run, name)
            if value == "":
                if earnings:
                    self.bad(f"run.{name}", "required.")
            elif not _match(_PERIOD, value):
                self.bad(f"run.{name}", "use q1-2026, h2-2026 or fy-2025 (lowercase).")
        a, b = _period_key(run.current_period), _period_key(run.prior_period)
        if earnings:
            self.earnings_periods(a, b)
        if a and b and a[0] == b[0] and (b[2] > a[2] or (b[2] == a[2] and b[1] >= a[1])):
            self.bad("run.prior_period", "must be earlier than the current period.")
        self.currency("run.reporting_currency", run.reporting_currency, req=True)

    def earnings_periods(
        self, current: tuple[str, int, int] | None, prior: tuple[str, int, int] | None
    ) -> None:
        """Earnings runs compare quarters or fiscal years: no h period, and one kind for both."""
        halves = False
        for name, key in (("current_period", current), ("prior_period", prior)):
            if key is not None and key[0] == "h":
                halves = True
                self.bad(f"run.{name}", "earnings runs compare quarters or fiscal years only.")
        if current and prior and not halves and current[0] != prior[0]:
            self.bad("run.prior_period", "must be the same kind as the current period.")

    def identity_section(self) -> None:
        ident = self.ctx.identity
        self.text("identity.issuer_name", ident.issuer_name, req=True)
        if ident.issuer_id == "":
            self.bad("identity.issuer_id", "required.")
        elif not _match(_SLUG, ident.issuer_id):
            self.bad(
                "identity.issuer_id",
                "use lowercase letters, digits and hyphens only, not starting with a hyphen.",
            )
        for name in ("guarantors", "aliases"):
            for i, item in enumerate(getattr(ident, name)):
                if not item.strip():
                    self.bad(f"identity.{name}[{i}]", "list items must not be empty.")
        if ident.ticker and not ident.listed_equity:
            self.bad("identity.ticker", "must be empty for an unlisted issuer.")

    def assumptions_section(self) -> None:
        a = self.ctx.assumptions
        if a.cp2a is not None:
            n = len(a.cp2a.scenarios)
            if not 1 <= n <= _MAX_SCEN:
                self.bad("assumptions.cp2a.scenarios", "add 1 to 4 scenarios.")
            for i, s in enumerate(a.cp2a.scenarios):
                p = f"assumptions.cp2a.scenarios[{i}]"
                self.limited(
                    f"{p}.ebitda_decline_pct", s.ebitda_decline_pct, "cp2a.ebitda_decline_pct"
                )
                self.limited(
                    f"{p}.interest_increase_pct",
                    s.interest_increase_pct,
                    "cp2a.interest_increase_pct",
                )
            self.text("assumptions.cp2a.rationale", a.cp2a.rationale, req=True)
        if a.cp2d is not None:
            p = "assumptions.cp2d"
            self.limited(f"{p}.horizon_months", a.cp2d.horizon_months, "cp2d.horizon_months")
            self.limited(f"{p}.minimum_cash_m", a.cp2d.minimum_cash_m, "cp2d.minimum_cash_m")
            self.text(f"{p}.rationale", a.cp2d.rationale, req=True)
        if a.cp2e is not None:
            p = "assumptions.cp2e"
            self.shocks(f"{p}.rate_shocks_bps", a.cp2e.rate_shocks_bps, "cp2e.rate_shocks_bps")
            self.shocks(f"{p}.fx_shocks_pct", a.cp2e.fx_shocks_pct, "cp2e.fx_shocks_pct")
            self.limited(f"{p}.hedge_ratio_pct", a.cp2e.hedge_ratio_pct, "cp2e.hedge_ratio_pct")
            self.text(f"{p}.rationale", a.cp2e.rationale, req=True)
        if a.cp3c is not None:
            p = "assumptions.cp3c"
            self.limited(f"{p}.repricing_bps", a.cp3c.repricing_bps, "cp3c.repricing_bps")
            self.text(f"{p}.rationale", a.cp3c.rationale, req=True)
        if a.cp3d is not None:
            p = "assumptions.cp3d"
            self.limited(f"{p}.recovery_pct", a.cp3d.recovery_pct, "cp3d.recovery_pct")
            self.text(f"{p}.rationale", a.cp3d.rationale, req=True)
        if a.cp4c is not None:
            p = "assumptions.cp4c"
            self.limited(f"{p}.ev_multiple", a.cp4c.ev_multiple, "cp4c.ev_multiple")
            self.text(f"{p}.rationale", a.cp4c.rationale, req=True)

    def questions_section(self) -> None:
        questions = self.ctx.research_questions
        if len(questions) > _MAX_Q:
            self.bad("research_questions", f"give at most {_MAX_Q} rows.")
        for i, q in enumerate(questions):
            self.text(f"research_questions[{i}].text", q.text, req=True, cell=True)

    def run(self) -> list[str]:
        self.run_section()
        self.identity_section()
        self.assumptions_section()
        self.questions_section()
        return self.problems


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
    if context is not None:
        problems.extend(_Rules(context).run())
    if problems or context is None:
        raise ContextRefused(tuple(problems))
    return context

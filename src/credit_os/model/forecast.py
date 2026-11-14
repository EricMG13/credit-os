"""The forecast engine: one case of three forecast years from four base operands and seven drivers."""

from dataclasses import dataclass, fields
from decimal import Decimal

from credit_os.model.arithmetic import difference, product, ratio, total
from credit_os.model.value import Value

NC_EBITDA = "Not calculable: EBITDA is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
NC_INTEREST = "Not calculable: cash interest is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
NC_DEBT = "Not calculable: debt is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"

Triple = tuple[Decimal, Decimal, Decimal]
Scheduled = tuple[Decimal, Decimal]

_ONE = Value(amount=Decimal(1))
_MINUS_ONE = Value(amount=Decimal(-1))


def _decimal(item: object, name: str) -> None:
    if type(item) is not Decimal:
        raise TypeError(f"{name} must be a Decimal")
    if not item.is_finite():
        raise ValueError(f"{name} must be finite")


def _decimals(items: object, count: int, name: str) -> None:
    if type(items) is not tuple:
        raise TypeError(f"{name} must be a tuple")
    if len(items) != count:
        raise ValueError(f"{name} must hold exactly {count} values")
    for item in items:
        _decimal(item, name)


@dataclass(frozen=True, slots=True)
class Operands:
    revenue: Value
    debt: Value
    cash: Value
    undrawn: Value

    def __post_init__(self) -> None:
        for field in fields(self):
            if type(getattr(self, field.name)) is not Value:
                raise TypeError(f"Operands.{field.name} must be a Value")


@dataclass(frozen=True, slots=True)
class Drivers:
    revenue_growth: Triple
    ebitda_margin: Triple
    capex_pct_revenue: Triple
    tax_wc_pct_revenue: Triple
    interest_rate: Triple
    dividends: Triple
    debt_repayment: Triple

    def __post_init__(self) -> None:
        for field in fields(self):
            _decimals(getattr(self, field.name), 3, f"Drivers.{field.name}")


@dataclass(frozen=True, slots=True)
class Shock:
    ebitda_decline: Decimal
    rate_increase: Decimal

    def __post_init__(self) -> None:
        _decimal(self.ebitda_decline, "Shock.ebitda_decline")
        _decimal(self.rate_increase, "Shock.rate_increase")


@dataclass(frozen=True, slots=True)
class Year:
    revenue: Value
    ebitda: Value
    interest: Value
    tax_wc: Value
    capex: Value
    cfo: Value
    fcf: Value
    opening_debt: Value
    repayment: Value
    closing_debt: Value
    opening_cash: Value
    dividends: Value
    closing_cash: Value
    undrawn: Value
    liquidity: Value
    total_leverage: Value
    net_debt: Value
    net_leverage: Value
    coverage: Value
    fcf_to_debt: Value


def _check_schedule(schedule: object) -> None:
    if schedule is None:
        return
    if type(schedule) is not tuple:
        raise TypeError("schedule must be a tuple")
    if len(schedule) != 3:
        raise ValueError("schedule must hold exactly 3 years")
    for pair in schedule:
        _decimals(pair, 2, "schedule pair")


def _flow(year: int, drivers: Drivers, shock: Shock, opening: Operands) -> tuple[Value, ...]:
    """Revenue, EBITDA, tax and working capital, then capex."""
    revenue = product([opening.revenue, total([_ONE, Value(amount=drivers.revenue_growth[year])])])
    keep = difference(_ONE, Value(amount=shock.ebitda_decline))
    ebitda = product([revenue, Value(amount=drivers.ebitda_margin[year]), keep])
    tax_wc = product([revenue, Value(amount=drivers.tax_wc_pct_revenue[year])])
    capex = product([revenue, Value(amount=drivers.capex_pct_revenue[year])])
    return revenue, ebitda, tax_wc, capex


def _interest(
    year: int, opening_debt: Value, drivers: Drivers, shock: Shock, scheduled: Scheduled | None
) -> Value:
    """Debt x rate, or the scheduled amount (the driver is then not used); both x (1 + shock)."""
    rate_up = total([_ONE, Value(amount=shock.rate_increase)])
    if scheduled is None:
        return product([opening_debt, Value(amount=drivers.interest_rate[year]), rate_up])
    if opening_debt.missing is not None:
        return opening_debt
    return product([Value(amount=scheduled[0]), rate_up])


def _negated(value: Value) -> Value:
    return product([value, _MINUS_ONE])


def _year(
    index: int,
    opening: Operands,
    drivers: Drivers,
    shock: Shock,
    scheduled: Scheduled | None,
) -> Year:
    revenue, ebitda, tax_wc, capex = _flow(index, drivers, shock, opening)
    interest = _interest(index, opening.debt, drivers, shock, scheduled)
    repayment = Value(amount=drivers.debt_repayment[index])
    if scheduled is not None:
        repayment = Value(amount=scheduled[1])
    dividends = Value(amount=drivers.dividends[index])
    cfo = total([ebitda, _negated(interest), _negated(tax_wc)])
    fcf = difference(cfo, capex)
    closing_debt = difference(opening.debt, repayment)
    closing_cash = total([opening.cash, fcf, _negated(dividends), _negated(repayment)])
    net_debt = difference(closing_debt, closing_cash)
    return Year(
        revenue=revenue,
        ebitda=ebitda,
        interest=interest,
        tax_wc=tax_wc,
        capex=capex,
        cfo=cfo,
        fcf=fcf,
        opening_debt=opening.debt,
        repayment=repayment,
        closing_debt=closing_debt,
        opening_cash=opening.cash,
        dividends=dividends,
        closing_cash=closing_cash,
        undrawn=opening.undrawn,
        liquidity=total([closing_cash, opening.undrawn]),
        total_leverage=ratio(closing_debt, ebitda, non_positive=NC_EBITDA),
        net_debt=net_debt,
        net_leverage=ratio(net_debt, ebitda, non_positive=NC_EBITDA),
        coverage=ratio(ebitda, interest, non_positive=NC_INTEREST),
        fcf_to_debt=ratio(fcf, closing_debt, non_positive=NC_DEBT),
    )


def forecast(
    operands: Operands,
    drivers: Drivers,
    *,
    shock: Shock | None = None,
    schedule: tuple[Scheduled, Scheduled, Scheduled] | None = None,
) -> tuple[Year, Year, Year]:
    """Three forecast years. A driver whose 1 + g, 1 - s or 1 + k needs more than 38 digits is refused."""
    if type(operands) is not Operands:
        raise TypeError("operands must be an Operands")
    if type(drivers) is not Drivers:
        raise TypeError("drivers must be a Drivers")
    if shock is not None and type(shock) is not Shock:
        raise TypeError("shock must be a Shock or None")
    _check_schedule(schedule)
    used = shock if shock is not None else Shock(Decimal(0), Decimal(0))
    years: list[Year] = []
    opening = operands
    for index in range(3):
        scheduled = None if schedule is None else schedule[index]
        year = _year(index, opening, drivers, used, scheduled)
        years.append(year)
        opening = Operands(year.revenue, year.closing_debt, year.closing_cash, year.undrawn)
    return years[0], years[1], years[2]

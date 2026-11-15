"""Answer key for step 3A, PR 9a-2b: the context's value rules for deal terms, quotes, ratings and
valuation. Written by the controller before the code existed, by hand from the predecessor's
`src/deploy_workflow/context.py` at `8e3954a` (its texts quoted as written); implementers do not
edit this file and do not weaken a comparison against it.

SYNTHETIC FIXTURE: every value below is invented. Rows change `FULL` (as amended in 9a-2a: peer
source `user_comps`, basis `blend`, blank market and multiple), which passes every rule; the
problems come in section order (deal terms, quotes, ratings, valuation) and, within one, in the
predecessor's order.
"""

from typing import Any

from orchestrator_context_key import FULL
from orchestrator_context_rules_key import DATE, PLAIN, REQUIRED, on

AFTER = "is after the run as-of date (2026-09-30); sources dated after it are refused."
_D, _QT, _R, _V = ("deal_terms", 0), ("quotes", 0), ("ratings", 0), ("valuation",)
_DEAL: dict[str, Any] = FULL["deal_terms"][0]
_QUOTE: dict[str, Any] = FULL["quotes"][0]
_RATING: dict[str, Any] = FULL["ratings"][0]
_PEER: dict[str, Any] = FULL["valuation"]["peers"][0]
_PREC: dict[str, Any] = FULL["valuation"]["precedents"][0]
MARKET = {
    "market_cap_m": "1200",
    "net_debt_m": "-50",
    "ev_m": "",
    "ebitda_basis": "LTM",
    "as_of": "2026-09-15",
    "source": "Synthetic terminal",
}


def d(field: str, value: Any) -> bytes:
    return on({(*_D, field): value})


def v(changes: dict[tuple[Any, ...], Any]) -> bytes:
    return on({(*_V, *path): value for path, value in changes.items()})


Row = tuple[bytes, tuple[str, ...]]
RULES_B: dict[str, Row] = {
    # ---------------------------------------------------------------- deal terms
    "primary_without_deal": (
        on({("deal_terms",): []}),
        ("deal_terms: add at least one facility row.",),
    ),
    "research_without_deal": (on({("deal_terms",): [], ("run", "run_type"): "research"}), ()),
    "deals_twenty": (on({("deal_terms",): [_DEAL] * 20}), ()),
    "deals_twenty_one": (
        on({("deal_terms",): [_DEAL] * 21}),
        ("deal_terms: give at most 20 rows.",),
    ),
    "deal_currency_lowercase": (
        d("currency", "eur"),
        ("deal_terms[0].currency: use three uppercase letters, such as USD.",),
    ),
    "deal_currency_empty": (d("currency", ""), ()),
    **{
        f"deal_{name}_negative": (d(name, "-1"), (f"deal_terms[0].{name}: {PLAIN}",))
        for name in (
            "size_m",
            "tenor_years",
            "talk_spread_bps_low",
            "talk_spread_bps_high",
            "talk_oid_low",
            "talk_oid_high",
            "floor_pct",
            "coupon_pct",
            "margin_bps",
        )
    },
    "deal_size_at_zero": (d("size_m", "0"), ()),
    "deal_size_thousands": (
        d("size_m", "1,450"),
        ("deal_terms[0].size_m: no thousands separators; write 1250, not 1,250.",),
    ),
    "deal_maturity_not_a_day": (d("maturity", "2031-02-30"), (f"deal_terms[0].maturity: {DATE}",)),
    "deal_maturity_after_run_is_fine": (d("maturity", "2032-01-31"), ()),
    "deal_as_of_after_run": (d("as_of", "2026-10-01"), (f"deal_terms[0].as_of: {AFTER}",)),
    "deal_spread_low_above_high": (
        d("talk_spread_bps_low", "401"),
        ("deal_terms[0].talk_spread_bps_low: low must not exceed high.",),
    ),
    "deal_spread_low_equal_high": (d("talk_spread_bps_low", "400"), ()),
    "deal_oid_low_above_high": (
        d("talk_oid_low", "99.5"),
        ("deal_terms[0].talk_oid_low: low must not exceed high.",),
    ),
    # A low that is not a number is judged as a number only, not against its high.
    "deal_spread_low_not_a_number": (
        d("talk_spread_bps_low", "x"),
        (f"deal_terms[0].talk_spread_bps_low: {PLAIN}",),
    ),
    "deal_in_order": (
        on(
            {
                (*_D, "as_of"): "2026-10-01",
                (*_D, "currency"): "eur",
                (*_D, "talk_oid_low"): "99.5",
                (*_D, "size_m"): "-1",
            }
        ),
        (
            "deal_terms[0].currency: use three uppercase letters, such as USD.",
            f"deal_terms[0].size_m: {PLAIN}",
            f"deal_terms[0].as_of: {AFTER}",
            "deal_terms[0].talk_oid_low: low must not exceed high.",
        ),
    ),
    # ---------------------------------------------------------------- quotes and ratings
    "quotes_forty": (on({("quotes",): [_QUOTE] * 40}), ()),
    "quotes_forty_one": (on({("quotes",): [_QUOTE] * 41}), ("quotes: give at most 40 rows.",)),
    "quote_bid_negative": (on({(*_QT, "bid"): "-1"}), (f"quotes[0].bid: {PLAIN}",)),
    "quote_as_of_empty": (on({(*_QT, "as_of"): ""}), (f"quotes[0].as_of: {REQUIRED}",)),
    "quote_as_of_after_run": (on({(*_QT, "as_of"): "2026-10-01"}), (f"quotes[0].as_of: {AFTER}",)),
    "quote_provider_blank": (on({(*_QT, "provider"): "  "}), (f"quotes[0].provider: {REQUIRED}",)),
    "quote_bid_above_ask": (
        on({(*_QT, "bid"): "99.5"}),
        ("quotes[0].bid: bid must not exceed ask.",),
    ),
    "quote_bid_equal_ask": (on({(*_QT, "bid"): "99.25"}), ()),
    "ratings_twenty": (on({("ratings",): [_RATING] * 20}), ()),
    "ratings_twenty_one": (on({("ratings",): [_RATING] * 21}), ("ratings: give at most 20 rows.",)),
    "rating_agency_empty": (on({(*_R, "agency"): ""}), (f"ratings[0].agency: {REQUIRED}",)),
    "rating_blank": (on({(*_R, "rating"): " "}), (f"ratings[0].rating: {REQUIRED}",)),
    "rating_as_of_after_run": (on({(*_R, "as_of"): "2026-10-01"}), (f"ratings[0].as_of: {AFTER}",)),
    "rating_as_of_empty": (on({(*_R, "as_of"): ""}), ()),
    # ---------------------------------------------------------------- peers
    "peers_thirty": (v({("peers",): [_PEER] * 30}), ()),
    "peers_thirty_one": (
        v({("peers",): [_PEER] * 31}),
        ("valuation.peers: give at most 30 rows.",),
    ),
    "peers_with_source_none": (
        v({("peer_source",): "none"}),
        ("valuation.peers: must be empty when peer_source is none.",),
    ),
    "peers_with_cp_dr_public": (
        v({("peer_source",): "cp_dr_public"}),
        ("valuation.peers: must be empty when peer_source is cp_dr_public.",),
    ),
    "peers_too_many_and_none": (
        v({("peer_source",): "none", ("peers",): [_PEER] * 31}),
        (
            "valuation.peers: give at most 30 rows.",
            "valuation.peers: must be empty when peer_source is none.",
        ),
    ),
    "user_list_with_figures": (
        v({("peer_source",): "user_list"}),
        tuple(
            f"valuation.peers[0].{name}: must be blank when peer_source is user_list."
            for name in ("ev_m", "ebitda_m", "as_of", "source")
        ),
    ),
    "user_list_names_only": (
        v(
            {
                ("peer_source",): "user_list",
                ("peers",): [{**_PEER, "ev_m": "", "ebitda_m": "", "as_of": "", "source": ""}],
            }
        ),
        (),
    ),
    "user_comps_peer_name_empty": (
        v({("peers", 0, "name"): ""}),
        (f"valuation.peers[0].name: {REQUIRED}",),
    ),
    "user_comps_peer_ev_empty": (
        v({("peers", 0, "ev_m"): ""}),
        (f"valuation.peers[0].ev_m: {REQUIRED}",),
    ),
    "user_comps_peer_ev_zero": (v({("peers", 0, "ev_m"): "0"}), ()),
    "user_comps_peer_ebitda_zero": (
        v({("peers", 0, "ebitda_m"): "0"}),
        ("valuation.peers[0].ebitda_m: must be above 0.",),
    ),
    "user_comps_peer_as_of_empty": (
        v({("peers", 0, "as_of"): ""}),
        (f"valuation.peers[0].as_of: {REQUIRED}",),
    ),
    "user_comps_peer_as_of_after": (
        v({("peers", 0, "as_of"): "2026-10-01"}),
        (f"valuation.peers[0].as_of: {AFTER}",),
    ),
    "user_comps_peer_source_empty": (
        v({("peers", 0, "source"): ""}),
        (f"valuation.peers[0].source: {REQUIRED}",),
    ),
    # ---------------------------------------------------------------- precedents
    "precedents_thirty": (v({("precedents",): [_PREC] * 30}), ()),
    "precedents_thirty_one": (
        v({("precedents",): [_PREC] * 31}),
        ("valuation.precedents: give at most 30 rows.",),
    ),
    "precedents_under_public_comps": (
        v({("basis",): "public_comps"}),
        ("valuation.precedents: must be empty when basis is public_comps.",),
    ),
    "precedents_under_auto": (
        v({("basis",): "auto"}),
        ("valuation.precedents: must be empty when basis is auto.",),
    ),
    "precedents_basis": (v({("basis",): "precedents"}), ()),
    "precedent_target_empty": (
        v({("precedents", 0, "target"): ""}),
        (f"valuation.precedents[0].target: {REQUIRED}",),
    ),
    "precedent_date_after": (
        v({("precedents", 0, "date"): "2026-10-01"}),
        (f"valuation.precedents[0].date: {AFTER}",),
    ),
    "precedent_ev_empty": (
        v({("precedents", 0, "ev_m"): ""}),
        (f"valuation.precedents[0].ev_m: {REQUIRED}",),
    ),
    "precedent_ebitda_zero": (
        v({("precedents", 0, "ebitda_m"): "0"}),
        ("valuation.precedents[0].ebitda_m: must be above 0.",),
    ),
    "precedent_source_empty": (
        v({("precedents", 0, "source"): ""}),
        (f"valuation.precedents[0].source: {REQUIRED}",),
    ),
    # Under a basis without precedents, the rows are not judged one by one.
    "bad_precedent_under_auto": (
        v({("basis",): "auto", ("precedents", 0, "target"): ""}),
        ("valuation.precedents: must be empty when basis is auto.",),
    ),
    # ---------------------------------------------------------------- issuer market
    "issuer_trading": (
        v({("basis",): "issuer_trading", ("precedents",): [], ("issuer_market",): MARKET}),
        (),
    ),
    "issuer_trading_blank_market": (
        v({("basis",): "issuer_trading", ("precedents",): []}),
        (
            f"valuation.issuer_market.as_of: {REQUIRED}",
            f"valuation.issuer_market.source: {REQUIRED}",
            "valuation.issuer_market.ev_m: give EV, or both market cap and net debt.",
        ),
    ),
    "issuer_trading_unlisted": (
        on(
            {
                ("identity", "listed_equity"): False,
                ("identity", "ticker"): "",
                (*_V, "basis"): "issuer_trading",
                (*_V, "precedents"): [],
                (*_V, "issuer_market"): MARKET,
            }
        ),
        ("valuation.basis: issuer_trading needs a listed issuer.",),
    ),
    "issuer_trading_ev_alone": (
        v(
            {
                ("basis",): "issuer_trading",
                ("precedents",): [],
                ("issuer_market",): {
                    **MARKET,
                    "market_cap_m": "",
                    "net_debt_m": "",
                    "ev_m": "2100",
                },
            }
        ),
        (),
    ),
    "issuer_trading_cap_alone": (
        v(
            {
                ("basis",): "issuer_trading",
                ("precedents",): [],
                ("issuer_market",): {**MARKET, "net_debt_m": ""},
            }
        ),
        ("valuation.issuer_market.ev_m: give EV, or both market cap and net debt.",),
    ),
    "issuer_trading_cap_negative": (
        v(
            {
                ("basis",): "issuer_trading",
                ("precedents",): [],
                ("issuer_market",): {**MARKET, "market_cap_m": "-1"},
            }
        ),
        (f"valuation.issuer_market.market_cap_m: {PLAIN}",),
    ),
    "issuer_trading_ev_zero": (
        v(
            {
                ("basis",): "issuer_trading",
                ("precedents",): [],
                ("issuer_market",): {**MARKET, "ev_m": "0"},
            }
        ),
        ("valuation.issuer_market.ev_m: must be above 0.",),
    ),
    "issuer_trading_as_of_after": (
        v(
            {
                ("basis",): "issuer_trading",
                ("precedents",): [],
                ("issuer_market",): {**MARKET, "as_of": "2026-10-01"},
            }
        ),
        (f"valuation.issuer_market.as_of: {AFTER}",),
    ),
    "market_filled_under_blend": (
        v({("issuer_market",): MARKET}),
        ("valuation.issuer_market: must be blank when basis is blend.",),
    ),
    "market_ntm_only_under_blend": (
        v({("issuer_market", "ebitda_basis"): "NTM"}),
        ("valuation.issuer_market: must be blank when basis is blend.",),
    ),
    # ---------------------------------------------------------------- user multiple
    "multiple_filled_under_blend": (
        v({("user_multiple",): {"value": "8.5", "basis": "NTM", "rationale": "Synthetic view"}}),
        ("valuation.user_multiple: must be blank when basis is blend.",),
    ),
    "user_multiple_blank": (
        v({("basis",): "user_multiple", ("precedents",): []}),
        (
            f"valuation.user_multiple.value: {REQUIRED}",
            f"valuation.user_multiple.rationale: {REQUIRED}",
        ),
    ),
    **{
        f"user_multiple_{name}": (
            v(
                {
                    ("basis",): "user_multiple",
                    ("precedents",): [],
                    ("user_multiple",): {
                        "value": value,
                        "basis": "LTM",
                        "rationale": "Synthetic view",
                    },
                }
            ),
            problems,
        )
        for name, value, problems in (
            ("at_excluded_low", "0", ("valuation.user_multiple.value: must be above 0.",)),
            ("inside_low", "0.01", ()),
            ("at_high", "99.99", ()),
            ("above", "100", ("valuation.user_multiple.value: must be 99.99 or less.",)),
        )
    },
    # Across both parts: run and issuer, then these four sections, then assumptions and questions.
    "all_sections_in_order": (
        on(
            {
                ("assumptions", "cp3d", "recovery_pct"): "100",
                (*_D, "currency"): "eur",
                ("identity", "issuer_id"): "",
            }
        ),
        (
            f"identity.issuer_id: {REQUIRED}",
            "deal_terms[0].currency: use three uppercase letters, such as USD.",
            "assumptions.cp3d.recovery_pct: must be below 100.",
        ),
    ),
    # Sections in order: deal terms, quotes, ratings, valuation.
    "sections_in_order": (
        on(
            {
                (*_V, "peers", 0, "name"): "",
                (*_R, "agency"): "",
                (*_QT, "provider"): "",
                (*_D, "currency"): "eur",
            }
        ),
        (
            "deal_terms[0].currency: use three uppercase letters, such as USD.",
            f"quotes[0].provider: {REQUIRED}",
            f"ratings[0].agency: {REQUIRED}",
            f"valuation.peers[0].name: {REQUIRED}",
        ),
    ),
}

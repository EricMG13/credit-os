# Forward credit model

## Request
Forward credit model for Harrow Vale Synthetic Industries, three fiscal years from FY2025. SYNTHETIC FIXTURE: every figure, name and text is invented.

## Sources

| Source file name / supplied module | Use |
| --- | --- |
| Financial foundation (CP-1) | Upstream handoff. |

## Findings

### Bottom line

The forward model states its base, three cases and the shock, with the two facilities that carry most of the debt.

### Forecast inputs (machine-readable)

```json
{
"schema_version": "cpos-forecast-inputs/1",
"base": {
  "revenue": {"amount": "1456000", "reason": null, "row": "Revenue", "period": "FY2024", "column": null},
  "ebitda": {"amount": "320000", "reason": null, "row": "EBITDA (Reported)", "period": "FY2024", "column": null},
  "interest": {"amount": "64000", "reason": null, "row": "Cash Interest Paid", "period": "FY2024", "column": null},
  "taxes": {"amount": "37000", "reason": null, "row": "Income taxes paid", "period": "FY2024", "column": null},
  "wc": {"amount": "19000", "reason": null, "row": "Change in working capital", "period": "FY2024", "column": null},
  "capex": {"amount": "72000", "reason": null, "row": "Capital expenditure", "period": "FY2024", "column": null},
  "fcf": {"amount": "128000", "reason": null, "row": "Free cash flow", "period": "FY2024", "column": null},
  "debt": {"amount": "1250000", "reason": null, "row": "Total Debt", "period": "FY2024", "column": null},
  "cash": {"amount": "283000", "reason": null, "row": "Cash & Equivalents", "period": "FY2024", "column": null},
  "undrawn": {"amount": "175000", "reason": null, "row": "Undrawn committed facilities", "period": "FY2024", "column": null}
},
"base_drivers": {
  "revenue_growth": {"values": ["0.045", "0.04", "0.035"], "category": "Management Language", "rationale": "Invented for the fixture.", "limitation": null},
  "ebitda_margin": {"values": ["0.225", "0.23", "0.23"], "category": "Analyst Interpretation", "rationale": "Invented for the fixture.", "limitation": null},
  "capex_pct_revenue": {"values": ["0.05", "0.05", "0.048"], "category": "Analyst Interpretation", "rationale": "Invented for the fixture.", "limitation": null},
  "tax_wc_pct_revenue": {"values": ["0.035", "0.035", "0.035"], "category": "Analyst Interpretation", "rationale": "Invented for the fixture.", "limitation": null},
  "interest_rate": {"values": ["0.0525", "0.055", "0.055"], "category": "Analyst Interpretation", "rationale": "Invented for the fixture.", "limitation": null},
  "dividends": {"values": ["12000", "15000", "15000"], "category": "Management Language", "rationale": "Invented for the fixture.", "limitation": null},
  "debt_repayment": {"values": ["32000", "32000", "40000"], "category": "Documentary Fact", "rationale": "Invented for the fixture.", "limitation": null}
},
"downside_shock": {"ebitda_decline": "0.15", "rate_increase": "0.2"},
"upside_drivers": {
  "revenue_growth": {"values": ["0.065", "0.06", "0.055"], "category": "Analyst Interpretation", "rationale": "Invented for the fixture.", "limitation": null}
},
"downside_drivers": {
  "revenue_growth": {"values": ["0.01", "0", "0.01"], "category": "Analyst Interpretation", "rationale": "Invented for the fixture.", "limitation": null},
  "ebitda_margin": {"values": ["0.2", "0.19", "0.19"], "category": "Analyst Interpretation", "rationale": "Invented for the fixture.", "limitation": null}
},
"years": [{"year": 2025, "start": "2024-07-01", "end": "2025-06-30"}, {"year": 2026, "start": "2025-07-01", "end": "2026-06-30"}, {"year": 2027, "start": "2026-07-01", "end": "2027-06-30"}],
"facilities": [
  {"name": "Term loan B", "balance": "640000", "fixed_rate_pct": null, "spread_pct": "3.25", "floor_pct": "0.75", "reference_rate": ["0.0415", "0.0385", "0.036"], "annual_amortisation": "32000", "maturity": "2026-09-30"},
  {"name": "Senior notes 2029", "balance": "450000", "fixed_rate_pct": "7.125", "spread_pct": null, "floor_pct": null, "reference_rate": null, "annual_amortisation": null, "maturity": "2029-03-15"}
],
"scale": 1000,
"currency": "USD",
"scope_limits": ["Invented fixture: no issuer is forecast."]
}
```

## Calculations
None.

## Gaps

None.

## Next module
None.

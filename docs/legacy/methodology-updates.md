# Predecessor methodology updates since the baseline

Read on 2026-11-14 from the predecessor's `main` at `0f16bad`, against the baseline pin
`8e3954a` (`METHODOLOGY-REVIEW.md`, `docs/rulings`, `docs/reuse/selected-methods`,
`owners/cpos_launch.py`, `model/handoff.py`). Each update is the owner's ruling there and binds
the rebuild. None is ported yet; the step that owns it adapts it and moves the port map's
`Adapted to`. Nothing after `cbf4400` changes a method (a synthetic market-data test pack only).

| Update (predecessor ruling) | What changed | Owning step here |
| :--- | :--- | :--- |
| CP-1 runs the Deploy V method (`2026-11-13-cp1-deploy-v-method-and-acceptance-check.md`) | CP-1's method block is now the `cp-1-canonical-data-foundation` skill, runbook and step file, then `prompts/CP-1.md`; the schema and system references are archived, not sent. CP-1 is a scored module. Debt, net debt and leverage use balance-sheet carrying value; reported EBITDA is the primary denominator; missing values read `Not supplied:` or `Not calculable:` | Phase 6 (CP-1 text); 2B (confidence inputs) |
| CP-1 acceptance check in code (same ruling) | `owners/cpos_cp1_check.py`: CP-1's statement tables and figures are checked at handoff; the launcher sends the check's block and the period table rule on every run | 3A (launcher), 2B (the check) |
| Register and routing scope reduction (`2026-11-13-appendix-and-routing-scope.md`) | `CPOS_REGISTER_SCOPE.md` is a new last section of the method block for CP-0, CP-1A, CP-DR, CP-2, CP-2A, CP-2E, CP-2G, CP-3, CP-5 and CP-6: the registers each no longer writes. `ROUTING_RULES`, sent to every module, drops the methods' routing text; the orchestrator owns inter-module communication. The method pin of those ten modules changes | 3A (shared text, presence rule), 1A (the parser must not require the dropped registers), phase 6 |
| CP-DR looks online (`2026-11-13-cpdr-web-lookup.md`) | Page fetch and SEC EDGAR tools, an allowlist of reputable domains, on by default for public cases; a page dated after the as-of date is refused as a source of figures and allowed as a labelled later event | Not carried: the owner ruled on 2026-11-14 that the rebuild leaves the web lookup out (decision 0008). CP-DR works from supplied files only |
| CP-DR source guidance (2026-11-12, in `METHODOLOGY-REVIEW.md`) | `WEB_SEARCH_RULES`: rely on filings, regulators, rating agencies, official statistics and established press; each web row of `## Sources` carries a `Source type` cell, and a web row without one is refused | 3A (shared text), 2B (the refusal) |
| Reader vocabulary and Python-computed confidence (`2026-11-12-module-output-review-changes.md`) | The launcher's shared text overrides helper-script steps and the module-stated score; adds the `### Confidence inputs` table (Python computes the score), Sources columns, bottom-line word limits, and Financial foundation's `### Post-balance-sheet adjustments` | 3A, 2B, 1A |
| Downside follows the forward model (`2026-11-13-downside-follows-forward-model.md`) | The Forecast Downside is the forward credit model's own drivers with the shock, not the shock on base drivers; `rate_increase` is proportional | 1B (forecast arithmetic); the page wording is already in `docs/design/predecessor-behaviour.md` |
| Negative cash is not calculable (`2026-11-13-negative-cash-not-calculable.md`) | Net debt, net leverage and liquidity are missing, with a reason, for a year whose cash is negative before funding | 1B; page wording already in `predecessor-behaviour.md` |
| Reader check amendment (`2026-11-11-reader-and-issuer-report.md`, amended 2026-11-13) | The reading of one real run against the September VMO2 reference is no longer required; the VMO2 outputs stay the voice reference | Phase 6 acceptance |
| Full and lite assessments (`2026-11-13-full-and-lite-credit-assessments.md`) | CP-L10 stays wired but is not offered; a new run of it is refused with a message naming the lite assessment | 3A, 5C (run start) |

## What this changes in the plans

- The roadmap's ported table named `prompts/CP-1.md` as CP-1's whole method; it now names the
  Deploy V skill as well.
- Steps 1A, 1B and 2B were planned from the baseline. Their coordinator checks each plan
  against the rows above before the next dispatch.
- CP-DR's web lookup is not carried (decision 0008).

## Not verified

- Read from diffs, rulings and `METHODOLOGY-REVIEW.md`; no predecessor code was run.
- The predecessor's own records say every update above is proven offline only, with no paid run.
- The launcher and handoff files grew by about 3,200 lines since the baseline; only their
  method lists and shared-text names were read, not every rule.

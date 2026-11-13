# Screen inventory

Every screen the predecessor draws, mapped on 2026-11-13 from its `main` at `8e3954a`. This is
the list the new front end must cover. Section and component names are the predecessor's; the
design track may rename, merge or replace them.

## Screens

| Group | Screen | Predecessor route | What the reader does there |
| :--- | :--- | :--- | :--- |
| Library | Library home | `#W-Library/cases` | Picks an issuer and a run |
| Library | Report history | `#W-Report/history` | Sees an issuer's runs over time |
| Library | Overview | per run | Reads the verdict, key findings, contrary evidence, limitations |
| Library | Changes | per run | Reads what changed against the earlier run (CP-8) |
| Library | Modules | `#<module>/<section>` | Reads one module's analysis in full |
| Library | Evidence | tabs: summary, trace, sources, calculations, gaps, registers, record | Audits a figure or a claim |
| Library | Trace drawer | opens from any paragraph, row or figure | Follows one item to its source |
| Model | Forecast | `#W-Forecast/<model id>` | Reads the forecast cases and their drivers |
| Model | Model shell | Front Page, Analysis, Model, Portfolio Fit, Evidence, Limitations | Reads statements, bridges and cases |
| Run | Run start | steps Documents, Purpose, Confirm, More context, Start | Uploads files, approves a summary, submits |
| Run | Run started panel and readiness side panel | within run start | Confirms what will run and its cap |
| Run | Run activity | `#CP-OS/activity` | Watches module progress |
| Signal | Signal | separate page in the predecessor | Not inventoried in detail; step D0b maps it |

Run states to draw: queued, running, finished, failed, capped, rejected, interrupted.

## Sections seen per page

- Overview: verdict panel, metric strip, for-and-against board, findings feed, callout, dated
  timeline, module tiles, limitations block.
- Changes: change cards (value, period, assumption, conclusion, source, limitation), module
  state tiles, "no earlier run" state.
- Modules: bottom line, key findings, contrary evidence, what would change the view,
  limitations, then typed records.
- Forecast and Model: trend line, cash flow section, statements, case comparison, bridges.
- Evidence: the only place for sources, file names, hashes, ids, registers, gap ledgers, run
  codes and calculations.

## Record shapes (17)

matrix, watch, dated, edges, ranked, case rows, module state, question and answer, sided,
change, facts, cases, status, metric, measure, statement, default records.

## Chart kinds

Grouped columns, waterfall or bridge, stack, bullet, limits, dumbbell, range strip, scatter,
recovery, pair tile, comparison, path or hedge, trend.

## States every screen must draw

- No runs yet.
- A gap: "Not established for this run".
- A withheld value.
- A failed or blocked module: "Not assessable".
- Missing versus zero: missing is "n.a.", never 0.
- No earlier run to compare.
- Long text, and many modules.

## Rules carried over (decision 0003 lists which may change)

- Audit material appears only on Evidence and in the trace drawer.
- One trace control per paragraph, row or figure.
- Text written for another module is drawn nowhere.
- Bottom line first. No module code on screen.
- The page recomputes nothing: every figure comes from `data.js`.
- Motion only for live state.
- Every chart has a table form. Every page works from `file://`.

## Known defects in the predecessor's screens

- Flat repeated tables; spreadsheet error values shown as content.
- Prose mixed with data; long paragraphs with no hierarchy.
- Red and green fills carrying meaning with no icon or label.

## Not verified

- Signal's screens were not read; the list above has one row for it.
- Section lists come from one mapping pass, not from every run in the predecessor.

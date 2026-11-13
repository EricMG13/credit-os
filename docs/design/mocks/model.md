# Mocks: Financial Model and Forecast

Step D1b of the [design track plan](../../superpowers/plans/2026-11-13-design-track.md),
drawn 2026-11-13 against [design system](../design-system.md) 0.6, the
[component map](../component-map.md) as merged at `9fef96e`, and
[decision 0003](../../decisions/0003-design-track.md) including "Source look", and revised to
its review 2 rulings (`origin/main` `e3897a1`). Nothing here is built in React.

**Mock project:** [Claude Design project](https://claude.ai/design/p/d971501e-80a2-4b17-ab8f-7011bb867f0e?file=Forecast.dc.html).
Standalone Claude Design has announced that its tools stop working by 2026-12-14.

Every figure is sample data: invented numbers, made internally consistent, set on the public
TransDigm case. They are not TransDigm's reported figures. The logo is a placeholder.

## Screens

| Screen | File in the project | What is on it |
| :--- | :--- | :--- |
| Forecast | `Forecast.dc.html` | Run tabs with Forecast selected; the two cases; drivers against their range; interest cover trend; EBITDA paths by case; FY26 cash flow walk; a gap panel; what would change the forecast |
| Model: Front page | `Model 1 Front page.dc.html` | Bottom line; eight headline figures (one n.a., one withheld); what the model covers; parts of the model, one "Not assessable" |
| Model: Analysis | `Model 2 Analysis.dc.html` | Section index; key findings; measures with their consequence; headroom; segment margins; contrary evidence; what would change the view; limitations |
| Model: Model | `Model 3 Model.dc.html` | The two cases; statements (income statement, cash flow, balance sheet, key measures; FY22 to FY24, LTM, FY25E to FY27E; base and downside); EBITDA bridge; net debt walk; case comparison; debt stack; maturities; recovery; a gap panel; link to the run's Evidence |
| Model: Portfolio fit | `Model 4 Portfolio fit.dc.html` | Exposure against limits; agency ratings; "Not assessable" relative value; scatter against holdings; issuer against the holdings' range |
| Model: Limitations | `Model 5 Limitations.dc.html` | Six limitations, open, each with a label; three gap panels; link to the gaps in Evidence |
| States | `States.dc.html` | Each state below in one place |

The Model shell's tabs are Front page, Analysis, Model, Portfolio fit, Limitations, and an
"Evidence" link that leaves the model for the run's Evidence (ruling 8). The pages share
`Shell.dc.html` (rail, page header, tabs, "Show sources" switch), `Tbl.dc.html` (the table
form), `mock.css`, `mock2.css`, `mock3.css` and `charts.js`. `zz-check.html` is a render
harness, not a screen.

What works in the mock: the case cards switch every case-dependent chart and the statements'
forecast columns; every Chart or Table toggle; the statement tabs; Bars or Figures; "Show
sources" (trace controls otherwise show on hover and focus). All of it is CSS; the page
script only places marks.

## Chart kinds

Each has a working Chart or Table toggle and a missing value drawn by the map's rule.

| Kind | Map | Where | Missing value shown |
| :--- | :--- | :--- | :--- |
| Grouped columns | C1 | Model: maturities by year | 2026 term loans: no bar, "n.a." at the baseline; zeros drawn and labelled 0 |
| Recovery | C1 | Model: recovery by class and case | Receivables facility, downside: no bar, "n.a." |
| Trend | C2 | Forecast: interest cover | FY23: the line breaks, "n.a." at the baseline |
| Path | C3 | Forecast: EBITDA by case, last actual marked | None in the sample |
| Stack | C4 | Model: debt by instrument, ranked legend | None in the sample |
| Comparison | C5 | Model: the two cases side by side, six panels | Lowest cash balance, downside: no bar, "n.a." |
| Bullet | C6 | Analysis: headroom to covenants and triggers | Secured net leverage: no bar, "n.a.", the target line stays |
| Scatter | C9 | Portfolio fit: leverage and margin against holdings | Two holdings listed under "Not plotted" with the missing measure |
| Waterfall or bridge | C10 | Forecast: cash flow walk; Model: EBITDA bridge, net debt walk | "Other" and "Shareholder returns": empty slot, "n.a."; a zero step is labelled 0 |
| Dumbbell | C11 | Analysis: EBITDA margin by segment | Acquired businesses: one mark, no line, "n.a." for the other |
| Range strip | C12 | Forecast: drivers; Portfolio fit: issuer against holdings | Marker missing: range with "n.a."; range missing: no strip |
| Limits | C13 | Portfolio fit: exposure against limits | No limit: bar with "limit n.a." and no tick; no exposure: no bar, "n.a.", the tick stays |
| Pair tile | C15 | Portfolio fit: agency ratings | None in the sample |

Also drawn: the statement table (R1). It has no Trend sparkline column (review 2, ruling 4);
its Bars view stays.

## States

| State | Where |
| :--- | :--- |
| Gap, "Not established for this run", as a block | Forecast, Model, Limitations, States |
| Gap as an inline badge in a table cell | Model: balance sheet, pension deficit; States |
| Withheld value | Front page: metric tile; Model: cash flow, acquisitions FY25E; States |
| Missing is "n.a.", never 0, with zero beside it | Statements; every chart above; States |
| Failed part, "Not assessable", with its sentence | Front page: parts list; Portfolio fit: relative value; States (both forms) |
| Loading | States: static skeleton, no animation |
| Table form of a chart | Every chart; States |

No looping animation is on any screen.

Inventory states that do not apply here, and are not drawn: "no runs yet" and "no earlier run
to compare" (the Model and Forecast exist only inside one run and compare nothing with an
earlier one; that belongs to the library home and Changes), and "many modules" (these screens
list no modules). Long text is not drawn as a state of its own: prose is capped at 72 to 90
characters a line and wraps, and table labels do not wrap.

## Type

- Page title: the design system's `h1`, 36 / 42, weight 700, inside the Untitled UI page
  header layout, as the run and library mocks use (review 2, ruling 2).
- Bottom line lead: the design system's `h3`, 22 / 30, weight 600, as the library mock does.
- Judgement prose (key findings, contrary evidence, what would change the view): the design
  system's `body`, 16 / 26. It was the source's 14px before this round.
- Every other source component keeps its source's size (ruling 2).

## Source look

Read live on 2026-11-13 and copied for layout, sizes, radius and density, in the design
system's colours and typefaces: Untitled UI metrics (simple), button groups, page headers,
tabs, line and bar charts; HyperUI vertical menu (icon, left border), toasts (standout),
tables (sticky first column), details list; shadcnblocks banner (inset), list panel
(numbered), alert (warning), collapsible (card), stat (delta), choicebox, item, chart (bar multiple, bar
stacked, bar horizontal, target line). Badge, tab, button and table sizes were taken from the design system project's own source samples.

## Departures

| From | What the mock does | Why |
| :--- | :--- | :--- |
| Map 3.2 | Bullet and dumbbell are on Analysis, scatter and a second range strip on Portfolio fit, recovery on Model | The brief asks for all thirteen kinds on these screens; the map places only nine here |
| Map 3.2 | A "States" board is added | One place to review the states; it is not a product screen |
| Design system, toggle row | Chart or Table is the Untitled UI joined button group, 40 high, the selected item filled `surface-subtle` | Source look, confirmed at review 2 (ruling 2: a source component keeps its source's size) |
| Design system, chart marks | Charts carry four faint horizontal gridlines, no axis line, 6px bar corners, legend beside or under the plot | Review 2, ruling 5 |
| Map F1 | Metric tiles are separate cards in a grid, not a joined strip | Review 2, ruling 5 |
| Map 2.5, frame | Charts, the statement table, the details list and stats sit in a design system card; components that bring their own container (metrics, banner, list rows, alert, toast, collapsible, choicebox, item) sit on the canvas | Review 2, ruling 1: a card may hold a chart or a group of source components, as page layout |
| Map P1 | The bottom line is a Navy band with white text | Review 2, ruling 6 |
| Map P4 | "What would change the view" uses the info status colours | Review 2, ruling 5 |
| Map F2 | The delta line is neutral text with an arrow, not green or red | Whether a rise is good depends on the measure; colour alone was a defect in the predecessor |
| Map C13 | Limits are vertical columns, each on its own scale, with a horizontal dashed tick | Keeps limits visibly different from the bullet's horizontal bars; limits differ by a factor of ten |
| Map C10 | Increases and decreases use the design system's above and below baseline colours, with signed labels | The series palette has no direction |
| Map N1 | The rail shows four placeholder icons with tooltips | Icons come from the npm package at build time |
| Design system, type | Table cells are 16px (HyperUI's size); header notes and chart ticks are 12px | Source sizes (review 2, ruling 2) |
| Map R1 | The statement table has no in-row sparkline | Review 2, ruling 4 |

## Questions for the owner

Settled at review 2 and removed from this list: the Trend column (ruling 4), a card around a
chart or statement (ruling 1), the Navy bottom line (ruling 6), and the 40-high button group
(ruling 2).

1. Bullet, dumbbell, scatter and recovery are not placed on the Model by the map. Keep them
   where the mock puts them, or leave them to the library's module pages only?
2. Limits on separate scales read cleanly but the bars cannot be compared with each other.
   Acceptable, or one shared scale?
3. Forecast repeats the case cards that the Model page has. Should Forecast link to the
   Model for the statements, as drawn, or carry a summary statement of its own?
4. Period set: the mock shows FY, LTM and forecast years. Your list also names quarters, YTD
   and prior-year YTD, prior LTM and pro forma. Which belong on the Model page by default?
   (Listed in decision 0003 as open, not ruled.)

## Trace controls

One per figure, row or passage: each metric tile, each measure, each statement row, each row
of a chart's table form, each chart, each finding, the bottom line, contrary evidence, what
would change the view, each limitation (Analysis and Limitations), each fact in "What the
model covers", each sentence in the parts list, and each case card (Forecast and Model). A
control shows when its own row, tile or passage is hovered or focused, and all show under
"Show sources". On a touch device (no hover) every control is always shown.

## Fixed after the first render

- EBITDA by case: the downside labels now sit clear below their markers.
- Maturities: three-series groups use narrower bars and wider gaps, with the middle label one
  line higher, so no label meets a neighbouring bar or label.
- Trace controls were one per card; they are now one per figure, row or passage, as above.
- The facts, the parts list, the case cards and the limitations on the Limitations page had
  no trace control; each now has one. In a case card it is a button inside the card's label,
  at the lower right.

## Not verified

- Rendered in headless Chrome at 1440px wide only; not in Edge, not at narrow widths, not in
  the Claude Design editor. Console messages were not captured.
- The three fixes were checked in one render each (Forecast, Analysis and Model with "Show
  sources" on); hover and focus of a single trace control were not exercised.
- The four added trace places were checked in one render each with "Show sources" on (the
  top of Forecast and Model, Front page, Limitations). Whether pressing the control inside a
  case card leaves the case unchanged was not exercised.
- Table, Bars, the cash flow and balance sheet tabs, the downside case and "Show sources"
  were rendered once each through the harness; the key measures tab and the Table side of
  the charts on Forecast, Analysis and Portfolio fit were not looked at.
- Source pages were read by screenshot and, for Untitled UI and HyperUI, by their class
  names; no pixel comparison was made. Shadcnblocks sizes are read by eye.
- Whether Recharts can draw these forms, dashes, markers and missing-value rules is untested.
- Contrast of the two baseline colours (`#6676FF`, `#E5704D`) as bar fills was not computed.
- Keyboard order and screen reader output were not tested.
- The review 2 round was checked in one render each of Model, Analysis and States. The
  always-shown trace controls on touch are a `hover: none` rule that was not rendered on a
  touch device. The sparkline's style rules remain in `mock.css`, unused.

# Mocks: Financial Model and Forecast

Step D1b of the [design track plan](../../superpowers/plans/2026-11-13-design-track.md),
drawn 2026-11-13 against [design system](../design-system.md) 0.6, the
[component map](../component-map.md) as merged at `9fef96e`, and
[decision 0003](../../decisions/0003-design-track.md) including "Source look". Nothing here
is built in React.

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

Also drawn: the statement table (R1) with its in-row sparkline (F5), which breaks at a
missing period.

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

## Source look

Read live on 2026-11-13 and copied for layout, sizes, radius and density, in the design
system's colours and typefaces: Untitled UI metrics (simple), button groups, page headers,
tabs, line and bar charts; HyperUI vertical menu (icon, left border), toasts (standout),
tables (sticky first column), details list; shadcnblocks banner (inset), list panel
(numbered), alert (warning), collapsible (card), stat (delta), choicebox, item, sparkline
(line), chart (bar multiple, bar stacked, bar horizontal, target line). Badge, tab, button
and table sizes were taken from the design system project's own source samples.

## Departures

| From | What the mock does | Why |
| :--- | :--- | :--- |
| Map 3.2 | Bullet and dumbbell are on Analysis, scatter and a second range strip on Portfolio fit, recovery on Model | The brief asks for all thirteen kinds on these screens; the map places only nine here |
| Map 3.2 | A "States" board is added | One place to review the states; it is not a product screen |
| Design system, toggle row | Chart or Table is the Untitled UI joined button group, 40 high, the selected item filled `surface-subtle` | Source look; the design system row describes a white pill on a subtle track |
| Design system, chart marks | Charts carry four faint horizontal gridlines, no axis line, 6px bar corners, legend beside or under the plot | Source look (Untitled UI and shadcnblocks charts); the design system says no gridlines beyond a zero line and 4px tops |
| Map F1 | Metric tiles are separate cards in a grid, not a joined strip | The source's simple metric is a separate card |
| Map 2.5, frame | Charts, the statement table, the details list and stats sit in a design system card; components that bring their own container (metrics, banner, list rows, alert, toast, collapsible, choicebox, item) sit on the canvas | The map forbids wrapping a source component in a card of ours; a chart has no container of its own |
| Map P1 | The bottom line is a Navy band with white text | The source's inset banner is a dark filled bar; `surface-inverse` is the system's only inverse colour |
| Map P4 | "What would change the view" uses the info status colours | The source toast is blue-tinted; info is the nearest status |
| Map F2 | The delta line is neutral text with an arrow, not green or red | Whether a rise is good depends on the measure; colour alone was a defect in the predecessor |
| Map C13 | Limits are vertical columns, each on its own scale, with a horizontal dashed tick | Keeps limits visibly different from the bullet's horizontal bars; limits differ by a factor of ten |
| Map C10 | Increases and decreases use the design system's above and below baseline colours, with signed labels | The series palette has no direction |
| Map N1 | The rail shows four placeholder icons with tooltips | Icons come from the npm package at build time |
| Design system, type | Table cells are 16px (HyperUI's size); header notes and chart ticks are 12px | Source sizes |

## Questions for the owner

1. The statement table keeps an in-row sparkline (map R1). Your rule "why charts in tables
   when they should be charts" may forbid it. Keep the Trend column, or drop it and rely on
   Bars?
2. Is a design system card around a chart or a statement acceptable under "source look", or
   should those sit bare on the canvas as well?
3. The bottom line as a Navy band: keep the source's dark banner, or a light one?
4. Bullet, dumbbell, scatter and recovery are not placed on the Model by the map. Keep them
   where the mock puts them, or leave them to the library's module pages only?
5. Limits on separate scales read cleanly but the bars cannot be compared with each other.
   Acceptable, or one shared scale?
6. Should the Chart or Table toggle be the source's 40-high button group on every chart, or
   a smaller size?
7. Forecast repeats the case cards that the Model page has. Should Forecast link to the
   Model for the statements, as drawn, or carry a summary statement of its own?
8. Period set: the mock shows FY, LTM and forecast years. Your list also names quarters, YTD
   and prior-year YTD, prior LTM and pro forma. Which belong on the Model page by default?

## Trace controls

One per figure, row or passage: each metric tile, each measure, each statement row, each row
of a chart's table form, each chart, each finding, the bottom line, contrary evidence, what
would change the view, and each limitation on Analysis. A control shows when its own row,
tile or passage is hovered or focused, and all show under "Show sources".

## Fixed after the first render

- EBITDA by case: the downside labels now sit clear below their markers.
- Maturities: three-series groups use narrower bars and wider gaps, with the middle label one
  line higher, so no label meets a neighbouring bar or label.
- Trace controls were one per card; they are now one per figure, row or passage, as above.

Not given a trace control: the facts in "What the model covers", the parts list, the case
cards, and the limitations on the Limitations page.

## Not verified

- Rendered in headless Chrome at 1440px wide only; not in Edge, not at narrow widths, not in
  the Claude Design editor. Console messages were not captured.
- The three fixes were checked in one render each (Forecast, Analysis and Model with "Show
  sources" on); hover and focus of a single trace control were not exercised.
- Table, Bars, the cash flow and balance sheet tabs, the downside case and "Show sources"
  were rendered once each through the harness; the key measures tab and the Table side of
  the charts on Forecast, Analysis and Portfolio fit were not looked at.
- Source pages were read by screenshot and, for Untitled UI and HyperUI, by their class
  names; no pixel comparison was made. Shadcnblocks sizes are read by eye.
- Whether Recharts can draw these forms, dashes, markers and missing-value rules is untested.
- Contrast of the two baseline colours (`#6676FF`, `#E5704D`) as bar fills was not computed.
- Keyboard order and screen reader output were not tested.

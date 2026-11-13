# Library mocks

Step D1a of the [design track plan](../../superpowers/plans/2026-11-13-design-track.md), drawn
2026-11-13 against [design system](../design-system.md) 0.6, the
[component map](../component-map.md) and [decision 0003](../../decisions/0003-design-track.md)
(rulings of review 1 and "Source look"). For the owner's review 2. Nothing here is built.

**Mock project:** [Claude Design, Issuer library mocks (D1a)](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Overview.dc.html).
Standalone Claude Design has announced that its tools stop working by 2026-12-14.

Sample content is synthetic: the issuer "Halden Aerostructures", the other four issuers and
every figure are invented. No real issuer, company name, tagline or wordmark appears; the logo
and all icons are placeholder shapes.

## Screens drawn

| Screen | File | Kit used |
| :--- | :--- | :--- |
| Library home | [Library home](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Library+home.dc.html) | N1, N5, N6, R10 with F4, S1, S5 |
| Report history | [Report history](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Report+history.dc.html) | R11, S1 (run states) |
| Overview | [Overview](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Overview.dc.html) | N2, N4, P1, F1, P6, P2, P4, R4, R7, P5 |
| Changes | [Changes](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Changes.dc.html) | F3, C11, N6 (three-way), R7 |
| Module, prose (Business profile) | [Module prose](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Module+prose.dc.html) | N3, P1 to P5, C7, R8, R3, R5 |
| Module, data (Capital structure) | [Module data](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Module+data.dc.html) | N3, P1, P2, F1, F2, C4, C1, C6, C10, C9, C12, R2, R6, R1 with F5, S3, P5 |
| Evidence, Summary | [Evidence 1 Summary](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Evidence+1+Summary.dc.html) | N2, N5, F4, F1, R16 |
| Evidence, Trace with calculations | [Evidence 2 Trace](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Evidence+2+Trace.dc.html) | R13 holding R12 |
| Evidence, Sources | [Evidence 3 Sources](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Evidence+3+Sources.dc.html) | R14, R15, R16, S6 |
| Evidence, Gaps | [Evidence 4 Gaps](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Evidence+4+Gaps.dc.html) | R13 grouped by severity |
| Evidence, Record with registers | [Evidence 5 Record](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Evidence+5+Record.dc.html) | R17 with N6, R16, F4, R13 |
| Trace drawer | [Trace drawer](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Trace+drawer.dc.html) | N7 holding R12 |
| States | [States](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=States.dc.html) | S2, S5, R7, N8, blocked module |

Shared files in the project: `ds.css` (the design system's tokens and its own pieces), `src.css`
(source components at their source's sizes), `x.css` (issuer card and composed charts), and the
parts `Rail`, `RunHead`, `ModNav`, `EvTabs`.

## States drawn

| State | Where |
| :--- | :--- |
| No runs yet | States, first block |
| A gap, "Not established for this run" | Module data, Hedge expiries (panel); Evidence Gaps (inline badge); Library home, capped run |
| A withheld value | Module data: Average cost of debt tile, Receivables facility row and test; Evidence Gaps |
| A failed or blocked module, "Not assessable" | States, Recovery page; Overview and Changes module items; Overview metric reads n.a. |
| Missing is "n.a.", never 0 | Module data: maturities chart (2029 is 0, leases n.a.), statement (2022), facility terms (drawn USD 0m, fee n.a.), range with no band, peer not plotted; Changes "from n.a." with no direction |
| No earlier run to compare | States, second block; Report history, first run |
| Long text | Library home, third card; Module prose, limitation that collapses after three lines with "Show all" |
| Many modules | States, fourth block; Changes, "9 modules unchanged" |
| Run states in history | Report history: finished, capped, rejected, failed, interrupted; Library home: running (static), failed, capped |
| Loading | Library home, sixth card; States, fifth block (static skeleton) |
| Trace control | Hidden at rest; hover state on Overview's Net leverage tile; all shown with "Show sources" on, on Module prose |

No animation loops on any screen. The running badge is the half-filled circle without its halo.

## Where the mock departs, and why

1. **Shadcnblocks variants could not be read.** Every variant the map names from shadcnblocks
   (banner Inset, list panel Numbered, collapsible Card, stat Delta, item group, snippet Copy,
   gantt Timeline, list Groups, the chart variants) is behind its paid tier: the preview is
   client-rendered and its source returns 401. The mock copies the public base components those
   variants compose (shadcn/ui new-york-v4 and the Kibo UI registry, both read), so radius,
   padding, text sizes and borders are the base's; a variant's own overrides are not known.
2. **P1 bottom line.** The source banner is a 52px strip with 14px text. The map asks for the
   lead sentence "in the largest type", so the lead is set in the system's `h3` and the padding
   is 24 by 32. Fill is Navy (`surface-inverse`); radius 10 and the icon circle are the source's.
3. **N4 page header.** Untitled UI's title is 20px. The issuer name is page text, so it is the
   system's `h1` (36px) inside the source's header layout. The source header has no badge; the
   as-of, pathway and state badges sit under the name.
4. **F1 metric strip.** Untitled UI has no joined strip; each metric is its own card. The map
   asks for a joined strip, so the tiles share one container with hairline dividers. The
   figure is the source's 30px, not the system's 40px `metric`.
5. **Charts sit on the system's card.** Untitled UI's chart demos have no frame. A page of
   loose charts on the canvas read flat, so each chart is on a card. Marks follow the system
   (4px tops, a baseline, no gridlines); the legend, tick text and height follow Untitled UI.
6. **N5 filter bar.** The source has no applied-count badge. The mock shows the chosen value in
   each chip and the words "No filter applied".
7. **Modules navigator.** N3 is one vertical menu with two groups: the sections of this page,
   then the modules in this run with their state shape. This carries the owner's rule that the
   Modules navigator is always visible; the map lists only the section index.
8. **Source text sizes.** The owner ruled in the D1a session on 2026-11-13: "Use 16px body for
   findings". Key findings (P2), contrary evidence (P3) and what would change the view (P4) are
   set in the system's 16 / 26 body, with a 600-weight lead; their layout, radius, border and
   padding stay the source's. Applying it to P3 and P4 as well as P2 is this session's reading
   of question 2 as it was put. R7 and P5 keep their source's 14px.
9. **Status shapes for sets the system does not define.** Module state, change state, gap
   severity and how much of a file was read are drawn with proposed shapes (question 1).
10. **Table forms are not drawn.** Each chart has its Chart or Table toggle; the Table side,
    the List side of Library home and the Figures side of the statement are not drawn.
11. **Mock mechanics.** Bar heights, positions and thousands separators are computed in the
    mock's script from the sample values. That is drawing only; the product computes no figure.
12. **States page, many modules.** That block lists fourteen modules to show the collapse; the
    run elsewhere has thirteen.

## Questions for the owner

1. **Status shapes to fix in the design system.** Proposed, each distinct within its set:
   - Module state (R7 on Overview, the navigator, timings): Delivered, filled circle, success.
     Delivered with gaps, half-filled circle, info. Not assessable, slashed circle, neutral.
   - Change state per module (Changes): Changed, half-filled circle, action. Unchanged, square,
     neutral. Not assessable, slashed circle, neutral.
   - Gap severity (Evidence): High, diamond. Medium, triangle. Low, ring.
   - File read (Evidence Sources): Read in full, filled circle. Read in part, triangle. Not
     readable, diamond.
2. **Source look against "larger type".** Answered by the owner on 2026-11-13: 16px body for
   findings (departure 8). Still open: whether that also covers contrary evidence and the
   callout, as drawn, and whether module items (R7) and limitations (P5) stay at 14px. The
   ruling is not yet in decision 0003.
3. **Shadcnblocks.** Its named variants cannot be read without a paid account. Accept the
   public base components as the look, buy access, or move those rows to a source that can be
   read?
4. **Three alert shapes (map Q13).** P3 is a warning-tinted bordered box, P4 a left-ruled
   Ultramarine callout, and the library has no S4. They read as different here. Keep as mapped?
5. **Statement with a trend column (R1 with F5).** Drawn as mapped. Does the in-row sparkline
   break "why charts in tables when they should be charts"?
6. **A run in progress on Library home.** The card shows the latest finished run with a Running
   badge and a sentence naming both dates. Is that right, or should the running run lead?
7. **Capped, failed and rejected runs.** History says nothing from a failed run is shown and
   that a capped run's delivered modules can be read. Is that the intended behaviour?
8. **Evidence downloads.** "Download handoffs" is on Evidence Summary and "Download all" on the
   registers. Is Summary the right place?
9. **Module "Delivered with gaps".** A new state word. Keep it, or show only Delivered and let
   the limitations count carry it?
10. **Dumbbell scales.** Each row has its own scale, so line lengths cannot be compared across
    rows. Acceptable, or drop the Chart side on Changes?

## Not verified

- Rendered in headless Chrome at 1440px wide only; not checked at narrow widths, in Edge, in
  the Claude Design editor, or printed. Hover, focus and the switch are drawn states, not
  working controls; nothing was tested with a keyboard or a screen reader.
- Source sizes come from class names in the Untitled UI and HyperUI repositories and one
  headless measurement of seven Untitled UI pages. No mock was compared side by side with its
  source page, and hover and selected states were not measured.
- Shadcnblocks values are its base components', not the named variants' (departure 1). Which
  shadcn style the previews use was not confirmed; new-york-v4 values were used.
- Contrast was not re-measured on the mock. The white-on-Navy banner and the heat grid labels
  use pairs in the design system's table; the banner's small label (`#CCD1FF` on Navy) and the
  trace control's tertiary icon on a hairline edge were not computed.
- The runtime logs "never resolved" for two lists inside table bodies on Module data and
  Evidence Trace; the rows render. No other console message appeared.
- Recharts cannot be judged from a mock: the composed kinds (bridge, dumbbell, scatter, range,
  bullet, heat grid) are CSS drawings.
- Fonts load from Google Fonts in the mock. Sample content was not checked by a credit analyst.

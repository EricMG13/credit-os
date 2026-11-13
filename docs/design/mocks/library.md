# Library mocks

Step D1a of the [design track plan](../../superpowers/plans/2026-11-13-design-track.md), drawn
2026-11-13 against [design system](../design-system.md) 0.7, the
[component map](../component-map.md) and [decision 0003](../../decisions/0003-design-track.md)
(rulings of review 1, "Source look" and review 2). Revised after review 2. Nothing here is built.

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
| Changes | [Changes](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Changes.dc.html) | F3, C11, N6 (three-way, all three sides drawn), R7 |
| Module, prose (Business profile) | [Module prose](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Module+prose.dc.html) | N3, P1 to P5, C7, R8, R3, R5 |
| Module, data (Capital structure) | [Module data](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Module+data.dc.html) | N3, P1, P2, F1, F2, C4, C1, C6, C10, C9, C12, R2, R6, R1 (no F5), S3, P5 |
| Evidence, Summary | [Evidence 1 Summary](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Evidence+1+Summary.dc.html) | N2, N5, F4, F1, R16 |
| Evidence, Trace with calculations | [Evidence 2 Trace](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Evidence+2+Trace.dc.html) | R13 holding R12 |
| Evidence, Sources | [Evidence 3 Sources](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Evidence+3+Sources.dc.html) | R14, R15, R16, S6 |
| Evidence, Gaps | [Evidence 4 Gaps](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Evidence+4+Gaps.dc.html) | R13 grouped by severity |
| Evidence, Record with registers | [Evidence 5 Record](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Evidence+5+Record.dc.html) | R17 with N6, R16, F4, R13 |
| Trace drawer | [Trace drawer](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=Trace+drawer.dc.html) | N7 holding R12 |
| States | [States](https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=States.dc.html) | S2, S5, R7, N8, blocked module |

Shared files in the project: `ds.css` (the design system's tokens and its own pieces), `src.css`
(source components at their source's sizes), `x.css` (issuer card and composed charts), `status.css` (the gap colours for
"Delivered with gaps"), and the
parts `Rail`, `RunHead`, `ModNav`, `EvTabs`.

## States drawn

| State | Where |
| :--- | :--- |
| No runs yet (Library home: the library holds no issuer) | States, first block |
| No report yet (per issuer: the issuer has no finished run) | States, second block |
| A gap, "Not established for this run" | Module data, Hedge expiries (panel); Evidence Gaps (inline badge); Library home, capped run |
| A withheld value | Module data: Average cost of debt tile, Receivables facility row and test; Evidence Gaps |
| A failed or blocked module, "Not assessable" | States, Recovery page; Overview and Changes module items; Overview metric reads n.a. |
| Missing is "n.a.", never 0 | Module data: maturities chart (2029 is 0, leases n.a.), statement (2022), facility terms (drawn USD 0m, fee n.a.), range with no band, peer not plotted; Changes "from n.a." with no direction |
| No earlier run to compare | States, third block; Report history, first run |
| Long text | Library home, third card; Module prose, limitation that collapses after three lines with "Show all" |
| Many modules | States, fifth block; Changes, "9 modules unchanged" |
| Run states in history | Report history: finished, capped, rejected, failed, interrupted; Library home: running (static), failed, capped |
| Loading | Library home, sixth card; States, sixth block (static skeleton) |
| Trace control | Hidden at rest; hover state on Overview's Net leverage tile; all shown with "Show sources" on, on Module prose. On touch (no hover) trace controls are always shown |
| Table side of a chart | Module data, maturities; Module prose, risk matrix; Changes, the Table side of Cards, Chart or Table; Evidence Record, module timings |

No animation loops on any screen. The running badge is the half-filled circle without its halo.

Audit material on Overview: none. Its "Dates to watch" are issuer dates (results, refinancing,
maturity). Module timings, run codes, hashes and registers are on Evidence Record only.

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
4. **F1 metric tiles.** Each metric is its own card with a 16px gap, as Untitled UI draws
   them (decision 0003, review 2 ruling 5); the joined strip is gone. The figure is the
   source's 30px, not the system's 40px `metric`.
5. **Charts follow the source look** (review 2 rulings 1 and 5). Each chart sits on a card.
   Bar charts carry faint horizontal gridlines, value tick labels and no axis line (a hairline
   marks the baseline), and the source's rounded bar
   tops (6px); the legend, tick text and height are Untitled UI's. The statement table has no
   Trend sparkline column (ruling 4); its Bars view stays as a toggle and is not drawn.
6. **N5 filter bar.** The source has no applied-count badge. The mock shows the chosen value in
   each chip and the words "No filter applied".
7. **Modules navigator.** N3 is one vertical menu with two groups: the sections of this page,
   then the modules in this run with their state shape. This carries the owner's rule that the
   Modules navigator is always visible; the map lists only the section index.
8. **Source text sizes.** The owner ruled in the D1a session on 2026-11-13: "Use 16px body for
   findings". Key findings (P2), contrary evidence (P3) and what would change the view (P4) are
   set in the system's 16 / 26 body, with a 600-weight lead; their layout, radius, border and
   padding stay the source's. This is now decision 0003, review 2 ruling 2. Module items (R7) and limitations (P5) keep
   their source's 14px.
9. **Status shapes.** None: the four sets added in design system 0.7 are applied as written.
   Module state (Overview, the navigator, the module page header, module timings, States):
   Delivered, filled circle, success; Delivered with gaps, dashed ring, gap colours; Not
   assessable, slashed circle, neutral. "Not run" is not drawn: no ended run in the mocks has
   one. Change state (Changes): Changed, triangle, action; Unchanged, square, neutral; Not
   assessable, slashed circle, neutral. Gap severity (Evidence Gaps): High, diamond, error;
   Medium, triangle, warning; Low, ring, neutral. File state (Evidence Sources): Read in full,
   filled circle, success; Read in part, triangle, warning; Unreadable, diamond, error, with
   the reason in the sentence beside it. "Uploading" belongs to the run start page.
10. **Table forms.** One Table side is drawn per page that has a chart: maturities (Module
    data), the risk matrix (Module prose), Cards, Chart or Table (Changes) and module timings
    (Evidence Record). Both sides are stacked in the mock so they can be reviewed; the product
    shows one. The other charts' Table sides, the List side of Library home and the Bars view
    of the statement are not drawn.
11. **Mock mechanics.** Bar heights, positions and thousands separators are computed in the
    mock's script from the sample values. That is drawing only; the product computes no figure.
12. **P4 "What would change the view".** HyperUI's Standout toast in the info status
    colours (review 2 ruling 5). The toast's own 4px left rule and square corners are kept,
    in the info mark colour; the Ultramarine callout is gone.
13. **Unapproved sources behind the shadcnblocks rows.** Because of departure 1, the look of
    these rows was copied from shadcn/ui and Kibo UI, which are not among the eight approved
    sources: P1, P2, P3, P5, F2, R6, R7, R8, R16, C4, C6, C7 (shadcn/ui base components) and
    R17 (Kibo UI gantt). Review 2 ruling 3 accepts this for the mocks only. The build takes
    each of these pieces from Untitled UI or HyperUI where an equivalent exists. F5 is no
    longer used.

## Questions for the owner

1. **Source look against "larger type".** Closed by decision 0003, review 2 ruling 2, and
   "Keep 14px" for module items (R7) and limitations (P5).
2. **Shadcnblocks.** Closed by review 2 ruling 3 (departure 13).
3. **Three alert shapes (map Q13).** P3 is a warning-tinted bordered box and P4 is now the
   info-coloured toast; the library has no S4.
4. **Statement trend column.** Closed by review 2 ruling 4: removed.
5. **A run in progress on Library home.** The card shows the latest finished run with a Running
   badge and a sentence naming both dates. Is that right, or should the running run lead?
6. **Capped, failed and rejected runs.** History says nothing from a failed run is shown and
   that a capped run's delivered modules can be read. Is that the intended behaviour?
7. **Evidence downloads.** "Download handoffs" is on Evidence Summary and "Download all" on the
   registers. Is Summary the right place?
8. **Module "Delivered with gaps".** Closed: design system 0.7 lists it in the module-state set.
9. **Dumbbell scales.** Each row has its own scale, so line lengths cannot be compared across
    rows. Acceptable, or drop the Chart side on Changes?

10. **Dashed ring too faint at 10px.** The shape is the design system's and is also the gap
    badge's. Measured, 1x: the current 10px ring with a 1.5px edge has 9 pixels at 3:1 or
    more; 2px dashed has 30 at 10px, 33 at 12px and 42 at 14px; 2px dotted at 12px has 23.
    Proposed for the design system: a 2px dashed edge at 12px. Not applied to the mocks.

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
- All thirteen screens were re-rendered after the design system 0.7 status sets were applied,
  and looked at once each at 1440px. The only console message is "never resolved" for a list
  inside a table body on Evidence Trace; the rows render. The trace drawer's dimmed backdrop
  is a cut-down Overview, not the full page.
- The dashed ring was measured on the rendered screenshots (headless Chrome, 1440px, 1x). It
  is 10px with a 1.5px dashed edge. Its colour passes on every surface it sits on (`#514D80`:
  7.7:1 on white, 7.1:1 on the canvas, 6.4:1 on the selected navigator row). As drawn it does
  not: 7 to 9 of its 31 inked pixels reach 3:1 and the median inked pixel is about 1.55:1,
  against 70 of 88 for the filled circle and 32 of 60 for the slashed circle beside it. A 2x
  display and a real person's reading were not tested (question 10).
- No repository gate applies to this change: it is one Markdown file under `docs/`, and
  neither `tools/gates.py` nor the web gates were run.
- The always-shown trace control on touch is a CSS rule (`hover: none`); it was not seen on a
  touch device.
- Recharts cannot be judged from a mock: the composed kinds (bridge, dumbbell, scatter, range,
  bullet, heat grid) are CSS drawings.
- Fonts load from Google Fonts in the mock. Sample content was not checked by a credit analyst.

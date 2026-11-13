# Component map

Step D0b of the [design track](../superpowers/plans/2026-11-13-design-track.md), written
2026-11-13 and revised twice the same day: after the owner's first review, and after an
audit of the merged map. It maps every screen,
section, record shape, chart kind and state in the [screen inventory](screen-inventory.md) to
one component. Nothing here is built.

[Decision 0003](../decisions/0003-design-track.md), "Rulings at review 1", governs. The design
system (`docs/design/design-system.md`) owns tokens, status shapes, the appearance of gap,
withheld and blocked states, and motion. This map owns which component presents which kind of
information.

## How to read it

- **One kind of information, one component.** Section 2 is the kit: each row is one kind of
  information and the single component that presents it. The same kind on two screens uses
  the same component. Where one component still serves more than one use, section 7 says so
  and why.
- **Atoms are exempt.** Icon, tooltip, button, the status shape and the design system's five
  badge forms (status, label, count, dot, trace control) are parts used inside components,
  not presentations of a kind of information.
- **The page counts nothing.** Every count a component shows (on a tab, a group heading, a
  collapsed tile, the limitations heading) is a number delivery wrote.
- **"Ruling n"** is decision 0003's numbering. **"Q n"** is this map's own question in
  section 6.
- **The reader** is a portfolio manager or credit committee member who has not read the
  sources. They decide first (findings pages) and challenge second (Evidence). "Why" columns
  are written for that reader.
- **Read** means the component's own live page was opened on 2026-11-13. Section 7 lists what
  could not be read.
- Sources: **UUI** is Untitled UI React (React Aria). **HUI** is HyperUI, static Tailwind
  markup. **SB** is shadcnblocks.
- **Source look** (decision 0003). A component taken from a source copies that source page's
  visual design closely: layout, proportions, spacing, sizes, radius, shadow and states. It
  is not restyled and is not wrapped in a card or tile of ours. An SB component is **built on
  React Aria** where its source uses Radix or Base UI: the same look on a different
  primitive, so no Radix or Base UI enters the repository (ruling 3).
- **DS** is this repository's design system. It supplies only the colour values, the
  typefaces, the status shapes, the gap, withheld and blocked states, the static skeleton
  and motion, plus the two pieces no source supplies: the card and the tile.
- React Bits, Flowbite React, Preline, Uiverse and the Ant Design grid are not used.

## 1. What the live pages changed

Reading the pages overturned assumptions carried from the predecessor's map:

1. SB "Comparison" is a before-and-after image slider. It is not a two-sided board.
2. HUI charts load Chart.js from a CDN and draw to a canvas. They break the content security
   policy and are not used. Their hidden data table per chart is the pattern to keep.
3. UUI and SB charts are both Recharts. Five chart kinds have no usable source page:
   waterfall, dumbbell, range strip, limits, and scatter (the only scatter shown is HUI's,
   on Chart.js). No source has a node-and-link diagram either; this map draws a pathway as a
   step chain (R5), so none is needed.
4. SB "List" is a draggable status list in groups, not a plain list.
5. UUI card headers are a paid example; the card is written here.

## 2. The kit

### 2.1 Navigation and shell

| ID | Kind of information | Component | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| N1 | Which application area | Sidebar navigation: slim icon rail; dual-tier where an area has channels (Signal) | UUI [Sidebar navigations](https://www.untitledui.com/react/components/sidebar-navigations) | Four areas need four icons, not a menu bar; counts sit on the item |
| N2 | Which page of a run, of the Model, of Evidence, or of settings | Tabs with a count badge where a tab holds a list: underline when horizontal; side line when vertical (settings sections) | UUI [Tabs](https://www.untitledui.com/react/components/tabs) | The reader always sees the five places a run has and how much is in each |
| N3 | Where in a long module page | Vertical menu with icons and an active left border | HUI [Vertical Menu](https://www.hyperui.dev/components/application/vertical-menu) | A module is long; the index shows the judgement sections first |
| N4 | Which issuer and run this is | Page header: issuer name large, then as-of date, pathway and state as badges | UUI [Page headers](https://www.untitledui.com/react/components/page-headers) with [Badges](https://www.untitledui.com/react/components/badges) | The run code is an audit key and stays in Evidence; the reader needs issuer and date |
| N5 | Narrowing a list | Filter bar: search, dropdown filters, applied count | UUI [Filter bars](https://www.untitledui.com/react/components/filter-bars) | One control row instead of five selects |
| N6 | Two presentations of the same content | Segmented toggle (Chart or Table, Cards or List, Bars or Figures, Top or Latest) | UUI [Button groups](https://www.untitledui.com/react/components/button-groups) | Lets the reader pick the form they trust without leaving the page |
| N7 | A detail beside the page | Slide-out drawer with header, body and pinned footer | UUI [Drawers](https://www.untitledui.com/react/components/drawers) | The reader keeps their place while checking one item |
| N8 | Jump to a named item | Command menu with grouped results | UUI [Command menus](https://www.untitledui.com/react/components/command-menus) | Evidence is large; a challenger knows what they are looking for |

### 2.2 Judgement passages

| ID | Kind of information | Component | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| P1 | The bottom line | Inset banner, not dismissible: lead sentence in the largest type, the rest below | SB [Banner](https://www.shadcnblocks.com/components/banner) (Inset), built on React Aria | The decision in one glance, before any figure |
| P2 | Key findings; a digest's numbered points | Numbered list panel: bold lead, body, trace control | SB [List Panel](https://www.shadcnblocks.com/components/list-panel) (Numbered), built on React Aria | Ordered and scannable; the number gives committee members something to cite |
| P3 | Contrary evidence | Warning-toned alert with a status shape, title and text, never dismissible | SB [Alert](https://www.shadcnblocks.com/components/alert), built on React Aria | The case against must look different from the case for, and cannot be scrolled past as body text |
| P4 | What would change the view | Standout callout, static | HUI [Toasts](https://www.hyperui.dev/components/application/toasts) (Standout, repurposed) | The trigger for changing their mind is the one passage they return to |
| P5 | Limitations | Collapsible card, open by default, with a count and a link to the gaps in Evidence | SB [Collapsible](https://www.shadcnblocks.com/components/collapsible) (Card), built on React Aria | Qualifications stay exact and in view; the count tells them how qualified the view is |
| P7 | A one-line note written by a model (needs ruling) | Announcement: an "AI" label badge and one line | SB [Announcement](https://www.shadcnblocks.com/components/announcement), built on React Aria | The reader must never take a model's line for a colleague's or a module's |
| P6 | For and against | Two-sided board: two equal columns, one side each, each item a DS tile with a figure and a qualifier label | HUI [Grids](https://www.hyperui.dev/components/application/grids) (1x1) for the columns; the tile is DS, the only use of it | The debate as a picture; the reader sees the balance before reading either side |

### 2.3 Figures

| ID | Kind of information | Component | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| F1 | A headline figure | Metric tile, simple, in a joined strip; definition in a tooltip | UUI [Metrics](https://www.untitledui.com/react/components/metrics) (MetricsSimple) | Four to six numbers to scan before reading; no chart inside the tile |
| F2 | A measure over two periods with its consequence | Stat with delta, consequence sentence beneath | SB [Stat](https://www.shadcnblocks.com/components/stat) (Delta), built on React Aria | The change and what it means sit together |
| F3 | A change between two runs | Stat with a "from" value, then cause and effect | HUI [Stats](https://www.hyperui.dev/components/application/stats) (title, value, from value) | Before and after read left to right; the cause is one line away |
| F4 | Progress toward a stated total (modules delivered of modules planned, spend against the cap) | Progress bar with its label "n of N"; never used where no total is stated | UUI [Progress indicators](https://www.untitledui.com/react/components/progress-indicators) | A cap or a count is a part of a whole, not a trend |
| F6 | A move from one grade to another (a rating action) | Badge group: badge, arrow, badge | UUI [Badge groups](https://www.untitledui.com/react/components/badge-groups) | From and to read in one glance, in the order they happened |
| F7 | A strength on a short scale (signal strength; needs ruling) | Rating, read-only, three marks with a word | SB [Rating](https://www.shadcnblocks.com/components/rating), built on React Aria | Three marks sort a feed faster than a number; the word keeps it honest |
| F5 | A small trend inside a row or tile | Sparkline, bar or line, no axes | SB [Sparkline](https://www.shadcnblocks.com/components/sparkline), its look copied, drawn with Recharts | Direction at a glance where a full chart would crowd the row |

### 2.4 Records

| ID | Kind of information | Component | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| R1 | A financial statement | Table with a sticky first column and an in-row sparkline; Bars or Figures toggle (N6) | HUI [Tables](https://www.hyperui.dev/components/application/tables) (Sticky first column) with F5 | A statement is a table by nature; the bars make it scannable without dropping a figure |
| R2 | Facts with a label | Details list, grouped by category | HUI [Details Lists](https://www.hyperui.dev/components/application/details-list) | Label and value pairs read faster than a three-column table |
| R3 | Questions and their answers | Accordion on native `details`, an answer-state badge on each row | HUI [Accordions](https://www.hyperui.dev/components/application/accordions) | The reader opens only the question they care about; the badge shows which were answered |
| R4 | Events with dates | Timeline, vertical, with the date on every entry and past, next and later marked by status shape | HUI [Timelines](https://www.hyperui.dev/components/application/timelines) (Vertical) | Past, next and later is how a watch date is used |
| R5 | Cause and effect | Step chain with title and description per step | HUI [Steps](https://www.hyperui.dev/components/application/steps) (grouped, title and description) | A pathway reads as a sequence; the relationship is the step text |
| R6 | Status of each item in a list | Status list in groups, one group per state with a count; read-only, no drag | SB [List](https://www.shadcnblocks.com/components/list) (Groups), built on React Aria | What is not met is one group at the top, not a column of words to scan |
| R7 | One module's state and lead sentence | Item: icon media, title, lead sentence, a trailing status badge, in an item group | SB [Item](https://www.shadcnblocks.com/components/item), built on React Aria | Each module is one line; a repeated state collapses to one item with a count |
| R8 | An indicator to watch | Ticker row, static: indicator, threshold, leading or lagging icon | SB [Ticker](https://www.shadcnblocks.com/components/ticker), built on React Aria, with no live update | A watch list is a list of levels; the icon replaces the words "leading" and "lagging" |
| R9 | The named cases | Choice cards: one per case with its assumption and what it leaves out; choosing one sets the case every chart on the page shows | SB [Choicebox](https://www.shadcnblocks.com/components/choicebox), built on React Aria | The definitions double as the case switch, so the reader always knows which case they are looking at |
| R10 | An issuer and its latest run | Card: header, content, footer | DS card, written here; no source is copied | A portfolio manager picks an issuer, not a run row |
| R11 | Runs or activity over time | Activity feed, connected | UUI [Activity feeds](https://www.untitledui.com/react/components/activity-feeds) (Connected) | History is a sequence with a state at each point |
| R12 | How a figure was derived | Tree with connectors: result, formula, inputs, source excerpt | UUI [Tree views](https://www.untitledui.com/react/components/tree-views) | A calculation is a tree; the challenger opens only the branch in doubt |
| R13 | Register rows that are sorted and scanned (Evidence; Signal's source list) | Sortable table, the source's `sm` dense rows | UUI [Tables](https://www.untitledui.com/react/components/tables) | On Evidence and in Signal's settings only, never on a findings page. Complete and sortable matters more here than airy |
| R14 | A file | File row: type icon, name, size, state | UUI [File uploaders](https://www.untitledui.com/react/components/file-uploaders) (list item) | The file the analyst uploaded looks the same when it is later cited |
| R15 | Who else (modules that read a file, sources that carried a story, who shared it) | Avatar group with initials and a +N count | UUI [Avatars](https://www.untitledui.com/react/components/avatars) (group) | A stack of initials replaces a sentence of names |
| R16 | A value to copy (a hash, an id) | Snippet with a copy button | SB [Snippet](https://www.shadcnblocks.com/components/snippet) (Copy), built on React Aria | Evidence only. Nobody retypes a hash |
| R17 | Spans on a time axis (module start to accepted; hedge expiries) | Gantt, timeline variant; read-only, no drag; a Chart or Table toggle (N6) | SB [Gantt](https://www.shadcnblocks.com/components/gantt) (Timeline), built on React Aria | Overlap and order are visible without reading times |
| R18 | An outside story | Media object: source monogram, then kind label, headline, source, time, summary, tags, actions; any reactions sit under it | HUI [Media](https://www.hyperui.dev/components/application/media) (left, align top) | A story is somebody else's words; it must not look like an issuer card or a finding |
| R19 | A person or a group of people | Avatar with a title and a subtitle | UUI Avatars (label group) | The name chip, a group row and a member all read as "who", with the role beneath |
| R20 | Keywords and labels attached to something | Tag group, with a count where it helps | UUI [Tags](https://www.untitledui.com/react/components/tags) | A topic is its keywords; tags show the rule without a sentence |
| R21 | A stage in a fixed sequence (a regulatory case) | Progress bar with stage labels | HUI [Progress Bars](https://www.hyperui.dev/components/application/progress-bars) (with labels and status colours) | Where the case stands and how far it has to go, in one line |

### 2.5 Charts

Every chart sits in one frame: title, a Chart or Table toggle (N6), direct labels on the
values that matter, a legend only for two or more series, the module's basis note, one trace
control. The frame and base are UUI
[Line and bar charts](https://www.untitledui.com/react/components/line-bar-charts) (Recharts,
`charts-base`; ruling 2), copied as its page shows it. The table form is R1's table without
the sparkline. Kinds with no source page are composed with Recharts and follow the look of
the source chart named in their row.

| ID | Chart kind | Form | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| C1 | Grouped columns; recovery by class and case | Bar chart, grouped | UUI Line and bar charts (bar) | Amounts side by side on one zero baseline |
| C2 | Trend | Line chart, one series | UUI Line and bar charts (line) | One measure through time |
| C3 | Path | Line chart, several series, the last actual marked | UUI Line and bar charts (line, multiple) | Base against downside on the same axis |
| C4 | Stack | One horizontal stacked bar with a ranked legend | SB [Chart](https://www.shadcnblocks.com/components/chart) (bar, stacked), its look copied, drawn with Recharts in the frame | Parts of a whole by rank; never a pie |
| C5 | Comparison | Small multiples of horizontal bars, one panel per measure | SB Chart (bar, multiple), its look copied, drawn with Recharts in the frame | Each measure keeps its own scale, so no case is flattened |
| C6 | Bullet | Horizontal bar with a target line | SB Chart (target line), its look copied, drawn with Recharts in the frame | Headroom is the distance to the line |
| C7 | Risk matrix (record shape) | Heat grid, three by three, items placed in cells, on the DS magnitude scale | SB Chart (heatmap, repurposed), its look copied, drawn with Recharts in the frame | Probability and impact as position, not two badge columns |
| C8 | Ranked thresholds (record shape) | Ranked bars | SB Chart (ranked bars), its look copied, drawn with Recharts in the frame | The first break point is the longest bar |
| C9 | Scatter | Scatter with axis titles | Composed with Recharts; no usable source page. Follows the look of the UUI line chart: its axes, grid, markers, tooltip and legend | Two measures per issuer; outliers stand apart |
| C10 | Waterfall or bridge; cash flow walk | Floating columns to a total | Composed with Recharts; in no source. Follows the look of the UUI bar chart: its bars, axes, grid and tooltip | Additive steps to a total |
| C11 | Dumbbell | Two marks joined by a line per row | Composed with Recharts; in no source. Follows the look of the UUI line chart: its line weight, markers and tooltip | Earlier against current when both are numbers |
| C12 | Range strip | A range bar with one marker | Composed with Recharts; in no source. Follows the look of the SB horizontal bar chart, the marker as in its target-line chart | The issuer against the peer range |
| C13 | Limits | Bars with limit ticks | Composed with Recharts; in no source. Follows the look of the SB target-line chart: its bars and its line as the tick | Exposure against each limit |
| C14 | Hedge | R17 (spans on a time axis) | SB Gantt, built on React Aria | Expiries are spans, not points |
| C15 | Pair tile | Two F1 metric tiles in one container | UUI Metrics | Two agencies' ratings are two headline figures |

A missing value in a chart is never drawn as zero:

- Sparkline (F5): the line breaks at the missing period and does not join across it; a bar
  sparkline leaves the slot empty.
- Bars and columns: no bar is drawn; "n.a." in the tertiary text colour sits at the baseline
  in the bar's place, and the category keeps its slot.
- Heat grid (C7): an item with a missing grade is listed beside the grid under "Not placed";
  an empty cell stays the card colour and never takes the lowest colour step.
- Lines (C2, C3): the line breaks; no point is interpolated.
- Scatter (C9): an issuer missing either measure gets no point; it is listed under the chart
  as "Not plotted", with which measure is missing.
- Waterfall (C10): a missing step leaves its slot empty with "n.a." at the baseline; later
  columns float from the values the module wrote, and a total the module did not write is
  not drawn.
- Dumbbell (C11): with one end missing, only the present mark is drawn, with no line, and
  "n.a." stands where the other mark would be.
- Range strip (C12): a missing marker leaves the range with "n.a." beside the label; a
  missing range draws no strip.
- Limits (C13): a missing limit draws the bar with no tick and the words "limit n.a."; a
  missing exposure draws no bar.
- Stat tiles: F2 with a missing period shows "n.a." in place of that figure and no delta
  shape; F3 with no earlier value reads "from n.a." and shows no direction.
- The table form shows "n.a." in the same cell.

### 2.6 Input and run

| ID | Kind of information | Component | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| I1 | Steps the analyst completes | Stepper, form wizard | SB [Stepper](https://www.shadcnblocks.com/components/stepper), built on React Aria | Five steps with the current one named; validation per step |
| I2 | Files to add | Drop zone with R14 rows and a progress bar | UUI [File uploaders](https://www.untitledui.com/react/components/file-uploaders) | Upload state per file, with retry |
| I3 | The purpose of a run | Radio cards with icon, title and description | UUI [Radio groups](https://www.untitledui.com/react/components/radio-groups) (Icon Card) | The purpose is a choice with consequences; the description states them |
| I4 | A decision that costs money or cannot be undone (Start only) | Confirmation modal, warning style, stating the cap | UUI [Modals](https://www.untitledui.com/react/components/modals) | Submit stays an explicit act with the cost in front of it |
| I5 | Progress of a live run | Progress steps, vertical, one per module: complete, current, incomplete | UUI [Progress steps](https://www.untitledui.com/react/components/progress-steps) | Which module is running and how many are left |
| I6 | One pick from a list of named things (a group, a schedule, a length, a visibility) | Select | UUI [Select](https://www.untitledui.com/react/components/select) | A plain setting; it needs no description card |
| I7 | A conversation | Message list with reactions and a composer; no typing indicator | UUI [Messaging](https://www.untitledui.com/react/components/messaging) | Signal threads only; colleagues' words look like messages and nothing else does |
| I8 | Free text from the analyst | Text area with label and hint | UUI [Textareas](https://www.untitledui.com/react/components/textareas) | More context is optional; the hint says what helps |
| I10 | A short form that must be answered now (display name; share to group) | Form modal: title, one or two fields, Cancel and a primary action; no warning style | UUI Modals (Form) | A small question in its own frame; it must not look like the paid-run warning |
| I11 | A short text value | Input with label and hint | UUI [Inputs](https://www.untitledui.com/react/components/inputs) | One line, labelled, with the error beside it |
| I9 | A rule that is on or off | Toggle with label and hint, one row per rule | UUI [Toggles](https://www.untitledui.com/react/components/toggles) | The label states the rule; the switch states whether it applies |

### 2.7 States and messages

| ID | Kind of information | Component | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| S1 | A state (of a run, a module, a source) | Status badge: a fixed shape, a colour and a word, always all three. Running is the pulsing filled circle. Queued is the neutral ring, with the CSS shimmer where its result will appear | DS status shapes on UUI Badges | Fixes the predecessor's colour-only fills; the shape survives grayscale |
| S2 | Nothing here yet, and what to do | Empty state: featured icon, title, text, one action | UUI [Empty states](https://www.untitledui.com/react/components/empty-states) | A blank page reads as broken; the reason reads as honest |
| S3 | A gap as a block: content or a chart not established for this run | Hatched dashed gap panel with the words and the module's stated reason | DS gap panel | Never an error colour: a gap is a fact about the run, shown where the content would have been |
| S4 | The system telling the reader something that changes what they do next (run started, cannot reach the service, run capped, run rejected) | Alert, floating, tone by severity, with an action | UUI [Alerts](https://www.untitledui.com/react/components/alerts) | Says what happened and what to do next |
| S5 | Content still loading, anywhere but a live run page | Static skeleton in the shape of what will arrive; no animation | DS skeleton | No layout jump when content lands |
| S6 | A small action finished and needs nothing further (copied, saved) | Toast, success | HUI Toasts (Success) | Confirms without a page change; anything the reader must act on is S4 |
| S7 | A live run with no step count yet | Spinner with a label, on a run page while a run is live only | UUI [Loading indicators](https://www.untitledui.com/react/components/loading-indicators) (line simple) | Says the run is alive before the first module reports |
| S8 | New items waiting above a list | Pill, static | SB [Pill](https://www.shadcnblocks.com/components/pill), built on React Aria | Tells the reader there is more without moving what they are reading |

## 3. Screen by screen

### 3.1 Library

| Screen | Section | Kit |
| :--- | :--- | :--- |
| Every page | Area rail; run tabs; issuer and run identity | N1; N2; N4 |
| Library home | Search and filters; issuer cards with the latest lead sentence, as-of date, pathway and modules delivered of modules planned; Cards or List | N5; R10 with F4; N6 |
| Library home | A run in progress; the list still loading | R10 with S1 (running); S5 |
| Report history | One entry per run: state, date, pathway, "what changed" link | R11 |
| Overview | Verdict panel | P1 |
| Overview | Metric strip | F1 |
| Overview | For-and-against board | P6 |
| Overview | Findings feed | P2 |
| Overview | Callout | P4 |
| Overview | Dated timeline | R4 |
| Overview | Module tiles | R7 |
| Overview | Limitations block | P5 |
| Changes | Change cards; a dumbbell when both values are numbers; Cards, Chart or Table | F3; C11; N6 (three-way), the table as R1's |
| Changes | Module state tiles | R7 |
| Changes | No earlier run | S2 |
| Modules | Section index | N3 |
| Modules | Bottom line; key findings; contrary evidence; what would change the view; limitations | P1; P2; P3; P4; P5 |
| Modules | Typed records | Section 4 |
| Modules | Amounts by period or year (revenue and EBITDA, maturities); recovery by class and case | C1 |
| Modules | Debt stack; liquidity | C4 |
| Modules | Covenant and rating-trigger headroom | C6 |
| Modules | Issuer against peers on two measures; against the peer range on one | C9; C12 |
| Modules | Hedge expiries | C14 |
| Modules | EBITDA bridge | C10 |
| Modules | A chart the module could not draw | S3 |
| Evidence | Summary: modules delivered of modules planned; counts of files, calculations and gaps | F4; F1 |
| Evidence | Trace, with the calculation as the expanded row | R13 holding R12 |
| Evidence | Sources: file, readers, hash; "copied" confirmation | R14; R15; R16; S6 |
| Evidence | Gaps, grouped by severity | R13 |
| Evidence | Record: module timings, Chart or Table; hashes and instructions; model calls; registers as written | R17 with N6; R16; R13 |
| Evidence | Module filter; jump to an item | N5; N8 |
| Trace drawer | Statement, then its derivation, then "Open in Evidence" | N7 holding R12 |

Evidence has five tabs (ruling 8): Summary, Trace, Sources, Gaps, Record. The trace control is
the design system's trace control (icon only, with an accessible name and a tooltip), one per paragraph, row or figure, shown on hover
and keyboard focus, always on touch, with a page-level "Show sources" switch (ruling 7).

### 3.2 Model and Forecast

| Screen | Section | Kit |
| :--- | :--- | :--- |
| Model shell | Front Page, Analysis, Model, Portfolio Fit, Limitations; Evidence is a link to the run's Evidence filtered to the model | N2 |
| Front Page | Bottom line; headline figures | P1; F1 |
| Analysis | Passages; measures with their consequence | P2; P3; P4; P5; F2 |
| Model | Statements | R1 |
| Model | Bridges; cash flow section | C10 |
| Model | Case comparison; the cases themselves | C5; R9 |
| Model | Debt stack; maturities by year | C4; C1 |
| Portfolio Fit | Exposure against limits; agency ratings | C13; C15 |
| Limitations | As the library | P5 |
| Forecast | Cases and their drivers | R9; C12 for a driver against its range |
| Forecast | Trend line; paths by case | C2; C3 |

### 3.3 Run

| Screen | Section | Kit |
| :--- | :--- | :--- |
| Run start | Steps Documents, Purpose, Confirm, More context, Start | I1 |
| Run start | Documents (file names appear here because the analyst is choosing them: an input control, the one exception to "file names only on Evidence") | I2 |
| Run start | Purpose | I3 |
| Run start | Confirm: the summary to approve | R2 |
| Run start | More context | I8 |
| Run start | Start | I4 |
| Run started panel | What will run and its cap | S4 (info tone) with F4 |
| Readiness side panel | Readiness items; the cap | R6; F4 |
| Run activity | Module progress; the running module; a queued module; a live run before its first module reports | I5; S1 (pulsing circle); S1 (ring, with the shimmer); S7 |
| Run activity | Activity lines; spend against the cap | R11; F4 |
| Run activity | No run, or the activity cannot be read | S2; S4 |

Elapsed time and spend are the values the run data gives; the page counts nothing up and no
numeral is animated (ruling 6).

### 3.4 Signal

Signal is a separate served page, outside the open-from-disk rule and its gate (ruling 9).
Parts that need paid model calls are marked "needs ruling".

| Screen | Section | Kit |
| :--- | :--- | :--- |
| Feed | Area rail and channel list (views, topics, groups, digests) with unread counts | N1 (dual-tier) |
| Feed | A topic's follow star | Icon toggle button (atom) on the channel item |
| Feed | Name chip with role | R19 |
| Feed | Kind filter and search | N5 |
| Feed | Top or Latest | N6 |
| Feed | Freshness line | S1, static |
| Feed | New stories waiting | S8 |
| Feed | Story cards | R18 |
| Feed | Loading; "Show older" | S5; a secondary button (atom) under the list, absent when nothing older exists |
| Story card | Kind label; topic tags | Label badge (atom); R20 |
| Story card | Also in N other sources; "shared by" line | R15 |
| Story card | Signal strength (needs ruling) | F7 |
| Story card | AI "why it matters" line (needs ruling) | P7 |
| Story card | Regulatory case stage | R21 |
| Story card | Rating move, from and to | F6 |
| Group view | Group header with its members; its shared stories, each with its "shared by" line and comment count; New thread and Attach story for a writer | R19 with R15; R18; buttons (atoms) |
| Thread panel | Quoted story; comments and replies; composer | N7 holding R18 and I7 |
| Thread panel | Reactions | Part of I7 |
| Share to group | Pick a group, add a note | I10 holding I6 and I8 |
| Digest card and page (needs ruling) | Numbered points, each with the stories behind it, under an "AI" label badge | P2 |
| Name dialog | Display name | I10 holding I11 |
| Settings | Section list | N2 (vertical, side line) |
| Settings | Groups: name and members; visibility | R19 with R15; I6 |
| Settings | Sources: kind, state, health, items per week (a register the owner sorts; R13's second use) | R13 with S1 and F5 |
| Settings | Thread rules; notifications | I9 |
| Settings | Topics: name, keywords, kinds | R20 |
| Settings | Digest form: covers, schedule, length, brief | I6; I8; I11 |
| Settings | AI spend against the cap | F4 |

## 4. Record shapes (17)

| Shape | Kit | Not |
| :--- | :--- | :--- |
| matrix | C7 | Two badge columns |
| watch | R8 | A table with a "Leading / Lagging" column |
| dated | R4 | A table of dates |
| edges | R5 | An edge table |
| ranked | C8 | A numbered table |
| case rows | R9 | A table with a row per case |
| module state | R7 | A row per module saying "Unchanged" |
| question and answer | R3 | A two-column table |
| sided | P6 | A table with a "Side" column |
| change | F3, or C11 when both values are numbers | Two columns |
| facts | R2 | A three-column table |
| cases | C5 with R9 as the switch | A column per case |
| status | R6 | A status column of words |
| metric | F1, grouped by family | A five-column table |
| measure | F2 | A row with a "Consequence" cell |
| statement | R1 | A line chart through two points |
| default records | R2, one card per row, label first | A raw grid |

## 5. States

Appearance is the design system's; this table says which component carries each state.

| State | Kit | Notes |
| :--- | :--- | :--- |
| No runs yet | S2 | Action: start a run |
| A gap, "Not established for this run" | S3 as a block; inside a table cell or a chart, an inline gap badge with those words | Never an empty cell, never a status colour |
| A withheld value | A short neutral striped bar where the figure would be, with a neutral "Withheld" badge (DS) | Distinct from a gap in shape and word |
| A failed or blocked module, "Not assessable" | A neutral badge with the slashed circle and one sentence saying why (DS), inside the module's R7 item and at the top of its page | The item keeps its place so the count of modules stays true |
| Missing versus zero | The text "n.a." in the tertiary text colour, right-aligned like a number; zero is the figure 0 | A text rule, not a component. Charts: section 2.5 |
| No earlier run | S2 | On Changes and on F3 |
| Long text | Passages (P1 to P4) and findings show in full and wrap; a long record cell wraps inside its row; nothing is cut with an ellipsis. Only P5 collapses, after a set number of lines, and prints open | Never truncates a qualification |
| Many modules | R7 collapses a repeated state to one item with a count that delivery wrote; N3 scrolls | |
| Run queued | S1, neutral ring, with the CSS shimmer where its result will appear | Loops only while the run is live |
| Run running | S1, pulsing filled circle | Loops only while the run is live |
| Run finished | S1 | |
| Run failed, capped, rejected, interrupted | S1 in the design system's shapes (diamond, triangle, cross, pause bars), each with its word, and S4 saying what happened and what to do | |
| Signal: no display name yet | The name dialog opens; the name chip (R19) reads "Set your name" | |
| Signal: reader or writer | A reader sees no write control at all (none is drawn disabled); the role sits under the name in R19 | |
| Signal: nothing followed, nothing saved, no approved source, no story yet, no story of the chosen kind, no search match | S2, one text each; "nothing followed" lists topics to follow | |
| Signal: loading; cannot reach the service | S5 (static, no spinner); S4 with Retry | |
| Signal: sources not checked yet | The freshness line (S1) in its neutral shape with those words | |
| Signal: new stories waiting | S8 | |
| Signal: older stories exist | "Show older" button under the list | |
| Signal: a story with no link or no time | R18 with a plain-text headline and no Open source action; the time is left out, not shown as "n.a." | |
| Signal: a source proposed, approved, paused, healthy, quiet or failing | S1 in the design system's shape for each meaning, each with its own word, in the sources table; failing shows its reason | Two states may share a shape and differ by colour and word |
| Signal: AI off or at its cap | S4 in settings; story cards carry no AI line; digests show as paused | |
| Signal: a digest with nothing material to report | The digest card with one sentence and no numbered list | No model call is made for it |
| Signal: an unread digest | The dot badge (atom) on its channel item (N1) and on the digest card | |
| Signal: comment edited, comment removed, thread archived | Inline text marks inside I7; an archived thread has no composer | |

## 6. Questions put to the owner, and the rulings

Thirteen questions (Q1 to Q13) were put at review 1. The owner accepted the recommended
defaults; the outcomes are recorded in [decision 0003](../decisions/0003-design-track.md),
which governs. The Q numbers below are this map's and are not the decision's ruling numbers;
the last column says where the decision records each.

| Q | Question | Outcome | In decision 0003 |
| :--- | :--- | :--- | :--- |
| Q1 | Charts need a library or hand drawing; five kinds are in no usable source | Recharts through UUI `charts-base`, with the missing kinds composed inside it. It needs its own decision record at D2a and must pass the open-from-disk check first | Ruling 2 |
| Q2 | "The page computes no figure" against chart scales and animated counters | A chart library may compute scales and positions from the values it is given; no figure shown as text is computed on the page. No animated numerals | The paragraph after "Also accepted"; ruling 6 |
| Q3 | "Motion only for live state" against drawer, tab and accordion transitions | One-off transitions up to 200 ms; only live run state loops; all off under reduced motion | Ruling 6 |
| Q4 | One trace control per paragraph, row and figure | Shown on hover and keyboard focus, always on touch, with a page-level "Show sources" switch | Ruling 7 |
| Q5 | "Every chart has a table form" against "no repeated plain table" | The table is the other side of the Chart or Table toggle | "Also accepted" |
| Q6 | Evidence has seven tabs | Five: Summary, Trace with calculations, Sources, Gaps, Record with registers; nothing removed | Ruling 8 |
| Q7 | The Model's own Evidence and Limitations pages | The Model links to the run's Evidence instead of its own | Ruling 8 |
| Q8 | Limitations open or collapsed | Open by default | "Also accepted" |
| Q9 | Signal cannot open from `file://` | A separate served page outside the open-from-disk rule and its gate | Ruling 9 |
| Q10 | Which Signal screens to mock | Every designed screen; parts needing paid model calls are marked as needing a ruling | Ruling 9 |
| Q11 | Two primitive libraries | React Aria only. Shadcnblocks pieces are built on it; Radix and Base UI are not added | Ruling 3 |
| Q12 | Unused sources | Flowbite React, Ant Design, Preline and Uiverse are unused. React Bits is also unused: its licence forbids redistribution and this repository is public; animations are CSS written here | "Also accepted"; ruling 4 |
| Q13 | Three alert-shaped components (P3, P4, S4) | Kept as mapped; contrary evidence moves into P6 on module pages if the mocks cannot make the three plainly different | "Also accepted" |

Decision 0003 names the pathway among the kinds composed in Recharts. This map draws a
pathway as a step chain (R5) and composes no pathway chart; if the mocks show the chain is
not enough, the pathway becomes a sixth composed kind.

## 7. Not read, and fragile choices

Not read, or read in part:

- Flowbite React: its Timeline, Drawer and Accordion pages were read in a browser, after its
  browser check (fetches return 429). Not used.
- Uiverse loaders: the page lists 1,218 CSS and Tailwind loaders by author with no names; no
  loader's code was opened. Not used.
- Preline: `preline.co/blocks` returns 404; `preline.co/examples.html` and five block pages
  under `/blocks/data-display/` were read. Not used.
- Ant Design grid: read (24 columns, six breakpoints). Not used; Tailwind's grid covers layout.
- React Bits: its index and five component pages were read. Not used (ruling 4).

One component, more than one use. Each is kept because the uses are the same kind of
information; the mocks should test whether the reader can still tell them apart:

- **R2 (details list)** serves a module's facts, the run summary the analyst approves, and
  default records. All three are label and value pairs with no order and no state. Default
  records are the fallback for a shape no rule recognises, so they take the plainest form.
- **R13 (audit table)** serves Evidence's rows and Signal's source list in settings. Both are
  administrative registers that the challenger or the owner sorts and scans, not findings.
- **R15 (avatar group)** serves modules that read a file, sources that carried a story and
  colleagues who shared it. All answer "who else".
- **R17 (Gantt)** serves the run record's module timings and hedge expiries. Both are spans
  on a time axis.
- **P2 (numbered list)** serves key findings and a digest's points. A digest always carries
  an "AI" label badge so that it is not read as a module's finding.
- **F4 (progress indicator)** serves counts of a total and spend against a cap.
- **I6 (select)** serves group, schedule, length and visibility. All are one pick from a list.
- **UUI Modals** supplies two kit rows in two of its variants: I4 (warning confirmation, used
  for Start only) and I10 (form). They must look different, and the source's own variants do.
- **N6 (segmented toggle)** has a three-way use on Changes (Cards, Chart or Table).

Other fragile choices to test in the mocks and at D2a:

- Every SB component is built on React Aria to look like its source page; the effort per
  component is not estimated, and how closely a different primitive can match is untested.
  R6 and R17 lose their drag behaviour by design.
- C9 to C13 have no source page; each follows the look of the source chart its row names.
- R8 (ticker) and C7 (heatmap) are repurposed from live prices and a week-by-hour grid.
- P1 (banner) and P4 (toast) are repurposed from announcements and notifications.
- P6 is two columns of DS tiles and R10 is the DS card: the two pieces with no source look to copy.
- UUI Notifications needs Sonner and UUI Code snippets needs Shiki; both are avoided (S6 and
  R16 instead).

## Not verified

- No component was installed, built or opened from disk; whether each passes the content
  security policy, and whether Recharts runs under it, is unknown until D2a.
- Licences and paid tiers: SB and UUI pages do not mark them for every component; none was
  read from a licence text.
- Pages were read through a summarising fetch or as page text, not by eye; variant names are
  as reported.
- Kinds of information were derived from the inventory and the predecessor's map, not from
  every run; a shape not listed falls to R2.
- The design system this map was checked against is version 0.3 on its own branch (in review),
  read for its status, gap, run-state, badge, skeleton, tabs and motion sections, not line by
  line; it may change before it merges.
- The "source look" reading (what the design system supplies and what the source supplies) is
  the coordinator's and is to be confirmed at review 2.

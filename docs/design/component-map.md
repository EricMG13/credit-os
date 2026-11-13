# Component map

Step D0b of the [design track](../superpowers/plans/2026-11-13-design-track.md), written
2026-11-13 and revised the same day after the owner's first review. It maps every screen,
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
- **Atoms are exempt.** Badge, icon, tooltip, button and the status shape are parts used
  inside components, not presentations of a kind of information.
- **The reader** is a portfolio manager or credit committee member who has not read the
  sources. They decide first (findings pages) and challenge second (Evidence). "Why" columns
  are written for that reader.
- **Read** means the component's own live page was opened on 2026-11-13. Section 7 lists what
  could not be read.
- Sources: **UUI** is Untitled UI React, taken as built (React Aria). **HUI** is HyperUI,
  static Tailwind markup. **SB** is shadcnblocks, used as a **layout reference only and
  redrawn on React Aria**: no shadcnblocks code, Radix or Base UI enters the repository
  (ruling 3). **DS** is this repository's design system: cards, tiles, status shapes, gap
  panels and every animation are CSS written here.
- React Bits, Flowbite React, Preline, Uiverse and the Ant Design grid are not used.

## 1. What the live pages changed

Reading the pages overturned assumptions carried from the predecessor's map:

1. SB "Comparison" is a before-and-after image slider. It is not a two-sided board.
2. HUI charts load Chart.js from a CDN and draw to a canvas. They break the content security
   policy and are not used. Their hidden data table per chart is the pattern to keep.
3. UUI and SB charts are both Recharts. No approved source ships a waterfall, bullet,
   dumbbell, range strip, limit-tick bar or node-and-link diagram.
4. SB "List" is a draggable status list in groups, not a plain list.
5. UUI card headers are a paid example; the card is written here.

## 2. The kit

### 2.1 Navigation and shell

| ID | Kind of information | Component | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| N1 | Which application area | Sidebar navigation: slim icon rail; dual-tier where an area has channels (Signal) | UUI [Sidebar navigations](https://www.untitledui.com/react/components/sidebar-navigations) | Four areas need four icons, not a menu bar; counts sit on the item |
| N2 | Which page of a run, of the Model, or of Evidence | Tabs, underline, with a count badge where a tab holds a list | UUI [Tabs](https://www.untitledui.com/react/components/tabs) | The reader always sees the five places a run has and how much is in each |
| N3 | Where in a long module page | Vertical menu with icons and an active left border | HUI [Vertical Menu](https://www.hyperui.dev/components/application/vertical-menu) | A module is long; the index shows the judgement sections first |
| N4 | Which issuer and run this is | Page header: issuer name large, then as-of date, pathway and state as badges | UUI [Page headers](https://www.untitledui.com/react/components/page-headers) with [Badges](https://www.untitledui.com/react/components/badges) | The run code is an audit key and stays in Evidence; the reader needs issuer and date |
| N5 | Narrowing a list | Filter bar: search, dropdown filters, applied count | UUI [Filter bars](https://www.untitledui.com/react/components/filter-bars) | One control row instead of five selects |
| N6 | Two presentations of the same content | Segmented toggle (Chart or Table, Cards or List, Bars or Figures, Top or Latest) | UUI [Button groups](https://www.untitledui.com/react/components/button-groups) | Lets the reader pick the form they trust without leaving the page |
| N7 | A detail beside the page | Slide-out drawer with header, body and pinned footer | UUI [Drawers](https://www.untitledui.com/react/components/drawers) | The reader keeps their place while checking one item |
| N8 | Jump to a named item | Command menu with grouped results | UUI [Command menus](https://www.untitledui.com/react/components/command-menus) | Evidence is large; a challenger knows what they are looking for |

### 2.2 Judgement passages

| ID | Kind of information | Component | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| P1 | The bottom line | Inset banner on a DS card, not dismissible: lead sentence in the largest type, the rest below | SB [Banner](https://www.shadcnblocks.com/components/banner) (Inset), redrawn | The decision in one glance, before any figure |
| P2 | Key findings; a digest's numbered points | Numbered list panel: bold lead, body, trace control | SB [List Panel](https://www.shadcnblocks.com/components/list-panel) (Numbered), redrawn | Ordered and scannable; the number gives committee members something to cite |
| P3 | Contrary evidence | Warning-toned alert with a status shape, title and text, never dismissible | SB [Alert](https://www.shadcnblocks.com/components/alert), redrawn | The case against must look different from the case for, and cannot be scrolled past as body text |
| P4 | What would change the view | Standout callout, static | HUI [Toasts](https://www.hyperui.dev/components/application/toasts) (Standout, repurposed) | The trigger for changing their mind is the one passage they return to |
| P5 | Limitations | Collapsible card, open by default, with a count and a link to the gaps in Evidence | SB [Collapsible](https://www.shadcnblocks.com/components/collapsible) (Card), redrawn | Qualifications stay exact and in view; the count tells them how qualified the view is |
| P6 | For and against | Two-sided board: two equal columns of DS tiles, one side each, a figure and a qualifier tag per item | HUI [Grids](https://www.hyperui.dev/components/application/grids) (1x1) holding DS tiles | The debate as a picture; the reader sees the balance before reading either side |

### 2.3 Figures

| ID | Kind of information | Component | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| F1 | A headline figure | Metric tile, simple, in a joined strip; definition in a tooltip | UUI [Metrics](https://www.untitledui.com/react/components/metrics) (MetricsSimple) | Four to six numbers to scan before reading; no chart inside the tile |
| F2 | A measure over two periods with its consequence | Stat with delta, consequence sentence beneath | SB [Stat](https://www.shadcnblocks.com/components/stat) (Delta), redrawn | The change and what it means sit together |
| F3 | A change between two runs | Stat with a "from" value, then cause and effect | HUI [Stats](https://www.hyperui.dev/components/application/stats) (title, value, from value) | Before and after read left to right; the cause is one line away |
| F4 | Progress toward a stated total (modules delivered, spend against the cap) | Progress indicator: half circle for counts, bar for spend | UUI [Progress indicators](https://www.untitledui.com/react/components/progress-indicators) | A cap or a count is a part of a whole, not a trend |
| F5 | A small trend inside a row or tile | Sparkline, bar or line, no axes | SB [Sparkline](https://www.shadcnblocks.com/components/sparkline), redrawn on the chart base | Direction at a glance where a full chart would crowd the row |

### 2.4 Records

| ID | Kind of information | Component | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| R1 | A financial statement | Table with a sticky first column and an in-row sparkline; Bars or Figures toggle (N6) | HUI [Tables](https://www.hyperui.dev/components/application/tables) (Sticky first column) with F5 | A statement is a table by nature; the bars make it scannable without dropping a figure |
| R2 | Facts with a label | Details list, grouped by category | HUI [Details Lists](https://www.hyperui.dev/components/application/details-list) | Label and value pairs read faster than a three-column table |
| R3 | Questions and their answers | Accordion on native `details`, an answer-state badge on each row | HUI [Accordions](https://www.hyperui.dev/components/application/accordions) | The reader opens only the question they care about; the badge shows which were answered |
| R4 | Events with dates | Timeline, vertical, with the date on every entry and past, next and later marked by status shape | HUI [Timelines](https://www.hyperui.dev/components/application/timelines) (Vertical) | Past, next and later is how a watch date is used |
| R5 | Cause and effect | Step chain with title and description per step | HUI [Steps](https://www.hyperui.dev/components/application/steps) (grouped, title and description) | A pathway reads as a sequence; the relationship is the step text |
| R6 | Status of each item in a list | Status list in groups, one group per state with a count; read-only, no drag | SB [List](https://www.shadcnblocks.com/components/list) (Groups), redrawn | What is not met is one group at the top, not a column of words to scan |
| R7 | One module's state and lead sentence | DS tile: icon, title, lead sentence, a trailing status shape, in a group | SB [Item](https://www.shadcnblocks.com/components/item), redrawn | Thirteen modules become thirteen one-line tiles; a repeated state collapses to one tile with a count |
| R8 | An indicator to watch | Ticker row, static: indicator, threshold, leading or lagging icon | SB [Ticker](https://www.shadcnblocks.com/components/ticker), redrawn without live update | A watch list is a list of levels; the icon replaces the words "leading" and "lagging" |
| R9 | The named cases | Choice cards: one per case with its assumption and what it leaves out; choosing one sets the case every chart on the page shows | SB [Choicebox](https://www.shadcnblocks.com/components/choicebox), redrawn | The definitions double as the case switch, so the reader always knows which case they are looking at |
| R10 | An issuer and its latest run | DS card: header, content, footer | DS, layout checked against SB [Card](https://www.shadcnblocks.com/components/card) | A portfolio manager picks an issuer, not a run row |
| R11 | Runs or activity over time | Activity feed, connected | UUI [Activity feeds](https://www.untitledui.com/react/components/activity-feeds) (Connected) | History is a sequence with a state at each point |
| R12 | How a figure was derived | Tree with connectors: result, formula, inputs, source excerpt | UUI [Tree views](https://www.untitledui.com/react/components/tree-views) | A calculation is a tree; the challenger opens only the branch in doubt |
| R13 | Audit rows | Sortable table, dense | UUI [Tables](https://www.untitledui.com/react/components/tables) | Evidence only. Complete and sortable matters more here than airy |
| R14 | A file | File row: type icon, name, size, state | UUI [File uploaders](https://www.untitledui.com/react/components/file-uploaders) (list item) | The file the analyst uploaded looks the same when it is later cited |
| R15 | Who else (modules that read a file, sources that carried a story, who shared it) | Avatar group with initials and a +N count | UUI [Avatars](https://www.untitledui.com/react/components/avatars) (group) | A stack of initials replaces a sentence of names |
| R16 | A value to copy (a hash, an id) | Snippet with a copy button | SB [Snippet](https://www.shadcnblocks.com/components/snippet) (Copy), redrawn | Evidence only. Nobody retypes a hash |
| R17 | Spans on a time axis (module start to accepted; hedge expiries) | Gantt, timeline variant; read-only, no drag | SB [Gantt](https://www.shadcnblocks.com/components/gantt) (Timeline), redrawn | Overlap and order are visible without reading times |
| R18 | An outside story | Media object on a DS card: source monogram, then kind label, headline, source, time, summary, tags, actions | HUI [Media](https://www.hyperui.dev/components/application/media) (left, align top) | A story is somebody else's words; it must not look like an issuer card or a finding |
| R19 | A person or a group of people | Avatar with a title and a subtitle | UUI Avatars (label group) | The name chip, a group row and a member all read as "who", with the role beneath |
| R20 | Keywords and labels attached to something | Tag group, with a count where it helps | UUI [Tags](https://www.untitledui.com/react/components/tags) | A topic is its keywords; tags show the rule without a sentence |

### 2.5 Charts

Every chart sits in one frame: title, a Chart or Table toggle (N6), direct labels on the
values that matter, a legend only for two or more series, the module's basis note, one trace
control. The frame and base are UUI
[Line and bar charts](https://www.untitledui.com/react/components/line-bar-charts) (Recharts,
`charts-base`; ruling 2). The table form is R1's table without the sparkline. Forms no source
has are composed inside the frame.

| ID | Chart kind | Form | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| C1 | Grouped columns; recovery by class and case | Bar chart, grouped | UUI Line and bar charts (bar) | Amounts side by side on one zero baseline |
| C2 | Trend | Line chart, one series | UUI Line and bar charts (line) | One measure through time |
| C3 | Path | Line chart, several series, the last actual marked | UUI Line and bar charts (line, multiple) | Base against downside on the same axis |
| C4 | Stack | One horizontal stacked bar with a ranked legend | SB [Chart](https://www.shadcnblocks.com/components/chart) (bar, stacked), redrawn in the frame | Parts of a whole by rank; never a pie |
| C5 | Comparison | Small multiples of horizontal bars, one panel per measure | SB Chart (bar, multiple), redrawn in the frame | Each measure keeps its own scale, so no case is flattened |
| C6 | Bullet | Horizontal bar with a target line | SB Chart (target line), redrawn in the frame | Headroom is the distance to the line |
| C7 | Risk matrix (record shape) | Heat grid, three by three, items placed in cells | SB Chart (heatmap, repurposed), redrawn in the frame | Probability and impact as position, not two badge columns |
| C8 | Ranked thresholds (record shape) | Ranked bars | SB Chart (ranked bars), redrawn in the frame | The first break point is the longest bar |
| C9 | Scatter | Scatter with axis titles | Composed in the frame; no source page shows one without Chart.js | Two measures per issuer; outliers stand apart |
| C10 | Waterfall or bridge; cash flow walk | Floating columns to a total | Composed in the frame; in no source | Additive steps to a total |
| C11 | Dumbbell | Two marks joined by a line per row | Composed in the frame; in no source | Earlier against current when both are numbers |
| C12 | Range strip | A range bar with one marker | Composed in the frame; in no source | The issuer against the peer range |
| C13 | Limits | Bars with limit ticks | Composed in the frame; in no source | Exposure against each limit |
| C14 | Hedge | R17 (spans on a time axis) | SB Gantt, redrawn | Expiries are spans, not points |
| C15 | Pair tile | Two F1 metric tiles in one container | UUI Metrics | Two agencies' ratings are two headline figures |

A missing value in a chart is never drawn as zero:

- Sparkline (F5): the line breaks at the missing period and does not join across it; a bar
  sparkline leaves the slot empty.
- Bars and columns: no bar is drawn; "n.a." in the tertiary text colour sits at the baseline
  in the bar's place, and the category keeps its slot.
- Heat grid (C7): an item with a missing grade is listed beside the grid under "Not placed";
  an empty cell stays the card colour and never takes the lowest colour step.
- Lines (C2, C3): the line breaks; no point is interpolated.
- The table form shows "n.a." in the same cell.

### 2.6 Input and run

| ID | Kind of information | Component | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| I1 | Steps the analyst completes | Stepper, form wizard | SB [Stepper](https://www.shadcnblocks.com/components/stepper), redrawn | Five steps with the current one named; validation per step |
| I2 | Files to add | Drop zone with R14 rows and a progress bar | UUI [File uploaders](https://www.untitledui.com/react/components/file-uploaders) | Upload state per file, with retry |
| I3 | The purpose of a run | Radio cards with icon, title and description | UUI [Radio groups](https://www.untitledui.com/react/components/radio-groups) (Icon Card) | The purpose is a choice with consequences; the description states them |
| I4 | A decision that costs money or cannot be undone | Confirmation modal, warning style, stating the cap | UUI [Modals](https://www.untitledui.com/react/components/modals) | Submit stays an explicit act with the cost in front of it |
| I5 | Progress of a live run | Progress steps, vertical, one per module: complete, current, incomplete | UUI [Progress steps](https://www.untitledui.com/react/components/progress-steps) | Which module is running and how many are left |
| I6 | One pick from a list of named things (a group, a schedule, a length, a visibility) | Select | UUI [Select](https://www.untitledui.com/react/components/select) | A plain setting; it needs no description card |
| I7 | A conversation | Message list with a composer; no typing indicator | UUI [Messaging](https://www.untitledui.com/react/components/messaging) | Signal threads only; colleagues' words look like messages and nothing else does |
| I8 | Free text from the analyst | Text area with label and hint | UUI [Textareas](https://www.untitledui.com/react/components/textareas) | More context is optional; the hint says what helps |
| I9 | A rule that is on or off | Toggle with label and hint, one row per rule | UUI [Toggles](https://www.untitledui.com/react/components/toggles) | The label states the rule; the switch states whether it applies |

### 2.7 States and messages

| ID | Kind of information | Component | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| S1 | A state (of a run, a module, a source) | Status badge: a fixed shape, a colour and a word, always all three. Running is the CSS pulsing dot; queued is the CSS shimmer | DS status shapes on UUI Badges | Fixes the predecessor's colour-only fills; the shape survives grayscale |
| S2 | Nothing here yet, and what to do | Empty state: featured icon, title, text, one action | UUI [Empty states](https://www.untitledui.com/react/components/empty-states) | A blank page reads as broken; the reason reads as honest |
| S3 | A gap as a block: content or a chart not established for this run | Hatched dashed gap panel with the words and the module's stated reason | DS gap panel | Never an error colour: a gap is a fact about the run, shown where the content would have been |
| S4 | The system telling the reader something (cannot reach the service, run capped, run rejected) | Alert, floating, tone by severity, with an action | UUI [Alerts](https://www.untitledui.com/react/components/alerts) | Says what happened and what to do next |
| S5 | Content still loading | Skeleton in the shape of what will arrive, static | SB [Skeleton](https://www.shadcnblocks.com/components/skeleton), redrawn | No layout jump when content lands |
| S6 | An action was done | Toast, success | HUI Toasts (Success) | Confirms a copy or a save without a page change |
| S7 | Waiting with no known duration | Spinner with a label | UUI [Loading indicators](https://www.untitledui.com/react/components/loading-indicators) (line simple) | Says the page is working when no step count exists |

## 3. Screen by screen

### 3.1 Library

| Screen | Section | Kit |
| :--- | :--- | :--- |
| Every page | Area rail; run tabs; issuer and run identity | N1; N2; N4 |
| Library home | Search and filters; issuer cards with the latest lead sentence, as-of date, pathway and modules delivered (F4, bar); Cards or List | N5; R10; N6 |
| Library home | A run in progress; the list still loading | R10 with S1 (running); S7 |
| Report history | One entry per run: state, date, pathway, "what changed" link | R11 |
| Overview | Verdict panel | P1 |
| Overview | Metric strip | F1 |
| Overview | For-and-against board | P6 |
| Overview | Findings feed | P2 |
| Overview | Callout | P4 |
| Overview | Dated timeline | R4 |
| Overview | Module tiles | R7 |
| Overview | Limitations block | P5 |
| Changes | Change cards; a dumbbell when both values are numbers, Cards or Chart | F3; C11; N6 |
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
| Evidence | Summary: counts of modules, files, calculations, gaps | F4 |
| Evidence | Trace, with the calculation as the expanded row | R13 holding R12 |
| Evidence | Sources: file, readers, hash; "copied" confirmation | R14; R15; R16; S6 |
| Evidence | Gaps, grouped by severity | R13 |
| Evidence | Record: module timings; hashes and instructions; model calls; registers as written | R17; R16; R13 |
| Evidence | Module filter; jump to an item | N5; N8 |
| Trace drawer | Statement, then its derivation, then "Open in Evidence" | N7 holding R12 |

Evidence has five tabs (ruling 8): Summary, Trace, Sources, Gaps, Record. The trace control is
an icon-only badge with a tooltip (atoms), one per paragraph, row or figure, shown on hover
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
| Run start | Documents | I2 |
| Run start | Purpose | I3 |
| Run start | Confirm: the summary to approve | R2 |
| Run start | More context | I8 |
| Run start | Start | I4 |
| Run started panel | What will run and its cap | S4 (success) with F4 |
| Readiness side panel | Readiness items; the cap | R6; F4 |
| Run activity | Module progress; the running module; a queued module | I5; S1 (pulsing dot); S1 (shimmer) |
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
| Feed | New stories waiting | Pill, static, above the list; SB [Pill](https://www.shadcnblocks.com/components/pill), redrawn |
| Feed | Story cards | R18 |
| Feed | Loading; "Show older" | S5; a secondary button (atom) under the list, absent when nothing older exists |
| Story card | Kind label; topic tags | Badge (atom); R20 |
| Story card | Also in N other sources; "shared by" line | R15 |
| Story card | Signal strength (needs ruling) | SB [Rating](https://www.shadcnblocks.com/components/rating), read-only, three marks with a word, redrawn |
| Story card | AI "why it matters" line (needs ruling) | SB [Announcement](https://www.shadcnblocks.com/components/announcement), redrawn: an "AI" tag and one line |
| Story card | Regulatory case stage | HUI [Progress Bars](https://www.hyperui.dev/components/application/progress-bars) (with labels and status colours) |
| Story card | Rating move, from and to | UUI [Badge groups](https://www.untitledui.com/react/components/badge-groups): badge, arrow, badge |
| Group view | Group header with its members; its shared stories, each with its "shared by" line and comment count; New thread and Attach story for a writer | R19 with R15; R18; buttons (atoms) |
| Thread panel | Quoted story; comments and replies; composer | N7 holding R18 and I7 |
| Thread panel | Reactions | Pill with a count (as above) |
| Share to group | Pick a group, add a note | I4's modal holding I6 and I8 |
| Digest card and page (needs ruling) | Numbered points, each with the stories behind it, under an "AI" tag | P2 |
| Name dialog | Display name | UUI Modals holding a UUI [Input](https://www.untitledui.com/react/components/inputs) |
| Settings | Section list | N2 (vertical) |
| Settings | Groups: name and members; visibility | R19 with R15; I6 |
| Settings | Sources: kind, state, health, items per week | R13 with S1 and F5 |
| Settings | Thread rules; notifications | I9 |
| Settings | Topics: name, keywords, kinds | R20 |
| Settings | Digest form: covers, schedule, length, brief | I6; I8; UUI Inputs |
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
| module state | R7 | Twelve rows saying "Unchanged" |
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
| A failed or blocked module, "Not assessable" | A neutral badge with the slashed circle and one sentence saying why (DS), inside the module's R7 tile and at the top of its page | The tile keeps its place so the count of modules stays true |
| Missing versus zero | The text "n.a." in the tertiary text colour, right-aligned like a number; zero is the figure 0 | A text rule, not a component. Charts: section 2.5 |
| No earlier run | S2 | On Changes and on F3 |
| Long text | P5's collapsible after a set number of lines; prints open | Never truncates a qualification |
| Many modules | R7 collapses a repeated state to one tile with a count; N3 scrolls | |
| Run queued | S1 with the CSS shimmer where its result will appear | Loops only while the run is live |
| Run running | S1 with the CSS pulsing dot | Loops only while the run is live |
| Run finished | S1 | |
| Run failed, capped, rejected, interrupted | S1, each with its own shape and word, and S4 saying what happened and what to do | Four shapes and four words |
| Signal: no display name yet | The name dialog opens; the name chip (R19) reads "Set your name" | |
| Signal: reader or writer | A reader sees no write control at all (none is drawn disabled); the role sits under the name in R19 | |
| Signal: nothing followed, nothing saved, no approved source, no story yet, no story of the chosen kind, no search match | S2, one text each; "nothing followed" lists topics to follow | |
| Signal: loading; cannot reach the service | S5; S4 with Retry | |
| Signal: sources not checked yet | The freshness line (S1) in its neutral shape with those words | |
| Signal: new stories waiting | The static pill above the list | |
| Signal: older stories exist | "Show older" button under the list | |
| Signal: a story with no link or no time | R18 with a plain-text headline and no Open source action; the time is left out, not shown as "n.a." | |
| Signal: a source proposed, approved, paused, healthy, quiet or failing | S1, six shapes and words, in the sources table; failing shows its reason | |
| Signal: AI off or at its cap | S4 in settings; story cards carry no AI line; digests show as paused | |
| Signal: a digest with nothing material to report | The digest card with one sentence and no numbered list | No model call is made for it |
| Signal: an unread digest | A dot badge on its channel item (N1) and on the digest card | |
| Signal: comment edited, comment removed, thread archived | Inline text marks inside I7; an archived thread has no composer | |

## 6. Questions put to the owner, and the rulings

Thirteen questions were put at review 1. The owner accepted the recommended defaults; the
rulings are recorded in [decision 0003](../decisions/0003-design-track.md), which governs.
As they apply to this map:

| # | Question | Ruling |
| :--- | :--- | :--- |
| 1 | Charts need a library or hand drawing; six forms are in no source | Recharts through UUI `charts-base`, with the missing forms composed inside it. It needs its own decision record at D2a and must pass the open-from-disk check first |
| 2 | "The page computes no figure" against chart scales and animated counters | Chart positions may be computed from given values. No animated numerals |
| 3 | "Motion only for live state" against drawer, tab and accordion transitions | One-off transitions up to 200 ms; only live run state loops; all off under reduced motion |
| 4 | One trace control per paragraph, row and figure | Shown on hover and keyboard focus, always on touch, with a page-level "Show sources" switch |
| 5 | "Every chart has a table form" against "no repeated plain table" | The table is the other side of the Chart or Table toggle |
| 6 | Evidence has seven tabs | Five: Summary, Trace with calculations, Sources, Gaps, Record with registers; nothing removed |
| 7 | The Model's own Evidence and Limitations pages | The Model links to the run's Evidence instead of its own |
| 8 | Limitations open or collapsed | Open by default |
| 9 | Signal cannot open from `file://` | A separate served page outside the open-from-disk rule and its gate |
| 10 | Which Signal screens to mock | Every designed screen; parts needing paid model calls are marked as needing a ruling |
| 11 | Two primitive libraries | React Aria only. Shadcnblocks pieces are redrawn on it; Radix and Base UI are not added |
| 12 | Unused sources | Flowbite React, Ant Design, Preline and Uiverse are unused. React Bits is also unused: its licence forbids redistribution and this repository is public; animations are CSS written here |
| 13 | Three alert-shaped components (P3, P4, S4) | Kept as mapped; contrary evidence moves into P6 on module pages if the mocks cannot make the three plainly different |

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
  an "AI" tag so that it is not read as a module's finding.
- **F4 (progress indicator)** serves counts of a total and spend against a cap.
- **I6 (select)** serves group, schedule, length and visibility. All are one pick from a list.

Other fragile choices to test in the mocks and at D2a:

- Every SB component is redrawn on React Aria from its page; the effort per component is not
  estimated, and R6 and R17 lose their drag behaviour by design.
- R8 (ticker) and C7 (heatmap) are repurposed from live prices and a week-by-hour grid.
- P1 (banner) and P4 (toast) are repurposed from announcements and notifications.
- P6 is two columns of tiles and has no source component of its own.
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
- The design system file is on another branch; this map was aligned to it as the coordinator
  described and as its headings read on 2026-11-13, not line by line.

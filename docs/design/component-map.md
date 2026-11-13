# Component map

Step D0b of the [design track](../superpowers/plans/2026-11-13-design-track.md), written
2026-11-13. It maps every screen, section, record shape, chart kind and state in the
[screen inventory](screen-inventory.md) to one component from an approved
[source](component-sources.md). It is a proposal for the owner's first review; nothing here
is built.

## How to read it

- **One kind of information, one component.** Section 2 is the kit: each row is one kind of
  information and the single component that presents it. The same kind on two screens uses
  the same component; two different kinds never share one.
- **Atoms are exempt.** Badge, icon, tooltip, button and the state mark are parts used inside
  components, not presentations of a kind of information.
- **The reader** is a portfolio manager or credit committee member who has not read the
  sources. They decide first (findings pages) and challenge second (Evidence). "Why" columns
  are written for that reader.
- **Read** means the component's own live page was opened on 2026-11-13. Section 7 lists what
  could not be read.
- Sources are abbreviated: **UUI** Untitled UI React, **SB** shadcnblocks, **RB** React Bits,
  **HUI** HyperUI. Flowbite React, Preline, Uiverse and the Ant Design grid are not used
  (section 7 says why).

## 1. What the live pages changed

Reading the pages overturned five assumptions carried from the predecessor's map:

1. SB "Comparison" is a before-and-after image slider. It is not a two-sided board.
2. HUI charts load Chart.js from a CDN and draw to a canvas. They break the content security
   policy and are not used. Their hidden data table per chart is the pattern to keep.
3. UUI and SB charts are both Recharts. No approved source ships a waterfall, bullet,
   dumbbell, range strip, limit-tick bar or node-and-link diagram (question 1).
4. RB "Status Mark" has idle, progress and done. It has no failed state.
5. SB "List" is a draggable status list in groups, not a plain list.

## 2. The kit

### 2.1 Navigation and shell

| ID | Kind of information | Component | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| N1 | Which application area | Sidebar navigation: slim icon rail; dual-tier where an area has channels (Signal) | UUI [Sidebar navigations](https://www.untitledui.com/react/components/sidebar-navigations) | Four areas need four icons, not a menu bar; counts sit on the item |
| N2 | Which page of a run, of the Model, or of Evidence | Tabs, underline, with a count badge where a tab holds a list | UUI [Tabs](https://www.untitledui.com/react/components/tabs) | The reader always sees the five places a run has and how much is in each |
| N3 | Where in a long module page | Vertical menu with icons and an active left border | HUI [Vertical Menu](https://www.hyperui.dev/components/application/vertical-menu) | A module is long; the index shows the judgement sections first |
| N4 | Which issuer and run this is | Page header: issuer name large, then as-of date, pathway and state as badges | UUI [Page headers](https://www.untitledui.com/react/components/page-headers) with [Badges](https://www.untitledui.com/react/components/badges) | The run code is an audit key and stays in Evidence; the reader needs issuer and date |
| N5 | Narrowing a list | Filter bar: search, dropdown filters, applied count | UUI [Filter bars](https://www.untitledui.com/react/components/filter-bars) | One control row instead of five selects |
| N6 | Two presentations of the same content | Segmented toggle (Chart or Table, Cards or List, Bars or Figures) | UUI [Button groups](https://www.untitledui.com/react/components/button-groups) | Lets the reader pick the form they trust without leaving the page |
| N7 | A detail beside the page | Slide-out drawer with header, body and pinned footer | UUI [Drawers](https://www.untitledui.com/react/components/drawers) | The reader keeps their place while checking one item |
| N8 | Jump to a named item | Command menu with grouped results | UUI [Command menus](https://www.untitledui.com/react/components/command-menus) | Evidence is large; a challenger knows what they are looking for |

### 2.2 Judgement passages

| ID | Kind of information | Component | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| P1 | The bottom line | Inset banner, not dismissible: lead sentence in the largest type, the rest below | SB [Banner](https://www.shadcnblocks.com/components/banner) (Inset) | The decision in one glance, before any figure |
| P2 | Key findings; a digest's numbered points | Numbered list panel: bold lead, body, trace control | SB [List Panel](https://www.shadcnblocks.com/components/list-panel) (Numbered) | Ordered and scannable; the number gives committee members something to cite |
| P3 | Contrary evidence | Warning-toned alert with icon, title and text, never dismissible | SB [Alert](https://www.shadcnblocks.com/components/alert) | The case against must look different from the case for, and cannot be scrolled past as body text |
| P4 | What would change the view | Standout callout, static | HUI [Toasts](https://www.hyperui.dev/components/application/toasts) (Standout, repurposed) | The trigger for changing their mind is the one passage they return to |
| P5 | Limitations | Collapsible card, open by default, with a count and a link to the gaps in Evidence | SB [Collapsible](https://www.shadcnblocks.com/components/collapsible) (Card) | Qualifications stay exact and in view; the count tells them how qualified the view is |
| P6 | For and against | Two-sided board on a centre line: one side each, a figure and a qualifier tag per item | HUI [Timelines](https://www.hyperui.dev/components/application/timelines) (Vertical with middle line, repurposed) | The debate as a picture; the reader sees the balance before reading either side |

### 2.3 Figures

| ID | Kind of information | Component | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| F1 | A headline figure | Metric card, simple, in a joined strip; definition in a tooltip | UUI [Metrics](https://www.untitledui.com/react/components/metrics) (MetricsSimple) | Four to six numbers to scan before reading; no chart inside the tile |
| F2 | A measure over two periods with its consequence | Stat with delta, consequence sentence beneath | SB [Stat](https://www.shadcnblocks.com/components/stat) (Delta) | The change and what it means sit together |
| F3 | A change between two runs | Stat with a "from" value, then cause and effect | HUI [Stats](https://www.hyperui.dev/components/application/stats) (title, value, from value) | Before and after read left to right; the cause is one line away |
| F4 | Progress toward a stated total (modules delivered, spend against the cap) | Progress indicator: half circle for counts, bar for spend | UUI [Progress indicators](https://www.untitledui.com/react/components/progress-indicators) | A cap or a count is a part of a whole, not a trend |
| F5 | A small trend inside a row or tile | Sparkline, bar or line, no axes | SB [Sparkline](https://www.shadcnblocks.com/components/sparkline) | Direction at a glance where a full chart would crowd the row |

### 2.4 Records

| ID | Kind of information | Component | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| R1 | A financial statement | Table with a sticky first column and an in-row sparkline; Bars or Figures toggle (N6) | HUI [Tables](https://www.hyperui.dev/components/application/tables) (Sticky first column) with F5 | A statement is a table by nature; the bars make it scannable without dropping a figure |
| R2 | Facts with a label | Details list, grouped by category | HUI [Details Lists](https://www.hyperui.dev/components/application/details-list) | Label and value pairs read faster than a three-column table |
| R3 | Questions and their answers | Accordion on native `details`, an answer-state badge on each row | HUI [Accordions](https://www.hyperui.dev/components/application/accordions) | The reader opens only the question they care about; the badge shows which were answered |
| R4 | Events with dates | Timeline with done, current and upcoming states | SB [Timeline](https://www.shadcnblocks.com/components/timeline) (Activity) | Past, next and later is how a watch date is used |
| R5 | Cause and effect | Step chain with title and description per step | HUI [Steps](https://www.hyperui.dev/components/application/steps) (grouped, title and description) | A pathway reads as a sequence; the relationship is the step text |
| R6 | Status of each item in a list | Status list in groups, one group per state with a count, drawn read-only | SB [List](https://www.shadcnblocks.com/components/list) (Groups) | What is not met is one group at the top, not a column of words to scan |
| R7 | One module's state and lead sentence | Item with icon, title, description and a trailing state mark, in a group | SB [Item](https://www.shadcnblocks.com/components/item) with [Status](https://www.shadcnblocks.com/components/status) | Thirteen modules become thirteen one-line tiles; a repeated state collapses to one tile with a count |
| R8 | An indicator to watch | Ticker row, static: indicator, threshold, leading or lagging icon | SB [Ticker](https://www.shadcnblocks.com/components/ticker) (repurposed, no live update) | A watch list is a list of levels; the icon replaces the words "leading" and "lagging" |
| R9 | The named cases | Choice cards: one per case with its assumption and what it leaves out; choosing one sets the case every chart on the page shows | SB [Choicebox](https://www.shadcnblocks.com/components/choicebox) | The definitions double as the case switch, so the reader always knows which case they are looking at |
| R10 | An issuer and its latest run | Card: header, content, footer | SB [Card](https://www.shadcnblocks.com/components/card) (Standard) | A portfolio manager picks an issuer, not a run row |
| R11 | Runs or activity over time | Activity feed, connected | UUI [Activity feeds](https://www.untitledui.com/react/components/activity-feeds) (Connected) | History is a sequence with a state at each point |
| R12 | How a figure was derived | Tree with connectors: result, formula, inputs, source excerpt | UUI [Tree views](https://www.untitledui.com/react/components/tree-views) | A calculation is a tree; the challenger opens only the branch in doubt |
| R13 | Audit rows | Sortable table, dense | UUI [Tables](https://www.untitledui.com/react/components/tables) | Evidence only. Complete and sortable matters more here than airy |
| R14 | A file | File row: type icon, name, size, state | UUI [File uploaders](https://www.untitledui.com/react/components/file-uploaders) (list item) | The file the analyst uploaded looks the same when it is later cited |
| R15 | Who else (modules that read a file, sources that carried a story) | Avatar group with initials and a +N count | UUI [Avatars](https://www.untitledui.com/react/components/avatars) | A stack of initials replaces a sentence of names |
| R16 | A value to copy (a hash, an id) | Snippet with a copy button | SB [Snippet](https://www.shadcnblocks.com/components/snippet) (Copy) | Evidence only. Nobody retypes a hash |
| R17 | Spans on a time axis (module start to accepted; hedge expiries) | Gantt, timeline variant, read-only | SB [Gantt](https://www.shadcnblocks.com/components/gantt) (Timeline) | Overlap and order are visible without reading times |

### 2.5 Charts

Every chart sits in one frame: title, a Chart or Table toggle (N6), direct labels on the
values that matter, a legend only for two or more series, the module's basis note, one trace
control. The frame and base are UUI
[Line and bar charts](https://www.untitledui.com/react/components/line-bar-charts) (Recharts,
`charts-base`). The table form is R1's table without the sparkline.

| ID | Chart kind | Form | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| C1 | Grouped columns; recovery by class and case | Bar chart, grouped | UUI Line and bar charts (bar) | Amounts side by side on one zero baseline |
| C2 | Trend | Line chart, one series | UUI Line and bar charts (line) | One measure through time |
| C3 | Path | Line chart, several series, the last actual marked | UUI Line and bar charts (line, multiple) | Base against downside on the same axis |
| C4 | Stack | One horizontal stacked bar with a ranked legend | SB [Chart](https://www.shadcnblocks.com/components/chart) (bar, stacked) | Parts of a whole by rank; never a pie |
| C5 | Comparison | Small multiples of horizontal bars, one panel per measure | SB Chart (bar, multiple) | Each measure keeps its own scale, so no case is flattened |
| C6 | Bullet | Horizontal bar with a target line | SB Chart (target line) | Headroom is the distance to the line |
| C7 | Risk matrix (record shape) | Heat grid, three by three, items placed in cells | SB Chart (heatmap, repurposed) | Probability and impact as position, not two badge columns |
| C8 | Ranked thresholds (record shape) | Ranked bars | SB Chart (ranked bars) | The first break point is the longest bar |
| C9 | Scatter | Scatter with axis titles | Composed in the frame from Recharts; no source page shows one without Chart.js | Two measures per issuer; outliers stand apart |
| C10 | Waterfall or bridge; cash flow walk | Floating columns to a total | Composed in the frame; in no source | Additive steps to a total |
| C11 | Dumbbell | Two marks joined by a line per row | Composed in the frame; in no source | Earlier against current when both are numbers |
| C12 | Range strip | A range bar with one marker | Composed in the frame; in no source | The issuer against the peer range |
| C13 | Limits | Bars with limit ticks | Composed in the frame; in no source | Exposure against each limit |
| C14 | Hedge | R17 (spans on a time axis) | SB Gantt | Expiries are spans, not points |
| C15 | Pair tile | Two F1 metric cards in one container | UUI Metrics | Two agencies' ratings are two headline figures |

### 2.6 Input and run

| ID | Kind of information | Component | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| I1 | Steps the analyst completes | Stepper, form wizard | SB [Stepper](https://www.shadcnblocks.com/components/stepper) | Five steps with the current one named; validation per step |
| I2 | Files to add | Drop zone with R14 rows and a progress bar | UUI [File uploaders](https://www.untitledui.com/react/components/file-uploaders) | Upload state per file, with retry |
| I3 | One choice among a few | Radio cards with icon, title and description | UUI [Radio groups](https://www.untitledui.com/react/components/radio-groups) (Icon Card) | The purpose of a run is a choice with consequences; the description states them |
| I4 | A decision that costs money or cannot be undone | Confirmation modal, warning style, stating the cap | UUI [Modals](https://www.untitledui.com/react/components/modals) | Submit stays an explicit act with the cost in front of it |
| I5 | Progress of a live run | Progress steps, vertical, one per module: complete, current, incomplete | UUI [Progress steps](https://www.untitledui.com/react/components/progress-steps) | Which module is running and how many are left |
| I6 | The running module | Lattice loader with its stopwatch, beside the current step | RB [Lattice Loader](https://reactbits.dev/micro/lattice-loader) | The one place motion earns its keep: proof the run is alive |
| I7 | Activity lines arriving | Animated list, only while the run is live | RB [Animated List](https://reactbits.dev/components/animated-list) | New lines announce themselves; a finished run shows a still list |
| I8 | A conversation | Message list with a composer | UUI [Messaging](https://www.untitledui.com/react/components/messaging) | Signal threads only; colleagues' words look like messages and nothing else does |

### 2.7 States and messages

| ID | Kind of information | Component | Source (read) | Why it fits the reader |
| :--- | :--- | :--- | :--- | :--- |
| S1 | A state (of a run, a module, a source) | State mark: icon, colour and a word, always all three | SB [Status](https://www.shadcnblocks.com/components/status); RB [Status Mark](https://reactbits.dev/micro/status-mark) for queued, running and finished only | Fixes the predecessor's colour-only fills |
| S2 | Nothing here, and why | Empty state: featured icon, title, text, one action | UUI [Empty states](https://www.untitledui.com/react/components/empty-states) | A blank page reads as broken; the reason reads as honest |
| S3 | A chart that could not be drawn | Empty chart inside the chart frame, with the module's stated reason | SB [Empty](https://www.shadcnblocks.com/components/empty) (Data 2, empty chart) | The reader sees what is missing where it would have been |
| S4 | The system telling the reader something (cannot reach the service, run capped, run rejected) | Alert, floating, tone by severity, with an action | UUI [Alerts](https://www.untitledui.com/react/components/alerts) | Says what happened and what to do next |
| S5 | Content still loading | Skeleton in the shape of what will arrive | SB [Skeleton](https://www.shadcnblocks.com/components/skeleton) | No layout jump when content lands |
| S6 | An action was done | Toast, success | HUI Toasts (Success) | Confirms a copy or a save without a page change |
| S7 | Waiting with no known duration | Spinner with text | HUI [Loaders](https://www.hyperui.dev/components/application/loaders) (Spinner with text) | Pure Tailwind classes; a named Uiverse loader can replace it at D1c |

## 3. Screen by screen

### 3.1 Library

| Screen | Section | Kit |
| :--- | :--- | :--- |
| Every page | Area rail; run tabs; issuer and run identity | N1; N2; N4 |
| Library home | Search and filters; issuer cards with the latest lead sentence, as-of date, pathway and modules delivered (F4, bar); Cards or List | N5; R10; N6 |
| Library home | A run in progress | R10 with S1 and I6 |
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
| Evidence | Summary: counts of modules, files, calculations, gaps | F4 |
| Evidence | Trace; gaps (grouped by severity); registers as written | R13 |
| Evidence | Sources: file, readers, hash | R14; R15; R16 |
| Evidence | Calculations | R12 |
| Evidence | Record: module timings; hashes and instructions; model calls | R17; R16; R13 |
| Evidence | Module filter; jump to an item | N5; N8 |
| Trace drawer | Statement, then its derivation, then "Open in Evidence" | N7 holding R12 |

The trace control is an icon-only badge with a tooltip (atoms), one per paragraph, row or
figure.

### 3.2 Model and Forecast

| Screen | Section | Kit |
| :--- | :--- | :--- |
| Model shell | Front Page, Analysis, Model, Portfolio Fit, Evidence, Limitations | N2 |
| Front Page | Bottom line; headline figures | P1; F1 |
| Analysis | Passages | P2 to P5 |
| Model | Statements | R1 |
| Model | Bridges; cash flow section | C10 |
| Model | Case comparison; the cases themselves | C5; R9 |
| Portfolio Fit | Exposure against limits; agency ratings | C13; C15 |
| Evidence; Limitations | As the library | 3.1; P5 |
| Forecast | Cases and their drivers | R9; C12 for a driver against its range |
| Forecast | Trend line; paths by case | C2; C3 |

### 3.3 Run

| Screen | Section | Kit |
| :--- | :--- | :--- |
| Run start | Steps Documents, Purpose, Confirm, More context, Start | I1 |
| Run start | Documents | I2 |
| Run start | Purpose | I3 |
| Run start | Confirm: the summary to approve | R2 |
| Run start | More context | Text area from the base layer (UUI Textareas; listed in the index, page not opened) |
| Run start | Start | I4 |
| Run started panel | What will run and its cap | S4 (success) with F4 |
| Readiness side panel | Readiness items; the cap | R6; F4 |
| Run activity | Module progress; the running module; activity lines; spend against the cap | I5; I6; I7; F4 |

### 3.4 Signal

| Screen | Section | Kit |
| :--- | :--- | :--- |
| Feed | Area rail and channel list (views, topics, groups, digests) with unread counts | N1 (dual-tier) |
| Feed | Kind filter and search | N5 |
| Feed | Top or Latest | N6 |
| Feed | Freshness line | S1 |
| Feed | New stories waiting | SB [Pill](https://www.shadcnblocks.com/components/pill) with its pulsing indicator (live state) |
| Feed | Story card: kind, headline, source, time, summary, tags, actions | R10 |
| Story card | Also in N other sources | R15 |
| Story card | Signal strength | SB [Rating](https://www.shadcnblocks.com/components/rating), read-only, three marks, with a word |
| Story card | AI "why it matters" line | SB [Announcement](https://www.shadcnblocks.com/components/announcement): an "AI" tag and one line |
| Story card | Regulatory case stage | HUI [Progress Bars](https://www.hyperui.dev/components/application/progress-bars) (with labels and status colours) |
| Story card | Rating move, from and to | UUI [Badge groups](https://www.untitledui.com/react/components/badge-groups): badge, arrow, badge |
| Digest card and page | Numbered points, each with the stories behind it, under an "AI" tag | P2 |
| Thread panel | Quoted story; comments and replies; composer | N7 holding I8 |
| Thread panel | Reactions | SB Pill with a count |
| Share to group | Pick a group, add a note | I4's modal holding I3 (Avatar variant) |
| Name dialog | Display name | UUI Modals (input field) |
| Settings | Section list | N2 (vertical) |
| Settings | Groups: members, visibility | R7; R15; I3 |
| Settings | Sources: kind, state, health | R13 with S1 and F5 |
| Settings | Thread rules; notifications | Toggle rows from the base layer (UUI Toggles; listed in the index, page not opened) |
| Settings | Topics | R2 with tags |
| Settings | Digest form | I3 for schedule and length; base-layer inputs |
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

| State | Kit | Notes |
| :--- | :--- | :--- |
| No runs yet | S2 | Action: start a run |
| A gap, "Not established for this run" | Inline: a badge with an icon and those words in place of the value; S3 when it is a chart | Never an empty cell |
| A withheld value | Inline: a lock-icon badge "Withheld", the reason in a tooltip | Distinct from a gap in icon and word |
| A failed or blocked module, "Not assessable" | S2 inside the module's tile and page, with the stated reason | The tile keeps its place so the count of modules stays true |
| Missing versus zero | The text "n.a." in the muted text colour; zero is the figure 0 | A text rule, not a component |
| No earlier run | S2 | On Changes and on F3 |
| Long text | SB Collapsible (text) after a set number of lines; prints open | Never truncates a qualification |
| Many modules | R7 collapses a repeated state to one tile with a count; N3 scrolls | |
| Run queued | S1 (RB Status Mark, idle ring) | |
| Run running | S1 (RB Status Mark, progress) with I6 | The only looping motion |
| Run finished | S1 (RB Status Mark, check) | |
| Run failed, capped, rejected, interrupted | S1 (SB Status with an icon and the word) and S4 saying what happened and what to do | Four different icons and words; RB Status Mark has no failed state |
| Signal: no name, nothing followed, nothing saved, no source, no story, no match | S2, one text each | |
| Signal: loading; cannot reach the service; new stories waiting | S5; S4; the Pill above | |
| Signal: AI off or at its cap | S4 in settings; cards simply carry no AI line | |
| Signal: comment edited, comment removed, thread archived | Inline text marks inside I8 | |

## 6. Questions for the owner

Each is a place where a rule in the inventory, or a limit of the sources, pulls against the
better design. The recommendation is the coordinator-facing default if the owner says nothing.

1. **Charts need a library or hand drawing.** The only usable charts in the eight sources are
   Recharts (a new dependency needing a decision record). Five chart kinds (waterfall, dumbbell,
   range strip, limits, scatter) and the pathway diagram are in no source. May they be composed
   inside the adopted chart frame, or does "only from the eight sources" forbid that?
   Recommend: adopt Recharts through UUI `charts-base`; compose the missing forms in its frame.
2. **"The page computes no figure" against charts and counters.** A chart library computes
   scales and positions from the values it is given. An animated counter (RB Count Up) shows
   numbers that are not in the data while it runs. Recommend: positions are allowed; no
   animated numerals anywhere, so Count Up is not used.
3. **"Motion only for live state" against a modern feel.** A drawer that slides, a tab
   indicator that moves and an accordion that opens are motion. Recommend: one-off transitions
   up to 200 ms are allowed; nothing loops except live run state; all off under reduced motion.
4. **One trace control per paragraph, row and figure** puts dozens of icons on an airy page.
   Recommend: the control shows on hover and keyboard focus, and always on touch; a page-level
   "Show sources" switch pins them all on.
5. **"Every chart has a table form" against "no repeated plain table".** Recommend: the table
   is the other side of the Chart or Table toggle and is the only place a findings page shows
   a plain table, apart from statements.
6. **Evidence has seven tabs.** Recommend five: Summary, Trace (with calculations as the
   expanded row), Sources, Gaps, Record (with registers). Fewer places to look, nothing removed.
7. **The Model has its own Evidence and Limitations pages** beside the library's. Recommend:
   the Model links to the run's Evidence filtered to the model, and shows limitations as P5.
8. **Limitations: always open, or collapsed behind a count?** Recommend open by default, as
   mapped, because a qualification the reader did not see is a defect.
9. **Signal cannot open from `file://`.** It polls a local service, keeps a name in a cookie
   and writes saves and comments. Is Signal a separate served page with its own policy, outside
   the open-from-disk rule and its gate?
10. **Signal's AI line, signal strength and digests need paid model calls** and a ruling with
    a cap, and Signal's back end is not planned. Should D1d mock the designed screens (threads,
    share, digests, settings, AI fields) or only what the predecessor built (feed, name dialog)?
    Recommend: mock all, mark the AI parts as "needs ruling".
11. **Two primitive libraries.** UUI is built on React Aria; every SB component is built on
    Radix or Base UI. The map uses 22 SB components. Allow Radix beside React Aria (a second
    dependency record), or redraw the SB pieces on React Aria? SB's free and paid tiers are
    not marked per component on its pages.
12. **Four sources are unused**: Flowbite React and Ant Design are npm packages with nothing
    the kit lacks; the Preline blocks that fit are paid or need its script; Uiverse loaders
    have no names to cite. Confirm that is acceptable.
13. **Three alert-shaped components** (P3 contrary evidence, P4 what would change the view,
    S4 system messages) come from three sources so that each kind has its own, but they share
    an anatomy. If the mocks cannot make them plainly different, should contrary evidence move
    into the two-sided board (P6) on module pages?

## 7. Not read, and fragile choices

Not read:

- Flowbite React: only its Timeline page opened, after a browser check; other pages returned
  429. Not used.
- Uiverse loaders: the page lists 1,218 CSS and Tailwind loaders by author with no names; no
  loader's code was opened. Not used; S7 is the stand-in.
- Preline: `preline.co/blocks` returns 404; `preline.co/examples.html` and five block pages
  under `/blocks/data-display/` were read. Not used.
- Ant Design grid: read (24 columns, six breakpoints). Not used; Tailwind's grid covers layout.
- UUI Textareas, Toggles, Inputs, Buttons, Tags, Select and Card headers: named in the index
  page, their own pages not opened.
- React Bits pages state no props, dependencies or licence; those need the source on GitHub.

Fragile choices to test in the mocks and at D2a:

- R6 (SB List) and R17 (SB Gantt) are drag-and-drop components drawn read-only; their pages
  do not confirm a read-only mode or name their drag library.
- R8 (SB Ticker) and C7 (SB heatmap) are repurposed from live prices and a week-by-hour grid.
- P1 (SB Banner) and P4 (HUI Toast) are repurposed from announcements and notifications.
- R2 serves both facts and default records, as one kind (label and value).
- UUI Notifications needs Sonner and UUI Code snippets needs Shiki; both are avoided (S6 and
  R16 instead).

## Not verified

- No component was installed, built or opened from disk; whether each passes the content
  security policy is unknown until D2a.
- Licences and paid tiers: SB and UUI pages do not mark them per component; none was read
  from a licence text.
- Pages were read through a summarising fetch, not by eye; variant names are as it reported.
- Kinds of information were derived from the inventory and the predecessor's map, not from
  every run; a shape not listed falls to R2.
- Whether SB components work without Radix, and whether Recharts runs under the policy.

# Run mocks

Step D1c of the [design track plan](../../superpowers/plans/2026-11-13-design-track.md),
drawn 2026-11-13 and revised the same day to [design system](../design-system.md) 0.7 and the
[component map](../component-map.md) as merged at `c620c79`.
[Decision 0003](../../decisions/0003-design-track.md) governs, including "Source look" and its
rulings at review 2, cited below as "review 2, ruling n".
Nothing here is built; no file under `web/` was touched.

**Claude Design project:** [Run mocks](https://claude.ai/design/p/3fb77bd2-6b91-490c-98d1-55d7a7dfe794)

- [Run start](https://claude.ai/design/p/3fb77bd2-6b91-490c-98d1-55d7a7dfe794?file=Run+start.dc.html): 8 frames.
- [Run activity](https://claude.ai/design/p/3fb77bd2-6b91-490c-98d1-55d7a7dfe794?file=Run+activity.dc.html): 11 frames.
- `run.css`: the shared stylesheet. Tokens, status shapes, status sets and motion are copied
  from the design system; each source component's block names its source and the sizes it
  copies.

Standalone Claude Design has announced that its tools stop working by 2026-12-14. The three
files are plain HTML and CSS and can be exported from the project before then.

Sample content is the public TransDigm case. File names, purposes, module names, times and
amounts are illustrative. The logo is a striped placeholder; icons are outlined placeholder
squares, because the icon set comes only through its npm package (review 1, ruling 5).

## Screens and states drawn

### Run start

| Frame | Screen or state | Kit |
| :--- | :--- | :--- |
| 01 | Documents, no documents yet. Next is unavailable | I1, I2, S2 |
| 02 | Documents with files in all four file states: two read in full, one uploading, one read in part with its sentence, one unreadable with its reason and "Replace file" | I2, R14, F4 |
| 03 | Purpose: three radio cards, one chosen, each stating what it runs | I3 |
| 04 | Confirm: the summary awaiting the analyst's approval, grouped Issuer, Documents, Run, with one "n.a." | R2, S1 |
| 05 | More context: optional free text | I8 |
| 06 | Start: Submit, the paid action | R2, button |
| 07 | Start, confirmation: the warning modal stating the cap | I4 |
| 08 | Run started: what will run and its cap, with a link to Run activity | S4 (info) with F4 |

The readiness side panel is on every frame: "Not met" (triangle) above "Met" (filled circle),
each with a count, then the cap as a progress bar (R6, F4). It is drawn with four items unmet
(frame 01), three (frame 02), one (frames 03 and 04) and none (frames 05 to 08). The slim area rail (N1) is on every frame.

Submit looks like the paid action in three ways: it is the only extra-large button on the
page, its label states the amount ("Submit, spend up to USD 20.00"), and a heading above it
says that it starts a paid run. "Approve summary" on Confirm is an ordinary button and its
panel says approving costs nothing. The modal repeats the cap and is used nowhere else.
`CLAUDE.md` lets Submit start a paid run only under an owner ruling in `docs/decisions/` that
names its cap; the mock draws the USD 20 cap of decision 0002 and assumes that ruling
(question 6).

### Run activity

| Frame | Run state or screen | What it shows |
| :--- | :--- | :--- |
| 01 | Running | 5 finished, 1 running, 7 queued; spend, modules and elapsed; the activity feed |
| 02 | Queued | Every module queued; spend 0.00; elapsed "n.a." |
| 03 | Running, before the first module reports | The spinner with its label (S7); modules "n.a." |
| 04 | Finished | 12 finished and one "Not assessable" with its sentence; "Open the library" |
| 05 | Failed | Alert, the module that stopped, the rest "Not run" |
| 06 | Capped | Alert, a full spend bar, one module stopped part-way, three "Not run" |
| 07 | Rejected | Alert, nothing ran, an empty state in the module panel |
| 08 | Interrupted | Alert, the module that was running, the rest "Not run" |
| 09 | Running, many modules (22) | Finished modules collapsed to one step with a count; three queued shown; the rest collapsed |
| 10 | No run | Empty state with "Start a run" (S2) |
| 11 | Activity cannot be read | "State not known" in place of the run-state badge; alert with "Try again", over a static skeleton (S4, S5) |

Every frame with a run has the page heading (issuer, run-state badge, purpose and as-of
labels), a summary of spend against the cap, modules finished of modules planned, and elapsed
time (F4), module progress as vertical progress steps (I5) with a status badge per module
(S1), and the connected activity feed (R11). The seven run-state badges are also shown
together at the top of the page.

Run states use the design system's shapes: Queued ring, Running half-filled circle, Finished
filled circle, Failed diamond, Capped triangle, Rejected cross, Interrupted pause bars, each
with its word.

The other states use the design system 0.7 sets (review 2, ruling 7):

| Set | Where | As drawn |
| :--- | :--- | :--- |
| File state | Run start, frame 02 | Uploading: half-filled circle, action. Read in full: filled circle, success. Read in part: triangle, warning. Unreadable: diamond, error, with the reason in the sentence beside it |
| Approval | Run start, frame 04 | Awaiting your approval: half-filled circle, info |
| Module state | Run activity, frames 04 to 06 and 08 | Not assessable: slashed circle, neutral. Not run, only in a run that has ended: ring, neutral |
| Activity that cannot be read | Run activity, frame 11 | State not known: dashed ring in the gap colours, where the run-state badge would be |

"Unreadable" is the one word for a file, whether it could not be read or was refused at run
start; "Rejected" and the cross stay the run's. "Delivered with gaps" is not drawn on these
screens.

No trace control appears on either page. Where one appears elsewhere it is always shown on a
touch device (design system, "Trace control").

Motion, checked in the rendered page: the halo on the half-filled circle, the shimmer on a
queued module and the spinner animate only inside frames 01, 02, 03 and 09 (the live ones).
No element animates in any other frame or anywhere on Run start. The newest activity line
rises in once, 200 ms. No numeral animates. All of it sits under
`prefers-reduced-motion: no-preference`.

No module code or method step identifier appears on either page.

## Source pages read

Read 2026-11-13 from the live page and, where it is public, the component's source:

| Kit | Source | Variant copied |
| :--- | :--- | :--- |
| N1 | Untitled UI sidebar navigations | Slim rail: 68 wide, 36 items, radius 6 |
| I1 | shadcnblocks stepper | `stepper-form-1`: 28 indicator, 2 border, 1 separator, title beside |
| I2, R14 | Untitled UI file uploaders | Drop zone and progress-bar file row |
| I3 | Untitled UI radio groups | Icon card: header strip with a 16 check control, body below |
| R2 | HyperUI details list | Base: three columns, 12 row padding, 1 dividers |
| I8 | Untitled UI textareas | `md` |
| I4 | Untitled UI modals | Warning, stacked, left aligned: 400 wide, radius 16 |
| S4 | Untitled UI alerts | Floating: padding 16, radius 12, outline icon with two rings |
| F4 | Untitled UI progress indicators | Bar: 8 track, radius 6, label right or below |
| R6 | shadcnblocks list | `list-groups-1`: flat groups, header strip, items radius 6 |
| I5 | Untitled UI progress steps | Icons with text, vertical, `sm`: 24 marker, 2 connector |
| R11 | Untitled UI activity feeds | Connected: 40 avatar, dotted connector |
| S2 | Untitled UI empty states | `md`: 48 featured icon |
| S7 | Untitled UI loading indicators | Line simple, `md` |
| S1 | Untitled UI badges | `pill-color`, `md` |
| Buttons | Untitled UI buttons | `md`; `xl` for Submit; `lg` for "Open the library" |

## Departures from the map and the design system, and why

1. **Design system cards hold the page regions.** Ruled, no longer a departure: a card may
   hold a group of source components as page layout (review 2, ruling 1). The step card, the
   readiness panel, the summary and the two activity panels are such cards; no single source
   component is restyled.
2. **Page titles use the design system's 36px `h1`.** Ruled, no longer a departure (review 2,
   ruling 2). Every other source component keeps its source's size. Issuer, state and labels
   follow N4's order.
3. **Status shapes replace source glyphs.** In the file row (the four file states), the
   alert's outline icon, the modal's featured icon, the readiness group headers and the
   activity feed's avatar circle, the design system's shape stands where the source has an
   icon, a coloured dot or a photo.
4. **A status badge is added to each progress step.** The source step has a marker and text.
   The map asks for S1 on the running and the queued module, so each step carries a trailing
   badge. Marker and badge then say the same thing twice for finished and running modules.
5. **The progress step's marker has no failed form.** A module that failed or did not run
   keeps the source's "incomplete" marker; its badge and sentence carry the state.
6. **A count badge is added to the readiness group headers.** The source group header has a
   dot and a name only. The source's groups have no radius and no border, and are copied
   that way inside a rounded card.
7. **The stepper has five steps and Untitled UI buttons.** The source example has three steps
   and its own 36px buttons. Buttons are the design system's Untitled UI `md`.
8. **The radio card's body has no price.** The source body shows a price line; here it holds
   the description and a small label with the module count.
9. **File, approval, module and unreadable-activity states.** Ruled, no longer a departure:
   they are design system 0.7 sets (review 2, ruling 7) and the mocks now draw them as the
   table under "Run activity" lists. Against the first draft: "Read" became "Read in full",
   "Read in part" was added, a file's "Rejected" became "Unreadable", "Uploading" took the
   action colour, and "State not known" moved from the plain ring to the dashed ring in the
   gap colours.
10. **A module that fails inside a run reads "Not assessable"**, as design system 0.7 now
    states, with its sentence. The word "Failed" and the diamond are kept for the run. Still
    outside the module state set: a module in a live run carries the run-state words
    (Queued, Running, Finished), and the module that was running when a run was interrupted
    carries "Interrupted" (question 18).
11. **Source greys map to four tokens.** No longer a departure: control edges use
    `border-control` `#7F848D`; container hairlines use `border-hairline` `#E8E9EB`; the
    source's stronger container border (alert, featured icon, file icon) uses
    `border-container` `#D1D4D8`; the activity feed's connector dots use `connector`
    `#BBBEC4`. Both are design system 0.7 tokens and the stylesheet names them. The modal
    overlay is Navy at 70 percent.
12. **Many modules collapse on the run page.** The map's rule for many modules is written for
    the library (R7). On Run activity the finished modules collapse to one step and the
    queued ones beyond the next three collapse to another, each with a count the run data
    gives and a "Show all" link.
13. **"Stop run" is drawn** as a secondary button on live frames. No document asks for it;
    it is a proposal (question 7).
14. **The progress bar (F4) also shows a file's upload progress.** It is part of the source's
    file row; the map's I2 row does not name F4.
15. **A static skeleton (S5) sits under the alert when the activity cannot be read.** The map
    gives S4 alone for that state; the skeleton keeps the page's shape and does not move.
16. **No tooltip is drawn on the rail.** Its items are icon-only, as the source's are; in the
    build each needs the source's tooltip and an accessible name.

## Questions for the owner

Questions 1, 2, 13 and 15 were ruled at review 2 and keep their numbers. The rest are open;
decision 0003 names 3, 6, 7 and 8 as open product questions.

1. Ruled: a design system card may hold a group of source components (review 2, ruling 1).
2. Ruled: page titles use the design system's 36px `h1` (review 2, ruling 2).
3. Purpose: are the three purposes and what each runs right? The owner's earlier prompts name
   a pathway chosen first, a complexity (basic, standard, advanced) and an effort (Fast,
   Balanced, High). Do those belong on this step, and if so as radio cards or as selects?
4. Should the purpose card show an expected spend, or only the module count?
5. Confirm: which facts must the summary show before approval? The mock shows issuer,
   currency, year end, latest period, documents read and left out, purpose, modules and cap.
6. Is the warning modal wanted after Submit (two confirmations of one paid action), or is
   Submit alone enough? The map names both. And is there a ruling that lets the analyst's
   Submit start a paid run at the USD 20 cap, as `CLAUDE.md` requires?
7. May a running run be stopped from this page? If so, is "Stop run" a secondary button or
   the destructive one, and does it ask first?
8. After a failed or interrupted run, may the analyst resume it, and does resuming go back
   through Start and its modal, as the mock says? Does a resumed run keep the same cap?
9. What does "rejected" mean for a run? The mock uses "a document changed after the summary
   was approved". Who or what rejects, and can money have been spent?
10. Can more than one module run at once? The mock shows one. If several can, the steps list
    shows several "current" markers.
11. Many modules: collapse finished and far-queued modules (departure 12), or show every
    module and let the panel scroll?
12. A module that fails inside a run: "Not assessable" (as drawn), or its own "Failed" badge
    on the module?
13. Ruled: the states are design system 0.7 sets (review 2, ruling 7), applied as listed
    above.
14. Should the marker and the badge both show on a progress step (departure 4), or only one?
15. Ruled: `border-container` and `connector` are design system 0.7 tokens.
16. Elapsed time and cost per module are shown on Run activity. Is cost per module wanted
    there, or only the run total?
17. Does Run activity list earlier runs, or only the current one? The mock shows one run.
18. Which words does a module carry while its run is live, and when the run is interrupted
    mid-module? The module state set has Delivered, Delivered with gaps, Not assessable and
    Not run. The mock uses the run-state words Queued, Running and Finished for a live
    module, and "Interrupted" for the module that was running (departure 10).
19. Does a file read in part block Next? The mock lets the run go on and blocks only on an
    unreadable file.

## Not verified

- Rendered in the desktop app's built-in browser at 1440 wide only. No console errors, no
  failed layout and no horizontal overflow at that width; narrower widths, Edge, and the
  Claude Design editor were not checked. Both layouts fall to one column below about 1040px
  by rule, unseen.
- Source sizes were taken from class lists, computed styles and public source by three
  reading agents, not compared pixel by pixel with the source pages. Untitled UI's radio
  icon card, alerts, activity feeds, progress steps and page headers are not in its public
  repository; their values come from the live pages only. The progress step `md` size was
  not seen. shadcnblocks' stepper and list are behind its paid tier; values come from the
  rendered page, and its completed-step look was read from a sibling example. Nothing is
  bought, and the build takes I1 and R6 from Untitled UI or HyperUI where an equivalent
  exists (review 2, ruling 3). No equivalent was
  looked for here.
- The 0.7 revision was checked in the same browser at 1440 wide: the four file states and
  "State not known" by computed colour, border and word, and one look at frames 02 and 11.
  The "Read in part" and "Unreadable" rows of frame 02 were checked by computed style, not
  seen in a screenshot. The other frames were not looked at again.
- Reduced motion was checked by reading the stylesheet, not by switching the setting.
- Contrast was not recomputed. Every text and mark colour is a design system pair, except
  the placeholder icons (drawn at 70 percent opacity) and the `border-container` and
  `connector` tokens, which the design system lists as decorative.
- No screen was tested with an analyst. Purposes, readiness items, file and rejection
  reasons, module names, amounts and times are invented for the mock and are not the
  system's.
- Hover, focus, pressed and drag-over states are not drawn. No keyboard order was checked.
- Whether delivery or the store can supply each value shown (per-module cost and duration,
  counts for collapsed groups, readiness items) was not checked against `src/`.

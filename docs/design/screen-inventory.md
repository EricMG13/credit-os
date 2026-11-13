# Screen inventory

Every screen the predecessor draws, mapped on 2026-11-13 from its `main` at `8e3954a` (Signal
from its `origin/main` at `bb1950c`, where the Signal branches are merged). This is the list
the new front end must cover. Section and component names are the predecessor's; the
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
| Signal | Feed | `/` on Signal's own service; views For you, Latest, Saved, one per topic | Scans new outside stories, filters by kind, searches, saves, opens the source |
| Signal | Name dialog | opens on first visit and from the name chip | Types a display name (a label, not a login) |
| Signal | Group view and thread panel | designed only (mockup) | Reads a group's shared stories; comments and replies beside the feed |
| Signal | Share to group | designed only | Sends a story or a note to a group's thread |
| Signal | Digest card and digest page | designed only | Reads a scheduled brief and the stories behind each point |
| Signal | Settings | designed only; sections Groups, Thread rules, Sources, Topics, Digests, Notifications, AI and cost | Manages groups and topics, proposes sources, builds digests, sees source health and spend |

"Designed only" means the predecessor has a mockup (`docs/design/mockups/signal.html`) and a
design (`docs/superpowers/specs/2026-11-13-signal-design.md`) but no built page. Only the
feed and the name dialog are built there.

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
- Signal feed (built): application rail, channel list (views, then topics with a story count
  and a follow star), name chip with role, view title, freshness line, kind filter chips,
  search box, "new stories" pill, error band with Retry, story cards, loading skeleton,
  "Show older".
- Signal story card (built): kind label, headline linking to the source, source monogram and
  name, relative time, the feed's own summary, topic tags, "Also in N other sources", Save,
  Open source.
- Signal story card (designed only): signal strength (1 to 3), an AI "why it matters" line
  marked as AI, Comment with a count, Share to group, a "shared by" line, a Top or Latest
  order switch.
- Signal thread panel (designed only): the story quoted at the top, comments with one level
  of replies, a fixed set of reactions, "edited" and "removed" marks, a composer.
- Signal settings (designed only): group rows with members and visibility; thread rule
  switches; source rows with kind, state and health (last check, last item, items per week
  for six weeks); topic rows with keywords and kinds; the digest form (covers, schedule,
  brief, length, "Run once now"); a two-switch notification grid; AI spend against the cap.

## Record shapes (17)

matrix, watch, dated, edges, ranked, case rows, module state, question and answer, sided,
change, facts, cases, status, metric, measure, statement, default records.

Signal story kinds (4, designed; the built card draws all four alike): news with duplicates
folded, regulatory case with a stage tracker (opened, initial review, in-depth review,
decision), rating action with the move from and to, digest with numbered points.

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

Signal's own states: no display name yet; reader or writer (a reader sees no write controls);
no topic followed (For you); nothing saved; no approved source; no story yet; no story of the
chosen kind; no search match; loading; the service cannot be reached (error band, Retry);
sources not checked yet; new stories waiting; a story with no link or no time; a source
proposed, approved, paused, healthy, quiet or failing; AI off, or at its cap (stories arrive
with no AI line, digests pause); a digest with nothing material to report; an unread digest;
a comment edited or removed; a thread archived.

## Rules carried over (decision 0003 lists which may change)

- Audit material appears only on Evidence and in the trace drawer.
- One trace control per paragraph, row or figure.
- Text written for another module is drawn nowhere.
- Bottom line first. No module code on screen.
- The page recomputes nothing: every figure comes from `data.js`.
- Motion only for live state.
- Every chart has a table form. Every page works from `file://`.
- Signal (from its design): AI text is always marked and never looks like a colleague's
  comment; no article body is shown; feed and comment text is plain text; opening or
  refreshing a page makes no model call. Signal is served by its own local service and polls
  it, so it does not open from `file://`
  ([component map](component-map.md), question 9).

## Known defects in the predecessor's screens

- Flat repeated tables; spreadsheet error values shown as content.
- Prose mixed with data; long paragraphs with no hierarchy.
- Red and green fills carrying meaning with no icon or label.

## Not verified

- Signal's built feed was read from its page source and two committed screenshots, not run.
  Its thread, share, digest and settings screens exist only as a mockup with invented content.
- Section lists come from one mapping pass, not from every run in the predecessor.

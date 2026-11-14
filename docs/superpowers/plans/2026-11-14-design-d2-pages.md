# Design steps D2b to D2e: the pages

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Each step's session is a controller: it writes its own task plan from its mock record before the first dispatch, then executes it task by task.

**Goal:** every screen in the screen inventory built in React from the D2a kit, drawn from fixture data, matching its approved mock, and opening from `file://` under the content security policy.

**Architecture:** four page groups, each in its own folder with its own data slice, fixture and routes, so the four steps share no file. A scaffolding task (D2a's last task) creates the four empty group folders and the two shared files that read them, after which no group edits a shared file. The typed slice reader and the fixture of each group are the data contract that delivery (roadmap step 3B) later writes to; the front end computes no figure.

**Tech Stack:** as D2a (decisions 0001 and 0004). No new package.

**Spec:** `docs/design/mocks/library.md`, `model.md`, `run.md`, `signal.md` (each links its Claude Design project), `docs/design/component-map.md`, `docs/design/design-system.md`, `docs/design/screen-inventory.md`, `docs/decisions/0003-design-track.md`, `docs/decisions/0004-front-end-kit-dependencies.md`, `CLAUDE.md`.

## Steps

| Step | Pages | Folder (the only place it writes) | Mock record |
| :--- | :--- | :--- | :--- |
| D2b | Library home, Report history, Overview, Changes, Modules, Evidence (five tabs), trace drawer | `web/src/pages/library/`, `web/fixtures/library.json` | `library.md` |
| D2c | Forecast; Model front page, Analysis, Model, Portfolio fit, Limitations; the chart kinds | `web/src/pages/model/`, `web/src/components/chart/` (new chart kinds only), `web/fixtures/model.json` | `model.md` |
| D2d | Run start (five steps), readiness, run started, Run activity, every run state | `web/src/pages/run/`, `web/fixtures/run.json` | `run.md` |
| D2e | Signal: feed, story kinds, name dialog, group and thread, share, digests, settings | `web/src/pages/signal/`, `web/fixtures/signal.json` | `signal.md` |

D2b to D2e run in parallel once D2a, including its scaffolding task, is merged. D2c is the only step that adds chart kinds; D2b uses the ones D2a and D2c provide and, until D2c merges, draws a chart's Table side only where a kind is missing, saying so in its report.

## Scaffolding (D2a, last task, before any group starts)

**Files:**
- Create: `web/src/pages/library/routes.tsx`, `web/src/pages/model/routes.tsx`, `web/src/pages/run/routes.tsx`, `web/src/pages/signal/routes.tsx` (each exports `routes: readonly Route[]`, empty, and `readSlice(source: unknown): SliceResult<…>` returning `{ kind: "absent" }`); `web/src/pages/route-table.ts`; `web/fixtures/library.json`, `model.json`, `run.json`, `signal.json` (each `{}`); `web/scripts/fixture-data.mjs`
- Modify: `web/src/data.ts`, `web/src/App.tsx`, `web/scripts/open-from-disk.mjs`, `web/package.json` (scripts only)
- Test: `web/src/pages/route-table.test.ts`, `web/scripts/fixture-data.test.mjs`

**Interfaces:**
- `type Route = { path: string; title: string; render: (params: Record<string, string>) => JSX.Element }`; `path` uses `:name` segments (`/library/:issuer/:run/overview`).
- `function matchRoute(hash: string, routes: readonly Route[]): { route: Route; params: Record<string, string> } | null`.
- `type LibraryData` gains optional `library`, `model`, `run`, `signal` members typed `unknown`; `type SliceResult<T> = { kind: "ok"; data: T } | { kind: "absent" } | { kind: "invalid"; reason: string }`.
- `route-table.ts` imports the four `routes` arrays and exports them concatenated; `App` renders the matched route inside the shell, the existing states when there is no match and no data, and a "Page not found" state for an unknown hash.
- `node scripts/fixture-data.mjs <outDir>` writes `<outDir>/data.js` as `window.CREDIT_OS_DATA = { schema: "credit-os-data/1", issuers: […], library, model, run, signal }` from the four fixture files. `open-from-disk.mjs` gains a check that loads the built page with that file and visits every route path a group's `routes` array declares with the parameters its fixture names, failing on a policy violation, an uncaught error or the "Page not found" state.

Tests: `matchRoute` on a parameterised path, an unknown path and a trailing slash; the fixture script's output parses and carries the four slices; an `invalid` slice renders a visible "This part of the library could not be read" state, never a blank page.

## Global Constraints (every group)

- Write only inside the step's own folder and fixture file. Shared files, the kit under `web/src/components/` (D2c's new chart kinds excepted), `docs/`, decision records and `VERIFICATION.md` are not edited; a needed kit change is reported, not made.
- Match the mock: the component the map names, the source's look, the design system's colours, typefaces, status shapes, gap states and motion. Every departure the mock record lists as ruled is followed; anything the build cannot match is listed in the report.
- The slice reader validates the whole slice by hand (no new package) and returns `invalid` with the first failing path. The page draws only what the reader returned.
- The front end computes no figure shown as text: no sum, ratio, percentage, rounding or unit conversion on data values. A value arrives as the exact string to show plus, where a chart needs it, a number for position only. Missing is `null` and draws "n.a."; zero draws as zero.
- Audit material (sources, file names, hashes, ids, registers, run codes, calculations) appears only on Evidence and in the trace drawer. One trace control per paragraph, row or figure, shown on hover and focus, always on touch, with the page-level "Show sources" switch.
- Every state in the mock record is reachable from the fixture and has a test: gap, withheld, not assessable, n.a., no earlier run, long text, many modules, and the group's own states.
- Every chart has its Chart or Table toggle and its table side. Only a live run page loops.
- Fixtures are synthetic or the public TransDigm case; no private issuer, no real private person, no company name, tagline or wordmark.
- Open product questions (decision 0003) are not settled by the build: where a screen depends on one, build what the mock draws and list it in the report as "built as mocked, awaits ruling".
- Signal and the run pages draw fixture data only. No polling, no service call, no write: the served-page wiring belongs to roadmap step 5C and to Signal's own plan. Controls that would write are present and disabled with their reason, or act on in-memory state only.
- Each PR within 800 changed lines; stacked PRs; merge none. `npm --prefix web run gates` exits 0 on each, Windows and Linux.
- Implement with `mx-feature`; review each task with `mx-precise`; whole-branch review per section 7 of the global rules before the last PR is offered. No stub or fake value standing in for real behaviour; no catch-all that hides a failure; every task report ends with `Not verified:`. The mock record and the design documents are the answer key and are not edited.

## Review Focus

1. A slice with one malformed record: the page shows the invalid state with the failing path, not a partial page that looks complete.
2. A figure that is missing in the fixture drawn as 0, as a dash, or as an empty chart bar touching the axis.
3. Audit material leaking onto a findings page through a tooltip, a title attribute or an accessible name.
4. A route whose parameters name an issuer or run the fixture does not hold.
5. Long text and many modules: the layout holds at 1440px and at 1024px with no horizontal page scroll.

## Each session's first act

Write `.superpowers/sdd/<plan>/` task briefs from the mock record: one task per screen or per screen section, each with its files, its slice types, its fixture records, its tests and the frames of the mock it must match. Record in the ledger any place the mock record and the component map disagree and the ruling made.

## Done when

Every screen and state in the group's mock record renders from the fixture when the built folder is opened from disk, with no policy violation; the gates pass on the last PR on both systems; the report lists the PRs, the slice's type names for step 3B, the departures from the mock, the open product questions the pages depend on, and ends with `Not verified:`.

## Not verified by this plan

- The route and slice design above was not prototyped; D2a's scaffolding task is its first test.
- Whether each mock can be matched with free components only; three paid-only components already come from HyperUI (decision 0004).
- No screen has been checked against a real delivered run: delivery (step 3B) does not exist yet, so the slice types are the front end's proposal for that contract.

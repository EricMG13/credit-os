# credit-os rebuild roadmap

Date: 2026-11-13. Owner: coordinator session. This is the master plan; each phase gets its
own plan file, written by the coordinator just before that phase is dispatched, against the
code as it then stands.

**Goal:** the predecessor's live path (sources, modules, Markdown handoffs, checks, delivery,
issuer library) rebuilt as one layered Python package and one React front end, running
unchanged on the work PC.

**Source for ports:** `EricMG13/RBOT-HTML`, read-only, baseline `origin/main` `8e3954a`. Paths
below are in that repository. It keeps changing; `docs/legacy/ports.md` tracks each ported
path and the legacy commit it was last adapted from.

## What is ported and what is left behind

| Ported | Left behind |
| :--- | :--- |
| Module method texts (`src/deploy_vii/methods/*.md`, 20 files) | Structured JSON-step runtime (`run_pathway`, `owner_workflow`, `financial_workflow`, `earnings_workflow`, `host`, `workflow`, `replay`, `owners/cp*.py`) |
| Handoff grammar and checks (`handoff_delivery`, `prose_checks`, `confidence`, `changes`, `changes_check`) | Direct OpenAI, Anthropic and OpenRouter transports, pricing tables, dollar-cap accounting |
| Decimal kernel (`src/deploy_vii/model/*`) and forecast (`owners/cpos_forecast`) | `model_testing/`, `rendering.py`, `financial_rendering.py`, `cpos_status.py`, `deploy_vii/delivery.py`, `deploy_vii/inputs/` |
| Run admission by hash chain (`library_index`) | Second front end (`deploy_vii/render.py`, `assets/app.js`), duplicated Markdown parsers |
| Library pages and their data contract (`apps/issuer-library`) as the behaviour to match | `docs/reuse` archive, `docs/work-pc` change packs, bundled-Python packaging, OCR subprocess |
| Context schema (`context.py`), rulings as decision records | File-lock code (`platform_io`), JSON state files |

## Phases

Steps on one line of a phase touch disjoint files and may run as parallel sub-sessions, one
PR each. A phase starts only when the phase before it is merged.

| Phase | Step | Delivers | Layer |
| :--- | :--- | :--- | :--- |
| 0 | 0A | Python package skeleton, gates, layering test, CI on Windows and Linux | repo |
| 0 | 0B | React application skeleton, gates, `file://` browser proof, CI | `web/` |
| 1 | 1A | One handoff parser to a typed document, proved on a retained real run's handoffs | `handoff/` |
| 1 | 1B | Decimal kernel and forecast, each formula tested against independently worked values | `model/` |
| 1 | 1C | Provider interface, canned adapter, Copilot adapter (SDK 1.0.8) | `provider/` |
| 1 | 1D | Source pinning and page reading (PDF, docx, HTML, xlsx, csv) | `sources/` |
| 2 | 2A | Run state in SQLite: runs, events, attempts, admitted deliveries | `store/` |
| 2 | 2B | Prose, figure and confidence checks on a handoff document | `checks/` |
| 3 | 3A | Orchestrator: module plan, dependency order, bounded retries, resume, CLI | `orchestrator/` |
| 3 | 3B | Delivery: library data file written from handoff documents, hash-checked | `delivery/` |
| 4 | 4A | Library shell, routing, trace control, Overview page | `web/` |
| 4 | 4B to 4E | Modules, Forecast (with Model), Evidence, Changes pages, one PR each, in sequence | `web/` |
| 5 | 5A | CP-8 comparison against an earlier run | `orchestrator/`, `checks/` |
| 5 | 5B | Run start page (served) | `web/`, `orchestrator/` |
| 6 | one module per PR | Each method text ported and proved with a real retained response | `methods/` |
| 7 | 7A | Acceptance on the work PC: gates, one run through Copilot, library opened from disk | none |

Signal is not in this roadmap. It is unmerged in the predecessor and gets its own plan once
phase 4 is done.

## Rules for every phase

- Global rules §1, §3 and §7 apply. Sub-sessions are controllers; implementers are `mx-*`.
- Phase 6 is analytical-module work: one module at a time, in one session, never parallel.
- A port is new code: it passes the same gates and review as anything written fresh.
- A phase plan names its answer key (a retained handoff, a hand-worked figure, a browser
  probe). Implementers do not edit the answer key or weaken the comparison.
- Paid model runs happen only in phases 6 and 7, each under an owner ruling in
  `docs/decisions/`.

## Prior art (searched 2026-11-13)

- Owner's repositories: `caos-workbench/frontend` and `caos-firebase/frontend` already run
  React 19.3.0, Vite 6.4.3, Tailwind 4.3.3, TypeScript 5.9.3, Vitest 4.1.11 with eslint and
  prettier configured. Decision: adapt their pins and gate configuration for `web/`
  (decision 0001). `RBOT-HTML` is the source for every port above.
- Public GitHub: not searched for phase 0, which is scaffolding from the owner's own
  configuration. Phases 1A (Markdown table parsing) and 2A (SQLite run store) record their
  own search in their plan.

## Open questions for the owner

1. Is an Edge or Chrome browser available on the work PC for the `file://` check in 7A?
2. May the work PC run a localhost page (phase 5B), or must run start stay a command?
3. Is `hypothesis` installable on the work PC, or are property tests CI-only?

## Not verified

- The ported/left-behind split rests on static import analysis of the predecessor; nothing
  was executed to confirm which code a live run reaches.
- GitHub Copilot SDK 1.0.8 has not been read against 1.0.28, which the predecessor targets;
  phase 1C's plan fetches the 1.0.8 documentation before any task is written.
- Nothing in the predecessor has been run on Windows.

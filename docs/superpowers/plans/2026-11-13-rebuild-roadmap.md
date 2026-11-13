# credit-os rebuild roadmap

Date: 2026-11-13, revised the same day after an adversarial review of the plans (2 High and
17 Medium findings; the changes are listed at the end). Owner: coordinator session. This is
the master plan; each step gets its own plan file, written by the coordinator just before
that step is dispatched, against the code as it then stands.

**Goal:** the predecessor's live path (sources, modules, Markdown handoffs, checks, delivery,
issuer library) rebuilt as one layered Python package and one React front end, running
unchanged on the work PC.

**Source for ports:** `EricMG13/RBOT-HTML`, read-only, baseline `origin/main` `8e3954a`. Paths
below are in that repository. It keeps changing; `docs/legacy/ports.md` tracks each ported
path and the legacy commit it was last adapted from.

## What is ported and what is left behind

| Ported | Left behind |
| :--- | :--- |
| The method texts the live launcher sends (`cpos_launch.METHODS`): `docs/reuse/selected-methods` for 19 of 22 modules, `prompts/CP-1.md`, and `src/deploy_vii/methods/cp8.md` and `cpl10.md` | Structured JSON-step runtime (`run_pathway`, `owner_workflow`, `financial_workflow`, `earnings_workflow`, `host`, `workflow`, `replay`, `research/`, `owners/cp*.py` except `cpos*.py` and `cp2g.py`), and the other `src/deploy_vii/methods` texts, which the launcher no longer sends |
| Handoff grammar and checks (`handoff_delivery`, `markdown_delivery`, `prose_checks`, `confidence`, `changes`, `changes_check`) | Direct OpenAI, Anthropic and OpenRouter transports (`providers.py`, `transport.py`) |
| Decimal kernel (`src/deploy_vii/model/*`) and the forecast arithmetic (`owners/cp2g.py`, `cp2g.forecast`), with its readers `cpos_forecast`, `cpos_periods`, `cpos_facilities` | `model_testing/` except `configs.py`, `rendering.py`, `financial_rendering.py`, `cpos_status.py`, `deploy_vii/delivery.py`, `deploy_vii/inputs/` |
| Run admission by hash chain (`library_index`) | Second front end (`deploy_vii/assets/app.js`), duplicated Markdown parsers |
| Library pages and their data contract (`apps/issuer-library`) as the behaviour to match | `docs/reuse` outside `selected-methods`, `docs/work-pc` change packs, bundled-Python packaging, OCR subprocess |
| Context schema (`context.py`), rulings as decision records, the per-run cost cap (`budget.py`, Copilot rows of `pricing.py`) unless the owner replaces it | File-lock code (`platform_io`), JSON state files |

The predecessor is more entangled than this table suggests: its live files reach about 170
further modules through imports, most of them on the left-behind side. Each step's plan
traces what its port actually needs. The earlier estimate of 25,000 to 30,000 source lines is
withdrawn until phase 1 shows the real size.

## Steps

A step is a **sequence of pull requests**, each within the 800-changed-line gate; the split is
written in the step's plan. A phase starts when the steps it depends on are merged.

| Phase | Step | Delivers | Layer | Needs |
| :--- | :--- | :--- | :--- | :--- |
| 0 | 0A | Python package skeleton, gates, layering test, CI on Windows and Linux | repo | none |
| 0 | 0B | React application skeleton, gates, `file://` browser proof, CI | `web/` | none |
| 0 | 0C | Python duplication gate in `tools/gates.py` (out of the web script); `pypdf` and `github-copilot-sdk` added to the lock; decision record for the Python gate tools; build backend pinned | repo | 0A, 0B |
| 1 | 1A | One handoff parser to a typed document, proved on a full retained run's handoffs | `handoff/` | 0C |
| 1 | 1C | Provider interface, canned adapter, Copilot adapter (SDK 1.0.8, model `gpt-6-sol`) | `provider/` | 0C |
| 1 | 1D | Source pinning and page reading (PDF, docx, HTML, xlsx, csv) | `sources/` | 0C |
| 1 | 1B | Decimal kernel and forecast, each formula tested against independently worked values | `model/` | 1A |
| 2 | 2A | Run state in SQLite: runs, events, attempts, admitted deliveries | `store/` | 1A |
| 2 | 2B | Prose, figure and confidence checks on a handoff document | `checks/` | 1A |
| 3 | 3A | Orchestrator: module plan, dependency order, bounded retries, resume, run cap | `orchestrator/` | 1C, 1D, 2A, 2B |
| 3 | 3B | Delivery: library data file written from handoff documents, hash-checked | `delivery/` | 1B, 2A, 2B |
| 4 | 4A | Library shell, routing, trace control, Overview page | `web/` | 3B |
| 4 | 4X | One command from a run to an openable library folder (run, deliver, copy the built front end, `data.js`, downloads), with the 0B browser check run on a real delivered folder | new top-level entry module, named in its plan and covered by the layering test | 3A, 4A |
| 4 | 4B to 4D | Modules, Forecast (with Model), Evidence pages, in sequence | `web/` | 4A |
| 5 | 5A | CP-8 comparison against an earlier run, with its data contract in delivery | `orchestrator/`, `checks/`, `delivery/` | 3A, 3B |
| 5 | 5B | Changes page | `web/` | 5A, 4A |
| 5 | 5C | Run start page (served) | `web/`, `orchestrator/` | 5B |
| 6 | one module per PR | Each method text ported and proved with a real retained response | `methods/` | 4X |
| 7 | 7A | Acceptance on the work PC: gates, one run through Copilot, library opened from disk | none | all |

**May run as parallel sub-sessions** (disjoint files, neither needs the other's result):
0A with 0B; 1A with 1C with 1D; 2A with 2B; 3A with 3B. Everything else is sequential.

Signal is not in this roadmap. It is unmerged in the predecessor and gets its own plan once
phase 4 is done.

## Rules for every step

- Global rules §1, §3 and §7 apply. Sub-sessions are controllers; implementers are `mx-*`.
- Code, including test helpers and gate scripts, is reviewed per task by `mx-precise`. Only
  configuration, docs and decision records take the batched `mx-feature` review.
- Before a step's PR merges it takes §7's pre-merge steps: `/sweep refactoring discover
  changed-update`, then the `mx-architect` adversarial whole-branch review.
- Phase 6 is analytical-module work: one module at a time, in one session, never parallel.
- A port is new code: it passes the same gates and review as anything written fresh.
- A step's plan names its answer key (a retained handoff, a hand-worked figure, a browser
  probe). Implementers do not edit the answer key or weaken the comparison.
- Committed fixtures come only from public or synthetic cases; this repository is public.
- Paid model runs happen only in phases 6 and 7, each under an owner ruling in
  `docs/decisions/`.

## Prior art (searched 2026-11-13)

- Owner's repositories: `caos-workbench/frontend` and `caos-firebase/frontend` already run
  React 19.3.0, Tailwind 4.3.3, TypeScript 5.9.3, Vitest 4.1.11 with eslint and prettier
  configured. Decision: adapt their pins and gate configuration for `web/` (decision 0001).
  `RBOT-HTML` is the source for every port above.
- Public GitHub: not searched for phase 0. `import-linter` is the known public tool for the
  layering rule; it was not adopted because the rule is one small test and a new dependency
  needs a record. Steps 1A (Markdown table parsing) and 2A (SQLite run store) record their own
  search in their plans.

## Open questions for the owner

1. **Packages outside the work PC record.** The record lists pydantic, pypdf, openpyxl, the
   Copilot SDK, pytest, ruff and mypy. This project also uses `pytest-cov`, `hypothesis`,
   `complexipy`, `bandit`, `pip-audit`, the `hatchling` build backend, Node 24 and the whole
   npm tree in decision 0001. Can the work PC install all of them?
2. **Vite 6.4.5** (released 2026-10-21, under the 30-day rule): confirm, because 6.4.3 and
   6.4.4 fail `npm audit`.
3. **The 1A answer key.** Legacy `main` tracks only two handoff fragments (60 lines). Name one
   retained run of a public issuer whose full handoffs can be committed here as the frozen
   answer key.
4. **The run cap.** A standing ruling caps a run-start Submit at USD 20. Keep it for the
   Copilot route (port `budget.py` and the Copilot pricing rows), or replace it with a
   different bound?
5. **The model.** The work PC record says `gpt-6-sol`; legacy defines `copilot-sol-medium` as
   `gpt-6.1-sol`. Which is right for the work PC?
6. Is an Edge or Chrome browser available on the work PC for the `file://` check in 7A?
7. May the work PC run a localhost page (step 5C), or must run start stay a command?

## Not verified

- The ported and left-behind split rests on static import analysis of the predecessor;
  nothing was executed to confirm which code a live run reaches.
- Version differences from the predecessor have not been tested against its code: Python
  3.13 to 3.12, pydantic 2.14.1 to 2.13.4, mypy 2.4.0 to 1.18.1, Copilot SDK 1.0.28 to 1.0.8.
  Step 1C's plan fetches the SDK 1.0.8 documentation before any task is written.
- The work PC itself has not been inspected; its environment is known only from the owner's
  record.

## Changes after the adversarial review (2026-11-13)

- Method texts now come from what the launcher sends, not `src/deploy_vii/methods` (High).
- The forecast arithmetic file `owners/cp2g.py` and its two readers are ported and tracked
  (High).
- The port map tracks direct imports, and `Adapted to` no longer moves past a deferred change.
- Steps are PR sequences within the line cap; parallel pairs are listed explicitly; 1B waits
  for 1A; the Changes page follows the comparison; step 0C and step 4X are new.
- The run cap, the model id and the packages outside the work PC record are open questions.

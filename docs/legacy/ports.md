# Legacy port map

The predecessor, `EricMG13/RBOT-HTML`, keeps changing on its `main` while this rebuild is
under way. This file records which legacy code each part of credit-os is adapted from and
how far each part has been brought level, so a change there is seen and adapted here, not
lost.

Legacy is read-only. Nothing is copied automatically: a legacy change is read, then adapted
through the normal plan, task and review route.

**Baseline pin:** `8e3954a` (legacy `origin/main`, 2026-11-13).

## Map

A row's paths include the modules its files import directly; those are listed too, because a
behaviour change often lands in a helper. Only the coordinator edits this table.

`Adapted to` is the last legacy commit whose changes to the row are adapted **and merged**
here. It never moves past a change that was deferred: a deferred change is written in
`Pending` as a commit range with the task that owns it, and stays there until that task
merges. A row not yet ported sits at the baseline pin with nothing pending.

| Legacy path | credit-os target | Phase | Adapted to | Pending |
| :--- | :--- | :--- | :--- | :--- |
| `src/deploy_workflow/docx_text.py`, `html_text.py`, `pdf_headers.py`, `inline_xbrl.py`, `src/deploy_vii/preparation.py`, `contracts.py`, `readiness.py` | `sources/` | 1D | `8e3954a` | none |
| `src/deploy_workflow/handoff_delivery.py`, `markdown_delivery.py`, `run_scopes.py`, `src/deploy_vii/bindings/shipped.py`, `display.py`, `report_view.py` | `handoff/` | 1A | `8e3954a` | none |
| `tests/fixtures/sol_medium_run_2026_11_09` (two fragments), `apps/issuer-library/fixtures/synthetic-new-format`; the full answer key is the retained run named in decision 0002, which is not in the legacy repository | `tests/fixtures/` | 1A | `8e3954a` | none |
| `src/deploy_vii/model`, `src/deploy_workflow/model_handoff_delivery.py`, `owners/cpos_forecast.py`, `owners/cp2g.py` (the forecast arithmetic, `cp2g.forecast`), `owners/cpos_periods.py`, `owners/cpos_facilities.py` | `model/` | 1B | `8e3954a` | none |
| `src/deploy_workflow/model/handoff.py`, `loop.py`, `copilot.py`, `copilot_adapter.py`, `adapter.py`, `record.py`, `redact.py`, `reply_classes.py`, `turn.py`, `model_testing/configs.py`, `src/deploy_vii/live/schema.py`, `live/prompts.py`, `live/tools.py`, `execution.py` | `provider/` | 1C | `8e3954a` | none |
| `src/deploy_workflow/run_events.py`, `library_index.py`, `reader_summary.py`, `platform_io.py` | `store/` | 2A | `8e3954a` | none |
| `src/deploy_workflow/prose_checks.py`, `confidence.py` | `checks/` | 2B | `8e3954a` | none |
| `src/deploy_vii/registry.py`, `business_context.py`, `src/deploy_workflow/owners/cpos.py`, `owners/cpos_launch.py`, `owners/cpos_cp1_check.py` (new in legacy #111; CP-1's acceptance check, imported by the launcher), `context.py`, `run_expectations.py`, `model/budget.py`, `model/pricing.py` (run cap; see open questions) | `orchestrator/` | 3A | `8e3954a` | none |
| `apps/issuer-library/update_library.py`, `credit_os/store.py`, `src/deploy_workflow/credit_os_catalogue.py`, `credit_os_chips.py`, `src/deploy_vii/render.py` | `delivery/` | 3B | `8e3954a` | none |
| `apps/issuer-library/credit_os/web` | `web/` (behaviour to match, not code to copy) | 4 | `8e3954a` | none |
| `src/deploy_workflow/changes.py`, `changes_check.py` | `orchestrator/`, `checks/`, `delivery/` | 5A | `8e3954a` | none |
| `src/deploy_workflow/run_start`, `inbox`, `docs/templates/context-form.html` | `web/`, `orchestrator/` | 5C | `8e3954a` | none |
| Method texts the live launcher sends, as named by `cpos_launch.METHODS`: `docs/reuse/selected-methods` (skills, `CANON_SHARED.md`, `manifest.json`), `prompts/CP-1.md`, `src/deploy_vii/methods/cp8.md`, `cpl10.md`; `src/deploy_vii/methodology.json` | `methods/` | 6 | `8e3954a` | none |
| `src/deploy_workflow/signal` (merged into legacy `main` by #101, #102, #106, #109, #115) | none yet: Signal's back end gets its own plan after phase 4 (roadmap); its screens are in the design track | after 4 | `8e3954a` | none |
| `docs/rulings` | `docs/decisions/` (carried as records when they still bind) | all | `8e3954a` | none |

The same paths, one per line, are in `docs/legacy/paths.txt` for the commands below. Keep the
two in step.

## Checking what moved

Once per clone, add the legacy repository as a fetch-only remote:

```bash
git remote add legacy https://github.com/EricMG13/RBOT-HTML.git
```

```bash
git remote set-url --push legacy DISABLED
```

Then, with `PIN` set to the oldest `Adapted to` value in the table:

```bash
git fetch legacy main
```

```bash
xargs git diff --stat PIN..legacy/main -- < docs/legacy/paths.txt
```

```bash
git log --oneline --first-parent PIN..legacy/main
```

The first shows which tracked paths changed and by how much. The second lists what merged, so
a new feature outside the tracked paths (Signal, for one) is noticed and either added to the
map or recorded below as left behind.

## When to check

- Before a phase plan is written: the coordinator runs the commands for that phase's rows and
  writes the plan against legacy `main` as it then stands, recording the commit in the plan.
- Before a phase's PR merges: run them again for its rows. A legacy change since the plan was
  written is adapted in that PR if small. Otherwise it goes in the row's `Pending` cell as a
  range with a named follow-up task.
- After the last phase that touches a row: any later legacy change to it is an ordinary
  adaptation task, with the legacy commit range in its brief.

## Left behind on purpose

Changes under these legacy paths are not adapted; the roadmap says why.

- `src/deploy_workflow/run_pathway.py`, `owner_workflow.py`, `financial_workflow.py`,
  `earnings_workflow.py`, `host.py`, `workflow.py`, `replay.py`, `research/`, `owners/cp*.py`
  other than `cpos*.py` and `cp2g.py`, `model_testing/` other than `configs.py`
- `src/deploy_workflow/model/providers.py`, `transport.py`
- `src/deploy_vii` outside the files named in the map
- `docs/reuse` outside `selected-methods`; within it, the archived `runtime/` snapshots
- `src/deploy_workflow/research/weblookup.py`, `web_allowlist.json` and the launcher code that
  calls them: CP-DR's web lookup (owner, 2026-11-14)
- `docs/work-pc`, `apps/issuer-library/packaging`, `tools/work_pc_delta.py`

A bug fix that lands in one of these and also describes a rule the rebuild must keep (a
figure check, a period rule) is carried as a test in the layer that owns the rule.

## Known limit of this map

The tracked legacy files import, directly or through other modules, about 170 legacy modules
that are not tracked here, 119 of them on the left-behind list (static import analysis,
2026-11-13). The map lists the direct imports only. When a phase plan is written, the
coordinator traces that phase's files one level further and adds what the port actually needs.

## Checks

Newest first. A check records what moved; it adapts nothing.

### 2026-11-14, legacy `main` at `cbf4400` (pin `8e3954a`, 20 merges, #99 to #120)

No row is ported yet, so nothing is pending: each phase plan is written against legacy `main`
as it stands that day. Mapped paths changed in 40 files (4,069 lines added, 291 removed):

| Row | What moved |
| :--- | :--- |
| `sources/` 1D, `store/` 2A, fixtures 1A | nothing |
| `handoff/` 1A | `markdown_delivery.py` (167 lines) |
| `model/` 1B | `owners/cpos_forecast.py`, `cpos_periods.py` (forecast labels, #112; downside follows the forward model, #113; negative cash not calculable, #114) |
| `provider/` 1C | `model/handoff.py` (865 lines), `copilot.py`, `copilot_adapter.py`, `adapter.py`, `record.py`, `turn.py` |
| `checks/` 2B | `prose_checks.py` (157 lines) |
| `orchestrator/` 3A | `owners/cpos_launch.py` (1,056 lines), `cpos.py`, `run_expectations.py`; `owners/cpos_cp1_check.py` is new and added to the row |
| `delivery/` 3B | `apps/issuer-library/credit_os/store.py`, `credit_os_catalogue.py` |
| `web/` 4 | `views.js`, `screening.js`, `shapes.js`, `screen.css`: a leverage or cover figure on adjusted EBITDA is marked in the list and left out of filters and sort (#117, #118); zero-width label (#105) |
| 5A, 5C | `changes.py`; `run_start/service.py`, `submissions.py`, `context-form.html` |
| `methods/` 6 | `selected-methods`: CP-1 now has a skill folder and `CPOS_REGISTER_SCOPE.md` is new; `cpos_launch.METHODS` sends the CP-1 skill and `prompts/CP-1.md` (#111). The roadmap's "19 of 22 modules" from `selected-methods` predates this |
| `docs/rulings` | five new rulings dated 2026-11-13 (appendix and routing scope, CP-1 method and acceptance check, CP-DR web lookup, downside follows the forward model, negative cash not calculable) and one changed |

Outside the map: Signal merged (row added above); `docs/work-pc` and sweeps records (left
behind).

**Ruled by the owner, 2026-11-14 ("Leave it out"):** the rebuild does not carry CP-DR's web
lookup. The live launcher imports `research/weblookup.py` since #110; step 3A's port drops
that import and the lookup's instructions, and `research/` stays left behind.

## Not tracked

Branches not yet merged into legacy `main`. On 2026-11-13 about 19 were ahead of it,
including Signal (since merged) and four with front-end changes. They enter this map when they merge.

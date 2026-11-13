# Legacy port map

The predecessor, `EricMG13/RBOT-HTML`, keeps changing on its `main` while this rebuild is
under way. This file records which legacy code each part of credit-os is adapted from and
the legacy commit each part was last brought level with, so a change there is seen and
adapted here, not lost.

Legacy is read-only. Nothing is copied automatically: a legacy change is read, then adapted
through the normal plan, task and review route.

**Baseline pin:** `8e3954a` (legacy `origin/main`, 2026-11-13).

## Map

`Synced to` is the legacy commit that row was last adapted from. A row not yet ported sits at
the baseline pin. Only the coordinator edits this table, when the PR that ports or adapts the
row merges.

| Legacy path | credit-os target | Phase | Synced to |
| :--- | :--- | :--- | :--- |
| `src/deploy_workflow/docx_text.py`, `html_text.py`, `pdf_headers.py`, `inline_xbrl.py`, `src/deploy_vii/preparation.py` | `sources/` | 1D | `8e3954a` |
| `src/deploy_workflow/handoff_delivery.py`, `markdown_delivery.py` | `handoff/` | 1A | `8e3954a` |
| `tests/fixtures/sol_medium_run_2026_11_09` | `tests/fixtures/` (answer key for 1A) | 1A | `8e3954a` |
| `src/deploy_vii/model`, `src/deploy_workflow/model_handoff_delivery.py`, `owners/cpos_forecast.py` | `model/` | 1B | `8e3954a` |
| `src/deploy_workflow/model/handoff.py`, `loop.py`, `copilot.py`, `copilot_adapter.py` | `provider/` | 1C | `8e3954a` |
| `src/deploy_workflow/run_events.py`, `library_index.py` | `store/` | 2A | `8e3954a` |
| `src/deploy_workflow/prose_checks.py`, `confidence.py` | `checks/` | 2B | `8e3954a` |
| `src/deploy_vii/registry.py`, `src/deploy_workflow/owners/cpos.py`, `owners/cpos_launch.py`, `context.py` | `orchestrator/` | 3A | `8e3954a` |
| `apps/issuer-library/update_library.py`, `credit_os/store.py`, `src/deploy_workflow/credit_os_catalogue.py`, `credit_os_chips.py` | `delivery/` | 3B | `8e3954a` |
| `apps/issuer-library/credit_os/web` | `web/` (behaviour to match, not code to copy) | 4 | `8e3954a` |
| `src/deploy_workflow/changes.py`, `changes_check.py` | `orchestrator/`, `checks/` | 5A | `8e3954a` |
| `src/deploy_workflow/run_start`, `docs/templates/context-form.html` | `web/`, `orchestrator/` | 5B | `8e3954a` |
| `src/deploy_vii/methods`, `methodology.json` | `methods/` | 6 | `8e3954a` |
| `docs/rulings` | `docs/decisions/` (carried as records when they still bind) | all | `8e3954a` |

The same paths, one per line, are in `docs/legacy/paths.txt` for the commands below. Keep the
two in step.

## Checking what moved

Once per clone, add the legacy repository as a remote (it is never pushed to):

```bash
git remote add legacy https://github.com/EricMG13/RBOT-HTML.git
```

Then, with `PIN` set to the oldest `Synced to` value in the table:

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
  written is adapted in that PR if small, or becomes a follow-up task named in the PR body.
- After the last phase that touches a row: any later legacy change to it is an ordinary
  adaptation task, with the legacy commit range in its brief.

Each check ends by setting the row's `Synced to` to the legacy commit it was read at.

## Left behind on purpose

Changes under these legacy paths are not adapted; the roadmap says why.

- `src/deploy_workflow/run_pathway.py`, `owner_workflow.py`, `financial_workflow.py`,
  `earnings_workflow.py`, `host.py`, `workflow.py`, `replay.py`, `owners/cp*.py` other than
  `cpos*.py`, `model_testing/`
- `src/deploy_workflow/model/providers.py`, `transport.py`, `pricing.py`, `budget.py`
- `src/deploy_vii` outside `methods`, `methodology.json`, `registry.py`, `model` and
  `preparation.py`
- `docs/work-pc`, `docs/reuse`, `apps/issuer-library/packaging`, `tools/work_pc_delta.py`

A bug fix that lands in one of these and also describes a rule the rebuild must keep (a
figure check, a period rule) is carried as a test in the layer that owns the rule.

## Not tracked

Branches not yet merged into legacy `main`. On 2026-11-13 about 19 were ahead of it,
including Signal and four with front-end changes. They enter this map when they merge.

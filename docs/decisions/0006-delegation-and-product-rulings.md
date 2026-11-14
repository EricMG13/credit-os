# 0006 Delegation to the coordinator, and the product rulings made under it

Date: 2026-11-14. Decided by: owner (the delegation); coordinator (the rulings below it).

## The delegation

The owner's words, 2026-11-14: "merge all PRs when they are ready, archive sessions when they
are done and resolve all decisions yourself". The goal set for the coordinator session is to
complete the roadmap.

How the coordinator applies it:

- **Merging.** A pull request is ready when its step's reviews have no High or Medium finding
  open, its gates pass on Windows and Linux, and the coordinator has read its diff or its
  review. Code still takes the sweep discovery and the adversarial whole-branch review first
  (global rules, section 7); the delegation removes the wait for the owner, not the review.
- **Decisions.** The coordinator rules and records the ruling here or in the step's record,
  with what it costs if wrong. The owner can overturn any of them.
- **Not delegated.** Starting a paid model run, or raising a spending cap: project rules make
  that a separate, explicit owner action, so phases 6 and 7 still need the owner's ruling
  naming the cap. Anything on the work PC. Changing the content security policy. Buying
  anything. Changing the owner's global or project instruction files.

## Rulings made under it

### Process

1. **Two coordinators.** The design track (this session) and the back-end track (the
   Rebuild 2 session) each coordinate their own steps and add their own section to
   `VERIFICATION.md`. Decision records take the next free number.
2. **Source look.** The split recorded in decision 0003 stands: the source supplies a
   component's layout, sizes, radius and density; the design system supplies colour values,
   typefaces, status shapes, gap states and motion.

### Run start and run activity

3. **Purpose step.** As mocked: the purposes as radio cards with what each runs. Pathway,
   complexity and effort are not on the page until the orchestrator (step 3A) defines them;
   step 5C revisits.
4. **One confirmation.** Start opens the warning modal, which states the USD 20 cap;
   confirming it is the analyst's Submit. There is no second confirmation.
5. **Stop.** A running run can be stopped: a secondary button that asks first. What ran
   stays readable.
6. **Resume.** A failed, interrupted or stopped run can be resumed. Resuming goes back
   through Start and its modal; the cap is the run's original cap, and what was spent counts.
7. **Rejected.** A run is rejected when a document changed after the summary was approved.
   Nothing ran and nothing was spent.
8. **Files.** A file read in part does not block Next; it carries its warning. An unreadable
   file blocks Next until it is removed or replaced.
9. **Modules in a run.** Several modules may run at once, so the steps list allows several
   current markers. A module in a live or interrupted run takes the run-state words and
   shapes (Queued, Running, Interrupted); a module that fails reads "Not assessable"; in an
   ended run an unstarted module reads "Not run". Finished and far-queued modules collapse
   with a count, as mocked. A step shows its marker and its badge, as mocked.
10. **Run activity** shows the current run only, with the run total and each module's cost
    and time where delivery supplies them.

### Library and Model

11. **Dashed ring.** "Delivered with gaps" and the gap badge use a 12px ring with a 2px
    dashed edge (the library session's measurement: 33 inked pixels reach 3:1, against 9
    for the 10px ring).
12. **Library home.** A card shows the latest finished run, with a Running badge and both
    dates when a newer run is in progress. Nothing from a failed run is shown; a capped
    run's delivered modules can be read.
13. **Evidence.** Downloads sit on the Summary tab and on the registers.
14. **Words.** "Delivered with gaps" stays as a module state. A file that cannot be read or
    was refused reads "Unreadable", with its reason beside it.
15. **Model periods.** By default: financial years, the last twelve months and the forecast
    years. Quarters, year to date, the prior twelve months and pro forma are not shown by
    default.
16. **Model charts.** Bullet, dumbbell, scatter and recovery stay where the Model mock put
    them. Limits are drawn on separate scales. A half-width chart card takes the whole row
    while its table side shows five or more columns. Forecast links to the Model for the
    statements.
17. **Disabled button.** As the source draws it (50 percent opacity), not the design
    system's disabled fill.

### Signal

18. **Reader and writer.** A reader may save stories, follow topics and react. Only a writer
    comments, shares to a group, starts a thread or attaches a story. A reader's Settings
    shows Topics and Notifications only.
19. **Reactions.** Words with a count, not symbols: Agree, Disagree, Seen.
20. **Kind filter.** Tabs, with the predecessor's kinds: All, Regulators, News, Ratings,
    Research. The thread panel's overlay is lightened so the feed stays readable. Stories
    sit on one card. The sources table folds kind and last item into other columns.
21. **Paid parts.** The AI line, signal strength, digests and "Run once now" are drawn in
    their "AI off" state. Nothing in Signal calls a model until the owner rules a cap; that
    is outside the delegation.

### Build and kit (added as they arise)

22. **Development-package advisories.** `npm audit` on the web lock reports 10 moderate
    advisories, all among development packages; `npm audit --omit=dev`, the gate, reports
    none. Two roots: vitest's mocker (fixed in 4.1.12, released 2026-10-15) and `minimatch`
    under typescript-eslint (a slow-pattern denial of service in a lint tool). Ruling: vitest
    and `@vitest/coverage-v8` move to 4.1.12 in step D2a's last pull request; the `minimatch`
    advisory is accepted, because the tool runs only on this repository's own files. The
    audit gate stays on runtime packages.
23. **Invalid fields.** An invalid input or select carries the design system's Error
    diamond and its message, not the source's info glyph, so the error never rests on colour
    alone (ruled by the D2a session after its review).

## Cost if wrong

Every ruling above changes fixture data, a label or a layout in one page group, not the data
contract's shape, except 9 and 10 (the run slice carries module states and costs) and 15
(the Model slice's period set). Those three are the ones to revisit first if the owner
disagrees.

## Not verified

- No ruling here was tested with an analyst or a portfolio manager.
- Rulings 5, 6, 8 and 9 assume orchestrator behaviour (stop, resume, parallel modules) that
  step 3A has not built.

# Low and Info findings held until after the final phase

Owner, 2026-11-15 about 00:30 UTC: "tell sessions to leave low findings to end of phase"; corrected
about 00:35 UTC: "correction leave all low findings until end of final phase" (both in the lead
coordinator's session). Kept by the back-end coordinator; one running list across phases, fixed in
one batch after the final roadmap phase (7), each checked against its reviewer's probe. A Low or
Info finding holds no PR, verdict or merge. High and Medium are unchanged. The headings below say where a finding
came from, not when it is fixed. Report paths are under the named worktree's `.superpowers/sdd/`
or the sessions' shared notes; the coordinator copies those out before a worktree is removed.

Each line: step and PR; finding id; file; what; probe or report path.

## Phase 1 (1B model, 1C provider, 1D sources)

- 1D #342 (2b-4): L1; tests; two rows (a UTF-8-valid file and a BOM file whose name reaches byte 4,096 stay read as UTF-8); `festive-franklin-1f7054/.superpowers/sdd/2026-11-14-phase-1d-sources/pr2b-4-adversary.md`

## Phase 2 (2A store, 2B checks)

- 2A #322: L1, L4 (were to ride in PR 3); see `strange-pasteur-eef6a5/.superpowers/sdd/2026-11-14-phase-2a-store/carry-forward.md`
- 2A 3a-2: invariants L1; `store/schema.py` docstring "(its open call with it)" can mislead 3c; `pr3/task-3a2-review-invariants.md`; precise L1 (three lines over 100, resolved by 3a-1's wraps at merge)

## Phase 3 (3A orchestrator, 3B delivery)

## Signal

- S-12 #343: A1 (predates); service: a committed add or remove can be answered 404 if the caller is removed before the reply's member read; `s12/review-adversary-1.md`

## Records (coordinator)

- #340: the 2A plan's D6 and D7 table rows show text the amendment replaces; one over-long line in the 3A plan's corrections.

## Later additions

- Signal S-10 #345: not verified at merge: hand mutants of the new guard `_TITLE_HELD_SQL` at head 56b4c02d (the 10 task-head mutants are killed); run them in the end-of-phase batch; `s10/probes/precise_mutants.py`, `relow_guard.py`
- 1C #338 (2h-2): Low; `provider/redact.py:296-297` docstring line break; `pr2h2/task-1-review.md`
- 1C #338 (2h-2): T1, Low unless round 3's mechanism covers it; `redact.py:404-408`; folders made of the Angstrom sign backtrack exponentially on an NFD near-miss (about 3.9 s at 10^5 characters, 12 folders); `pr2h2/probes/a_time_angstrom.py`, `a_time_nfd_wide.py`
- 2A #344 (3a-1): whole-branch L1, L2 (key rows missing: U1's place where the status refuses the call; #297 L1's pin) and Infos; full lines in `strange-pasteur-eef6a5/.superpowers/sdd/2026-11-14-phase-2a-store/lows-to-phase-end.md`; report `pr3/whole-branch-review-3a1.md`
- 2A #344 I1 (predates): U1's refusal of a damaged run lasts only while the store stays open; the next `open_store` refuses the whole file through `quick_check`. One sentence owed in U1's cost line.

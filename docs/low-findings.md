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
- 1D #342 (2b-4): L1, I1, I2, S1, N1 and 3b-2's six (S-L1, S-L2, S-I1, Q-L1, Q-I1); each with file and probe in `festive-franklin-1f7054/.superpowers/sdd/2026-11-14-phase-1d-sources/phase-lows.md`
- 1D #342 P2 (predates, Info): `sources/html.py` `_encoding`; a declared charset value is also ended by any byte outside `[A-Za-z0-9_.:-]`, so `iso-8859-1(15)` reads as iso-8859-1; closing rule: the value must end at a quote, whitespace, `;` or `>`; `probes/pr2b4-wb-3.py`
- Records #349: 3B plan not-verified line on the cell grammar and answer-key row 3 do not name R21 and R20; R17 and S7 word "no exponent" differently; 8a has no answer-key row
- Ledger owed in the next records PR: 1D 2b-3 (#320) task 1 `agent=mx-feature fix-rounds=0 gates-first-pass=n`, task 2 `agent=mx-feature fix-rounds=0 gates-first-pass=y`, two Low batches `agent=mx-scaffold fix-rounds=0 gates-first-pass=y`; 2b-4 (#342) `agent=mx-feature fix-rounds=0 gates-first-pass=y`
- 3A #347 (PR 1): task L1 to L6, I1, I2; sweep S1 to S6; whole-branch W1 to W4; full lines and probes in `3a-orchestrator-8665a5/.superpowers/sdd/3a/1/ready.md` (`probes/`, `sweep/`, `arch-probes/`). L5 (`plan.py:76-77`, an optional producer absent from a supplied table is dropped silently) needs the coordinator's ruling before any PR supplies its own table. W1 (producers() key order differs between processes) must be fixed by whichever of 9b, 8, 11 first serialises it.
- 3A #347 W5, records owed: plan D1 still lists required registers (corrected in #349's section, table row unchanged); the plan's PR 1 key row names 9d040f8 where the key says 8e3954a; ports.md does not say the predecessor's `retained` pins in dependencies and plan are not ported. Ledger: `3A-1 task=1 agent=mx-feature fix-rounds=0 gates-first-pass=y`. ports.md line: orchestrator/ catalogue `8e3954a`, CP-1 scored from methodology update row 1. Process note: the implementer wrote code before tests.
- 1D #314 + #335 set: whole-branch B-L1, N-L1, B-I1, N-I1, S-I1, P-I2; #335 security L1 to L4, I1, I2; sweep X2, X3; task review's five; all in `festive-franklin-1f7054/.superpowers/sdd/2026-11-14-phase-1d-sources/phase-lows.md`. Ledger: 3b task `agent=mx-feature fix-rounds=0 gates-first-pass=y`, fixes 1 to 3 `agent=mx-feature fix-rounds=1|2|3 gates-first-pass=y` (round 3 on an mx-autonomous plan), Low batch `agent=mx-scaffold fix-rounds=0 gates-first-pass=y`; 3b-2 `agent=mx-feature fix-rounds=4 gates-first-pass=y` twice (6ca7933f's source reverted in 73a5366b; fe28f58c fresh and blind).
- 1C #338 round 3: R1 (ruling 26, named limit of decision 0012); `provider/redact.py`; a known NFD name ending in a combining mark leaves that mark visible; `1c-provider/pr2h2/r3r_tail_mark.py`, `r3r_unit_enc.py`, `r3r_tail_two.py`. Records owed: add the limit line to decision 0012.

# 0014 A call a crash left open is settled by an owner-stated line, never by rewriting the call

Date: 2026-11-14. Decided by: coordinator, under decision 0006 and the owner's instruction of
2026-11-14 22:20 UTC ("tell coordinators to resolve all descisions"). The owner can reverse it.

## Why

The store writes a call row at `open_call` with its hold and closes it at `close_call` with what
the provider billed (2A plan, PR 3). A process that dies between the two leaves the call open.
The 3A plan's D7 says what that means: one hold is not shown to bound what the call cost (a call
may make several model requests, and a compaction's charge is outside `billed_usd`), so the run's
spend is unknown, the run does not resume by itself, and it stays stopped until the owner settles
the call. The store needed a place for that settlement. Three were possible: close the call late
with an owner-typed amount in `billed_usd`; add columns to `calls`; or a separate table.

## Decision

1. **A separate, append-only table, in migration 3 (2A PR 5).** One row per open call: the call's
   key, the amount the owner states in USD (money text, at least 0, the same CHECK as the other
   money columns), who stated it, the store's time, and a free note. Nothing in migration 2.
2. **The call row is never changed by a settlement.** It stays open as written. A closed call
   stays immutable, and a settlement naming a closed call is refused (`StoreRefused`). A second
   settlement of the same call is refused (`StoreConflict`); a wrong amount is corrected by a
   later decision, not by an overwrite.
3. **Read back as what it is.** A settlement reads as an owner-stated line, never as
   `billed_usd`. A run's spend is known when every call is closed or settled; the total then
   names how much of it is owner-stated. Delivery shows that part as stated by the owner, not as
   billed (3B draws only what the store gives it).
4. **Outside the run gate.** Attempts, calls and compactions are written only while a run is
   `running` (2A rulings U9). A settlement is written on a stopped run, so its table is outside
   that gate; the migration 2 docstring says so.
5. **Who may write one.** Only an explicit operator action, with the amount typed by the owner
   from the provider's own billing page. No code infers an amount, and none sums an open hold as
   spend. Resuming a settled run is still the owner's explicit action (decision 0006, ruling 6).

## Cost if wrong

A forward-only migration that adds columns or a second table; no stored row is lost or rewritten.

## Not verified

Nothing is built yet: this record precedes 2A PR 5's brief. Whether the provider's billing page
shows a per-call amount for a call that never returned is not known; if it does not, the owner
states the run's worst case and the note says so.

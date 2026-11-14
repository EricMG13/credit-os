# 0008 CP-DR's web lookup is not carried into the rebuild

Date: 2026-11-14. Decided by: owner, in the back-end coordinator's session ("Leave it out"),
when asked whether the rebuild carries the lookup.

## Decision

The rebuild does not port CP-DR's web lookup: the page fetch and SEC EDGAR tools, the domain
allowlist and the as-of rule that the predecessor added on 2026-11-13
(`docs/rulings/2026-11-13-cpdr-web-lookup.md` there, merged as #110). A run reads the issuer's
supplied files and nothing from the network.

## What follows

- Step 3A's port of the launcher drops the import of `research/weblookup.py`, the lookup tools
  and the instructions that describe them. `research/` stays on the left-behind list in
  `docs/legacy/ports.md`.
- CP-DR's method text (phase 6) is adapted so that it does not promise a lookup: it works from
  the supplied files and states what it could not find as a gap.
- The `Source type` rule for a web row in `## Sources` (step 2B) stays as a check; with no
  lookup, a module has no web row to write.
- This differs from the predecessor, where the lookup is on by default for public cases. The
  predecessor's ruling is not reversed there; it is not carried here.

## Not verified

- How much of CP-DR's findings in the retained TransDigm run came from web pages; that run
  predates the lookup.
- Whether a module can still name a web source from the model's own knowledge; step 2B's plan
  rules on that.

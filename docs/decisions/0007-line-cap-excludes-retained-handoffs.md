# 0007 The line cap does not count the retained handoff fixtures

Date: 2026-11-14. Decided by: the back-end coordinator under the owner's delegation
(decision 0006).

## Decision

The 800-changed-line check in `.github/workflows/python.yml` excludes
`tests/fixtures/handoffs/**` and nothing else under `tests/fixtures`.

## Why

Step 1A's answer key is 27 handoff files, 4,652 lines, copied byte for byte from the retained
public TransDigm run (decision 0002, item 3) and the predecessor's synthetic fixtures. They are
frozen data, not written code. The cap exists to keep written changes reviewable, and lock files
are excluded on the same reasoning. The alternative, about seven fixture-only pull requests, adds
review rounds with nothing to review.

## Limits

- Only copied handoff files, their `SHA256SUMS` and a `.gitattributes` may live in that folder.
- A test checks every file against `SHA256SUMS` and fails on a mismatch. It also fails on any file
  in the folder that `SHA256SUMS` does not list (other than `SHA256SUMS` itself and
  `.gitattributes`), so a written file cannot sit there uncounted.
- Expected values and any written test data stay outside the folder and count toward the cap.
- This is a change to a gate's scope made by decision record, not a loosening to pass one pull
  request, and the owner can reverse it.

Not verified: that nothing but copied files is ever placed in the folder is checked by review,
not by a gate.

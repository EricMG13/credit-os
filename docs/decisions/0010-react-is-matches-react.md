# 0010 `react-is` matches React

Date: 2026-11-14. Decided by: coordinator, under the owner's delegation (decision 0006);
raised by step D2a's whole-branch review and by step D2c before its bar charts.

## Decision

`web/` adds `react-is` 19.3.0 as a direct dependency, at the exact version of `react` and
`react-dom`.

| Package | Version | Released | Licence | Why |
| :--- | :--- | :--- | :--- | :--- |
| react-is | 19.3.0 | 2026-09-09 | MIT | Recharts' peer dependency. Recharts' README (3.10.1): "`react-is` needs to match the version of your installed `react` package" |

## Why

Recharts 3.10.1 declares `react-is` as a peer (`^16.8 || ^17 || ^18 || ^19`) and nothing in
`web/` installed one. npm satisfied the peer with the only copy in the tree, 17.0.2, which is
there for a test tool (`@testing-library/dom` through `pretty-format` 27.5.1). So a test
tool's dependency chose a version that ships in the built bundle. `react-is` 17 does not
recognise React 19 elements, so Recharts' child discovery through fragments (a `<Cell>` in a
`<Bar>` or `<Pie>`) can fail without an error. The line chart from step D2a does not use that
path, which is why nothing failed there.

The alternatives were to leave 17.0.2 and forbid `<Cell>` children by convention, or to force
one version with npm `overrides`. The first leaves a silent failure for the next author; the
second also changes what the test tool gets. A direct dependency is what Recharts documents.

## Rules

- `react-is` moves with `react` and `react-dom`: the three are changed together, to the same
  version.
- The copy `pretty-format` uses stays whatever that tool asks for; it is not shipped.
- When `react` is next changed, this record is amended with the new version.

## Not verified

- That `react-is` 17 fails with React 19.3 in this tree was reasoned from the two packages'
  code by step D2c, not reproduced in a browser.
- The work PC's package source was not checked for `react-is` 19.3.0.

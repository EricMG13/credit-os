# Step 1A: one handoff parser to a typed document

Date: 2026-11-14. Coordinator: the Rebuild 2 session. This file is the plan and the
sub-session's brief. Legacy read at `legacy/main` `cbf4400`
(`git show legacy/main:<path>`; never check it out, never change it).

**Goal:** `src/credit_os/handoff/` parses a module's Markdown handoff into one typed,
immutable document. It is the only place in the package that reads handoff Markdown. Nothing
here renders, delivers, scores or knows a module's own headings.

**Ends in:** a sequence of pull requests against `main`, each within 800 changed lines, each
passing both review steps. PRs are opened one at a time; the next starts from `main` after
the coordinator merges the last.

## Files this step may touch

`src/credit_os/handoff/**`, `tests/handoff/**`, `tests/fixtures/handoffs/**`. Nothing else;
not `pyproject.toml` (standard library and pydantic 2.13.4 only), not `VERIFICATION.md`, not
`docs/legacy/ports.md`.

## Pre-flight (coordinator)

- `src/credit_os/handoff/` holds an empty `__init__.py`. The layering test lets `handoff`
  import only `sources`.
- Legacy grammar code: `src/deploy_workflow/handoff_delivery.py` (810 lines: `physical_lines`,
  `heading_of`, `hide_comments`, `hide_fenced`, `section`, `table_row`, `table`, `is_gap`,
  `names_issuer`), `markdown_delivery.py` (`_prose_groups`, `gap_limitations`,
  `require_issuer`), `model_handoff_delivery.py` (`_inline_comments`, `_shown`, `_table_at`,
  `_literal_tables`), `prose_checks.py` (`is_earlier_format`, `_sentence_lines`,
  `DATA_SECTION_PREFIXES`), `confidence.py` (`inputs`), `apps/issuer-library/credit_os/store.py`
  (`parse_source`, `_reader_summary`, `STATED_GAP`), `owners/cpos_launch.py`
  (`_blocked_at_gate`, `_stated_gap`, `_has_register`), and the Basis item grammar, which
  exists only in `apps/issuer-library/credit_os/web/reader.js` (`splitBasis`, `basisItem`).
- These readers disagree with each other on comments, heading indent, fence characters,
  separator rows and escaped pipes. The rulings below pick one rule each.
- Left out on purpose: `mapped_module` and everything in `report_view.py`, `display.py`,
  `bindings/`, `run_scopes.py` (per-module mapping and rendering, not grammar).

## Prior art (searched 2026-11-14)

- Owner's repositories: the legacy readers above are the source. Decision: adapt, into one
  reader.
- Public GitHub, `gh search repos "markdown pipe table parser" --language python`: no result.
  A general Markdown library (markdown-it-py, mistune) is a new dependency and does not keep
  the line numbers and the project's own rules (gap markers, Basis lines, fixed skeleton).
  Decision: build new on the standard library.

## Answer keys (implementers do not edit them or weaken a comparison)

1. **Retained run** (decision 0002, item 3): the 20 handoffs in
   `~/Documents/RBOT-HTML/runs/cpos-tdg-sol-medium-all-001/deliveries/abd687ca74b49fbd703ed27dc3f8f9edaa20e12f0236efa80d9d1ea4757c2baa/`
   (public TransDigm case). The controller copies them byte for byte to
   `tests/fixtures/handoffs/tdg-2026-11-09/` in PR 1 with a `SHA256SUMS` file, and a test
   checks every file against it. They prove the earlier format.
2. **Synthetic new-format fixtures**: `git show
   legacy/main:apps/issuer-library/fixtures/synthetic-new-format/<name>` (five handoffs) and
   the two fragments under `tests/fixtures/sol_medium_run_2026_11_09/`, copied to
   `tests/fixtures/handoffs/synthetic-new-format/` and `.../fragments/`.
3. **Expected values** for the golden tests are written by the controller from reading the
   fixture text (section titles and line numbers, table shapes, a chosen cell per table, gap
   rows, Basis items), in `tests/handoff/expected/*.json`, before the implementer starts. They
   are not produced by running the parser.
4. The seven legacy table tests in `tests/test_handoff_delivery_table.py`, adapted.

## Rulings (grammar; each is a test)

- **Lines:** split on `\n`, `\r\n`, `\r` only. A leading UTF-8 byte-order mark is dropped.
  Every node carries its 1-based line number. The document records the SHA-256 of the bytes.
- **Headings:** one to six `#`, no leading space, then a space. `#1 risk` is prose.
- **Fences:** three or more backticks or tildes, indent of up to three spaces; an unclosed
  fence ends at the next level-2 heading and is recorded as unclosed.
- **Comments:** `<!-- -->` hidden with line numbers kept; never closed is an error. A
  `<!-- table-id: X -->` comment tags the next table.
- **Skeleton:** the level-2 headings outside fences and comments are exactly Request, Sources,
  Findings, Calculations, Gaps, Next module, once each, in order. Trailing spaces on a heading
  are ignored. (The legacy checks raw lines; this is the stricter reading and is recorded as a
  divergence.)
- **Tables:** boundary pipes on both sides, up to three leading spaces, a separator row of
  `:?-{3,}:?` cells, at least two columns, the same cell count on every row, `\|` unescaped. A
  whole-line bold label directly above names the table.
- **Front matter:** `key: value` lines between `---` lines at the very top, kept as strings;
  no YAML library.
- **Gaps:** a cell or passage is a gap when it is empty, "—", "Insufficient Information",
  "Not reconstructed", or starts "Not supplied" or "Not calculable". A gap is a distinct
  value, never zero and never an empty string.
- **Format:** new format when the first level-3 heading under Findings is "Bottom line";
  otherwise earlier. New format exposes Bottom line, Key findings, Contrary evidence and what
  would change the view, Limitations; a Bottom line starting "Not assessable:" marks a blocked
  module. Earlier format exposes the Reader summary's two tables.
- **Basis lines:** the last line of a paragraph or list item starting "Basis: ", split on
  "; ", final full stop dropped; items are a calculation id, an upstream module
  (`name (CP-X)`), a source file with optional page or pages, or plain text.
- **Typed data sections** by heading prefix: "Chart data: ", "Events: ", "Map: ",
  "Forecast inputs" (fenced JSON kept as text, not interpreted), "Confidence inputs" (the
  Input | Value table as rows; no score is computed here).
- **Registers and Sources (predecessor rulings of 2026-11-12 and 2026-11-13,
  `docs/legacy/methodology-updates.md`):** the parser requires no register. Ten modules no
  longer write certain registers, and which register a module owes is a rule for steps 2B and
  3A, not for the grammar. A register that is present is exposed with its id (from a heading
  that starts with the id, or a table-id tag). The Sources table is exposed with its own column
  names, whatever they are, including a `Source type` column when present; whether a row needs
  one is a check for step 2B.
- A parse failure is an error type carrying the line number and a plain message. No
  catch-all; nothing is guessed.
- Amounts, units, periods and source names are kept as the exact text; nothing is converted
  to a number in this layer.

**Rules added while building PR 1 and PR 2 (coordinator, 2026-11-14; each is a test):**

Scan (PR 1, #35):
1. `<!--` inside an inline code span is literal; spans are read left to right as tokens.
2. A line that began inside a comment is never a heading or a fence line; the text after its
   `-->` is shown.
3. A fence opener is tested before comments, so comment text on an opener line stays in the
   fence info.
4. A backtick fence's info holds no backtick; a closer is the same character, at least as
   long, with only spaces or tabs after it.
5. A `## ` line inside a fence ends it, even when a closer follows, and is read again in the
   normal state. Known limit: a fenced block that itself holds such a line is read as unclosed
   there.
6. The heading test is on the line as written (`#{1,6}` and a space; a bare `##` or a tab is
   prose); the title is the shown text.
7. A shown text left with only whitespace after a removal becomes `""`.
8. `shown` is the line with comments removed; a one-line comment is hidden too.

Blocks (PR 2, #42):
- Inline code spans: a run of n backticks opens a span only when a later run of exactly n
  follows on the same line, the nearest closing it; an unmatched run is text. This replaced a
  backtracking pattern and changes no line of the 27 fixtures.
- A table may have a header and no rows, and an empty first cell. A pipe inside a code span
  still splits a cell.
- The parser removes no text. A one-line bold paragraph directly above a table stays a
  paragraph, and the table also carries it as `label` with `label_line`; the layer that knows
  the section decides whether it is a caption or prose.
- A line outside a fence whose first non-blank character is `|` but which is not a table row
  (any leading whitespace other than up to three spaces: four spaces, a tab, a no-break space)
  is refused; it is never read as a paragraph.
- Lists are flat. `read_blocks` takes whole heading-to-heading ranges.

## PR sequence

| PR | Delivers |
| :--- | :--- |
| 1 | Fixtures and `SHA256SUMS`; lines, headings, fences, comments; error type |
| 2 | Blocks: tables, paragraphs, list items, code blocks |
| 3 | Front matter, section tree, skeleton check, `HandoffDocument` and `parse`; golden tests on all 27 fixture files |
| 4 | Format detection, reader passages, Basis lines, earlier-format reader summary |
| 5 | Gaps, confidence inputs, typed data sections, register tags, blocked flag |

A PR that would pass 800 lines is split, not trimmed of tests.

## How it runs

Global rules §1, §3 and §7. The sub-session is the controller and writes no code: `mx-feature`
implements test first, `mx-precise` reviews each task. Every brief and review prompt carries:
no stub or fake value standing in for real behaviour; no catch-all that hides a failure; the
answer keys above. Property tests (`hypothesis`) for the line splitter and table reader.
Mutation testing is not required (not sensitive code). Per task, the gate is
`uv run --locked python tools/gates.py` (run `npm ci` in `web/` once first), exit 0. Before
each PR is ready: `/sweep refactoring discover changed-update`, then the whole-branch review
(`mx-architect` running `adversarial-reviewer`, fresh agent, §7 severities); verdicts and
report paths in the PR body; CI green on both runners. Fix rounds follow §1.

## Done when

Each PR is open with CI green and both reviews passed, and the sub-session has sent the
coordinator one message per PR: the PR number, verdicts, report paths, gate exit codes, ledger
lines (`1A-<pr> task=<n> agent=<name> fix-rounds=<n> gates-first-pass=<y|n|n/a>`), parked Low
findings and a `Not verified:` line. The coordinator reads the diff and merges. The
sub-session does not merge and does not edit shared records.

## Not verified

- The retained run proves the grammar as it stood on 2026-11-09; the new format rests on five
  synthetic handoffs until a newer full run is retained.
- The rulings were written from a trace of the legacy readers, not from running them. Where a
  retained handoff does not parse under a ruling, that is a finding for the coordinator, not a
  reason to loosen the rule or edit the fixture.
- Legacy behaviour visible only in its end-to-end tests was not read.

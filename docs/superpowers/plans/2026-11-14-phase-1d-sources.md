# Step 1D: source pinning and page reading

Date: 2026-11-14. Coordinator: the Rebuild 2 session. This file is the plan and the
sub-session's brief. Legacy read at `legacy/main` `cbf4400`
(`git show legacy/main:<path>`; never check it out, never change it).

**Goal:** `src/credit_os/sources/` pins an issuer's source files (name, SHA-256, size, kind)
and reads each into pages of text, for PDF, docx, HTML, xlsx, csv and plain text.

**Ends in:** a sequence of pull requests against `main`, each within 800 changed lines, each
passing both review steps, opened one at a time.

**This is sensitive code** (security: it parses untrusted files). Each reader task also gets
an `mx-adversary` review, and changed files get mutation testing (`mutmut`, run with `uvx` and not added to `pyproject.toml`), survivors killed
or justified in the PR.

## Files this step may touch

`src/credit_os/sources/**`, `tests/sources/**`. Nothing else: `pypdf` 6.21.4 is already in
the lock (step 0C part 1). Not `VERIFICATION.md`, not `docs/legacy/ports.md`.

## Pre-flight (coordinator)

- The legacy has two source pipelines. **Ruling: port the live launcher's**
  (`owners/cpos_launch._issuer_files`, `model/handoff._pages`, `_workbook_pages`,
  `ModuleTools.read_pages`): a file is pinned by name and hash and read into a list of page
  strings. The other pipeline (`deploy_vii/preparation.py`, `contracts.py` spans and
  coverage, `readiness.py`, the CP-0 review) belongs to the structured runtime the roadmap
  leaves behind; only its guards are taken (below). `pdf_headers.py` recovers period headings
  for financial mapping, has no live caller, and is deferred. `inline_xbrl.py` is not on the
  launcher's path and is not ported here.
- Readers to adapt: `src/deploy_workflow/docx_text.py` (65 lines), `html_text.py` (181),
  the xlsx reading in `model/handoff.py` (`_is_workbook`, `_workbook_pages`, `_cell_label`)
  with the zip and XML guards of `deploy_vii/preparation.py` (`xml_part`, size constants),
  and `run_inputs.read_capped`.
- No legacy code reads csv with the `csv` module; the launcher decodes it as text and cuts it
  into 12,000-character pages.
- Legacy reader tests build every fixture inline (hand-built zips, `PdfWriter` pages); none is
  a real document. `openpyxl` appears only in legacy tests and is not used here.
- `pypdf` 6.21.4 documents, read through Context7 on 2026-11-14 (`/py-pdf/pypdf/6.21.4`):
  `PdfReader(stream, strict=False, password=None, root_object_recovery_limit=10000,
  xref_stream_maximum_entries=2000000)`; `is_encrypted` property; `reader.pages`;
  `page.extract_text(extraction_mode="plain" | "layout", ...)`, where layout mode is described
  as experimental; `pypdf.errors.PdfReadError`, base `PyPdfError`. Returned documents are
  data; the tasks confirm each call in the installed source.

## Prior art (searched 2026-11-14)

- Owner's repositories: the legacy readers above. Decision: adapt, on the standard library
  plus `pypdf`.
- Public GitHub: not searched. Reading docx and xlsx without a library is a known small job
  (`zipfile` and `xml.etree`); a library is a new dependency.

## Rulings

- **Pin:** `SourcePin(name, sha256, size_bytes, kind)`. `name` is the path relative to the
  issuer folder in forward slashes; `sha256` is of the original bytes, always, including for
  HTML and docx (the legacy pins the converted text; that is not kept). Names that differ only
  by case are refused. Absolute paths, drive-relative names and paths that leave the folder
  are refused.
- **Which files:** walk the folder; skip names starting with `.`, `_` or `~$`; accept the
  suffixes `.pdf .htm .html .docx .txt .md .xlsx .csv`; anything else is listed as skipped
  with its reason, never silently dropped. Kind comes from the suffix and is checked against
  the content's first bytes (a `.pdf` that does not start `%PDF-` is unreadable).
- **Reading a file:** regular files only; at most 50 MiB, checked from the file's size before
  reading; a zip's declared expanded size at most 200 MiB.
- **Pages:** `read_pages(pin, path) -> tuple[Page, ...]` with `Page(number, text)`, numbered
  from 1. A file that cannot be read gives a typed error with the reason; a file with no text
  at all is an error, not an empty list. Nothing is guessed and there is no catch-all.
- **PDF:** `PdfReader(..., strict=True)`; encrypted files refused; one page per PDF page,
  `extract_text(extraction_mode="layout")`; a page that raises is recorded as unreadable and a
  page with no text as empty, each distinct from text; no OCR.
- **docx:** body paragraphs, table rows as cells joined by " | ", content controls read
  through, deleted tracked text dropped; cut into 3,000-character pages on line ends.
- **HTML:** strict UTF-8 (byte-order mark aware), else a declared charset among
  windows-1252, iso-8859-1, ascii; script, style, head and hidden subtrees dropped; the
  legacy's line and block tag lists kept exactly; 3,000-character pages.
- **xlsx:** standard library only; one page per sheet; each stored cell as `A1=value`, a
  formula with its cached value; hidden sheets, rows and columns marked; shared strings and
  styles resolved with index bounds checked; external or escaping relationships refused.
- **csv and text:** decoded as UTF-8 with an optional byte-order mark, else windows-1252
  (stated in the page record); NUL refused; csv is parsed with the `csv` module and one line
  per row is written as cells joined by " | "; 12,000-character pages.
- **Zip and XML guards for docx and xlsx:** duplicate member names refused; `BadZipFile`,
  `zlib.error`, `EOFError`, `RuntimeError` (encrypted member), a missing part and a bad index
  all become "unreadable"; a part containing `<!DOCTYPE` or `<!ENTITY` is refused before
  parsing.
- Cell values, amounts and dates are kept as the stored text. Nothing is converted or
  computed in this layer.
- Paths are handled with `pathlib`; every rule above holds on Windows (CI runs both).

**Amendments (coordinator, 2026-11-14; each is a test):**

- **A reason per name rule.** `validate_name` says which rule refused the name: an empty or
  dot segment or one that leaves the folder; a trailing dot or space; a reserved device name;
  a forbidden character, named as `U+XXXX`; too long. The file name stays in the message.
- **More names refused.** Private-use and unassigned characters (categories `Co`, `Cn`); a
  segment that starts or ends with any space character (`Zs`, so U+3000 and U+00A0); `CLOCK$`
  in any case, with or without a suffix. Key rows use noncharacters (U+FDD0, U+FFFE), which
  are unassigned on every Python patch level; what counts as unassigned otherwise follows the
  interpreter's Unicode table.
- **Length.** A segment is at most 255 bytes in UTF-8 and a whole name at most 1,024 bytes;
  a longer one is refused before any file system call.
- **Kind.** The pin checks the first bytes only. Each reader proves the structure of its kind
  and raises "unreadable" when it does not hold: a zip that is not a docx, an xlsx offered as a
  docx, OLE or executable bytes offered as text or csv. The NUL refusal covers HTML as well as
  csv and text.

## Answer keys (implementers do not edit them or weaken a comparison)

1. Fixtures are built in the tests from literal bytes: hand-written zips for docx and xlsx,
   literal HTML and csv, and a minimal PDF written out as bytes with a known text stream (not
   produced by `pypdf`). No real document is committed.
2. Expected page texts and pins are literals written by the controller in each task brief
   from the fixture's content, including the SHA-256 computed with `shasum`, before the
   implementer starts.
3. The five legacy tests in `tests/test_docx_text.py` and the xlsx cases in
   `tests/test_handoff_loop.py` lines 196 to 300, adapted, minus the one that needs
   `openpyxl`.
4. A hostile set, one test each: a zip with duplicate names, a zip whose declared size passes
   the cap, an encrypted PDF, a truncated PDF, an XML part with an entity declaration, a path
   that leaves the folder, two names differing only by case, a file over the size cap.

## PR sequence

| PR | Delivers |
| :--- | :--- |
| 1 | Errors, `SourcePin`, name and kind rules (#41) |
| 1b | The amended name rules; capped read and path resolution (`files.py`); two PRs if together they pass 800 lines |
| 1c | Folder walk |
| 2 | Text, csv and HTML readers |
| 3 | Zip and XML guards; xlsx reader |
| 4 | docx reader |
| 5 | PDF reader |

## How it runs

Global rules §1, §3 and §7. The sub-session is the controller and writes no code: `mx-feature`
implements test first; `mx-precise` reviews each task; `mx-adversary` on the reader tasks.
Every brief and review prompt carries: no stub or fake value standing in for real behaviour;
no catch-all that hides a failure; the answer keys. Property tests (`hypothesis`) for paging
(pages rejoin to the text) and the folder-walk rules. Per task the gate is
`uv run --locked python tools/gates.py` (run `npm ci` in `web/` once first), exit 0. Before
each PR is ready: `/sweep refactoring discover changed-update`, then the whole-branch review
(`mx-architect` running `adversarial-reviewer`, fresh agent, §7 severities); verdicts and
report paths in the PR body; CI green on both runners. Fix rounds follow §1.

## Done when

Each PR is open with CI green and its reviews passed, and the sub-session has sent the
coordinator one message per PR: the PR number, verdicts, report paths, gate exit codes,
mutation result, ledger lines (`1D-<pr> task=<n> agent=<name> fix-rounds=<n>
gates-first-pass=<y|n|n/a>`), parked Low findings and a `Not verified:` line. The coordinator
reads the diff and merges. The sub-session does not merge and does not edit shared records.

## Not verified

- No real issuer document is read in this step; how `pypdf`'s layout mode reads a real annual
  report, and how long it takes, is unknown until phase 6.
- The readers are written from a trace of the legacy code, not from running it.
- The windows-1252 fallback for csv is new here; the legacy fails on such a file.
- Whether the live launcher depends on the inline XBRL period lines; if step 3A's plan finds
  it does, that reader is added then.

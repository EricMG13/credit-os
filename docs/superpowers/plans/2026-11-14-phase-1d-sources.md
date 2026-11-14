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
- **Order and wording (#61).** Characters first, then the whole-name length, then per segment:
  empty or dot, edge space or trailing dot, reserved device name, segment length. A leading
  ASCII space is refused (it is `Zs`).
- **Echo bound (#61).** Every message that echoes a name shows its first 120 characters, then
  `…`; a path is shown whole. A deep name can lose its file part: accepted.
- **Links (#59, #82).** `source_path` refuses a name that
  is, or passes through, a symbolic link or a Windows junction, even inside the source folder;
  each component below the resolved folder is tested. A failure of that test is refused, not
  raised untyped. `read_capped` refuses a final link on every platform: by `O_NOFOLLOW` where
  it exists, else by a test before the open (Windows). A link swapped in between a check and
  the open is not closed by this; when an existing pin is read, its size and hash guard the
  content (not when a pin is created: see the folder walk).
- **An unsearchable directory below the folder** is `SourceRefused` "cannot be resolved" from
  `source_path`, not `SourceUnreadable` from the open.
- **`read_capped` is at the complexity cap (15).** The next change that adds a branch to it
  carries the split, with an `mx-adversary` pass.
- **Reserved names (#82).** `COM0` and `LPT0` are refused as reserved device
  names (CPython 3.12's table omits them; that Microsoft's naming page lists them is from memory,
  not fetched).
- **For the first layer that loads pin records (store).** pydantic's `errors()` and `json()`
  carry the whole refused name; that layer bounds it before it prints one. A path with a lone
  surrogate gives a message that cannot be encoded as UTF-8: the first layer that prints or
  stores a `SourceError` encodes with `backslashreplace`.
- **The folder walk (#100), `sources/walk.py`.** A pin carries its name exactly as the
  directory listing gives it. A folder where two pinned names have the same key
  `NFD(casefold(NFD(name)))` (Unicode canonical caseless matching, which refuses more than
  case folding alone) is refused, naming both: the work PC is Windows. A directory the walk
  would enter whose own name fails `validate_name` refuses the folder, checked before it is
  listed; one it does not enter (hidden, excluded) is a skipped row. A skipped entry
  whose name fails `validate_name` is listed with its reason and its name written with ASCII
  backslash escapes; a file with an accepted suffix and an invalid name still raises. A
  listing failure is `SourceUnreadable` and the walk returns nothing. On a case-insensitive
  volume `read_pinned` may read a file whose name differs by case: accepted, the digest
  guards content. A directory swapped for a link during the scan can put outside names into
  the skipped list: accepted. When a pin is created no digest exists yet, so a link swapped in
  between `source_path`'s check and the open is hashed and pinned: an accepted limit, reported
  to the owner; closing it needs descriptor-relative opens.
- **PR 1e (#135).** An `OSError` from `root.is_dir()` in `source_path`
  or from `os.close` in `read_capped` is typed, not raised bare; `validate_name` refuses the
  slash look-alikes U+2044, U+2215, U+2571, U+FF0F and the invisible fillers U+115F, U+1160,
  U+3164, U+FFA0 (with the Windows-reserved punctuation, a closed list); the walk's property
  test and three bad-name rows that run on Windows. A close that fails after another error is
  a note on that error; a close that fails alone is `SourceUnreadable`.
- **Ruled for PR 2 (#161).** Every reader returns `SourcePages(pages, encoding)` of
  `Page(number, text, state)`, numbered from 1; readers are pure functions of bytes and
  `read_pages(folder, pin)` arrives with PR 5. Pages are consecutive slices that rejoin to the
  text exactly (text and csv 12,000 characters, HTML 3,000), ending at a line end where one
  is in reach; the predecessor's header line and `textwrap` are dropped, so page numbers
  differ from its. Text: UTF-8, else windows-1252 strictly; a control character other than
  tab, LF, CR and form feed is refused by name. csv: comma, strict, no sniffing; a line break
  in a cell is one space. HTML: the predecessor's tag lists; the reader holds a stated
  peak-memory bound by a committed `tracemalloc` test, with a lower size cap for HTML if the
  bound needs one; it is its own PR 2b with an adversarial review.
- **PR 2b-1 (#209) is merged** (HTML decoding and the line writer). PR 2b is cut 2b-1, 2b-2
  (the HTML engine, on `html.parser` at Python 3.12.14 with tests that pin the parser
  behaviour relied on, decision 0011) and 2b-3. Ruled for PR 3 (xlsx, standard library): a
  page-text cap of 32 Mi characters; expat; rows and cells in ascending order, a cell with no
  `r` read at the next position (the reviewer checks this against the format's published
  description); a formula cell shows its cached value, a shared string included; comments
  are not read; Strict OOXML is refused; five PRs 3a to 3e, 3d with a batched review.
- **PR 2 (#161) is merged.** Carried to PR 2b-1, key rows first: the two mutation survivors
  that are not equivalent (`cut_stream`'s inner `>=`; `held = 1` in `csv_pages`, a row cap lower
  by one after the first row) and an independent reference for `test_cut_stream_property`. A
  memory test states, for each shape, which class of wrong reader it must fail. For 3A: a csv
  of blank rows takes about 1.4 s per MiB and no time bound is stated.
- **Ruled for PR 2's first task.** An `OSError` without `strerror` gives `cannot read` with
  the error's class name, not `(None)`, failing test first; the comment in `source_path`
  says, as the walk's docstring does, that no digest exists when a pin is created.
- **For step 3A's plan.** The walk has no bound on the number of files or total bytes of a
  folder; a run-level bound is 3A's question. The first layer that stores or shows a
  `SourceError` keeps its notes and decides whether the absolute path in its message is kept.
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
| 1b-names (#61) | The amended name rules and the bounded name echo |
| 1b (#59) | Capped read, path resolution and the symbolic-link refusal (`files.py`) |
| 1c (#82) | `read_capped` refuses a final link on Windows; `COM0` and `LPT0` |
| 1d (#100) | Folder walk (`pin_folder`, `PinnedFolder`, `Skipped`) |
| 1e (#135) | The two untyped errors, the wider name refusals, the walk's property test |
| 2 (#161) | Text and csv readers; `Page` and `SourcePages` |
| 2b | HTML reader, with its peak-memory bound |
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

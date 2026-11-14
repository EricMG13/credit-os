# 0011 Python is pinned to 3.12.14 or later within 3.12

Date: 2026-11-14. Decided by: owner (the fact), coordinator (what follows from it, under
decision 0006).

## The fact

Asked "Which Python 3.12 patch level does the work PC run?", the owner answered "3.12.14 or
later".

## Why it was asked

`html.parser` in the standard library changed during 3.12: 3.12.14 carries the 2025 parser
changes (`locatetagend`, `commentabruptclose`, `RCDATA_CONTENT_ELEMENTS`, a different
`check_for_whole_start_tag`), 3.12.10 does not. Two readers go through it: Signal's feed text
reader (`signal/feeds.py`, in pull requests not yet merged when this was written) and the HTML
source reader (`sources/html.py`; its parser part is step 1D PR 2b-2, not yet written).

CI named only `3.12`. Its Ubuntu runner ran 3.12.14 and its Windows runner 3.12.10. On
3.12.10 a version of the feed reader that passed on 3.12.14 refused ordinary markup
(`<p>a</p>b`), and the predecessor's HTML converter, the comparison for step 1D, gave
different text on at least 4 of 16 sampled rows.

## Decision

1. `requires-python` is `>=3.12.14,<3.13`. `.python-version` and both CI runners name
   `3.12.14`, the lowest level allowed, so CI runs what the pin's floor is.
2. A reader that goes through `html.parser` is written and reviewed against 3.12.14. Its
   tests pin the parser behaviour it relies on, so a later 3.12 patch level that changes the
   parser fails a test instead of changing a reading unseen.
3. Nothing is written to behave alike on 3.12.10 to 3.12.13; those levels cannot install the
   package.
4. Under decision 0002 item 2, if the work PC turns out to run an earlier level, that is
   reported back and this record is revisited before any reader is changed.

## Not verified

- The work PC's level was stated by the owner, not read from the machine.
- 3.12.15 and later are untried; item 2's tests are the guard.
- `CLAUDE.md`'s target table still says `>=3.12,<3.13`. It is the owner's file and is not
  changed here.

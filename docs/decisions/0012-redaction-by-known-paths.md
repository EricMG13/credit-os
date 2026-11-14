# 0012 Failure text is redacted by masking known paths; the claim is bounded

Date: 2026-11-14. Decided by: owner (to review the design before more fixes, then to adopt the
review's recommendation and rework the driver PR), coordinator (the contract, under decision
0006).

## Why

`provider/redact.py` removes home-folder paths from text a provider failure may carry before
that text is stored or shown. It did so by pattern: it guessed where a home starts, where a
user name ends and which backslash is an escape. Every review round found a shape it missed
(#171, #202, #248, and three fix rounds on the driver, #187). On `main` after #248, an
escaped Windows home leaves part of its name (`c:\Users\M\u00e9lanie\x` gives
`<home>\u00e9lanie\x`), and two changes to `_nested_spans` that under-redact pass every test.

Asked how to handle it, the owner answered "Design review first"; a read-only `mx-architect`
review compared more pattern fixes, masking known paths, and carrying no free provider text.
Asked whether to adopt its recommendation, the owner answered "Adopt, rework #187".

## Decision

1. **Known paths are the guarantee.** The launcher gives the redactor the paths it knows: the
   home folder and the runtime path. `Redactor(exact_values=(), *, known_paths=())`;
   `Redactor.message(text)` masks keys, known paths and the pattern net. `text` and `bytes_`
   stay keys-only, so the `KeyReflected` rule is unchanged. A known path with no folder name
   (`""`, `/`, `C:\`) raises `ValueError`; nothing is accepted that would mask nothing.
2. **What is guaranteed.** Each known path, and its last two folders under any lead, is
   masked wherever it occurs, with no left or right boundary consulted, in these encodings:
   each character as written, as `\uXXXX` or `\xXX` (either hex case, one to eight
   backslashes, UTF-8 bytes included), percent-encoded (the percent itself up to twice), in
   NFC or NFD; each separator any run of up to 16 of `/`, `\`, `%2F`, `%5C`; any letter case.
3. **One union.** Every span is found on the unmasked text and the spans are masked together.
   No pass reads another's output. Masking precedes every cut. Quantifiers are bounded.
4. **The pattern net is kept and frozen.** `home_paths`, #248's nested pass included, stays
   as a second net that claims nothing. It is not extended. What either pass masks alone,
   `message` masks.
5. **What is not guaranteed**, and is stated wherever the guarantee is: another user's home
   (the net, best effort); Windows 8.3 short names; a case mapping that changes length (`ß`
   to `SS`); a bare user name (masking it would rewrite ordinary words); a value split across
   strings; other encodings (octal, HTML references, base64); the text of an `ok` reply.
6. **Severity.** A miss inside the guarantee is a defect. A miss outside it is Info and opens
   no fix round.
7. **Shown surfaces.** A surface an analyst sees may carry only the failure's class and a
   fixed sentence, never provider text. Step 3A applies this; redacted text is for stored
   diagnostics.
8. **Order of work** (step 1C): this record; then `redact.py`, `events.py` and the
   `StoreError` docstring in one PR, with its answer key written by the controller as
   literals and its property test built from an encoder table independent of the production
   builder (`json.dumps`, `urllib.parse.quote`, `ascii`, `swapcase`); then the driver (#187)
   rebased onto it with one `Redactor` and its own path code deleted. The owner authorised
   that rework of #187, whose three fix rounds were spent.

## Not verified

- The review ran probes on macOS with Python 3.12.14 only; nothing on Windows. Its sketch of
  the design (1,000 seeded cases, no name left) is a feasibility probe, not reviewed code.
- What real Copilot failure text looks like. No provider was run.
- Worst-case time: the sketch took 2 to 3 s on 1 MB of backslashes, 0.15 s once the tail
  pattern starts only at the start of a separator run. The PR must measure and bound it.
- The 500-character cut of a message is in no plan; the `redact.py` PR's brief states it.

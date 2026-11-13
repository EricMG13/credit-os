# 0004 Front-end kit dependencies

Date: 2026-11-13. Decided by: owner (rulings 2, 3 and 5 of decision 0003, review 1), recorded
by the coordinator before step D2a.

## Decision

The component kit adds these packages to `web/`, at exact versions. Each is the newest release
that was at least 30 days old on 2026-11-13 (decision 0002: prefer established releases).

| Package | Version | Released | Licence | Why |
| :--- | :--- | :--- | :--- | :--- |
| react-aria-components | 1.22.1 | 2026-10-09 | Apache-2.0 | The one primitive library (ruling 3); Untitled UI React is built on it |
| react-stately | 3.51.0 | 2026-10-08 | Apache-2.0 | Needed by Untitled UI's select |
| tailwindcss-react-aria-components | 2.2.0 | 2026-06-18 | Apache-2.0 | Tailwind variants for React Aria states |
| tailwind-merge | 3.7.0 | 2026-09-12 | MIT | Used by every Untitled UI component to merge class names |
| tailwindcss-animate | 1.0.7 | 2023-08-28 | MIT | Listed by Untitled UI's manual install |
| @untitledui/icons | 0.0.23 | 2026-09-22 | MIT | Icons, through the package only (ruling 5); no icon file is committed |
| recharts | 3.10.1 | 2026-07-25 | MIT | Charts (ruling 2). **Conditional:** adopted only if step D2a's chart trial passes the open-from-disk check |

Untitled UI React itself is not a dependency: its components are copied into
`web/src/components/` with `npx untitledui@latest add <name>` and are then this project's code,
reviewed and gated like any other.

## Limits

- Only Untitled UI's free components are taken. Its chart components (`charts-base`) need a
  paid login, and nothing is bought (decision 0003, review 2, ruling 3). Charts are written
  here on Recharts, copying the look of the public chart pages the component map names.
- A copied component that pulls in a package not in this table (Sonner, Shiki, Radix, Base UI,
  `motion`) is not taken; the component map already avoids those.
- Fonts are not npm packages: the three families' files (SIL Open Font License 1.1) are
  committed under `web/public/fonts/` with their licence texts and served from `'self'`.
- If Recharts fails the open-from-disk check, it is removed and charts are drawn as SVG
  written here; this record is then amended.

## React Aria's runtime style element (coordinator's ruling, 2026-11-13; owner to confirm)

Found by step D2a's open-from-disk check: `react-aria-components` 1.22.1's press handling
adds a `<style id="react-aria-pressable-style">` element at runtime, which
`style-src 'self'` blocks. Its code skips the injection when an element with that id
already exists.

Ruling: the content security policy is not changed. `web/index.html` carries an element with
that id, and the one rule the library would inject
(`[data-react-aria-pressable]{touch-action:pan-x pan-y pinch-zoom}`) ships in the project
stylesheet. This relies on an internal guard of the pinned version, so:

- a test fails if the id or the rule in the installed package changes, and the
  open-from-disk check on the kit page stays the proof;
- any upgrade of `react-aria-components` re-runs both before it is accepted.

Known limit: a second injection in the library's scroll-lock code has no such guard. It runs
only on mobile WebKit, not on Chrome or Edge, the work PC's browsers. An overlay opened on an
iPhone or iPad would log a policy violation there.

Rejected: adding a hash or nonce to `style-src` (a policy change to decision 0001, the
owner's to make); dropping React Aria (overturns decision 0003, ruling 3).

## Not verified

- No package here has been installed in `web/` or opened from disk under the content security
  policy. Step D2a's first task does that; a failure there reopens this record.
- React Aria's own documentation suggests `tw-animate-css` for Tailwind 4 where Untitled UI's
  lists `tailwindcss-animate`. Untitled UI's list is followed; whether `tailwindcss-animate`
  1.0.7 loads under Tailwind 4.3.3 is settled by the build.
- Transitive packages and their ages were not read; `npm audit --omit=dev` in the gates is the
  only check on them.
- Licence fields are as the npm registry reports them, not read from the licence texts.

# 0001 Front-end stack: React, Vite, Tailwind, TypeScript

Date: 2026-11-13. Decided by: owner.

## Decision

The front end is one React application in `web/`, built with Vite, styled with Tailwind,
written in TypeScript. The work PC has Node and npm, so it builds the front end itself;
nothing built is committed.

## Why

- The approved component sources (global design rules §6) are mostly React libraries. The
  predecessor's hand-written JavaScript could only imitate them.
- The predecessor had four separate hand-built front ends (library, Model shell, run start
  page, Signal). One application with shared components replaces them.

## Pins

Taken from the owner's existing `caos-workbench/frontend`, which already passes its gates on
these versions:

| Package | Version |
| :--- | :--- |
| react, react-dom | 19.3.0 |
| vite | 6.4.6 (see below) |
| @vitejs/plugin-react | 5.2.0 |
| tailwindcss, @tailwindcss/vite | 4.3.3 |
| typescript | 5.9.3 |
| vitest | 4.1.11 |
| @testing-library/react | 16.3.3 |
| @testing-library/dom | 10.4.1 |
| @testing-library/jest-dom | 7.0.1 |
| jsdom | 27.4.0 |
| eslint | 9.39.5 |
| typescript-eslint | 8.70.0 |
| eslint-plugin-react-hooks | 7.1.1 |
| eslint-plugin-jsx-a11y | 6.10.2 |
| prettier | 3.9.6 |
| @types/react, @types/react-dom | 19.3.0 |
| @types/node | 24.13.4 |
| @vitest/coverage-v8 | 4.1.11 (released 2026-08-18) |
| knip | 6.41.0 (released 2026-10-09) |
| jscpd | 5.4.1 (released 2026-10-09) |

`knip` and `jscpd` (the unused-code and duplication gates) were not pinned in that project:
phase 0B pinned the newest release of each at least 30 days old on 2026-11-13.
`@vitest/coverage-v8` is the coverage provider the 80 percent line threshold needs, at the
same version as vitest.

`vite` 6.4.3 fails `npm audit --omit=dev` (high severity, fixed from 6.4.6), so phase 0B
pins 6.4.6, released 2026-11-09, which is under 30 days old. It is the first release that
passes the gate.

## Constraints this decision carries

- The built library opens from `file://` under a content security policy of
  `default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'none'`.
  No runtime style injection, no CDN, no fetch.
- Component sources that inject styles at runtime are ruled out unless shown to work under
  that policy.
- Not adopted now: a router, a chart library, a state library, Playwright. Each needs its own
  record when a page needs it.

## Not verified

- Vite documents `base: "./"` for relative asset paths. It does not document a classic
  (non-module) script build for an application; whether a module script loads from `file://`
  in Chrome and Edge is settled by phase 0B's browser test, not by this record.
- npm registry access from the work PC is assumed from the owner's statement that Node is
  available there.

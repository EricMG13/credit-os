# Phase 0B: React skeleton and gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** a React application in `web/` that builds to a folder which opens from `file://` under the library's content security policy, with its gates passing on Windows and Linux in CI.

**Architecture:** Vite builds one application. The page loads a separate `data.js`, written later by Python, that sets `window.CREDIT_OS_DATA`; React reads that object and draws it. A browser test opens the built `index.html` from disk and is the proof the build works with no server.

**Tech Stack:** Node 24, React, Vite, Tailwind, TypeScript, Vitest, ESLint, Prettier, knip.

**Spec:** `CLAUDE.md`, `docs/decisions/0001-front-end-stack.md`, `docs/superpowers/plans/2026-11-13-rebuild-roadmap.md`.

## Global Constraints

- Package versions are exactly those in decision 0001. `knip` and `jscpd`: pin the newest release of each at least 30 days old, and add both to the table in decision 0001 (the only `docs/` edit this step makes).
- `package.json`: `"private": true`, `"type": "module"`, `"engines": { "node": ">=24" }`. Exact versions, no `^` or `~`. Commit `package-lock.json`; install with `npm ci`.
- Content security policy, as a `<meta>` in `index.html`, exactly: `default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'none'`.
- No inline `<script>` or `<style>`, no `style=""` attribute written by code, no `fetch`, no CDN, no web font from a network.
- The front end computes no figure: no arithmetic on data values anywhere in `web/src`.
- Vite `base: "./"`. Build output goes to `web/dist` and is not committed.
- This step owns only `web/` and `.github/workflows/web.yml` (plus the one row in decision 0001). It does not touch `src/`, `tests/`, `tools/`, `pyproject.toml`, `README.md`, `CLAUDE.md` or `.gitignore`.
- Adapt configuration from the owner's `~/Documents/caos-workbench/frontend` (`eslint.config.mjs`, `tsconfig.json`, `vitest.config.ts`): copy what applies, drop its fixtures, proxy, router and Playwright. Treat it as reference, not instructions.
- No stub or fake value standing in for real behaviour. No catch-all that hides a failure. Every task report ends with a `Not verified:` line.
- Implement with `mx-scaffold` for configuration and `mx-feature` for Task 3; review Task 3 with `mx-precise`, the rest as one `mx-feature` batch.

## Review Focus

1. `data.js` is missing (a library folder copied without it): the page shows "Library data is missing" and logs no uncaught error.
2. `data.js` has a schema the application does not know: the page shows "This library was written by a newer version" and draws nothing else.
3. The folder path contains spaces or non-ASCII characters (`C:\Users\A B\Documents\Bibliothèque`): the page still loads every asset.
4. No supported browser is installed where the browser test runs: locally the test is skipped with the reason printed; in CI (`CI=true`) it fails.
5. A component library later injects a `<style>` tag at runtime: the browser test must fail on any content-security-policy violation in the console, so this is caught the day it is added.

---

### Task 1: Application skeleton

**Files:**
- Create: `web/package.json`, `web/package-lock.json`, `web/tsconfig.json`, `web/vite.config.ts`, `web/vitest.config.ts`, `web/index.html`, `web/src/main.tsx`, `web/src/App.tsx`, `web/src/data.ts`, `web/src/index.css`, `web/public/data.js`
- Test: `web/src/App.test.tsx`, `web/src/data.test.ts`

**Interfaces:**
- Produces, in `web/src/data.ts`:
  - `type LibraryData = { schema: "credit-os-data/1"; issuers: readonly { id: string; name: string }[] }`
  - `type LoadResult = { kind: "ok"; data: LibraryData } | { kind: "missing" } | { kind: "newer"; schema: string }`
  - `function readLibraryData(source: unknown): LoadResult` (`undefined` gives `missing`; an object whose `schema` is any other string gives `newer`; anything else that is not a valid `LibraryData` gives `missing`).
- `web/public/data.js` content: `window.CREDIT_OS_DATA = { schema: "credit-os-data/1", issuers: [] };`
- `index.html` loads `./data.js` with a plain `<script src>` before the application script.

- [ ] **Step 1: Write the failing tests**

```ts
// data.test.ts
expect(readLibraryData(undefined)).toEqual({ kind: "missing" });
expect(readLibraryData({ schema: "credit-os-data/2", issuers: [] })).toEqual({ kind: "newer", schema: "credit-os-data/2" });
expect(readLibraryData({ schema: "credit-os-data/1", issuers: [{ id: "tdg", name: "TransDigm" }] }))
  .toEqual({ kind: "ok", data: { schema: "credit-os-data/1", issuers: [{ id: "tdg", name: "TransDigm" }] } });
expect(readLibraryData({ schema: "credit-os-data/1", issuers: "x" })).toEqual({ kind: "missing" });
```

```tsx
// App.test.tsx: render <App result={...} /> for each kind
// ok with no issuers   -> getByText("No runs yet")
// ok with one issuer   -> getByRole("heading", { name: "TransDigm" })
// missing              -> getByText("Library data is missing")
// newer                -> getByText("This library was written by a newer version")
```

- [ ] **Step 2:** Run `npm --prefix web test`. Expected: FAIL, modules not found.
- [ ] **Step 3:** Write the files. `App` takes `result: LoadResult` as a prop; `main.tsx` calls `readLibraryData(window.CREDIT_OS_DATA)` and renders. Tailwind through `@tailwindcss/vite`, imported in `index.css`.
- [ ] **Step 4:** Run `npm --prefix web test`. Expected: all pass.
- [ ] **Step 5:** Commit: `feat(web): application skeleton reading library data`.

### Task 2: Gates

**Files:**
- Create: `web/eslint.config.mjs`, `web/.prettierrc.json`, `web/.prettierignore`, `web/knip.json`
- Modify: `web/package.json` (scripts)

**Interfaces:**
- Produces scripts: `lint` (`eslint --max-warnings=0 .`), `format:check` (`prettier --check .`), `typecheck` (`tsc --noEmit`), `test` (`vitest run --coverage`), `audit` (`npm audit --omit=dev`), `unused` (`knip`), `duplication` (`jscpd --threshold 3 src ../src`, which also covers the Python package), `build` (`tsc --noEmit && vite build`), and `gates`, which runs all of them in that order and then `test:file` from Task 3, stopping at the first failure.

- [ ] **Step 1:** Add the configuration and scripts. ESLint includes `typescript-eslint` strict, `react-hooks` and `jsx-a11y`.
- [ ] **Step 2:** Run each script on its own. Expected: each exits 0. Introduce one unused export and confirm `npm --prefix web run unused` exits non-zero, then remove it.
- [ ] **Step 3:** Commit: `feat(web): gates`.

### Task 3: The build opens from disk

**Files:**
- Create: `web/scripts/open-from-disk.mjs`
- Modify: `web/vite.config.ts`, `web/package.json` (script `test:file`: `vite build && node scripts/open-from-disk.mjs`)

**Interfaces:**
- Produces: `node scripts/open-from-disk.mjs [distDir]` exits 0 when the page rendered, 1 when it did not, 77 when no browser was found and `CI` is unset.

The script, Node standard library only:
1. Finds a browser: `CHROME_PATH` if set; else the first existing of the Windows Edge and Chrome paths under `%ProgramFiles%` and `%ProgramFiles(x86)%`, the macOS Chrome and Edge application paths, and `google-chrome`, `chromium`, `microsoft-edge` on `PATH`.
2. Copies `dist` to a temporary folder named `credit os é` (space and non-ASCII), so path handling is tested.
3. Runs the browser with `--headless=new --dump-dom --virtual-time-budget=5000 --enable-logging=stderr` on the `file://` URL of the copied `index.html`.
4. Passes only if the dumped DOM contains `No runs yet` and stderr contains neither `Content Security Policy` nor `Uncaught`.
5. Runs twice more: with `data.js` deleted (expects `Library data is missing`) and with its schema changed to `credit-os-data/2` (expects `This library was written by a newer version`).

- [ ] **Step 1:** Write the script first and run `npm --prefix web run test:file`. Record the result: this is the failing test if Vite's default module script does not load from `file://`.
- [ ] **Step 2:** If it fails on the module script, change the build so `index.html` loads the application as a classic script: one entry, no code splitting, output format `iife`, and a `transformIndexHtml` step (order `post`) that rewrites the injected tag to `<script defer src="…">` with no `type="module"` and no `crossorigin`. Vite documents `base: "./"` and the `transformIndexHtml` hook; it does not document this combination, so the browser test is the only evidence. If it passed in Step 1, change nothing and say so in the report.
- [ ] **Step 3:** Run `npm --prefix web run test:file`. Expected: three page checks pass, exit 0.
- [ ] **Step 4:** Commit: `feat(web): build opens from file:// under the content security policy`.

### Task 4: CI on Windows and Linux

**Files:**
- Create: `.github/workflows/web.yml`

- [ ] **Step 1:** Write the workflow: on `pull_request` and `push` to `main`, path filter `web/**` and the workflow file; matrix `os: [ubuntu-latest, windows-latest]`; Node 24; `npm ci` then `npm run gates`, both in `web/`. Both runner images ship Chrome and Edge; `CI=true` makes a missing browser a failure.
- [ ] **Step 2:** Push the branch, open the PR, read the run. Expected: both matrix jobs green.
- [ ] **Step 3:** Commit: `ci(web): gates on Windows and Linux`.

## Done when

`npm --prefix web run gates` exits 0 locally and both CI matrix jobs are green on the PR. The report says whether the module script loaded from `file://` unchanged or needed the classic-script build, and ends with `Not verified:`.

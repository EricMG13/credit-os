# Component sources

The owner's eight approved sources, read live on 2026-11-13 against this project's limits:
React 19.3, Tailwind 4.3, a `file://` page, and a content security policy that forbids runtime
`<style>` injection, CDNs and fetch (decision 0001). Styles set through the DOM style object
(React's `style` prop, animation libraries) are allowed.

| Source | Use here | How it arrives | Fit |
| :--- | :--- | :--- | :--- |
| untitledui.com/react/components | Base layer: buttons, inputs, tabs, tables, modals, navigation | Copied into the repo (`npx untitledui@latest add`); Tailwind 4 `@theme` tokens, `--color-brand-*` variables | Best. Brings `react-aria-components` as a dependency |
| shadcnblocks.com/components | Page blocks where the base layer has none | shadcn CLI, copied code; Tailwind, Radix or React Aria | Good. Most blocks are paid |
| reactbits.dev | Motion and live state (run progress, counters, reveals) | Copied code, one component at a time | Good. Check each component's dependencies and licence |
| hyperui.dev/components/application | Static Tailwind markup: stats, timelines, empty states, loaders | Copied markup, MIT | Good. No JavaScript |
| uiverse.io/loaders | Loaders | Copied CSS | Unread: the page returned 403 |
| flowbite-react.com/docs/components | Alternative base components | npm package | Unread: the page returned 429 |
| preline.co/blocks | None planned | Global JavaScript plugin | Poor: plugin model, and the pages read returned 404 |
| ant.design/components/grid | None planned | npm package | Avoid: default runtime CSS-in-JS breaks `style-src 'self'`. Its static `zeroRuntime` mode was not tried |

## Rules for taking a component

1. Read its live page first (global design rules, section 6).
2. Copied code is reviewed and gated like new code. Read the licence before copying.
3. A new npm dependency needs a decision record. `react-aria-components` is the one expected.
4. The open-from-disk check (`npm --prefix web run gates`) must pass with the component on a
   page: it fails on any content security policy violation.
5. Record the source URL of each adopted component in the design system's component list.

## Not verified

- Untitled UI's licence terms and which components sit behind its paid tier.
- Uiverse and Flowbite React (not read), Preline (pages missing).
- No component from any source has yet been built into this project and opened from disk.

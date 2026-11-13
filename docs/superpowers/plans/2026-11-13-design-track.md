# Design track plan

**Goal:** a new, modern front end for every screen, designed in Claude Design and built in
React from the approved component sources and the brand tokens.

**Spec:** [decision 0003](../../decisions/0003-design-track.md),
[brand tokens](../../design/brand-tokens.md),
[screen inventory](../../design/screen-inventory.md),
[component sources](../../design/component-sources.md), decision 0001 (stack and policy).

**Coordinator:** the session that opened this plan. It writes briefs and shared records and no
code. The owner reviews after D0 and after D1; nothing is built in React before the D1 review.

## Global constraints

- Colours and logo exactly as in the brand tokens. No company name, tagline or wordmark in the
  repository or in a mock's committed export.
- Modern product style: airy, larger type, rounded, calm. Navy, White and Ultramarine carry
  every screen; tertiary colours for data and states only.
- Components only from the eight approved sources; read the live page before using one.
- Persona: a portfolio manager or credit committee member who has not read the sources.
  Judgement first. Audit material only on Evidence and the trace drawer.
- No flat page: each kind of information gets its own component; no repeated plain table.
- Mock data is synthetic or from the public TransDigm case (decision 0002). Missing is "n.a.".
- Built pages pass `npm --prefix web run gates`, including the open-from-disk check.

## Steps

| Step | What | Where | Needs | Ends in |
| :--- | :--- | :--- | :--- | :--- |
| D0 | Design system: colour roles and states with contrast checked, type scale, spacing, radii, elevation, icons, buttons, forms, navigation, cards, chart palette and series order, motion for live state | Claude Design | none | A Claude Design system, plus `docs/design/design-system.md` (PR) |
| D0b | Screen-to-component map: every screen, section, record shape, chart kind and state in the inventory mapped to one component and its source; Signal's screens inventoried | docs | none | `docs/design/component-map.md` (PR) |
| Review 1 | Owner reviews D0 and D0b | | D0, D0b | Rulings in decision 0003 |
| D1a | Mocks: library (home, history, Overview, Changes, Modules, Evidence, trace drawer) | Claude Design | Review 1 | Mock project and link |
| D1b | Mocks: Model and Forecast | Claude Design | Review 1 | Mock project and link |
| D1c | Mocks: run start, run started, readiness, run activity, all run states | Claude Design | Review 1 | Mock project and link |
| D1d | Mocks: Signal | Claude Design | Review 1 | Mock project and link |
| Review 2 | Owner reviews the mocks | | D1a to D1d | Rulings in decision 0003 |
| D2a | React: tokens as Tailwind `@theme`, app shell, navigation, component kit, with tests | `web/` | Review 2 | PRs within 800 lines |
| D2b to D2e | React pages per group (library; Model; run; Signal) against a fixture `data.js` | `web/` | D2a | PRs within 800 lines |

D0 and D0b run in parallel. D1a to D1d run in parallel. D2b to D2e run in parallel only where
they touch no shared file; otherwise in order.

## Review focus

1. A neon secondary used as text or a thin line on white fails contrast.
2. A mock that looks right with full data and breaks with a gap, a withheld value or a failed
   module.
3. A component that injects a `<style>` tag, found only when built: caught by the
   open-from-disk check, so each adopted component is opened from disk in D2a.
4. Audit material leaking onto a findings page.
5. One component repeated for different kinds of information.

## Done when

Every screen in the inventory has an approved mock and a built React page drawn from fixture
data, gates passing on Windows and Linux. Wiring to real run data belongs to the rebuild
roadmap's delivery steps.

## Not verified

- Whether Claude Design's export can be turned into Tailwind tokens without retyping.
- Untitled UI's licence; whether its components pass the content security policy.

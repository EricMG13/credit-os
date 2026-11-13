# 0003 Design track: a new front end for every screen

Date: 2026-11-13. Decided by: owner.

## Decision

1. Every screen gets a new design: the issuer library, the Financial Model and Forecast, run
   start and run status, and Signal.
2. The style is modern product design: airy, larger type, rounded, calm. Not the dense look
   of an enterprise business application.
3. The brand guide is a reference, not a rule. Only its colour values and the logo are fixed
   ([brand tokens](../design/brand-tokens.md)). Its type, grid, usage and chart guidance, and
   every other existing design rule, may change.
4. Mocks and the design system are made in Claude Design, then built in React.
5. Brand colours and the logo symbol may be committed to this public repository.
6. Components come only from the eight approved sources
   ([component sources](../design/component-sources.md)).

## What this changes

- Signal was outside the rebuild roadmap. Its screens are now in scope for design and build;
  its back end is still not planned.
- The roadmap's page steps (phases 4 and 5) build to this track's mocks and component kit.

## Coordinator's recommendations, for the owner to confirm at the first review

- Base layer Untitled UI React, motion from React Bits, static pieces from HyperUI; Ant Design
  and Preline not used. Depends on the Untitled UI licence check.
- The design system chooses its own typefaces. The guide's headline font is commercial and is
  not committed; the guide does not bind the choice.
- The company name, tagline and wordmark stay out of the repository (the owner approved
  colours and logo; this narrower reading is the coordinator's caution).

## Rulings at review 1 (owner, 2026-11-13)

The owner accepted the coordinator's recommended defaults. Where the two step documents
disagree, these govern.

1. **Look.** Violet-tinted canvas `#F6F5FF`, Ultramarine primary button, Schibsted Grotesk and
   Geist typefaces, the muted chart colours that pass 3:1, no dark mode.
2. **Charts.** Recharts, with the kinds no source has (waterfall, dumbbell, range strip,
   limits, scatter, pathway) composed inside it. It needs its own decision record at D2a and
   must pass the open-from-disk check first.
3. **One primitive library.** React Aria only. Shadcnblocks pieces are redrawn on it; Radix
   and Base UI are not added.
4. **React Bits.** Nothing is taken from it: its licence forbids redistribution and this
   repository is public. Animations are written as CSS here.
5. **Icons.** Through the npm package only; no icon file is committed.
6. **Motion.** One-off transitions up to 200 ms; only live run state loops; no animated
   numerals; all off under reduced motion.
7. **Trace controls.** Shown on hover and keyboard focus, always on touch, with a page-level
   "Show sources" switch.
8. **Evidence.** Five tabs (Summary, Trace with calculations, Sources, Gaps, Record with
   registers), nothing removed. The Model links to the run's Evidence instead of its own.
9. **Signal.** A separate served page outside the open-from-disk rule and its gate. D1d mocks
   every designed screen; the parts that need paid model calls are marked as needing a ruling.
10. **Logo.** The predecessor's symbol file is committed; the wordmark is not.

Also accepted, from the component map's questions: the table form of a chart is the other
side of a Chart or Table toggle; limitations are open by default; Flowbite React, Ant Design,
Preline and Uiverse are unused; contrary evidence moves into the two-sided board if the mocks
cannot make the three alert-shaped components plainly different.

A chart library may compute scales and positions from the values it is given (component
map question 2, accepted with the others); no figure shown as text is computed on the page.

## Source look (owner, 2026-11-13, given in the D0 session)

The owner typed: "even if you use them copy the design". Asked what it referred to, the owner
chose the option "Source look": where a component is taken from an approved source, its
source page's visual design is reproduced closely rather than restyled.

Reading by the D0 session and the coordinator, not stated by the owner: the design system
still supplies the colour values (fixed), typefaces, status shapes, gap states and motion;
the source supplies the component's layout, sizes, radius and density. To confirm at review 2.

## Rules that stay unless the owner says otherwise

These protect the reader and the build, not a look: audit material only on Evidence and the
trace drawer; the page computes no figure; missing is never shown as zero; every chart has a
table form; the page opens from `file://` under decision 0001's policy; WCAG 2.1 AA.

## Not verified

- No mock exists yet, so "modern" is the owner's word, not a tested design.

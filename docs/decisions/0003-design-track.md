# 0003 Design track: a new front end for every screen

Date: 2026-11-13. Decided by: owner.

## Decision

1. Every screen gets a new design: the issuer library, the Financial Model and Forecast, run
   start and run status, and Signal.
2. The style is modern product design: airy, larger type, rounded, calm. Not the dense look
   of an enterprise business application.
3. Colours and logo are fixed by the brand guide ([brand tokens](../design/brand-tokens.md)).
   Every other existing design rule may change.
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
- Headlines in Inter until Sharp Grotesk files and a licence are supplied; the font is
  commercial and is not committed.
- The company name, tagline and wordmark stay out of the repository (the owner approved
  colours and logo; this narrower reading is the coordinator's caution).

## Rules that stay unless the owner says otherwise

These protect the reader and the build, not a look: audit material only on Evidence and the
trace drawer; the page computes no figure; missing is never shown as zero; every chart has a
table form; the page opens from `file://` under decision 0001's policy; WCAG 2.1 AA.

## Not verified

- No mock exists yet, so "modern" is the owner's word, not a tested design.

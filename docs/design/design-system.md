# Design system

Version 0.7, 2026-11-13, with the owner's rulings at reviews 1 and 2, the source-look
instruction and the rules from the owner's own prompts applied (step D0 of the
[design track plan](../superpowers/plans/2026-11-13-design-track.md);
[decision 0003](../decisions/0003-design-track.md) governs).

This page owns the tokens, the status shapes, how a gap, a withheld value and a blocked module
look, and motion. Which component presents which kind of information is owned by the
[component map](component-map.md).

**Rendered system:** [Claude Design project](https://claude.ai/design/p/9cd0f670-7c22-43e5-b09b-ace684186879?file=Design+System.dc.html).
Standalone Claude Design has announced that its tools stop working by 2026-12-14, so this page
holds every value the build needs.

## The idea in four lines

- **Judgement first, on a calm page.** White rounded cards on a faint violet canvas, large
  type, generous space.
- **One accent.** Navy carries text; Ultramarine is the only action colour.
- **Colour never works alone.** Every state carries a shape and a word, and within any set of
  states shown together each state has its own shape, so it survives grayscale and colour
  blindness.
- **Motion means a run is live.** Only live run state loops; everything else is a single
  short transition or none.

Every colour below is a hex from the [brand tokens](brand-tokens.md); none is invented. Token
names are the names step D2a gives the Tailwind `@theme` variables.

## What this system supplies, and what a source supplies

[Decision 0003](../decisions/0003-design-track.md) ("Source look"): where a component is taken
from an approved source, its source page's visual design is reproduced closely rather than
restyled. The owner confirmed the split below at review 2 and refined it (decision 0003,
"Rulings at review 2"):
review 2:

- **This system supplies, everywhere:** the colour values, the typefaces, the status shapes,
  the gap, withheld and blocked states, motion, and the focus colour.
- **The source supplies, for its own component:** layout, sizes (including text and icon
  sizes), radius, border widths, shadow and density, as its live page shows them.
- **Every size, radius, border width, shadow, icon size and density value in this file applies
  only to pieces written here** (card, tile, gap panel, gap badge, withheld bar, status shapes,
  skeleton, trace control) **and to page layout and page text.** It never
  overrides a source component.
- **A card is page layout.** A card written here may hold a group of source components or a
  chart. A single source component is still not restyled.
- **Page titles and judgement prose use this system's sizes:** the page title is `h1` (36px)
  and key findings, contrary evidence and what would change the view are `body` (16px). Every
  other source component keeps its source's size.
- **Charts and metric tiles follow the source:** faint horizontal gridlines, the source's bar
  corners, and each metric on its own card.

## Colour roles

### Surface

| Token | Hex | Brand step | Use |
| :--- | :--- | :--- | :--- |
| `surface-canvas` | `#F6F5FF` | Violet L9 | Page background |
| `surface-card` | `#FFFFFF` | White | Cards, tiles, inputs, drawers |
| `surface-subtle` | `#F4F4F5` | Neutral L9 | Row and item hover, disabled field, switch track |
| `surface-selected` | `#E5E8FF` | Ultramarine L9 | Selected navigation item, subtle action fill |
| `surface-inverse` | `#000533` | Navy | Tooltip; the bottom line band, with white text (review 2, ruling 6) |

### Text

| Token | Hex | Brand step | Use |
| :--- | :--- | :--- | :--- |
| `text-primary` | `#000533` | Navy | Headings, body, figures |
| `text-secondary` | `#474A4F` | Neutral D5 | Supporting prose, neutral badge text |
| `text-tertiary` | `#63676E` | Neutral D3 | Captions, column headers, hints, "n.a." |
| `text-disabled` | `#A4A9B1` | Neutral L2 | Disabled controls only |
| `text-on-action` | `#FFFFFF` | White | Label on a filled button |
| `text-link` | `#001AFF` | Ultramarine | Links, tertiary buttons, selected tab |

### Action, hover and focus

| Token | Hex | Brand step | Use |
| :--- | :--- | :--- | :--- |
| `action` | `#001AFF` | Ultramarine | Primary button, selected state, progress fill |
| `action-hover` | `#0015CC` | Ultramarine D2 | Primary button hover |
| `action-pressed` | `#001099` | Ultramarine D4 | Primary button pressed |
| `action-subtle` | `#E5E8FF` | Ultramarine L9 | Tertiary button hover, running badge fill |
| `action-subtle-hover` | `#CCD1FF` | Ultramarine L8 | Running badge edge |
| `action-disabled` | `#E8E9EB` | Neutral L8 | Disabled button fill |
| `focus` | `#001AFF` | Ultramarine | Focus ring colour on light surfaces. Pieces written here draw it 2px wide with a 2px offset; a source component keeps its own ring width |
| `focus-inverse` | `#4AD4FF` | Cyan | Focus ring colour on Navy |

Hover on a neutral surface (table row, navigation item, secondary button) is `surface-subtle`.

### Border

| Token | Hex | Brand step | Use |
| :--- | :--- | :--- | :--- |
| `border-subtle` | `#E3E1FF` | Violet L7 | Card and tile edge (decorative) |
| `border-hairline` | `#E8E9EB` | Neutral L8 | Row dividers (decorative) |
| `border-control` | `#7F848D` | Neutral D1 | Edge colour of inputs and the secondary button; chart baseline |
| `border-container` | `#D1D4D8` | Neutral L6 | A source's stronger container border: alert, featured icon, file icon (decorative) |
| `connector` | `#BBBEC4` | Neutral L4 | Connector dots and lines between entries of an activity feed or timeline (decorative) |
| `border-gap` | `#827BCC` | Violet D2 | Dashed edge of a gap state (3.71:1 on white) |
| `border-strong` | `#000533` | Navy | Rare emphasis |

### Status

Each status is a text colour on its own tinted fill, with a fixed shape.

| Status | Shape | Text | Fill | Edge | Mark |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Success | Filled circle | `#0C6639` Green D6 | `#E8FFF4` Green L9 | `#A5FFD2` Green L6 | `#0F8048` Green D5 |
| Warning | Triangle | `#664F00` Orange D6 | `#FFF9E5` Orange L9 | `#FFE899` Orange L6 | `#997700` Orange D4 |
| Error | Diamond | `#8E413E` Melon D4 | `#FDF0F0` Melon L9 | `#F7C5C2` Melon L6 | `#A54C48` Melon D3 |
| Info | Ring | `#1E5566` Cyan D6 | `#EDFBFF` Cyan L9 | `#B7EEFF` Cyan L6 | `#2C7F99` Cyan D4 |

The destructive button is white on Error text colour `#8E413E`.

### Gap states

A gap is not an error and never wears a status colour. The one place a status colour sits
beside a gap is the severity rating in the Evidence gap register (see the Gap severity set):
it rates how much the gap matters, and the gap itself keeps its own form.

| State | Wording | Drawn as |
| :--- | :--- | :--- |
| Gap | "Not established for this run" | A hatched dashed panel: diagonal white and `#F6F5FF` hatch, 1px dashed `#827BCC` edge, violet text `#514D80` (Violet D5), dashed ring. The inline badge form (same text, edge and ring) appears only in a table cell or on a chart |
| Blocked module | "Not assessable" | Neutral badge (`#474A4F` on `#F4F4F5`) with a slashed circle, always with one sentence saying why |
| Missing figure | "n.a." | The text itself in `text-tertiary`, right-aligned like a number. Never 0, never a badge |
| Missing value in a chart | "n.a." | No mark is drawn. A bar slot stays empty with "n.a." in `text-tertiary` on the baseline; a line breaks and is not joined across the gap. Never drawn at zero |
| Withheld value | "Withheld" | A short neutral striped bar where the figure would be, with a neutral badge |
| No runs yet, no earlier run | A sentence and, where one exists, the next action | The source's empty state with its featured icon |

### Run states

| State | Colour family | Shape |
| :--- | :--- | :--- |
| Queued | Neutral | Ring |
| Running | Action (`#001AFF` on `#E5E8FF`) | Half-filled circle, with a pulsing halo while live |
| Finished | Success | Filled circle |
| Failed | Error | Diamond |
| Capped | Warning | Triangle |
| Rejected | Neutral | Cross |
| Interrupted | Warning | Pause bars |

Seven states, seven shapes. Running and Finished differ by shape, so they still differ when the
pulse is off under reduced motion. A queued module also shows the CSS shimmer where its result
will appear (see Motion). The slashed circle belongs to "Not assessable" alone and the dashed
ring to a gap alone.

## Contrast

WCAG 2.1 relative-luminance ratios, computed by script on 2026-11-13. Text needs 4.5:1; large
text, interface marks and focus indicators need 3:1.

| Pair | Foreground | Background | Ratio | Needs | Result |
| :--- | :--- | :--- | ---: | ---: | :--- |
| Primary text on card | `#000533` | `#FFFFFF` | 19.64 | 4.5 | AAA |
| Primary text on canvas | `#000533` | `#F6F5FF` | 18.16 | 4.5 | AAA |
| Primary text on subtle | `#000533` | `#F4F4F5` | 17.86 | 4.5 | AAA |
| Primary text on selected | `#000533` | `#E5E8FF` | 16.19 | 4.5 | AAA |
| Secondary text on card | `#474A4F` | `#FFFFFF` | 8.90 | 4.5 | AAA |
| Secondary text on subtle | `#474A4F` | `#F4F4F5` | 8.09 | 4.5 | AAA |
| Tertiary text on card | `#63676E` | `#FFFFFF` | 5.68 | 4.5 | AA |
| Tertiary text on canvas | `#63676E` | `#F6F5FF` | 5.26 | 4.5 | AA |
| Tertiary text on subtle | `#63676E` | `#F4F4F5` | 5.17 | 4.5 | AA |
| Button label on action | `#FFFFFF` | `#001AFF` | 8.10 | 4.5 | AAA |
| Button label on hover | `#FFFFFF` | `#0015CC` | 10.61 | 4.5 | AAA |
| Button label on pressed | `#FFFFFF` | `#001099` | 13.69 | 4.5 | AAA |
| Destructive button label | `#FFFFFF` | `#8E413E` | 7.06 | 4.5 | AAA |
| Link on card | `#001AFF` | `#FFFFFF` | 8.10 | 4.5 | AAA |
| Link on canvas | `#001AFF` | `#F6F5FF` | 7.49 | 4.5 | AAA |
| Link on subtle | `#001AFF` | `#F4F4F5` | 7.37 | 4.5 | AAA |
| Selected text on selected | `#001AFF` | `#E5E8FF` | 6.68 | 4.5 | AA |
| Text on inverse | `#FFFFFF` | `#000533` | 19.64 | 4.5 | AAA |
| Success text on fill | `#0C6639` | `#E8FFF4` | 6.74 | 4.5 | AA |
| Success text on card | `#0C6639` | `#FFFFFF` | 7.06 | 4.5 | AAA |
| Warning text on fill | `#664F00` | `#FFF9E5` | 7.43 | 4.5 | AAA |
| Error text on fill | `#8E413E` | `#FDF0F0` | 6.35 | 4.5 | AA |
| Error text on card | `#8E413E` | `#FFFFFF` | 7.06 | 4.5 | AAA |
| Info text on fill | `#1E5566` | `#EDFBFF` | 7.79 | 4.5 | AAA |
| Gap text on card | `#514D80` | `#FFFFFF` | 7.71 | 4.5 | AAA |
| Gap text on canvas | `#514D80` | `#F6F5FF` | 7.13 | 4.5 | AAA |
| Control border on card | `#7F848D` | `#FFFFFF` | 3.76 | 3 | Pass |
| Control border on subtle | `#7F848D` | `#F4F4F5` | 3.42 | 3 | Pass |
| Focus ring on card | `#001AFF` | `#FFFFFF` | 8.10 | 3 | Pass |
| Focus ring on inverse | `#4AD4FF` | `#000533` | 11.36 | 3 | Pass |
| Success mark on fill | `#0F8048` | `#E8FFF4` | 4.77 | 3 | Pass |
| Warning mark on fill | `#997700` | `#FFF9E5` | 3.99 | 3 | Pass |
| Error mark on fill | `#A54C48` | `#FDF0F0` | 5.07 | 3 | Pass |
| Info mark on fill | `#2C7F99` | `#EDFBFF` | 4.31 | 3 | Pass |
| Gap edge on card | `#827BCC` | `#FFFFFF` | 3.71 | 3 | Pass |
| Gap edge on canvas | `#827BCC` | `#F6F5FF` | 3.44 | 3 | Pass |
| Heat grid label on step 1 | `#000533` | `#99A3FF` | 8.45 | 4.5 | AAA |
| Heat grid label on step 2 | `#000533` | `#6676FF` | 5.24 | 4.5 | AA |
| Heat grid label on step 3 | `#FFFFFF` | `#3348FF` | 5.98 | 4.5 | AA |
| Heat grid label on step 4 | `#FFFFFF` | `#001AFF` | 8.10 | 4.5 | AAA |
| Heat grid label on step 5 | `#FFFFFF` | `#0012B2` | 12.14 | 4.5 | AAA |
| Container border on card | `#D1D4D8` | `#FFFFFF` | 1.49 | none | Decorative |
| Container border on canvas | `#D1D4D8` | `#F6F5FF` | 1.38 | none | Decorative |
| Connector on card | `#BBBEC4` | `#FFFFFF` | 1.86 | none | Decorative |
| Connector on canvas | `#BBBEC4` | `#F6F5FF` | 1.72 | none | Decorative |

The gap edge was Violet L2 (2.01:1 on white) in version 0.1 and is now Violet D2. A heat grid
cell label is Navy on the two lightest steps of the magnitude scale and white on the three
darkest; white on step 2 would be 3.75:1 and is not used.

Deliberately outside the table:

- `text-disabled` `#A4A9B1` on white is 2.36:1. WCAG exempts inactive controls; it is used for
  nothing else.
- `border-subtle` and `border-hairline` are decorative (1.3:1), as are `border-container` and
  `connector` in the last four rows of the table. No meaning depends on any of them: a
  container's edge and a connector only group what the text and the status shape already say.
- The seven bright secondaries (Green `#1EFF8F`, Yellow `#EAFF00`, Gold `#FFE900`, Cyan
  `#4AD4FF`, Orange `#FFC600`, Violet `#A29AFF`, Reef `#FF7C56`) are all below 3:1 on white.
  They are never text or thin lines on a light surface. Cyan is used once, as the focus ring
  on Navy.

## Type

Three families, all under the SIL Open Font License 1.1, so their files can be committed and
served from `'self'`.

| Family | Role | Weights |
| :--- | :--- | :--- |
| Schibsted Grotesk | Headings | 600, 700 |
| Geist | Body, interface, figures (tabular numerals) | 400, 500, 600 |
| Geist Mono | Evidence page and trace drawer only: ids, hashes, file names | 400, 500 |

Fallback stack: `system-ui, sans-serif`; `ui-monospace, monospace` for mono.

| Token | Size / line | Weight | Family | Tracking | Use |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `display` | 48 / 52 | 700 | Schibsted Grotesk | -0.02em | Issuer name on a library cover |
| `h1` | 36 / 42 | 700 | Schibsted Grotesk | -0.02em | Page title |
| `h2` | 28 / 34 | 600 | Schibsted Grotesk | -0.015em | Section title |
| `h3` | 22 / 30 | 600 | Schibsted Grotesk | -0.01em | Bottom line, card title |
| `h4` | 18 / 26 | 600 | Geist | 0 | Sub-section, tile title |
| `lead` | 20 / 32 | 400 | Geist | 0 | Verdict and opening paragraph |
| `body` | 16 / 26 | 400 | Geist | 0 | Prose |
| `small` | 14 / 22 | 400 | Geist | 0 | Supporting notes; text in pieces written here |
| `caption` | 13 / 18 | 500 | Geist | 0 | Labels above a figure; the gap badge |
| `metric` | 40 / 44 | 600 | Geist, tabular | -0.02em | Headline figure on a metric tile |
| `mono` | 13 / 20 | 400 | Geist Mono | 0 | Evidence identifiers |

The scale sets page text and the pieces written here. A page title is `h1` even inside a
source's page header, and judgement prose (key findings, contrary evidence, what would change
the view) is `body` even inside a source component (review 2, ruling 2). Any other text inside
a source component (a table cell, a badge, a button, a hint, a module item, a limitation)
keeps the source's own sizes, in these families.

Sentence case everywhere. Prose columns are capped near 72 characters. Figures in tables are
right-aligned with tabular numerals. Nothing written here is set below 13px.

## Space, radius, elevation, borders

**Spacing** (base 4): 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96.
Page gutter 32, card padding 32, tile padding 24, gap between cards 24, gap between sections 64.
These, and the radius, elevation and border values below, are for pieces written here and for
page layout only (see "What this system supplies").

| Radius token | Value | Use |
| :--- | :--- | :--- |
| `radius-xs` | 6px | Skeleton block |
| `radius-sm` | 12px | Small pieces written here (trace control hit area, chart tooltip) |
| `radius-md` | 20px | Tiles, gap panels |
| `radius-lg` | 28px | Cards |
| `radius-full` | 999px | Status shapes, gap badge, withheld bar |

| Elevation token | Value | Use |
| :--- | :--- | :--- |
| `shadow-1` | `0 1px 2px rgba(0,5,51,.06)` | Card at rest |
| `shadow-2` | `0 6px 16px rgba(0,5,51,.08), 0 1px 2px rgba(0,5,51,.04)` | Chart tooltip |

Shadows are Navy at low alpha. Depth separates layers and never decorates. A source drawer,
modal or menu keeps its source's own shadow.

**Borders** on pieces written here: 1px; 2px for the focus ring; dashed only for a gap. A
source component keeps its own border widths in this system's border colours.

## Icons

- Set: Untitled UI Icons (line style), used only through the `@untitledui/icons` npm package
  the base components already import. No icon file is committed (ruling 5). Source:
  <https://www.untitledui.com/free-icons>.
- Sizes: an icon inside a source component keeps the source's size. In pieces written here,
  16 beside `small` text and 20 beside `body` text.
- Icons inherit the text colour. An icon never stands without a label, except the trace
  control, which carries an accessible name.
- The ten status shapes (filled circle, half-filled circle, ring, dashed ring, slashed circle,
  triangle, diamond, square, cross, pause bars) are part of this system and are drawn in CSS,
  10px; they are not taken from the icon set.
- The Claude Design page draws icons and the logo symbol as placeholders. The predecessor's
  symbol file is committed at step D2a (ruling 10); the wordmark is not.

## Components

This table names, for each base component, the variants and states this system uses, the
colours they take, and the live page it is built from (read 2026-11-13). Which component presents which
kind of information (metrics, facts, dated records, activity, statements and the rest) is the
[component map](component-map.md)'s; it is not restated here. "UUI" is Untitled UI React (MIT,
copied in with `npx untitledui@latest add <name>`), built on React Aria, the one primitive
library (ruling 3).

Every source component follows the source-look rule in "What this system supplies" above: its
design is its source page's, in this system's colours and typefaces. That holds equally for a
Shadcnblocks piece redrawn on React Aria, which is redrawn to look like its source page.

| Component | Variants and states in this system | Source |
| :--- | :--- | :--- |
| Button | `primary`, `secondary`, `tertiary`, `primary-destructive`; the source's sizes (`sm` to `xl`; `md` by default here); hover, pressed, focus, disabled, loading | UUI <https://www.untitledui.com/react/components/buttons> |
| Input | Label, hint, error with message, disabled; the source's `md` size | UUI <https://www.untitledui.com/react/components/inputs> |
| Select | Default, focus, disabled, invalid | UUI <https://www.untitledui.com/react/components/select> |
| File upload | Drop zone; per-file progress, complete, failed with retry | UUI <https://www.untitledui.com/react/components/file-uploaders> |
| Tabs | Selected in Ultramarine with a 2px line (underline when horizontal, side line when vertical); count badge neutral | UUI <https://www.untitledui.com/react/components/tabs> |
| Chart or Table toggle | The source's joined button group, single selection, with the selected segment as the source shows it, in these colours | UUI <https://www.untitledui.com/react/components/button-groups> |
| Sidebar navigation | Light, in the variant the map names; selected item `surface-selected` with Ultramarine text and icon, hover `surface-subtle`, counts as neutral count badges | UUI <https://www.untitledui.com/react/components/sidebar-navigations> |
| Card and tile | Card (`radius-lg`, padding 32, `shadow-1`) and tile (`radius-md`, padding 24), written here on the tokens. A card may hold a group of source components or a chart. A metric is the source's metric card, one card per metric, never a joined strip | This system; metric card UUI <https://www.untitledui.com/react/components/metrics> |
| Table | Divider-line style; `md` rows on findings pages and `sm` rows for the dense audit tables on Evidence and the source rows in Signal settings; sortable heads; row hover `surface-subtle`; figures right-aligned with tabular numerals. The same colours and alignment apply to a HyperUI table | UUI <https://www.untitledui.com/react/components/tables> |
| Badge | `pill-color`; forms listed under "Badge forms" below | UUI <https://www.untitledui.com/react/components/badges> |
| Alert | Floating or inline; info, warning, error, success, each with its status shape | UUI <https://www.untitledui.com/react/components/alerts> |
| Empty state | Featured icon, title, one sentence, optional action | UUI <https://www.untitledui.com/react/components/empty-states> |
| Gap panel | Hatched dashed panel for "Not established for this run" | This system |
| Withheld value | Striped bar with a neutral badge | This system |
| Blocked module | Neutral badge with a slashed circle and its sentence | This system |
| Drawer | Slide-out with header, scrolling body, pinned footer; the source's own shadow and radius | UUI `SlideoutMenu` <https://www.untitledui.com/react/components/drawers> |
| Tooltip | Default with supporting text, on `surface-inverse` | UUI <https://www.untitledui.com/react/components/tooltips> |
| Progress steps | `IconsWithText` with the `number` marker; complete, current, incomplete | UUI <https://www.untitledui.com/react/components/progress-steps> |
| Progress bar | The source's track (8px by default) in `action-subtle`, fill `action` | UUI <https://www.untitledui.com/react/components/progress-indicators> |
| Loading indicator | `line-simple` spinner, on a run page while a run is live only (see Motion) | UUI <https://www.untitledui.com/react/components/loading-indicators> |
| Skeleton | Static blocks in `surface-subtle`, `radius-xs`, in the shape of what will arrive; no animation | This system |
| Timeline | Vertical, for dated records | HyperUI <https://www.hyperui.dev/components/application/timelines> |
| Featured icon | `light` theme, the source's size | UUI <https://www.untitledui.com/react/components/featured-icons> |

A component the map names that has no row here keeps its source's look unchanged, in this
system's colours and typefaces.

**Badge forms.** Five, so that a state never looks like a label:

| Form | Looks like | Used for |
| :--- | :--- | :--- |
| Status badge | Leading status shape, word, status colour | A state, and nothing else |
| Label badge | Word only, neutral (`text-secondary` on `surface-subtle`) | Pathway, kind, qualifier, "AI" |
| Count badge | Number only, neutral | Counts on tabs and navigation items |
| Dot badge | 8px `action` dot | Unread |
| Trace control | Icon only, with an accessible name and tooltip; shown on hover and focus, and always shown on a touch device | One per paragraph, row or figure |

**Status shapes.** Ten shapes, each with one meaning:

| Shape | Meaning |
| :--- | :--- |
| Filled circle | Complete, good |
| Half-filled circle | Under way, pending |
| Ring | Not started, idle; in the status set, a note |
| Square | Settled, approved |
| Triangle | Caution; something to look at |
| Diamond | Problem |
| Cross | Rejected |
| Pause bars | Paused, interrupted |
| Slashed circle | "Not assessable", and nothing else (a blocked module, in every set that lists modules) |
| Dashed ring | A gap, and nothing else: something this run did not establish |

A set is a group of states that can appear together in one list, table, legend or strip.
Within a set every state has a different shape; no two states differ by colour or word alone.

| Set | State, shape and colour family |
| :--- | :--- |
| Status | Success: filled circle. Warning: triangle. Error: diamond. Info: ring |
| Run states | Queued: ring, neutral. Running: half-filled circle, action. Finished: filled circle, success. Failed: diamond, error. Capped: triangle, warning. Rejected: cross, neutral. Interrupted: pause bars, warning |
| Signal source states | Proposed: half-filled circle, info. Approved: square, neutral. Healthy: filled circle, success. Quiet: ring, neutral. Paused: pause bars, neutral. Failing: diamond, error |
| Dated records | Past: filled circle, neutral. Next: half-filled circle, action. Later: ring, neutral |
| Answer state | Answered: filled circle, success. Partly answered: half-filled circle, info. Not answered: ring, neutral |
| Met or not met | Met: filled circle, success. Not met: triangle, warning |
| Freshness | Checked: filled circle, success. Not checked yet: ring, neutral |
| Module state | Delivered: filled circle, success. Delivered with gaps: dashed ring, gap colours. Not assessable: slashed circle, neutral. Not run (only in a run that has ended): ring, neutral |
| Change state | Changed: triangle, action. Unchanged: square, neutral. Not assessable: slashed circle, neutral |
| Gap severity | High: diamond, error. Medium: triangle, warning. Low: ring, neutral |
| File state | Uploading: half-filled circle, action. Read in full: filled circle, success. Read in part: triangle, warning. Unreadable: diamond, error |
| Approval | Awaiting your approval: half-filled circle, info |
| Activity that cannot be read | State not known: dashed ring, gap colours |

A shape recurs across sets with the same meaning: the filled circle is Success, Finished,
Healthy, Past, Answered, Met, Checked, Delivered and Read in full; the half-filled circle is
Running, Proposed, Next, Partly answered, Uploading and Awaiting your approval; the ring is
Info, Queued, Quiet, Later, Not answered, Not checked yet, Low and Not run; the triangle is
Warning, Capped, Not met, Medium, Read in part and Changed; the diamond is Error, Failed,
Failing, High and Unreadable; the square is Approved and Unchanged; the pause bars are
Interrupted and Paused; the dashed ring is a gap, Delivered with gaps and State not known. Two
states that share a shape never appear in one list together.

The sets added at review 2 (ruling 7), and why each shape:

- **Module state and change state sit together on the Changes page,** so across the two sets
  no shape has two meanings: filled circle, dashed ring and ring belong to module state only,
  triangle and square to change state only, and the slashed circle is "Not assessable" in
  both.
- **"Delivered with gaps" is the dashed ring in the gap colours** (`#514D80` text, dashed
  `#827BCC` edge, white fill), because what it reports is gaps. It is not the half-filled
  circle, which means under way, and not a warning.
- **"Changed" is the triangle in the action colours** (`#001AFF` on `#E5E8FF`): something to
  look at, not something wrong, so it does not wear the warning colour. Its shape differs from
  Unchanged and Not assessable, so the colour is never the only cue.
- **"Unreadable" is one state with one word** for a file that could not be read or was
  rejected at run start; the sentence beside it says which. It is the diamond, not the run
  state's cross.
- **A module that fails inside a run reads "Not assessable"** with its sentence; "Failed" and
  the diamond on a run page stay the run's.
- **"Not run" and "Queued" share the ring** and never meet: Queued exists only in a live run,
  Not run only in one that has ended.
- **"State not known"** stands where the run state badge would be when the activity cannot be
  read. It is a gap, so it takes the gap's shape, and is never listed beside a module's
  "Delivered with gaps".
- **Gap severity** is shown only in the Evidence gap register, beside the gap, never in place
  of the gap's own form.
Two sets never share one list, table or legend, so those states never sit side by side; where
two sets are on the same page (a run-state badge in the page header above a timeline), the
word and the position tell them apart. A set the map adds later takes shapes from the first
table by meaning and keeps them distinct within the set.

Agreed with the component map: status shapes are the CSS shapes above; running is the CSS
pulsing shape (a half-filled circle, so it differs from Finished with motion off); queued is
the CSS shimmer; a gap is the hatched dashed panel; withheld is the
striped bar with a neutral badge; a blocked module is a neutral badge with its sentence; the
card is written here; dated records use the HyperUI timeline; the Chart or Table toggle is the
Untitled UI joined button group.

What the live pages showed that the build must plan for:

- **Dependencies.** UUI's manual install lists five packages, not one: `react-aria-components`,
  `tailwindcss-react-aria-components`, `tailwind-merge`, `tailwindcss-animate` and
  `@untitledui/icons`. Select adds `react-stately`. Each needs a decision record.
- **Theme.** UUI reads `--color-brand-50` to `--color-brand-950` and `--font-body`,
  `--font-display`, `--font-mono` from a `theme.css` `@theme` block. This system maps onto
  those: the Ultramarine steps fill the brand scale, and the three families fill the fonts.
- **Shadcnblocks.** Nothing is bought, and its named variants could not be read (review 2,
  ruling 3). The build takes those pieces from Untitled UI or HyperUI where an equivalent
  exists; where none does, the piece copies the Shadcnblocks page's look, built on React Aria
  in place of Radix or Base UI. shadcn/ui and Kibo UI are not approved sources: their look was
  accepted for the mocks only. This system supplies only its colour values, typefaces, status
  shapes, gap states and motion.
- **React Bits.** Nothing is taken from it (ruling 4). Every animation here is CSS.
- **Charts.** Recharts (ruling 2), with its own decision record at D2a after it passes the
  open-from-disk check. The chart rules below apply to it.

## Chart palette

Six series in a fixed order, then "Other". A series keeps its colour when others are filtered
out; a seventh series folds into Other.

| Slot | Colour | Hex | Contrast on white | Gray value (0 to 255) | Line style |
| :--- | :--- | :--- | ---: | ---: | :--- |
| 1 | Ultramarine | `#001AFF` | 8.10 | 44 | Solid, circle marker |
| 2 | Violet D2 | `#827BCC` | 3.71 | 134 | Dashed, square marker |
| 3 | Reef D4 | `#994A34` | 6.21 | 95 | Solid, triangle marker |
| 4 | Orange D3 | `#B28B00` | 3.19 | 135 | Dotted, diamond marker |
| 5 | Green D5 | `#0F8048` | 5.00 | 88 | Solid, ring marker |
| 6 | Yellow D4 | `#8C9900` | 3.15 | 132 | Dash-dot, cross marker |
| Other | Neutral D1 | `#7F848D` | 3.76 | 132 | Solid, no marker |

Gray value is Rec. 601 luma on the 8-bit sRGB values: 0.299 R + 0.587 G + 0.114 B, rounded.

How it was tested (palette validator, light mode, white surface, exit 0):

- Every slot is at least 3:1 against white, inside the lightness band (OKLCH L 0.43 to 0.77)
  and above the chroma floor.
- Colour blindness: the worst neighbouring pair under simulated protanopia and deuteranopia is
  Green D5 and Orange D3 at ΔE 9.5 (target 8 or more). Under normal vision the worst
  neighbouring pair is ΔE 15.3 (floor 15).
- Slots 1 to 3 also pass with every pair compared (worst ΔE 15.6), so a scatter or a small
  multiple uses at most three series.
- Grayscale: neighbours alternate dark and light (44, 134, 95, 135, 88, 132), and every
  neighbouring pair differs by at least 39 gray levels. Slots 2, 4, 6 and Other sit within 3
  levels of each other, and slots 3 and 5 within 7, so two series that are not neighbours can
  look alike in gray. Colour is therefore never the only cue: lines carry the dash and marker
  above, at most four series are labelled directly, a legend is always present for two or more
  series, and every chart has its table form on the other side of the Chart or Table toggle.

A heat grid uses the magnitude scale below; an empty cell stays `surface-card`.

Other scales:

| Job | Steps |
| :--- | :--- |
| Magnitude (one hue, light to dark) | `#99A3FF`, `#6676FF`, `#3348FF`, `#001AFF`, `#0012B2` |
| Above and below a baseline | `#994A34`, `#E5704D`, `#DDDFE2` (neutral midpoint), `#6676FF`, `#001AFF` |

Marks follow the source chart (review 2, ruling 5): faint horizontal gridlines in
`border-hairline`, the source's bar corners and bar spacing, and its legend, tick text and
height. This system adds: one y-axis, never two; a 1px `border-control` baseline; and, on a
line, the dash and marker of the series table. A chart over periods puts the periods on the x-axis, oldest on the left. Labels, values
and legends use text colours, never the series colour. Status colours are
never used as a series. A missing value is never drawn at zero: the mark is left out and the
slot reads "n.a." (see Gap states).

## Motion

Three rules (ruling 6): only live run state loops; anything else is a one-off transition of at
most 200 ms; numerals never animate. All of it is off under `prefers-reduced-motion`. Every
animation is CSS in the stylesheet; none needs script or a library.

| Kind | Where | What moves | Timing |
| :--- | :--- | :--- | :--- |
| Loop, live run only | Running badge | The half-filled circle pulses a fading Ultramarine halo | 1.6s, ease-in-out, repeating |
| Loop, live run only | Queued module | A slow shimmer where its result will appear | 1.8s, linear, repeating |
| Loop, live run only | Spinner | Rotates while a run is live and no step count exists | The source's timing |
| One-off | Run progress bar | The fill eases to each new value | 200ms, `cubic-bezier(.2,0,0,1)` |
| One-off | Activity feed | A new entry rises 8px and fades in | 200ms, `cubic-bezier(.2,0,0,1)` |
| One-off | Drawer, tabs, accordion | Opens, switches or expands | Up to 200ms, `cubic-bezier(.2,0,0,1)` |

Loading anywhere else is the static skeleton, never a spinner: a list that is still loading
is not live run state. Spend, elapsed time and every other figure change to the new value with no animation. Hover
and focus change state at once.

## Where this departs from the brand guide

| Brand guide | This system | Why |
| :--- | :--- | :--- |
| White page with light grey panels | Faint violet canvas (`#F6F5FF`) with white cards | A tinted ground lets white cards carry the content without heavy borders; it reads calmer than grey |
| Sharp Grotesk Bold headlines, Inter text | Schibsted Grotesk headings, Geist text, Geist Mono for evidence | The headline font is commercial and cannot be committed; Geist has tabular numerals and a matching mono |
| Headline leading 95 percent, small body sizes | Leading 108 to 117 percent on headings; body 16 / 26 | Long analytical titles wrap to two lines; the reader reads prose, so the type is larger |
| No shadows stated | Two soft Navy shadows | A card and a chart tooltip need to sit above the page |
| Rounded tiles, radius undefined | Radii 6, 12, 20, 28 and full | The owner's "rounded" |
| Secondary colours paired with Navy as accents | Secondaries appear only as tints (L steps) and dark steps (D steps), never at full strength in the interface | At full strength none passes 3:1 on white |
| Tertiary used sparingly | Tertiary steps supply all secondary text, borders, status and chart colours | They are the only brand values that pass contrast |
| Chart series seen as Ultramarine, Green, Yellow, Violet, dark teal, Reef | Ultramarine, Violet D2, Reef D4, Orange D3, Green D5, Yellow D4 | Neon Green and Yellow fail 3:1; every dark Cyan step falls below the chroma floor and reads as grey; the order was searched for colour-blind separation |
| Flat fills, no gridlines | Flat fills kept; faint horizontal gridlines and the source chart's bar corners | Charts follow their source (review 2, ruling 5) |

Kept from the guide: the 4-unit grid, sentence case, Navy as the anchor, Ultramarine for
action, content before ornament.

## Rulings

The owner ruled on this system at review 1; [decision 0003](../decisions/0003-design-track.md)
("Rulings at review 1") is the record and governs. As applied here:

- **Accepted as proposed:** the violet canvas `#F6F5FF`, the Ultramarine primary button,
  Schibsted Grotesk with Geist and Geist Mono, and the muted chart colours that pass 3:1.
- **No dark mode.**
- **Charts** are built with Recharts; its decision record is written at D2a.
- **One primitive library:** React Aria. No Radix, no Base UI.
- **React Bits:** nothing is taken from it; count-up is removed and no numeral animates.
- **Icons** come through the npm package only.
- **Motion:** one-off transitions up to 200 ms, loops for live run state only, all off under
  reduced motion.
- **Logo:** the predecessor's symbol file is committed at D2a.
- **Source look:** source components copy their source page's design.

At review 2 (decision 0003, "Rulings at review 2"):

- **Cards:** a card may hold a group of source components or a chart, as page layout.
- **Type:** page titles (36px) and judgement prose (16px) use this system's sizes; every other
  source component keeps its own.
- **Shadcnblocks:** nothing is bought; the build uses Untitled UI or HyperUI where an
  equivalent exists.
- **Statement table:** no Trend sparkline column.
- **Charts and tiles follow the source:** faint horizontal gridlines, the source's bar
  corners, separate metric cards; "what would change the view" is the source toast in the
  info status colours.
- **Bottom line:** a Navy band with white text.
- **New status sets:** module state, change state, gap severity, file state and approval are
  defined above; "Delivered with gaps" and "Changed" do not use the half-filled circle.

## Rules from the owner's prompts

Rules the owner typed, found by reading the owner's prompts in this project's and the
predecessor's sessions on 2026-11-13. "Held in" names where the rule is written down; "nowhere
yet" means no file on `main` states it and the coordinator is told.

| Rule | Owner's words | Date | Held in |
| :--- | :--- | :--- | :--- |
| Findings show outcomes and links; backend and audit material is always findable but never sits among the analysis | "focused on presenting outcome and links ... anything that looks backend & audit relevant" | 2026-11-13 | Screen inventory; this file (Geist Mono and identifiers on Evidence and in the trace drawer only) |
| A handoff is a database: not everything in it is shown | "the handoff are to be used similarly to a database, not everything needs to be shown" | 2026-11-13 | `CLAUDE.md` (delivery selects) |
| One design is not repeated for a grouping of different information | "do not overuse a design for same grouping" | 2026-11-13 | Component map |
| No flat tables | "do not use flat boring tables" | 2026-11-13 | Component map; screen inventory (known defect) |
| No table identifiers on screen | "no table IDs" | 2026-11-13 | Nowhere yet |
| Nothing written for another module is displayed | "do not display anything also considered intermodule communication" | 2026-11-13 | Screen inventory |
| Presentation is chosen for the reader: what, how and why | "Always consider user persona regarding what, how and why" | 2026-11-13 | `CLAUDE.md` (Reader); design track plan |
| No module codes or method step identifiers on screen; the module's name instead, in the model's file navigator too | "Remove all cp-IDs and methodology step IDs from user facing screens" | 2026-11-10, 2026-11-12 | Screen inventory (module codes); step identifiers nowhere yet |
| A chart over periods has the periods on the x-axis | "Charts with periods should be transposed, with period on the x axis" | 2026-11-10 | This file (Chart palette, marks) |
| A chart is drawn as a chart, not inside a table | "why charts in tables when they should be charts" | 2026-11-12 | Decision 0003, review 2, ruling 4: the statement table has no Trend sparkline column; the Bars view stays |
| A sentence leads to its sources by a control or highlighted text, never by a citation in the prose | "clickable chips or highlighted text"; "citations within the credit narrative" named as a defect | 2026-11-12, 2026-11-11 | `CLAUDE.md` (Reader); ruling 7 (trace control) |
| The prose reads as a credit analyst's judgement, not restated data | "very robotic and more focused on data collection and restatement" | 2026-11-11 | `CLAUDE.md` (Reader) |
| Nothing on screen that does not help the reader | "remove anything not complimentary to UX" | 2026-11-10 | Component map |
| The look is modern product design, not enterprise business software; only colours and logo are fixed | "modern ux/ui and not enterprise business solutions style"; "The brand guide is not a rule" | 2026-11-13 | Decision 0003; this file |
| A source component copies its source's design | "even if you use them copy the design" | 2026-11-13 | Decision 0003; this file |
| A component's live page is read before it is used | "always check live" | 2026-11-12 | `CLAUDE.md` |
| The library's sections: Overview (key findings, no module navigator), Changes ("what has changed since the last time I looked"), Modules (all findings, one design language, navigator always visible and listing only modules that ran), Forecast, Evidence (handoffs to download, source files used), and the issuer's report history | Prompts of 2026-11-11 | 2026-11-11 | `CLAUDE.md`; screen inventory; "only modules that ran" and handoff download nowhere yet |
| A new run on an issuer starts from its report page; the run start page opens from the library by its icon | "starting a new run on an issuer from their report page" | 2026-11-11, 2026-11-12 | Nowhere yet |

"Stick to current font" (2026-11-12) was replaced by the typefaces the owner accepted at
review 1.

## Not verified

- Read live but not built: no component here has been installed in `web/` or opened from disk
  under the content security policy.
- Untitled UI's full licence agreement was not read beyond the repository licence files; which
  components sit behind its paid tier is known only where a page said so (card headers).
- Shadcnblocks pages are the source of the look for the components the map takes from them;
  none was read for this page. Flowbite React, Ant Design, Preline and Uiverse are unused
  (decision 0003).
- Recharts has not been installed or opened from disk; whether it can draw the dash, marker
  and missing-value rules above is untested.
- The half-filled circle and the square were checked at 10px in one headless Chrome render
  only.
- The states named in the Answer state, Met or not met and Freshness sets are this page's
  reading of the map's rows; the map does not list their names.
- The Claude Design page is at version 0.5. It does not show the sets added at review 2, the
  two new border tokens, the joined button group, or charts with gridlines and the source's
  bar corners; its chart still has 4px bar tops and no gridlines.
- The shapes for the review 2 sets were chosen from the mocks' written proposals; the mock
  pages themselves were not opened, and no set was drawn or checked at 10px in its new colour
  (the triangle in the action colours, the dashed ring as a module state).
- The Untitled UI metrics page answered HTTP 200 on 2026-11-13; its content was not read in
  this round. It was rendered in headless Chrome at 1440px wide
  from a local copy that is byte-identical to the uploaded file, with no console messages; it
  was not checked at narrow widths, in Edge, or in the Claude Design editor.
- The page's source component samples (button, input, tabs, badge, table, navigation) are
  drawings at the sizes, radius and shadow read on the Untitled UI pages on 2026-11-13. They
  were not compared pixel by pixel with those pages, and the Chart or Table toggle, checkbox
  and switch were not redrawn.
- The owner's rules were read from the typed prompts in the session transcripts on this
  machine for this project and its predecessors (452 messages). A prompt in a session not
  stored there was not read, and each rule's wording here is a reading of the owner's words.
- Tabular numerals in Geist were seen in the render, not tested glyph by glyph. The fonts were
  loaded from Google Fonts for the mock; the files to commit have not been downloaded.
- Colour-blind separation was simulated (Machado 2009), not tested with readers. Tritanopia was
  reported by the validator but is not a gate.
- The Claude Design project is an ordinary project, not a registered design system:
  `list_design_systems` still returns none after it was written, so the D1 mock projects
  cannot bind it and must copy its tokens from this page. How to register one was not found.
- The prior-art search was limited to the approved component sources.

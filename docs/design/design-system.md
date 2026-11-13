# Design system

Version 0.3, 2026-11-13, with the owner's rulings at review 1 and the source-look instruction
applied (step D0 of the
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
- **Colour never works alone.** Every status has its own shape and a word, so it survives
  grayscale and colour blindness.
- **Motion means a run is live.** Only live run state loops; everything else is a single
  short transition or none.

Every colour below is a hex from the [brand tokens](brand-tokens.md); none is invented. Token
names are the names step D2a gives the Tailwind `@theme` variables.

## Colour roles

### Surface

| Token | Hex | Brand step | Use |
| :--- | :--- | :--- | :--- |
| `surface-canvas` | `#F6F5FF` | Violet L9 | Page background |
| `surface-card` | `#FFFFFF` | White | Cards, tiles, inputs, drawers |
| `surface-subtle` | `#F4F4F5` | Neutral L9 | Row and item hover, disabled field, switch track |
| `surface-selected` | `#E5E8FF` | Ultramarine L9 | Selected navigation item, subtle action fill |
| `surface-inverse` | `#000533` | Navy | Tooltip; reserved for an inverse band |

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
| `focus` | `#001AFF` | Ultramarine | 2px ring, 2px offset, on light surfaces |
| `focus-inverse` | `#4AD4FF` | Cyan | The same ring on Navy |

Hover on a neutral surface (table row, navigation item, secondary button) is `surface-subtle`.

### Border

| Token | Hex | Brand step | Use |
| :--- | :--- | :--- | :--- |
| `border-subtle` | `#E3E1FF` | Violet L7 | Card and tile edge (decorative) |
| `border-hairline` | `#E8E9EB` | Neutral L8 | Row dividers (decorative) |
| `border-control` | `#7F848D` | Neutral D1 | Inputs, checkboxes, secondary button, chart baseline |
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

A gap is not an error and never wears a status colour.

| State | Wording | Drawn as |
| :--- | :--- | :--- |
| Gap | "Not established for this run" | A hatched dashed panel: diagonal white and `#F6F5FF` hatch, 1px dashed `#827BCC` edge, violet text `#514D80` (Violet D5), dashed ring. The inline badge form (same text, edge and ring) appears only in a table cell or on a chart |
| Blocked module | "Not assessable" | Neutral badge (`#474A4F` on `#F4F4F5`) with a slashed circle, always with one sentence saying why |
| Missing figure | "n.a." | The text itself in `text-tertiary`, right-aligned like a number. Never 0, never a badge |
| Missing value in a chart | "n.a." | No mark is drawn. A bar slot stays empty with "n.a." in `text-tertiary` on the baseline; a line breaks and is not joined across the gap. Never drawn at zero |
| Withheld value | "Withheld" | A short neutral striped bar where the figure would be, with a neutral badge |
| No runs yet, no earlier run | A sentence and, where one exists, the next action | Centred empty state with a 48px featured icon |

### Run states

| State | Colour family | Shape |
| :--- | :--- | :--- |
| Queued | Neutral | Ring |
| Running | Action (`#001AFF` on `#E5E8FF`) | Pulsing filled circle |
| Finished | Success | Filled circle |
| Failed | Error | Diamond |
| Capped | Warning | Triangle |
| Rejected | Neutral | Cross |
| Interrupted | Warning | Pause bars |

The slashed circle belongs to "Not assessable" alone. Running is the CSS pulsing dot and queued
is the CSS shimmer (see Motion).

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

The gap edge was Violet L2 (2.01:1 on white) in version 0.1 and is now Violet D2.

Deliberately outside the table:

- `text-disabled` `#A4A9B1` on white is 2.36:1. WCAG exempts inactive controls; it is used for
  nothing else.
- `border-subtle` and `border-hairline` are decorative (1.3:1). No meaning depends on them.
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
| `small` | 14 / 22 | 400 | Geist | 0 | Table cells, hints, notes |
| `caption` | 13 / 18 | 500 | Geist | 0 | Column headers, labels above a figure, badges |
| `metric` | 40 / 44 | 600 | Geist, tabular | -0.02em | Headline figure on a metric tile |
| `mono` | 13 / 20 | 400 | Geist Mono | 0 | Evidence identifiers |

Sentence case everywhere. Prose columns are capped near 72 characters. Figures in tables are
right-aligned with tabular numerals. Nothing is set below 13px.

## Space, radius, elevation, borders

**Spacing** (base 4): 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96.
Page gutter 32, card padding 32, tile padding 24, gap between cards 24, gap between sections 64.
Buttons, inputs and other source components keep their source's own sizes (see "Source look"
under Components).

| Radius token | Value | Use |
| :--- | :--- | :--- |
| `radius-xs` | 6px | Skeleton block |
| `radius-sm` | 12px | Small pieces written here (trace control hit area, chart tooltip) |
| `radius-md` | 20px | Tiles, gap panels |
| `radius-lg` | 28px | Cards |
| `radius-full` | 999px | Status shapes, gap badge, withheld bar |

Source components keep their source's own radius (see "Source look" under Components).

| Elevation token | Value | Use |
| :--- | :--- | :--- |
| `shadow-1` | `0 1px 2px rgba(0,5,51,.06)` | Card at rest |
| `shadow-2` | `0 6px 16px rgba(0,5,51,.08), 0 1px 2px rgba(0,5,51,.04)` | Menu, popover |
| `shadow-3` | `0 20px 48px rgba(0,5,51,.16)` | Trace drawer, modal |

Shadows are Navy at low alpha. Depth separates layers and never decorates.

**Borders:** 1px everywhere; 2px only for the focus ring and the selected tab underline; dashed
only for a gap.

## Icons

- Set: Untitled UI Icons (line style), used only through the `@untitledui/icons` npm package
  the base components already import. No icon file is committed (ruling 5). Source:
  <https://www.untitledui.com/free-icons>.
- Sizes: 16 inside badges, 20 beside text, 24 standalone, 48 as a featured icon in an empty
  state.
- Icons inherit the text colour. An icon never stands without a label, except the trace
  control, which carries an accessible name.
- The eight status shapes (circle, triangle, diamond, ring, dashed ring, slashed circle, cross,
  pause bars) are part of this system and are drawn in CSS; they are not taken from the icon
  set.
- The Claude Design page draws icons and the logo symbol as placeholders. The predecessor's
  symbol file is committed at step D2a (ruling 10); the wordmark is not.

## Components

This table fixes how each base component looks: its variants, sizes and states on these
tokens, and the live page it is built from (read 2026-11-13). Which component presents which
kind of information (metrics, facts, dated records, activity, statements and the rest) is the
[component map](component-map.md)'s; it is not restated here. "UUI" is Untitled UI React (MIT,
copied in with `npx untitledui@latest add <name>`), built on React Aria, the one primitive
library (ruling 3).

**Source look (owner, 2026-11-13).** A component taken from an approved source copies that
source page's visual design closely: its layout, proportions, spacing, sizes, radius, shadow
and states stay as the live page shows them. It is not restyled. This system supplies only
what the owner fixed or accepted: the colour tokens (through the source's own theme variables),
the typefaces, the status shapes, the gap, withheld and blocked states, and motion. Where a
size or radius on this page differs from the source's own, the source wins for that component;
the spacing, radius and elevation tokens above govern the pieces written here (card, tile, gap
panel, withheld bar, status shapes) and page layout. This applies equally to a Shadcnblocks
piece redrawn on React Aria: it is redrawn to look like its source page. The instruction was
given in the D0 session and is not yet in decision 0003.

| Component | Variants and states in this system | Source |
| :--- | :--- | :--- |
| Button | `primary`, `secondary`, `tertiary`, `primary-destructive`; the source's sizes (`sm` to `xl`; `md` by default here); hover, pressed, focus, disabled, loading | UUI <https://www.untitledui.com/react/components/buttons> |
| Input | Label, hint, error with message, disabled; the source's `md` size | UUI <https://www.untitledui.com/react/components/inputs> |
| Select | Default, focus, disabled, invalid | UUI <https://www.untitledui.com/react/components/select> |
| File upload | Drop zone; per-file progress, complete, failed with retry | UUI <https://www.untitledui.com/react/components/file-uploaders> |
| Tabs | Selected in Ultramarine with a 2px line (underline when horizontal, side line when vertical); count badge neutral | UUI <https://www.untitledui.com/react/components/tabs> |
| Chart or Table toggle | Button group, single selection; the selected item is a white pill on `surface-subtle` | UUI <https://www.untitledui.com/react/components/button-groups> |
| Sidebar navigation | Light, in the variant the map names; selected item `surface-selected` with Ultramarine text and icon, hover `surface-subtle`, counts as neutral count badges | UUI <https://www.untitledui.com/react/components/sidebar-navigations> |
| Card and tile | Card (radius 28, padding 32, `shadow-1`) and tile (radius 20, padding 24), written here on the tokens | This system |
| Table | Divider-line style; `md` rows on findings pages and `sm` rows for the dense audit tables on Evidence; sortable heads; row hover `surface-subtle`; figures right-aligned with tabular numerals. The same colours and alignment apply to a HyperUI table | UUI <https://www.untitledui.com/react/components/tables> |
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
| Loading indicator | `line-simple` spinner, on a run page while a run is live only (see Motion) |
| Skeleton | Static blocks in `surface-subtle`, `radius-xs`, in the shape of what will arrive; no animation | This system | UUI <https://www.untitledui.com/react/components/loading-indicators> |
| Timeline | Vertical, for dated records | HyperUI <https://www.hyperui.dev/components/application/timelines> |
| Featured icon | `light` theme, 48 | UUI <https://www.untitledui.com/react/components/featured-icons> |

A component the map names that has no row here (modal, radio cards, text area, toggle, metric
tile, avatar, page header, filter bar, command menu, activity feed, tree view, messaging, tags,
badge group, toast, stepper, half-circle progress) follows "Source look" with these tokens.

**Badge forms.** Five, so that a state never looks like a label:

| Form | Looks like | Used for |
| :--- | :--- | :--- |
| Status badge | Leading status shape, word, status colour | A state, and nothing else |
| Label badge | Word only, neutral (`text-secondary` on `surface-subtle`) | Pathway, kind, qualifier, "AI" |
| Count badge | Number only, neutral | Counts on tabs and navigation items |
| Dot badge | 8px `action` dot | Unread |
| Trace control | Icon only, with an accessible name and tooltip | One per paragraph, row or figure |

**Shapes for other states.** A state the map names that is not a run state takes the shape of
its meaning, always with its word:

| Meaning | Shape | Colour family |
| :--- | :--- | :--- |
| Good, done, healthy, met, answered | Filled circle | Success |
| Needs attention, thin, not met | Triangle | Warning |
| Failed, failing, breached | Diamond | Error |
| Changed, restated, next | Ring | Info |
| Not started, waiting, later, proposed, quiet, not checked | Ring | Neutral |
| Approved, past | Filled circle | Neutral |
| Paused, held | Pause bars | Neutral |
| Refused, removed | Cross | Neutral |

Two states in one list can share a shape and differ by colour and word (for example approved
and healthy); the word is what tells them apart, and the mocks test whether that is enough.

Agreed with the component map: status shapes are the CSS shapes above; running is the CSS
pulsing dot; queued is the CSS shimmer; a gap is the hatched dashed panel; withheld is the
striped bar with a neutral badge; a blocked module is a neutral badge with its sentence; the
card is written here; dated records use the HyperUI timeline; the Chart or Table toggle is the
Untitled UI button group.

What the live pages showed that the build must plan for:

- **Dependencies.** UUI's manual install lists five packages, not one: `react-aria-components`,
  `tailwindcss-react-aria-components`, `tailwind-merge`, `tailwindcss-animate` and
  `@untitledui/icons`. Select adds `react-stately`. Each needs a decision record.
- **Theme.** UUI reads `--color-brand-50` to `--color-brand-950` and `--font-body`,
  `--font-display`, `--font-mono` from a `theme.css` `@theme` block. This system maps onto
  those: the Ultramarine steps fill the brand scale, and the three families fill the fonts.
- **Shadcnblocks.** Its pages are layout references only: a piece taken from one is redrawn on
  React Aria with these tokens, as the component map lists. Radix and Base UI are not added.
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

Marks: bars with 4px rounded tops and a 2px gap between neighbours; 2px lines; markers 8px or
more; one y-axis, never two; a 1px `border-control` baseline, no gridlines beyond a faint zero
line. Labels, values and legends use text colours, never the series colour. Status colours are
never used as a series. A missing value is never drawn at zero: the mark is left out and the
slot reads "n.a." (see Gap states).

## Motion

Three rules (ruling 6): only live run state loops; anything else is a one-off transition of at
most 200 ms; numerals never animate. All of it is off under `prefers-reduced-motion`. Every
animation is CSS in the stylesheet; none needs script or a library.

| Kind | Where | What moves | Timing |
| :--- | :--- | :--- | :--- |
| Loop, live run only | Running badge | The state dot pulses a fading Ultramarine halo | 1.6s, ease-in-out, repeating |
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
| No shadows stated | Three soft Navy shadows | Drawers and menus need to sit above the page |
| Rounded tiles, radius undefined | Radii 6, 12, 20, 28 and full | The owner's "rounded" |
| Secondary colours paired with Navy as accents | Secondaries appear only as tints (L steps) and dark steps (D steps), never at full strength in the interface | At full strength none passes 3:1 on white |
| Tertiary used sparingly | Tertiary steps supply all secondary text, borders, status and chart colours | They are the only brand values that pass contrast |
| Chart series seen as Ultramarine, Green, Yellow, Violet, dark teal, Reef | Ultramarine, Violet D2, Reef D4, Orange D3, Green D5, Yellow D4 | Neon Green and Yellow fail 3:1; every dark Cyan step falls below the chroma floor and reads as grey; the order was searched for colour-blind separation |
| Flat fills, no gridlines | Kept, plus 4px rounded bar tops and a faint zero line | Softer marks match the rest of the system; a zero line is needed for bridges |

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

## Not verified

- Read live but not built: no component here has been installed in `web/` or opened from disk
  under the content security policy.
- Untitled UI's full licence agreement was not read beyond the repository licence files; which
  components sit behind its paid tier is known only where a page said so (card headers).
- Shadcnblocks pages are layout references listed in the component map; none was read for
  this page. Flowbite React, Ant Design, Preline and Uiverse are unused (decision 0003).
- Recharts has not been installed or opened from disk; whether it can draw the dash, marker
  and missing-value rules above is untested.
- The Claude Design page was rendered in headless Chrome at 1440px wide only, with no console
  errors; it was not checked at narrow widths, in Edge, or in the Claude Design editor.
- Tabular numerals in Geist were seen in the render, not tested glyph by glyph. The fonts were
  loaded from Google Fonts for the mock; the files to commit have not been downloaded.
- Colour-blind separation was simulated (Machado 2009), not tested with readers. Tritanopia was
  reported by the validator but is not a gate.
- The Claude Design project is an ordinary project, not a registered design system:
  `list_design_systems` still returns none after it was written, so the D1 mock projects
  cannot bind it and must copy its tokens from this page. How to register one was not found.
- The prior-art search was limited to the approved component sources.

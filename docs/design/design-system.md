# Design system

Version 0.1, 2026-11-13, for the owner's first review (step D0 of the
[design track plan](../superpowers/plans/2026-11-13-design-track.md)).

**Rendered system:** [Claude Design project](https://claude.ai/design/p/9cd0f670-7c22-43e5-b09b-ace684186879?file=Design+System.dc.html).
Standalone Claude Design has announced that its tools stop working by 2026-12-14, so this page
holds every value the build needs.

## The idea in four lines

- **Judgement first, on a calm page.** White rounded cards on a faint violet canvas, large
  type, generous space.
- **One accent.** Navy carries text; Ultramarine is the only action colour.
- **Colour never works alone.** Every status has its own shape and a word, so it survives
  grayscale and colour blindness.
- **Motion means a run is live.** Nothing else moves.

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
| `border-gap` | `#B5AEFF` | Violet L2 | Dashed edge of a gap state |
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
| Gap | "Not established for this run" | Violet text `#514D80` (Violet D5), dashed `#B5AEFF` edge, dashed ring. As a block: a card-width panel with a diagonal white and `#F6F5FF` hatch |
| Blocked module | "Not assessable" | Neutral badge (`#474A4F` on `#F4F4F5`) with a slashed circle, plus one sentence saying why |
| Missing figure | "n.a." | The text itself in `text-tertiary`, right-aligned like a number. Never 0, never a badge |
| Withheld value | "Withheld" | A short neutral striped bar where the figure would be, and a neutral badge |
| No runs yet, no earlier run | A sentence and, where one exists, the next action | Centred empty state with a 48px featured icon |

### Run states

| State | Colour family | Shape |
| :--- | :--- | :--- |
| Queued | Neutral | Ring |
| Running | Action (`#001AFF` on `#E5E8FF`) | Pulsing filled circle |
| Finished | Success | Filled circle |
| Failed | Error | Diamond |
| Capped | Warning | Triangle |
| Rejected | Neutral | Slashed circle |
| Interrupted | Warning | Pause bars |

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
| Warning mark on fill | `#997700` | `#FFF9E5` | 3.99 | 3 | Pass |

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
Controls are 44 high (buttons) and 48 high (inputs); small buttons are 36 and are not used for
a primary action.

| Radius token | Value | Use |
| :--- | :--- | :--- |
| `radius-xs` | 6px | Checkbox, skeleton line |
| `radius-sm` | 12px | Buttons, inputs, navigation items |
| `radius-md` | 20px | Tiles, gap panels |
| `radius-lg` | 28px | Cards, drawers, modals |
| `radius-full` | 999px | Badges, switches, pill tabs, progress track |

| Elevation token | Value | Use |
| :--- | :--- | :--- |
| `shadow-1` | `0 1px 2px rgba(0,5,51,.06)` | Card at rest |
| `shadow-2` | `0 6px 16px rgba(0,5,51,.08), 0 1px 2px rgba(0,5,51,.04)` | Menu, popover |
| `shadow-3` | `0 20px 48px rgba(0,5,51,.16)` | Trace drawer, modal |

Shadows are Navy at low alpha. Depth separates layers and never decorates.

**Borders:** 1px everywhere; 2px only for the focus ring and the selected tab underline; dashed
only for a gap.

## Icons

- Set: Untitled UI Icons (line style), from the `@untitledui/icons` package the base components
  already import. Source: <https://www.untitledui.com/free-icons>.
- Sizes: 16 inside badges, 20 beside text, 24 standalone, 48 as a featured icon in an empty
  state.
- Icons inherit the text colour. An icon never stands without a label, except the trace
  control, which carries an accessible name.
- The seven status shapes (circle, triangle, diamond, ring, dashed ring, slashed circle, pause
  bars) are part of this system and are drawn in CSS; they are not taken from the icon set.
- The Claude Design page draws icons and the logo symbol as placeholders: no icon file and no
  logo file is in this repository yet.

## Components

Each row names the source page it is built from. Pages were read live on 2026-11-13.
"UUI" is Untitled UI React (MIT, copied in with `npx untitledui@latest add <name>`).

| Component | Variants and states in this system | Source |
| :--- | :--- | :--- |
| Button | Primary, secondary, tertiary, destructive; sizes 36, 44, 52; hover, pressed, focus, disabled, loading | UUI <https://www.untitledui.com/react/components/buttons> |
| Input | Label, hint, error with message, disabled; 48 high | UUI <https://www.untitledui.com/react/components/inputs> |
| Select | Default, focus, disabled, invalid | UUI <https://www.untitledui.com/react/components/select> |
| Checkbox | Off, on, indeterminate, disabled | UUI <https://www.untitledui.com/react/components/checkboxes> |
| File upload | Drop zone; per-file progress, complete, failed with retry (run start, Documents step) | UUI <https://www.untitledui.com/react/components/file-uploaders> |
| Tabs | `underline` for the pages of a run; `button-minimal` as the pill switch between a chart and its table | UUI <https://www.untitledui.com/react/components/tabs> |
| Sidebar navigation | `Simple`, light, four areas (Library, Model, Runs, Signal) | UUI <https://www.untitledui.com/react/components/sidebar-navigations> |
| Header navigation | `Simple`, only where a page has no sidebar | UUI <https://www.untitledui.com/react/components/header-navigations> |
| Breadcrumb | `text`, issuer then run | UUI <https://www.untitledui.com/react/components/breadcrumbs> |
| Card and tile | Card (radius 28, padding 32) and tile (radius 20, padding 24), written here; the UUI card headers are a paid example and are not used | This system |
| Metric tile | Label, figure, change line with a shape; "n.a." form | UUI `MetricsSimple` <https://www.untitledui.com/react/components/metrics>, layout checked against HyperUI stats <https://www.hyperui.dev/components/application/stats> |
| Table | Divider-line style, `md` rows, sortable heads, row hover, one trace control per row | UUI <https://www.untitledui.com/react/components/tables> |
| Details list | Label and value pairs for facts | HyperUI <https://www.hyperui.dev/components/application/details-list> |
| Badge | `pill-color` with a leading shape; success, warning, error, info, neutral, action, gap | UUI <https://www.untitledui.com/react/components/badges> |
| Alert | Floating; info, warning, error, success | UUI <https://www.untitledui.com/react/components/alerts> |
| Empty state | Featured icon, title, one sentence, optional action | UUI <https://www.untitledui.com/react/components/empty-states> |
| Gap panel | Hatched dashed panel for "Not established for this run" | This system (static markup in the manner of HyperUI <https://www.hyperui.dev/components/application/empty-states>) |
| Trace drawer | Slide-out with header, scrolling body, pinned footer | UUI `SlideoutMenu` <https://www.untitledui.com/react/components/drawers> |
| Tooltip | Default with supporting text | UUI <https://www.untitledui.com/react/components/tooltips> |
| Progress steps | `IconsWithText`, numbered, for the five run start steps | UUI <https://www.untitledui.com/react/components/progress-steps> |
| Progress bar | Run progress and spend against the cap | UUI <https://www.untitledui.com/react/components/progress-indicators> |
| Loading indicator | `line-simple` spinner; three-dot pulse for an inline wait | UUI <https://www.untitledui.com/react/components/loading-indicators>, HyperUI <https://www.hyperui.dev/components/application/loaders> |
| Activity feed | `Connected`, for run activity | UUI <https://www.untitledui.com/react/components/activity-feeds> |
| Timeline | Vertical, for dated records | HyperUI <https://www.hyperui.dev/components/application/timelines> |
| Featured icon | `light` theme, 48, in empty states | UUI <https://www.untitledui.com/react/components/featured-icons> |
| Count-up figure | Spend and elapsed time on a live run | React Bits <https://reactbits.dev/text-animations/count-up> |
| Entering list row | New activity entry | React Bits <https://reactbits.dev/components/animated-list> |

What the live pages showed that the build must plan for:

- **Dependencies.** UUI's manual install lists five packages, not one: `react-aria-components`,
  `tailwindcss-react-aria-components`, `tailwind-merge`, `tailwindcss-animate` and
  `@untitledui/icons`. Select adds `react-stately`; the activity feed adds
  `@untitledui/file-icons`. Each needs a decision record.
- **Theme.** UUI reads `--color-brand-50` to `--color-brand-950` and `--font-body`,
  `--font-display`, `--font-mono` from a `theme.css` `@theme` block. This system maps onto
  those: the Ultramarine steps fill the brand scale, and the three families fill the fonts.
- **Licences.** UUI React and HyperUI are MIT. React Bits is MIT with a Commons Clause that
  forbids redistributing the components themselves. The Untitled UI icon licence forbids
  distributing the icons. Both matter for a public repository (see "For the owner's ruling").
- **Charts.** UUI's charts are built on Recharts; HyperUI's load Chart.js from a CDN, which the
  content security policy forbids. No chart source is adopted here; the chart rules below are
  library-neutral.

## Chart palette

Six series in a fixed order, then "Other". A series keeps its colour when others are filtered
out; a seventh series folds into Other.

| Slot | Colour | Hex | Contrast on white | Gray value (0 to 255) | Line style |
| :--- | :--- | :--- | ---: | ---: | :--- |
| 1 | Ultramarine | `#001AFF` | 8.10 | 80 | Solid, circle marker |
| 2 | Violet D2 | `#827BCC` | 3.71 | 133 | Dashed, square marker |
| 3 | Reef D4 | `#994A34` | 6.21 | 97 | Solid, triangle marker |
| 4 | Orange D3 | `#B28B00` | 3.19 | 144 | Dotted, diamond marker |
| 5 | Green D5 | `#0F8048` | 5.00 | 111 | Solid, ring marker |
| 6 | Yellow D4 | `#8C9900` | 3.15 | 145 | Dash-dot, cross marker |
| Other | Neutral D1 | `#7F848D` | 3.76 | 132 | Solid, no marker |

How it was tested (palette validator, light mode, white surface, exit 0):

- Every slot is at least 3:1 against white, inside the lightness band (OKLCH L 0.43 to 0.77)
  and above the chroma floor.
- Colour blindness: the worst neighbouring pair under simulated protanopia and deuteranopia is
  Green D5 and Orange D3 at ΔE 9.5 (target 8 or more). Under normal vision the worst
  neighbouring pair is ΔE 15.3 (floor 15).
- Slots 1 to 3 also pass with every pair compared (worst ΔE 15.6), so a scatter or a small
  multiple uses at most three series.
- Grayscale: neighbours alternate dark and light (80, 133, 97, 144, 111, 145). Slots 2, 4, 6
  and Other are close to each other in gray, so colour is never the only cue: lines carry the
  dash and marker above, at most four series are labelled directly, a legend is always
  present for two or more series, and every chart has its table form.

Other scales:

| Job | Steps |
| :--- | :--- |
| Magnitude (one hue, light to dark) | `#99A3FF`, `#6676FF`, `#3348FF`, `#001AFF`, `#0012B2` |
| Above and below a baseline | `#994A34`, `#E5704D`, `#DDDFE2` (neutral midpoint), `#6676FF`, `#001AFF` |

Marks: bars with 4px rounded tops and a 2px gap between neighbours; 2px lines; markers 8px or
more; one y-axis, never two; a 1px `border-control` baseline, no gridlines beyond a faint zero
line. Labels, values and legends use text colours, never the series colour. Status colours are
never used as a series.

## Motion

Motion appears only while a run is live, and stops under `prefers-reduced-motion`.

| Where | What moves | Timing |
| :--- | :--- | :--- |
| Running badge | The state dot pulses a fading Ultramarine halo | 1.6s, ease-in-out, repeating |
| Run progress bar | The fill eases to each new value | 320ms, `cubic-bezier(.2,0,0,1)` |
| Spend and elapsed time | The figure counts up to the new value | 320ms |
| Queued module | A slow shimmer where its result will appear | 1.8s, linear, repeating |
| Activity feed | A new entry rises 8px and fades in, once | 320ms, `cubic-bezier(.2,0,0,1)` |

Hover, focus, tabs, drawers and page changes switch state without animation. The four CSS
animations above are plain keyframes and transitions in the stylesheet; only the count-up needs
script.

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

## For the owner's ruling

1. **Canvas colour.** Violet-tinted `#F6F5FF` (proposed) or neutral `#F4F4F5`.
2. **Typefaces.** Schibsted Grotesk, Geist and Geist Mono.
3. **Primary button.** Ultramarine (proposed) or Navy with Ultramarine kept for links and
   selection.
4. **Chart colours.** The muted dark steps above pass 3:1 on their own. The brighter base hues
   look livelier but fall below 3:1 and would lean on labels and the table form.
5. **Motion.** As strict as written (no hover or drawer transitions), or allow short
   state-feedback transitions of 150ms or less.
6. **React Bits in a public repository.** Its licence forbids redistributing the components.
   Proposed: write the pulse, shimmer, progress and entry animations as CSS in this repository
   and take at most the count-up from React Bits, or write that too.
7. **Icons in a public repository.** The icon licence forbids distributing the icons. Proposed:
   use them only through the npm package, never as committed SVG files.
8. **New dependencies.** Five packages for the base layer rather than the one expected, each
   needing a decision record.
9. **Chart implementation.** Hand-built SVG to these rules (no dependency), or Recharts with a
   decision record.
10. **Dark mode.** Not designed. Say if it is wanted.
11. **Logo symbol.** Shown as a placeholder; the symbol file is not in this repository.

## Not verified

- Read live but not built: no component here has been installed in `web/` or opened from disk
  under the content security policy.
- React Bits pages do not state dependencies; whether count-up and animated list need the
  `motion` package was not confirmed from the page.
- Untitled UI's full licence agreement was not read beyond the repository licence files; which
  components sit behind its paid tier is known only where a page said so (card headers).
- Uiverse, Flowbite React, Preline, Ant Design and shadcnblocks were not read for this step;
  nothing here depends on them.
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

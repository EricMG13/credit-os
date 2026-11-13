# Signal mocks

Step D1d of the [design track plan](../../superpowers/plans/2026-11-13-design-track.md), drawn
2026-11-13 against [design system](../design-system.md) 0.6, the
[component map](../component-map.md) and [decision 0003](../../decisions/0003-design-track.md)
(rulings at review 1 and "Source look"). Nothing here is built; the mocks are for review 2.

**Claude Design project:** [Signal mocks (D1d)](https://claude.ai/design/p/8d91fd66-cfc3-4731-b93f-ab372dbb0265)

| Page | Frames | Link |
| :--- | ---: | :--- |
| Feed | 4 | [Signal 1 Feed](https://claude.ai/design/p/8d91fd66-cfc3-4731-b93f-ab372dbb0265?file=Signal+1+Feed.dc.html) |
| Feed states and the name dialog | 11 | [Signal 2 Feed states](https://claude.ai/design/p/8d91fd66-cfc3-4731-b93f-ab372dbb0265?file=Signal+2+Feed+states.dc.html) |
| Groups, thread panel, Share to group | 5 | [Signal 3 Groups and threads](https://claude.ai/design/p/8d91fd66-cfc3-4731-b93f-ab372dbb0265?file=Signal+3+Groups+and+threads.dc.html) |
| Digests | 4 | [Signal 4 Digests](https://claude.ai/design/p/8d91fd66-cfc3-4731-b93f-ab372dbb0265?file=Signal+4+Digests.dc.html) |
| Settings | 9 | [Signal 5 Settings](https://claude.ai/design/p/8d91fd66-cfc3-4731-b93f-ab372dbb0265?file=Signal+5+Settings.dc.html) |

Standalone Claude Design has announced that its tools stop working by 2026-12-14. The project
also holds `signal.css` (tokens and component styles) and `signal.js` (the shell, the settings
navigation and placeholder icons), so the look can be rebuilt from this record and those two
files' content if the project becomes unreadable; neither is committed here.

## How it was drawn

- **Colours, typefaces, status shapes, the card and the static skeleton** are the design
  system's, copied by value from `design-system.md` 0.6. No colour or motion rule was invented.
  Nothing on any Signal screen loops or animates.
- **Source look.** Each component the map names takes its layout, sizes, radius, border width,
  shadow and density from its source: Untitled UI React from its public repository source and
  live pages, HyperUI from its repository markup, shadcnblocks from its registry and the
  component source it installs. Sizes are the sources' class values converted to pixels.
- **Sample content** is invented: fictional companies, publications, a fictional rating agency
  and invented commenter names. The logo is a placeholder symbol and icons are placeholder
  line drawings. No article body appears anywhere.
- **AI text** carries the "AI" label badge in every place it appears (story line, digest card,
  digest page) and uses the announcement pill or the numbered panel, never the message bubble
  that colleagues' comments use.

## Screens and states drawn

| Page, frame | Screen | States and parts it shows |
| :--- | :--- | :--- |
| Feed 1 | For you, writer | Channel list with unread counts and follow stars; freshness line (checked); Top or Latest; kind filter; search; new stories waiting; news with duplicates folded and a "shared by" line; regulatory case with its stage; rating action with the move from and to; digest card, unread; Show older |
| Feed 2 | Latest, reader | Reader: no Comment, no Share to group; nothing older, so no Show older |
| Feed 3 | Saved | Saved stories; a regulatory case at its last stage |
| Feed 4 | A topic | Follow star, keywords as tags, kind filter set, an affirmed rating with an outlook change |
| States 1 | Name dialog | No display name yet; the name chip reads "Set your name" |
| States 2 | Feed | Loading (static skeleton) |
| States 3 | Feed | The service cannot be reached, with Retry |
| States 4 | Feed | Sources not checked yet; no story yet |
| States 5 | Feed | No approved source |
| States 6 | Feed | No topic followed, listing topics to follow |
| States 7 | Feed | Nothing saved |
| States 8 | Feed | No story of the chosen kind |
| States 9 | Feed | No search match |
| States 10 | Feed | A story with no link; a story with no time |
| States 11 | Feed | AI off or at its cap: no AI line, no signal strength, digests paused in the channel list |
| Groups 1 | Group view, writer | Group and members; shared stories with "shared by" and comment count; a note with no story; New thread and Attach story |
| Groups 2 | Group view, reader | No write control |
| Groups 3 | Thread panel | Quoted story; comments; one level of reply; reactions; a comment edited; a comment removed; own comment; composer |
| Groups 4 | Thread panel | A thread archived: no composer |
| Groups 5 | Share to group | Form modal: group, note |
| Digests 1 | Digest page | Numbered points, each with the stories behind it |
| Digests 2 | Digest cards | An unread digest; a read digest; a digest with nothing to report |
| Digests 3 | Digest page | Nothing material to report |
| Digests 4 | Digest page | Digests paused |
| Settings 1 | Groups | Members and visibility; a group with no members |
| Settings 2 | Thread rules | One switch per rule |
| Settings 3 | Sources | Proposed, approved, paused; healthy, quiet, failing with its reason; items per week with an empty slot for a week with no reading |
| Settings 4 | Topics | Keywords and kinds as tags; a topic with no keywords |
| Settings 5 | Digests | The digest form, with "Run once now" |
| Settings 6 | Notifications | Two switches per event |
| Settings 7 | AI and cost | Spend against the cap; a switch per AI part |
| Settings 8 | AI and cost | AI off |
| Settings 9 | AI and cost | AI at its cap |

Every Signal state in the [screen inventory](../screen-inventory.md) has a frame above.

## Parts that need a paid-call ruling

None of these is marked on a screen. Each needs an owner ruling in `docs/decisions/` naming
its cap before it is built to call a model (decision 0003, ruling 9).

| Part | Where it appears | What the call would be |
| :--- | :--- | :--- |
| AI "why it matters" line | Story cards (Feed 1, 2) | One call per story, or per story in a followed topic |
| Signal strength | Story cards (Feed 1, 2) | One call per story, unless a rule without a model can produce it |
| Digests | Digest card and page (Feed 1, Digests 1 to 4); the channel list | One call per digest on its schedule; none when there is nothing to report |
| "Run once now" | Settings 5 | An extra digest call started by a person |
| The cap itself | Settings 7 to 9 | The amount, its period, who may change it, and what stops at the cap. USD 15.00 a month on the screens is a sample value, not a proposal |

## Where the mocks depart from the map or the design system

| # | The map or design system says | The mock does | Why |
| :--- | :--- | :--- | :--- |
| 1 | A source component is not wrapped in a card of ours (R18) | The list of stories sits on one design-system card; each story is the HyperUI media object, with hairlines between | On the violet canvas the static skeleton (`surface-subtle`) and the monogram tile are close to invisible. The card holds the list, not each story |
| 2 | An icon never stands without a label | The area rail is icon only, as the source's slim rail is; the label is a tooltip and the accessible name | Source look |
| 3 | Sentence case; source group headings are uppercase | Channel-list headings (Topics, Groups, Digests) keep the source's size and weight in sentence case | Type rules are the design system's |
| 4 | Top or Latest: "the selected item is a white pill on `surface-subtle`" | The source's joined button group, selected item filled `surface-subtle` | The two descriptions differ; the source's layout was kept |
| 5 | N5 filter bar: search, dropdown filters, applied count | The source's "tabs and search" variant: kinds as tabs, search on the right | Five kinds fit as tabs and stay visible; a dropdown would hide them |
| 6 | F6 badge group | Badge, arrow, badge, then the word (Downgrade, Affirmed, Outlook), all neutral | The source's order is badge, text, arrow. Direction is carried by the word; no red or green is used |
| 7 | R21 HyperUI progress bar with labels | The source's label row and track, plus a row of the four stage names under it; "Stage 3 of 4" in place of a percentage | The source has no per-stage labels |
| 8 | P2 shadcnblocks List Panel, Numbered | Its Stacked variant with a number in the item's media slot | The Numbered variant is behind the source's paid tier and could not be read; the marker is drawn here |
| 9 | P7 announcement | One line at the source's 12px | Source look; a longer line would wrap inside a pill |
| 10 | I7 reactions | Words with a count (Agree 2, Seen 3) | The source uses emoji; the set of reactions is not defined anywhere |
| 11 | N7 "the reader keeps their place" | The source's slide-out with its 70 percent overlay, in Navy | Source look; the overlay hides most of the feed |
| 12 | S4 alert | Source layout; the icon is the status shape on its tinted square, the border the status edge colour | The design system gives each alert its status shape |
| 13 | Source borders are light grey | Inputs and the secondary button use `border-control`; other edges `border-hairline` | Only those two border roles exist |
| 14 | "Comment edited, removed, thread archived: inline text marks" | Edited and removed are text; archived is a neutral status badge with the square | Archived is a state of the thread; the square is "settled" |
| 15 | Sources: kind, state, health, items per week (R13) | Kind sits under the source name; last check and last item share a column; no sort arrows drawn | Seven columns at the source's cell padding did not fit beside the settings navigation |
| 16 | A missing value leaves its slot empty | In items per week, a week with no reading is an empty slot; a week with zero items is a 2px stub | Zero is a figure and missing is not |
| 17 | S8 pill | White with a hairline edge | The source's default fill is close to invisible on the canvas |
| 18 | I10 form modal | The source's 640px form modal for a one-field dialog | Source look |

Not drawn: hover, pressed and focus states (one focused input is shown), an open select menu,
narrow widths, and what a reader sees in Settings.

## Questions for the owner

1. **Card around the feed (departure 1).** Keep the stories on one white card, or put them
   straight on the canvas and change the skeleton colour?
2. **Thread panel overlay (departure 11).** Keep the source's dark overlay, or lighten or
   remove it so the feed stays readable beside the thread?
3. **What a reader may do.** The mocks let a reader save stories and follow topics (both are
   personal) and hide Comment, Share to group, New thread and Attach story. May a reader react?
   Which Settings sections does a reader see?
4. **Reactions.** Which fixed set, and words or symbols?
5. **Numbered panel (departure 8).** Accept the marker drawn here, or look at the paid source
   variant first?
6. **AI line.** Is one 12px line enough, or should it be larger and allowed to wrap?
7. **Signal strength.** Three stars and a word (Strong, Moderate, Light) follow the source. Are
   stars the right mark for a credit reader, and are these the words?
8. **Paid calls.** The five rulings in the table above, including whether signal strength may
   use a model at all.
9. **Kind filter (departure 5).** Tabs, or the dropdown with an applied count?
10. **Source monogram.** The source's media image is 80px square. Keep that size for a
    two-letter monogram, or make it smaller?
11. **Thread rules and notifications.** The four rules and the two channels (in Signal, on the
    desktop) are examples. What are the real ones?
12. **Sources table (departure 15).** Is folding kind and last item into other columns
    acceptable, or should the table get the full page width?
13. **Source look and borders (departure 13).** Darker input and button edges than the source,
    for contrast. Confirm.

## Not verified

- Each of the 33 frames was rendered in headless Chrome at 1440px wide and looked at, most at
  two-thirds scale; all five pages load with no console message. Not checked: narrow widths,
  Edge, the Claude Design editor, keyboard order, and contrast by measurement (the colours are
  the design system's, but no pairing on these screens was re-measured).
- The repository gates were not run for this change; it adds one Markdown file.
- Source sizes come from the sources' class values converted to pixels, not from measuring a
  rendered source page, and nothing was compared pixel by pixel. Untitled UI's filter bar,
  messaging, alert, modal and slide-out examples were read from its live pages, not its
  repository. The shadcnblocks announcement and pill were read from the component source it
  installs, because most of their example blocks are behind its paid tier.
- Fonts load from Google Fonts in the mock. Icons and the logo are placeholders.
- The shell and settings navigation are drawn by `signal.js`, so they cannot be clicked and
  edited in the Claude Design editor; the content of each screen can.
- No Signal back end exists. Counts, times, spend and source health on the screens are sample
  values, and whether the service can supply each one is unknown.

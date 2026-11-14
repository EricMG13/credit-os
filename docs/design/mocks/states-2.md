# States 2 mocks

Drawn 2026-11-14 for [States 2](../states-2.md) and the draft [decision
0013](../../decisions/0013-states-2.md), against the [design system](../design-system.md) and
[component map](../component-map.md). **Draft for the owner's review; nothing is ruled or built.**
All issuers, modules, dates, amounts and scores are sample data. The frames draw the recommended
options (C-A, R-A, M-A with N-A).

| File | Frames | Link |
| :--- | :--- | :--- |
| States 2 Library | L1 to L7 | <https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=States+2+Library.dc.html> |
| States 2 Module | L8 to L14 | <https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=States+2+Module.dc.html> |
| States 2 Evidence | E1 to E4 | <https://claude.ai/design/p/9c6141ea-840e-45bd-8b0e-84b5f181cf34?file=States+2+Evidence.dc.html> |
| Run activity states 2 | R1 to R8b | <https://claude.ai/design/p/3fb77bd2-6b91-490c-98d1-55d7a7dfe794?file=Run+activity+states+2.dc.html> |
| Model states 2 | M1 | <https://claude.ai/design/p/d971501e-80a2-4b17-ab8f-7011bb867f0e?file=Model+states+2.dc.html> |

The first three are in the library mock project (Issuer library mocks (D1a)) and share a new
stylesheet `states2.css` (confidence scale, reason line, not-scored text, two-badge cell); the
others are in the run and model mock projects.

## Frames

| Id | Name | Page | Shows | State(s) |
| :--- | :--- | :--- | :--- | :--- |
| L1, L2 | Home card, stopped at its cap; Home card, latest run failed, spend not known | Library home, Cards | Stopped, Spending cap, reason in the note; Failed with two labels; the card keeps the last finished run | Stopped: spending cap; Failed: spend not known |
| L3 | Home list, State column | Library home, List | Six rows, Sector and As of columns; State filter | Finished, Stopped (Spending cap; By the analyst), Failed (Model service; with Spend not known), Running; two badges in one cell |
| L4 | Report history, every end once | Report history | Nine entries, badges and fixed sentences | Every end, Rejected, Interrupted |
| L5 | Run frame head, a stopped run | Any run page | Two badges; a new reason line under the header | Stopped: spending cap |
| L6 | Overview modules list, run S1 | Overview | Thirteen modules: scale and band word, "Not scored", or nothing; two columns and one | Bands; Reduced inputs; Not assessable |
| L7 | Overview modules list, no module scored | Overview | One sentence under the heading, no row element | No module scored |
| L8 | Module head, scored | Module | Caption and tooltip, scale, band word, "77 of 100", link | Medium |
| L9, L10 | Module head, ceiling of 59; Module head, ceiling of 39 on a delivered module | Module | Ceiling sentence under the scale; Ceiling sentence; "Blocked" appears nowhere | `Restricted` as a sentence; `Blocked` as a sentence |
| L11 | Module head, not scored | Module | "Not scored" and its reason; link kept | Not scored: nothing asked |
| L12 | Module head, reduced inputs with a long reason | Module | Label badge; reason naming three producers; link to Limitations | Reduced inputs |
| L13, L14 | Module page, not assessable for a missing producer; Module page, not assessable although scored | Module | The merged blocked form, new words; No confidence row; the score is on Evidence only | Not assessable: producer missing; Blocked and scored |
| E1 | Record tab, the Confidence register | Evidence, Record | Thirteen rows, two open (inputs; a refused attempt's refusals) | Every outcome and status |
| E2, E3 | Record tab, how the run ended, spend not known; Record tab, a call's cost stated by the owner | Evidence, Record | "How the run ended"; Spend "n.a." with no bar; six calls; Same run after settling: label, total, bar again | Stopped: spend not known; Stated by the owner |
| E4 | Record tab, module timings with reduced inputs | Evidence, Record | Inputs column before State | Reduced inputs |
| R1 | Stopped at the spending cap | Run activity | Alert; Spend bar not full; steps | Stopped: spending cap |
| R2 | Stopped, spend not known | Run activity | Spend "n.a." and a note, no bar | Stopped: spend not known |
| R3, R4 | Stopped by cost control; Stopped by the analyst | Run activity | Alert and figures; Alert with resume link | Stopped: cost control; Stopped: by the analyst |
| R5 | Failed, spend known | Run activity | Alert and figures | Failed: model service |
| R6 | Failed, spend not known | Run activity | The three differences from R5 | Failed: spend not known |
| R7, R7b | A run with no end record; Activity cannot be read | Run activity | Interrupted; alert with last activity; The merged frame redrawn beside R7 | No end record; Record unreadable |
| R8, R8b | Module steps in a live run; The same run once it has ended | Run activity | Five steps, two Not assessable, one Queued; Header Finished; "Ran without ..." detail | Not assessable: producer missing, three attempts; Reduced inputs |
| M1 | Model run header, a stopped run | Model, Front page | Stopped with Spending cap | Stopped: spending cap |

## States and where each is drawn

| State | Frames |
| :--- | :--- |
| Confidence: High, Medium, Low, Insufficient Information | L6, L8, L9, L10, L12, E1 |
| Score status `Restricted`, `Blocked` (as a ceiling sentence) | L9, L10, E1 |
| Not scored: nothing asked | L6, L11, E1 |
| Outcome `blocked`; outcome `refused`; blocked and scored | E1, L14 |
| No module scored | L7 |
| Stopped: spending cap | L1, L3, L4, L5, R1, M1 |
| Stopped: spend not known | L4, E2, R2 |
| Stopped: cost control; by the analyst | L3, L4, R3, R4 |
| Failed: model service | L3, L4, R5 |
| Failed: spend not known | L2, L3, L4, R6 |
| Rejected | L4 |
| No end record (Interrupted); record unreadable | L4, R7, R7b |
| A call's cost stated by the owner | E3 |
| Reduced inputs (ran restricted) | L6, L12, E4, R8, R8b |
| Not assessable: a producer missing | L6, L13, R8 |
| Not assessable: not accepted after three attempts | L6, R8, E1 |

## Departures from the frame spec

- L1 and L2 sit beside the merged Finished card for comparison. L3 is the List layout's table, with
  Sector and As of columns. E1 adds a Code column (module codes appear on Evidence only). E2 and E3
  sample calls: five known calls of USD 1.10, 1.45, 0.95, 2.05 and 1.30 (USD 6.85); the unreported
  call reads n.a., then USD 1.20 "Stated by the owner", total USD 8.05. E4 shows six rows; Rating
  outlook's Inputs cell reads n.a.
- R1 to R7 use the merged run mock's thirteen module names, so R7 reads "while Covenants was
  running"; in R2, R3 and R4 the module running at the stop reads Interrupted with a reason line
  (the spec named none). R5 and R6 are consecutive frames, not side by side. R8 shows five modules;
  R8b is a separate frame with the header Finished.
- M1 is in the model mock project, whose stylesheet has no warning badge: the file defines it from
  the design system's Warning row (`#664F00` on `#FFF9E5`, mark `#997700`). The scale's marks are a
  CSS star outline standing in for the `Star01` icon of the built Signal part.

## Not verified

No reader has seen the frames. They were checked at 1440 px wide in a browser for layout and console
errors only; L6's one-column frame is 620 px, not a phone. The CSS star is not the shipped icon.
Sample amounts and scores are invented, the scores worked from the 2B plan's Score row, not by
`credit_os`.

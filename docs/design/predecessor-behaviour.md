# Predecessor behaviour the pages must match

Read on 2026-11-14 from the predecessor's `main` at `cbf4400` (20 merges after the `8e3954a`
baseline the mocks were drawn from). These rules reached the predecessor after the mocks; the
page steps D2b, D2c and D2e build them in. Wording in quotes is the predecessor's exact text.
Where a rule depends on data, delivery supplies it; the page computes nothing.

## Library list (step D2b)

A leverage, net leverage or interest cover figure stated on adjusted EBITDA is shown but not
screened. Cash and undrawn facilities are not affected.

| Where | Rule |
| :--- | :--- |
| The figure | Followed by a small "adj." mark; the cell's description is the adjusted label and the period, or "Period not recorded" |
| Filters | An adjusted figure passes no range filter: it counts as not recorded |
| Sort | An adjusted figure sorts as missing |
| Count line | "Leverage recorded for N of M runs · A on adjusted EBITDA, not screened" (the same for Net leverage and Interest coverage); unchanged when no figure is adjusted |
| Hidden rows heading | "Hidden by <Name>: no figure recorded, or a figure on adjusted EBITDA" when adjusted figures are present |

Money carries its unit: "US$m", or the currency code and "m" (for example "GBPm"). Nothing
is converted.

Not decided in the predecessor, so not built: how a reported run compares with an adjusted
run; a period with only adjusted EBITDA in the leverage chart; whether three modules' money
tables follow the issuer's currency.

## Forecast and Model (step D2c)

| Where | Rule |
| :--- | :--- |
| Published model link | "Download published model (Markdown)" when the model file is not HTML; otherwise "Download original HTML" with the collapsible frame "Published model (original HTML)" |
| Pro forma column, when empty | Reason: "pro forma figures are not placed in this column; the financial foundation shows any it states" |
| Stress case name | "Downside stress (shock on downside drivers)" when delivery says the shock was applied to the model's own downside drivers; otherwise "Downside stress (shock on base drivers)" |
| Stress case note | "Downside case is the stress case: a shock applied to the model's own downside drivers." or "…applied to the base-case drivers." to match |
| Own-drivers case | "Downside (CP-2G drivers)" and its note are unchanged; the group label stays "Downside case" |
| Negative closing cash | Net debt, net leverage and liquidity for that year are missing with the reason "Not calculable: cash is negative before funding"; closing cash itself is shown. The cells draw "n.a." with that reason, never 0 |

A downside year can therefore show three "n.a." cells beside a negative cash figure. Module
code names such as "CP-2G" are the predecessor's; decision 0003 keeps module codes off
findings pages, so the case names are delivered text and the page does not add a code.

## Signal (step D2e)

The predecessor now serves one built page (the feed, with the name dialog). Threads, share to
group, digests and settings are still designed only. Built wording the mocks should match:

- Navigation: heading "Signal"; each topic row has its name, a story count and a follow
  star; "No topics yet" when there are none; a skip link "Skip to the feed".
- Name: chip "Set your name"; dialog "Your name", "Signal shows your name next to what you
  save and follow. It is a display name, not a login.", field "Display name", error "Enter a
  name to continue.", buttons "Continue" and "Cancel".
- Freshness line: "Checking sources", then "Sources checked <time>" or "Sources not checked
  yet", with "· N sources failing" where it applies; "Source status unavailable" as a warning.
- Kind filter: "All", "Regulators", "News", "Ratings", "Research".
- Search: placeholder "Search stories".
- New stories: "N new story" or "N new stories". Older stories: "Show older".
- Errors, with "Retry": "Signal could not be reached. Check your connection and try again.",
  "Signal could not complete that request.", "The service sent an unreadable answer."
- Times: "just now", "N min ago", "N h ago", "N d ago", then a date.
- Empty states: "No story matches <query>" / "Check the spelling or clear the search.";
  "No stories of this kind here" / "Choose All to see every kind."; "Follow a topic to fill
  this view" / "Stories on the topics you follow appear here."; "Stories you save appear
  here" / "Use Save on a story to keep it."; "No approved sources yet" / "Stories appear once
  a source is approved."; "No stories yet" / "New stories appear here as sources are
  checked."; "No stories in this topic yet".

## Not verified

- Read from diffs and source, not from a rendered page. The "n.a." drawing for negative cash
  rests on the predecessor's own verification note, which says it was not seen in a browser.
- The predecessor's per-merge change packs were not read.
- The predecessor keeps moving; this page is a snapshot at `cbf4400`.

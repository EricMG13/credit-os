# 0013 States 2: how confidence, a run's end and a module's run are shown

Date: 2026-11-14. Status: **draft for the owner's review; nothing here is decided**. Drafted by the
design track's states 2 task. To be decided by: owner.

## Why

Three kinds of back-end state have no drawing on any merged page: a module's confidence outcome, why
a run ended, and a module that ran restricted or did not run because a module it needs was not
delivered. [States 2](../design/states-2.md) holds the inventory (read 2026-11-14), the proposal
with options, a build outline and what delivery would have to send; this record lists what the owner
is asked to rule and does not copy that detail. Option names (C-A, R-A, M-A, N-A and the rest) are
the proposal's. The [mocks](../design/mocks/states-2.md) draw the recommended options; no reader has
seen them.

The words are not settled in the back end either. The confidence words are in code on `main` (merged
in #312; read at `23c00a4d`, unchanged on `main`). The run status words are on the open pull request
#303 only. The run end reasons and the module rules are step 3A plan text with no code. A ruling
here is on how the states are shown, not on the states.

## Questions for the owner

Each row gives the options, the recommendation, and what changes if the other is ruled. Detail is in
States 2: Topic 1 (questions 1 to 7), Topic 2 (8 to 13), Topic 3 (14 and 15).

| # | Question | Options | Recommended | If the other is ruled |
| ---: | :--- | :--- | :--- | :--- |
| 1 | Where is confidence shown? | C-A: a short scale with band word and number at the module's head and its Overview row, delivered modules only, audit trail on Evidence. C-B: one sentence at the module's head, nothing on the Overview. C-C: a scale on every module row, a tally on every run | C-A | C-B: no kit piece or Overview change, modules cannot be compared at a glance. C-C: three slices change, and question 7 must first allow a tally |
| 2 | What is the scale's mark, and may one scale serve Signal and confidence? | The source's star (F7, read live 2026-11-14: every block draws stars; the page says Radix UI or Base UI, not the React Aria the component map records); the built three-mark Signal part becomes a kit part taking four marks, no new dependency. Or a mark written in the design system (for example filled segments), at the cost of a second component. Second part: Signal strength and module confidence are both a strength on a short ordinal scale, but the owner's rule forbids one component for different kinds of information | The star, ruled on the mock. One kit scale serves both: they are one kind of information, a judgement's strength on a short ordered scale read as marks plus a word; the rule forbids one component for different kinds, not the same kind; the uses differ only in mark count and word set, both supplied by data | A different mark for confidence: the kit gains a second scale component and the confidence mocks change their mark |
| 3 | Are the score's own status words (`Passed`, `Restricted`, `Blocked`) shown? | Not on findings pages: `Restricted` and `Blocked` show "Cannot be above 59: a material finding was recorded." (39 and "critical" for `Blocked`), `Passed` shows nothing, the words stay in the Evidence register. Or shown as words beside the score | Not on findings pages: "Blocked" would sit on a delivered module and beside "Not assessable" modules; "Restricted" clashes with a module that ran restricted and to a portfolio manager means an issuer they may not trade | Two words need reader-facing replacements that do not clash; the design has none |
| 4 | What is a "finding" in the ceiling sentence? The inputs table counts CRITICAL, MATERIAL and MINOR findings; the only description read is the predecessor's "the findings by severity"; on a findings page the word sits near "Key findings", about the issuer | Keep "finding", as the back end writes it; or another word the owner gives, with "finding" beside it on Evidence | The owner says what these findings are; until then the mock uses "finding" | One fixed sentence in delivery changes |
| 5 | A module that reads "Not assessable" and still has a score (a blocked module that wrote the fourteen inputs is scored; the key has one at 89, High) | Evidence only: findings pages show no confidence for a module with no delivered judgement; the register lists it with "Scored although the module reads Not assessable: it wrote the fourteen inputs." Or on the module's page too, with a qualifier | Evidence only | Someone must say what such a score means; no source does |
| 6 | Can a module be delivered whose outcome is `refused`, `absent` while a score was asked, or whose document is in the earlier format? Code and plans say no for a run the orchestrator made (each makes a refusal, a refused handoff is not accepted, only accepted handoffs are admitted); open: a retained earlier-format run, and an accepted reply checked later by a changed checker | Never: delivery refuses to write such a module and says why. Or allowed: the head reads "Not scored" with the fixed sentence for that case | Never, for `refused`. For a retained earlier-format run, if one is ever delivered: "Not scored: this report was written before confidence scoring." | The findings pages gain two no-score sentences otherwise seen only on Evidence |
| 7 | Is there a run-level confidence? The sources rule none | None; or a tally by band that delivery counts ("2 high, 2 medium, 3 low, 2 not scored") | None | A tally needs a ruling that it is a count, not analysis; the home card, history and run head each gain a line |
| 8 | How is a run's end shown? | R-A: one state per store status; "Stopped" (the triangle and warning tone of "Capped", folded into it) carries its reason as a label and a sentence, "Failed" likewise. R-B: "Capped" stays; "Stopped" takes the pause bars of "Interrupted", which leaves the run set. R-C: a state for every reason, needing three shapes the design system lacks | R-A | R-B: one store status has two shapes and the module word "Interrupted" needs a new home. R-C: the first step is a ruling to add shapes to the design system's ten |
| 9 | The reader's words for the end reasons ("the cap", "unknown spend", "a charge above its hold", "a stop asked for by the operator", "a provider failure that is not retried", "an exception out of `complete`") | Labels in that order: "Spending cap", "Spend not known", "Cost control", "By the analyst", "Model service", and "Model service" with "Spend not known"; sentences in States 2 ("operator" is written "the analyst"). Or the owner's words | As proposed | Delivery's fixed text only |
| 10 | `completed` or `finished`? The 3A plan's G3 writes `completed`; the 2A plan and #303 have `finished`. For the back-end coordinator | The page reads "Finished" either way | Back-end coordinator rules | One word in what delivery reads |
| 11 | A run that ended without an end record (the store became unusable, which "writes nothing", or the process died): the store still holds `running` and has no heartbeat; no source produces "Interrupted" for a run | "Interrupted" with "The run ended without recording why. Its last recorded activity was at 14:56.", once whatever writes the page's data can establish that no process holds the run; or "State not known" (the kit's dashed ring) until someone resumes or closes the run; or left reading "Running" | The first, never the third; it needs a back-end rule for "no process holds the run", which the design cannot supply | The second: "Interrupted" is no longer a run state |
| 12 | When spend is not known, may any figure be shown? | No: "n.a." with the reason, no cap bar, Evidence lists each call's own cost with the open call and total "n.a.". Or yes: "At least USD x recorded" | No | The budget (3A PR 2a) must define that figure; the plan has no part-total |
| 13 | Is a run refused at launch a "Rejected" run? Decision 0006 ruling 7 defines "Rejected" as a document changed after approval; the 3A plan refuses a run over 200 files or 400 MiB (D16) without saying whether that is the store's `rejected` or never a run. For the back-end coordinator | If a `rejected` run: its fixed sentence joins the reason list and "Rejected" keeps its cross. Or a message on the run start page | The first, if it is a `rejected` run | One more sentence, or a start-page message instead |
| 14 | A module that ran restricted (only an optional producer missing) | M-A: state stays "Delivered" or "Delivered with gaps", a neutral label "Reduced inputs" and a sentence naming what it ran without. M-B: a fifth module state, no shape free. M-C: one sentence in Limitations, no mark. Word: "Reduced inputs", "Limited inputs" or another; "Restricted" stays the back end's word, beside it on Evidence | M-A with "Reduced inputs" | M-B: a new shape is needed first. M-C: the Overview list shows nothing |
| 15 | A module not run because a module it needs was not delivered | N-A: "Not assessable", "it needs Capital structure, which was not delivered in this run." N-B: "Not run", same reason | N-A: the 3A plan calls it a blocked dependant, the design system draws a blocked module as "Not assessable" with a sentence, and under G1 the run goes on, so a live "Not run" would sit with "Queued", which shares its ring | N-B: the rule that "Not run" exists only in an ended run changes, or the live case needs a third word |

## What a ruling would change

States 2, "Build outline", lists the files the recommended options touch and what delivery (step 3B,
not yet planned) would have to send. The design system's own tables are untouched; the rows a ruling
would add are in its section "Proposed (states 2, not ruled)".

## Not verified

- No reader has seen the mocks; they were checked for layout and console errors only.
- The confidence words were read at `23c00a4d` and are unchanged on `main`. Rulings C1 to C10 are
  only in a side note, not a decision record. The run status words were read at the head of #303
  (`2fdd4ebf`), still open, and may change.
- Every run end and module word is plan text; no code or test exercises one.
- F7's page was read live on 2026-11-14 and records Radix UI or Base UI where the component map says
  React Aria; which is right is not settled.
- No analyst or portfolio manager has seen the proposed words. Whether step 3B can supply each
  field: it has no plan.

# 0016 The gpt-6-sol price row: published default-tier rates, a 272,000 context ceiling, a 32,000 output floor

Date: 2026-11-15. Decided by: back-end coordinator (D8 fetch, rulings 1-4) and 3A controller
(rulings 1-3 of the 2b rulings), deadline mode. The owner can reverse any of it.

## Why

The hold of a call (3A plan, D8) prices the whole context at the dearest input-side rate (plus the cache-write rate) and the
output at the dearest output rate. It needs the model's published prices. Fetched 2026-11-15, all
HTTP 200, no page shows a last-updated date.

## Published prices

Source: https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing
("All prices are per 1 million tokens"; "1 AI credit = $0.01 USD"). Listed as "GPT-6 Sol"
(OpenAI, GA) on https://docs.github.com/en/copilot/reference/ai-models/supported-models.

| Tier | Input | Cached input | Cache write | Output |
| :--- | ---: | ---: | ---: | ---: |
| Default, <= 272K input tokens | 2.00 | 0.20 | 2.50 | 10.00 |
| Long context, > 272K input tokens | 4.00 | 0.40 | 5.00 | 15.00 |

USD per 1M tokens. The page notes GPT-6 Sol charges a cache write cost in addition to cached
input. No premium-request multiplier is listed for GPT-6 Sol.

## Decision

1. **The row** is one constant, `COPILOT_SOL_MEDIUM`, config `copilot-sol-medium`: input-side
   rates `2.00` and `0.20`, a separate cache-write rate `2.50`, output rate `10.00`, written as
   `Decimal` from the text above. The cache-write rate is its own field, because 4.50 is not a
   published price and the row holds published prices only.
2. **Context ceiling 272,000 tokens, a project choice,** not a model limit. It is the published
   default-tier boundary, so every call stays in the default price tier and below the unpublished
   default context. Raising it is an owner decision.
3. **Cache write is priced additive in the hold.** Two readings fit the page's words ("a cache
   write cost in addition to cached input"). Replace: a written token is charged the cache-write
   rate in place of the base input rate (2.50). Additive: it is charged the base input rate plus
   the cache write, 2.00 + 2.50 = 4.50 per 1M. The hold takes the dearer, additive reading: a
   hold may overstate, never understate, and settlement uses what the provider reports. The
   difference is 2.00 x 272,000 / 1,000,000 = USD 0.544 per call. The owner can relax it to the
   replace reading if GitHub confirms that cache write replaces the base rate.
4. **The long-context tier is left out.** With the ceiling at 272,000 no call is priced in it.
   Raising the ceiling above 272,000 needs the long-context rates (4.00, 0.40, 5.00, 15.00) added
   to the row first.
5. **Output floor 32,000 tokens, a project choice,** not a provider fact: no maximum output is
   published. It equals the configured output limit of `copilot-sol-medium` (D25), so a hold
   never prices less output than the run's configured limit, even when a call passes a lower cap.
   The hold at the floor is (272,000 x 4.50 + 32,000 x 10.00) / 1,000,000 = USD 1.544.

## Cost if wrong

One constant and its key rows change; no stored row is affected.

## Not verified

- The default context size: not stated on any page read.
- The maximum output tokens: not stated on any docs.github.com page read.
- Whether the Copilot CLI 1.0.108 route uses the default or the extended (1 million token)
  context.
- The agent read parts of the supported-models page only as a tool summary.

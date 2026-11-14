# Step 1C: one model interface, a canned adapter and a Copilot adapter

Date: 2026-11-14. Coordinator: the Rebuild 2 session. This file is the plan and the
sub-session's brief. Legacy read at `legacy/main` `cbf4400`
(`git show legacy/main:<path>`; never check it out, never change it).

**Goal:** `src/credit_os/provider/` offers one interface for asking a model for a reply, with
two adapters: canned answers for tests, and GitHub Copilot through `github-copilot-sdk`
1.0.8 with model `gpt-6-sol` under the configuration name `copilot-sol-medium`.

**Ends in:** a sequence of pull requests against `main`, each within 800 changed lines, each
passing both review steps, opened one at a time.

**This is sensitive code** (money: the billed cost of a call; security: credentials and
redaction). Each task touching cost, credentials or redaction also gets an `mx-adversary`
review, and changed files get mutation testing (`mutmut`, run with `uvx` and not added to `pyproject.toml`), survivors killed or justified in
the PR.

## Files this step may touch

`src/credit_os/provider/**`, `tests/provider/**`. Nothing else: the SDK is already in the lock
(step 0C part 1). Not `VERIFICATION.md`, not `docs/legacy/ports.md`.

## Hard rules

- No paid or live model call, by any agent, in this step. Builds and tests run no provider.
  The one live check is a test marked `live`, which the gates exclude and nobody here runs.
- Tests do not import `copilot`. The SDK is imported in exactly one function, lazily; every
  test drives the adapter through a plain fake client.
- No credential file. The token comes only from `COPILOT_GITHUB_TOKEN` and the runtime path
  only from `COPILOT_CLI_PATH`, both read from the launching environment. The legacy option
  that takes a token from `gh auth token` is not ported.
- The SDK must never download a runtime: the adapter always passes an explicit runtime path
  and refuses to start without one.
- The legacy model id `gpt-6.1-sol` appears nowhere, fixtures included (decision 0002, item 5).

## Pre-flight (coordinator)

- Legacy files and where they go:
  - Interface: `model/turn.py` (395 lines, trimmed: no provider blocks, no hosted web
    search), `model/adapter.py` (`AdapterReply`, `ModelAdapter`, `RecordedAdapter`; not
    `LiveAdapter`, not the rulings gate), `model/redact.py` (240), `model/reply_classes.py`
    (34), and about 150 lines of helpers from `model/providers.py`.
  - Copilot adapter: `model/copilot.py` (293, pure event parser), `model/copilot_adapter.py`
    (1,029).
  - Not this step (they go to 3A): `model/handoff.py`, `model/loop.py`, `model/record.py`,
    budget and pricing. Left behind: `deploy_vii/live/*`, `deploy_vii/execution.py`, the
    other entries of `model_testing/configs.py`.
- **SDK 1.0.8 against the legacy's 1.0.28 calls.** Context7 has documents for 1.0.28 only, so
  the authority is the installed package source,
  `.venv/lib/python3.12/site-packages/copilot/` after `uv sync --locked`. Read by the
  coordinator on 2026-11-14:
  - Present in 1.0.8: `CopilotClient(connection=, github_token=, use_logged_in_user=,
    base_directory=, log_level=, env=, mode=)` with `mode` one of `"copilot-cli"`, `"empty"`;
    `RuntimeConnection.for_stdio`; `start`, `stop`, `force_stop`, `list_models`;
    `create_session(model=, reasoning_effort=, system_message=, tools=, available_tools=,
    on_permission_request=, streaming=, session_id=, infinite_sessions=)`;
    `CopilotSession.send`, `on`, `abort`, `disconnect`; `Tool` with `skip_permission`,
    `ToolResult.text_result_for_llm`, `ToolInvocation`; `PermissionDecisionReject` in
    `copilot.generated.rpc`; event types `assistant.usage`, `session.idle`, `session.error`,
    `tool.execution_start`, the compaction events; usage fields `totalNanoAiu`, `isByok`,
    `isAuto`; `supportedReasoningEfforts` on a model.
  - **Absent in 1.0.8:** `numToolCalls` on the usage event. The legacy uses it to decide that
    a call ending in tool calls is complete.
  - `copilot/_cli_version.py` names runtime 1.0.73 and `_cli_download.py` can fetch one. The
    target runtime is Copilot CLI 1.0.108.
  - Only names were checked, by search. Argument types, defaults and event payload shapes are
    for the tasks to read in the source and cite by file and line in their reports.

## Prior art (searched 2026-11-14)

- Owner's repositories: the legacy adapter above. Decision: adapt.
- Public GitHub: not searched; the SDK's own source is the reference for its calls.

## Rulings

- **Interface:** `Model` protocol with `config_id`, `complete(request, *, exchange_id,
  call_index) -> Reply`, `close()`. `Request(messages, tools, max_output_tokens, effort)`;
  `Reply(kind, turn, error_class, message, usage, billed_usd, raw, started_at, finished_at)`
  with `kind` one of `ok`, `not_sent`, `sent_usage`, `sent_unknown`; `Turn(text, tool_calls,
  usage, stop_reason, reported_model, request_id)`. Frozen types. No HTTP status, no retry
  hint, no reservation id (budget is step 3A).
- **Missing is not zero:** usage a call did not report is `None`, never 0. `billed_usd` is a
  `Decimal`, `totalNanoAiu` times 1E-11 exactly, and `None` when the event carries no figure.
- **End of a call without `numToolCalls`:** a call is complete on `session.idle`, on
  `session.error`, or, for a call that announces tool calls, when a usage event has arrived
  and every `tool.execution_start` seen has its handler invoked and no further event arrives
  before `session.idle`. If the installed source shows a better signal, the controller sends
  it to the coordinator before building on it.
- **Refusals at a normal reply**, kept from the legacy: reported model differs from the
  configured one, routed through a user-supplied key (`isByok`), auto-routed (`isAuto`).
- **Canned adapter:** replays replies from a JSON Lines recording in order, and fails loudly on
  a request it has no reply for. Recordings are synthetic.
- **Redaction:** values of `COPILOT_GITHUB_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN` and anything
  shaped like a GitHub token or an `sk-` key are removed from every error, log line and raw
  body; home and runtime paths are removed from errors; a body that reflects a key is replaced
  whole.
- **Timeouts:** idle and overall 1,800 seconds, release steps as the legacy sets them; all are
  constructor arguments so tests use short ones.
- The runtime sees only an allow-listed environment.

**Amendments (coordinator, 2026-11-14), each a test where it names behaviour:**

- **PR 1 is split.** #36 carries the types, the protocol and redaction; the canned adapter is
  PR 1b (line cap). Redaction ports `text`, `bytes_`, `from_environ` and `home_paths` only.
  `Usage` has the five counts SDK 1.0.8 reports. A `sent_usage` reply knows a count or a charge.
- **GitHub token shapes** are redacted with no left boundary and run to the end of their word,
  `_` and `-` included; `sk-` shapes keep the word rule. The rest of a token's word goes with it.
- **Compactions.** `Compaction(usage: Usage, billed_usd: Decimal | None)`;
  `Reply.compactions: tuple[Compaction, ...] = ()`. A compaction's charge is never folded into
  `Reply.billed_usd`, and nothing in this layer sums charges: step 3A's budget treats a total
  with any `None` in it as unknown. A recording writes `compactions` in every reply. A
  `not_sent` reply with a compaction is refused.
- **`totalNanoAiu` as a float** is converted only when finite and integer-valued (through
  `int`, then `Decimal` times 1E-11). Non-integer, negative, non-finite or above 2**53 is an
  unreadable charge: `billed_usd=None`, the raw body kept.
- **End of a call (SDK 1.0.8 source read, `generated/session_events.py`, `session.py`):** the
  ruling above stands. `finishReason` (optional, on the usage event only) and
  `assistant.turn_end` (a turn id and model, no usage) are kept in `raw` and are never the stop
  condition. A `session.idle` with `aborted` true is never an `ok` reply. One turn can hold
  several model calls (`assistant.turn_retry`), so usage is taken from every usage event of
  the call.
- **A recorded charge** is read only from a string of plain digits with an optional fraction
  (no sign, underscore, space, exponent, non-ASCII digit, or leading zero before another digit); anything else
  refuses the recording line with its number. `-0` is not a charge.

In `main` since PR 2 (#63):
- **Tool arguments** have one representation in both adapters, the one the SDK gives: a
  fraction is a finite `float`. Money never comes from a tool argument; a charge is read only
  from a decimal string.
- **Compactions, carrier and identity.** A compaction is attached to the reply of the call
  during which it is observed, or to the next call's reply; `Model.close()` returns those
  observed and not yet delivered. `Compaction` gains `event_id` (the envelope id of the SDK
  event, as text; a repeat is ignored) and `outcome`: `done`, `failed`, or `unfinished` for a
  compaction that started and had not reported when the call ended. An unknown charge is
  `None` in every case; an unfinished one has every count `None`. A compaction has no
  reasoning-token count. A late compaction goes on the next reply that may carry one (a
  `not_sent` reply carries none), else `close()` returns it.
- **Replacement link.** `Compaction.supersedes` is the `event_id` of an unfinished compaction,
  delivered earlier, that this one completes, else `None`. The type refuses a self-link, a
  link on an unfinished compaction, and two compactions of one reply naming the same one.

Ruled for PR 2b (the parser; not yet in `main`):
- **Several usage events in one call** (a retried turn). Each count and the charge are the
  exact sum over the call's usage events when every event reports them readably, else `None`;
  a repeat of an event id is counted once. The source does not say whether such events are
  per-attempt or cumulative: if cumulative the sum overstates and never understates.
- **Tool calls** are read from `tool.execution_start`; where a message carries `toolRequests`
  their ids must match, and a call with a parent tool call is refused. The parser takes
  `{"id", "type", "data"}` objects and imports nothing from the SDK.

- **Replies that are not ok** keep their figures whenever known: `sent_usage` if a count or
  the charge is known, else `sent_unknown`. An aborted idle is class `Aborted`.
- **Routing, a stated limit.** SDK 1.0.8 carries `isByok` and `isAuto` only on
  `model.call_failure`, so the two routing refusals are read from a failed call. A call routed
  elsewhere that succeeds first time gives no signal.

Ruled for PR 3 (not yet in `main`):
- **Which compaction a completed one replaces** is the driver's rule: it links only when
  exactly one delivered start is unpaired, and only to an unfinished compaction delivered on an
  earlier reply. With two or more unpaired starts, in the same reply, or onto a done entry,
  there is no link and the spend stays unknown.
- The driver removes repeats of an event id before building a `Reply`; `event_id` is built
  from the envelope id only; a complete whose `success` is not a bool is `failed`, counts and
  charge as read; what `close()` returns is attributed to the run by the orchestrator.
- **Home directory (open Medium M2 of #36's security review):** `home_paths` leaves part of a
  Windows user name that has a space or `'()` in it. It is fixed in `redact.py`, test first,
  with the reviewer's probe as the answer key, no later than PR 3, which does not merge while
  that probe fails. PR 3's driver also gives the home directory and the runtime path to the
  redactor as exact values; that alone is not enough.

## Answer keys (implementers do not edit them or weaken a comparison)

1. Synthetic event scripts written by the controller before each task, from the event shapes
   in the installed 1.0.8 source, with the expected `Reply` for each (text, tool calls, usage,
   cost, kind, error class). They are adapted from the legacy's `tests/model/test_copilot_parse.py`
   and `test_copilot_adapter.py` scripts with the model id changed.
2. Hand-worked costs: invented `totalNanoAiu` integers, each multiplied by 1E-11 by hand in the
   brief. No figure comes from the predecessor's run fragments (fixtures are public or
   synthetic only).
3. Redaction: a fixed list of strings with and without secrets and the exact expected output.

## PR sequence

| PR | Delivers |
| :--- | :--- |
| 1 | Types, protocol, redaction (#36) |
| 1b | Canned adapter, with `Compaction` and `Reply.compactions` |
| 2 (#63) | Compaction outcome, identity and replacement link; `close()` returns compactions; float tool arguments |
| 2b | Pure Copilot event parser and cost reading (`reply_from_events`); compactions from events here, or as 2c if it passes 800 lines |
| 3 | Session driver against a fake client: one turn, errors, timeouts |
| 3b | Tool-call turns (handlers parked until the next request), if 3 would pass 800 lines |
| 4 | The SDK 1.0.8 binding, the `copilot-sol-medium` configuration, the `live`-marked check |

## How it runs

Global rules §1, §3 and §7. The sub-session is the controller and writes no code: `mx-feature`
implements test first; `mx-precise` reviews each task; `mx-adversary` as above. Every brief
and review prompt carries: no stub or fake value standing in for real behaviour; no catch-all
that hides a failure; the answer keys. Per task the gate is
`uv run --locked python tools/gates.py` (run `npm ci` in `web/` once first), exit 0. Before
each PR is ready: `/sweep refactoring discover changed-update`, then the whole-branch review
(`mx-architect` running `adversarial-reviewer`, fresh agent, §7 severities); verdicts and
report paths in the PR body; CI green on both runners. Fix rounds follow §1.

## Done when

Each PR is open with CI green and its reviews passed, and the sub-session has sent the
coordinator one message per PR: the PR number, verdicts, report paths, gate exit codes,
mutation result, ledger lines (`1C-<pr> task=<n> agent=<name> fix-rounds=<n>
gates-first-pass=<y|n|n/a>`), parked Low findings and a `Not verified:` line. The coordinator
reads the diff and merges. The sub-session does not merge and does not edit shared records.

## Not verified

- Nothing in this step talks to Copilot. Whether SDK 1.0.8 and runtime 1.0.108 work together,
  whether `gpt-6-sol` is offered under that id, and the end-of-call rule on a real tool turn
  are settled only by the owner's first paid run (phase 6 or 7).
- No token limit is known for `gpt-6-sol`; the legacy's limit table and bytes-per-token
  estimate were measured on another model and are not ported as facts.
- The output-token cap is not passed to the SDK in the legacy; whether 1.0.8 can enforce it is
  for PR 4 to report.

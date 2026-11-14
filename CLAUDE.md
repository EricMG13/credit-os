# credit-os

Issuer source files in, a credit analyst's issuer library out. Analytical modules (CP-*)
read the sources through a model, each writes one Markdown handoff, and a delivery step
turns the handoffs into the library: Overview, Changes, Modules, Forecast and Evidence.

This is a rebuild of `EricMG13/RBOT-HTML` for one target environment. The predecessor is a
read-only source for ports (pinned at `origin/main` `8e3954a`); never change it.

## Reader

A portfolio manager or credit committee member who has not read the source documents.
Prose modules write bottom line, key findings, contrary evidence and what would change the
view, then limitations, judgement first. Source references appear only on the Evidence page
and in the trace control, never in narrative sentences.

## Target environment

| Component | Pin |
| :--- | :--- |
| Python | `>=3.12,<3.13` |
| uv | `>=0.12.5,<0.13` |
| Runtime | pydantic 2.13.4, pypdf 6.21.4, github-copilot-sdk 1.0.8 (openpyxl 3.1.5 is on the work PC but unused: xlsx is read with the standard library) |
| Dev | pytest 9.1.1, ruff 0.16.8, mypy 1.18.1 |
| Model route | GitHub Copilot CLI 1.0.108, model `gpt-6-sol`, config `copilot-sol-medium` |
| Front end | Node 24, React 19.3.0, Vite 6.4.5, Tailwind 4.3.3, TypeScript 5.9.3 |
| OS | Windows (work PC) and macOS (development); CI runs both Windows and Linux |
| Browsers | Chrome and Edge, both on the work PC |
| Run cap | USD 20 per run (decision 0002) |

One lockfile per stack. The aim is that what CI passes is what runs at work. Where the work PC
cannot install a pinned version, its copy uses the nearest it can and the difference is
reported back so the pin here follows (decision 0002). Prefer established packages and older
releases over the newest.

## Layout

```
src/credit_os/   one package, layered; a layer imports only layers listed before it
  sources/       pin and read issuer files
  handoff/       the one parser of module Markdown, to a typed document
  model/         Decimal financial kernel and forecast
  provider/      one model interface: Copilot for runs, canned answers for tests
  store/         run state in SQLite
  checks/        prose, figure and confidence checks on a handoff document
  orchestrator/  module order, retries, resume, CP-8 comparison
  delivery/      library data written from handoff documents
web/             React front end; draws what delivery wrote
methods/         module method texts
docs/decisions/  one record per dependency or design decision
docs/superpowers/plans/  the roadmap and one plan per phase
```

## Rules

- The handoff Markdown is parsed in `handoff/` and nowhere else.
- Python does all arithmetic. The front end draws the values it is given and computes none.
- The library must open from disk (`file://`) with no network and no server.
- Delivery adds no analysis: it selects and orders module-written passages, every number
  and qualification exact. Missing content stays an explicit gap.
- Expected values in tests are independent of the production calculation. Keep missing
  distinct from zero; keep amounts, currency, units, periods and source identities exact.
- Excel is an input format only; no workbook is ever generated.
- No credential files. Provider keys come only from the launching environment.
- A paid model run is a separate, explicit action by the owner. Builds and tests run no provider.
- No new dependency without a record in `docs/decisions/`.
- Work one analytical module at a time; module work is never split across sessions.

## How work runs here

- Global rules §1 (sub-agent-driven development), §3 (gates), §6 (design) and §7
  (coordinator sessions, pre-merge review) apply as written.
- `uv run --locked python tools/gates.py` and `npm --prefix web run gates` are the gates. Both
  exit 0 before a task is done; CI runs the same two commands. Always launch the first with
  `--locked`: a plain `uv run` re-locks silently before the gates start. Run `npm ci` in `web/`
  once before the Python gates: their duplication gate uses the `jscpd` pinned there (decision
  0005).
- Committed fixtures and retained responses come only from public or synthetic cases; this
  repository is public.
- An analyst's Submit on the run start page may start a paid run only under an owner ruling
  recorded in `docs/decisions/` that names its cap.
- Component and animation sources are limited to the eight sites in global §6; read the
  live page before using one.
- Keep one verification record, `VERIFICATION.md`, written only by the coordinator.
- Legacy `main` keeps moving. `docs/legacy/ports.md` maps each legacy path to its target here
  and the legacy commit it was last adapted from. The coordinator checks it before writing a
  phase plan and before that phase's PR merges, and is the only one who edits it.

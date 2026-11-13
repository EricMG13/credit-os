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
| Runtime | pydantic 2.13.4, pypdf 6.21.2, github-copilot-sdk 1.0.8 |
| Dev | pytest 9.1.1, ruff 0.16.8, mypy 1.18.1 |
| Model route | GitHub Copilot CLI, config `copilot-sol-medium` |
| Front end | Node 24, React 19.3.0, Vite 6.4.3, Tailwind 4.3.3, TypeScript 5.9.3 |
| OS | Windows (work PC) and macOS (development); CI runs both Windows and Linux |

One lockfile per stack. No per-machine adaptation: what CI passes is what runs at work.

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
- `uv run python tools/gates.py` and `npm --prefix web run gates` are the gates. Both exit 0
  before a task is done; CI runs the same two commands.
- Component and animation sources are limited to the eight sites in global §6; read the
  live page before using one.
- Keep one verification record, `VERIFICATION.md`, written only by the coordinator.

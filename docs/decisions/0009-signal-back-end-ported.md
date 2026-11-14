# 0009 Signal's back end is ported into the rebuild now

Date: 2026-11-14. Decided by: owner ("full port", relayed by the Signal session and confirmed
in the back-end coordinator's session: "Confirmed, prepare S-0"). The points below it are the
coordinator's, under decision 0006; the owner can overturn any of them.

## Decision

Signal's back end, slices 1 to 3, is ported into credit-os now. This replaces the roadmap's
line that it would get its own plan once phase 4 is done.

1. **A `signal` package that stands apart.** The code lives in `src/credit_os/signal/`. It
   imports none of the eight layers and none of them imports it. `signal` is in
   `credit_os.LAYERS` so the package is a known one, and in `credit_os.ISOLATED`, which the
   layering test enforces in both directions. Signal and the issuer library share a
   repository, gates and a front end, and no Python code.
2. **A served page beside the `file://` rule.** Signal is a local service on the standard
   library's `http.server`; its page polls it. The rule that the library opens from disk with
   no network and no server binds the library only. Decision 0003 (ruling 9) already placed
   Signal's page outside that rule and its gate; this record extends that to the back end.
3. **It starts before phase 4.** The port runs on its own track beside the numbered phases.
   It touches only `src/credit_os/signal/` and its tests, depends on no phase, and no phase
   depends on it.
4. **No new dependency.** The standard library's `http.server` and SQLite. The part of the
   predecessor's `research/webfetch.py` that Signal's `fetch.py` imports (address checks,
   connection types) is carried inside `signal/`; the rest of `research/` stays left behind.
5. **Names are not authentication: an accepted limit.** A user is a typed display name in a
   cookie, and the role comes from the `users` table (predecessor's Signal design, 5.2). Anyone
   who can reach the port can type a writer's name, post as them and read an invited group.
   The service starts on `127.0.0.1` by default, refuses a wildcard host, and answers only
   requests whose `Host` matches the address it was started on; those three behaviours are
   carried and tested. No owner action is offered over HTTP. Serving Signal to other machines
   is the owner's choice at launch and carries this limit with it.

## What does not change

- **Decision 0008.** A run reads the issuer's supplied files and nothing from the network.
  Signal's fetch of the feeds it follows is Signal's own and reaches no run.
- **No model call.** Nothing in Signal calls a model until the owner rules a cap (decision
  0006, ruling 21). The port carries no provider call.
- **Tests and builds** use synthetic data built in the test and open no network connection.
- **The page.** The predecessor's plain-JavaScript page and its browser tests are not carried
  as code. Design step D2e builds the React page; its slice reader takes Signal's JSON routes
  as its contract and the predecessor's 29 browser tests as its acceptance list.

## What follows

- S-0 (this record): `CLAUDE.md` Layout and the served-page rule, `LAYERS`, `ISOLATED` and the
  layering test, the roadmap's Signal paragraph, and the Signal row of `docs/legacy/ports.md`.
- S-1 to S-11, by the Signal session as a controller under global rules section 1, each
  within the 800-line cap with its tests and both gates at exit 0. Sizes are that session's
  estimates from file sizes.

| PR | Content |
| :--- | :--- |
| S-1 | `store.py` to migration 2, `identity.py`, `fold.py` |
| S-2 | `fetch.py`, with the needed part of `webfetch` |
| S-3 | `feeds.py`, `topics.py` |
| S-4 | `ingest.py`, `cli.py`, `__main__.py` |
| S-5 | `feedview.py` (slice 2 form) |
| S-6, S-7 | `service.py`, slice 1 and 2 routes |
| S-8 | Slice 3: migration 3 and `groups.py` |
| S-9, S-10 | Slice 3: `threads.py`, ingest posting, feed chips |
| S-11 | Slice 3: group and thread routes |

- Signal's code is sensitive code under the global rules (it parses untrusted feeds, opens
  network connections and serves HTTP): each of S-1 to S-11 takes `mx-adversary` review, the
  sweep discovery and the adversarial whole-branch review.
- A port is new code here: a defect that is the same in the predecessor is fixed in the port,
  not carried.

## What it costs if wrong

Two tracks now draw on the same reviewers and the same `main`, so phase 1 may merge later. If
the port stalls, `signal/` is a package nothing imports and can be removed without touching a
layer. The served page is the first thing in this repository that listens on a port; the
limit in point 5 is real from the first route that acts on a role (S-11).

## Not verified

- The predecessor's Signal sources against the Python 3.12 pin.
- credit-os gate results on any Signal file; none has been copied.
- The line counts and the split of `service.py`, `store.py` and `threads.py` by slice.
- The bind and `Host` behaviours in point 5 were read in the predecessor at `87161c3`
  (`cli.py`, `service.py`), not run.
- Slice 3 exists only on a local, unpushed predecessor branch (`claude/signal-3d-proof`).

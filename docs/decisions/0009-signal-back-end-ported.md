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
   requests whose `Host` matches the address it was started on; the port carries those three
   behaviours with tests (S-6, S-7). No owner action is offered over HTTP. Serving Signal to
   other machines is the owner's choice at launch and carries this limit with it.

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

## Addendum, 2026-11-14: rulings made while porting

By the Signal session as controller, accepted by the coordinator under decision 0006 with the
conditions shown. The full text is in the PR that carries each. The S-1 to S-11 table above
is replaced by a split by file, each PR within the cap: the port takes the reviewed tip's
files whole where they fit. The Signal session's estimate, by message and not a ruling, is
about 18 PRs in the order network pin, store, feeds, fetch, identity and topics, groups, feed
view, threads, ingest, service, command line.

**Departures from the predecessor made for this repository's gates.**
- No `assert` in source: an explicit check raises the module's own error.
- No SQL assembled from strings: every statement is static with `?` parameters. Where a
  statement becomes "fixed statement, filter in Python", order, limits and paging give the
  predecessor's rows, and a differential test covers them.
- Feeds are parsed with the standard library's `xml.parsers.expat`; a document type
  declaration and every kind of entity or notation declaration is refused. No `defusedxml`.
- The part of `research/webfetch.py` Signal uses is `signal/netpin.py`.

**In `main` (#74, #75): the network pin.**
- `is_public` takes an exact `str`, refuses a zone id, and refuses 2002::/16, 3fff::/20 and
  192.0.0.0/24 (except .9 and .10) by explicit range, so the verdict does not rest on the
  interpreter's tables. An ISATAP address is public only if the IPv4 it embeds is.
- `tls_context` adds `ssl.VERIFY_X509_STRICT`. `connect` refuses a pinned address that is not
  public, bounds the handshake by the time left on the total deadline (a defect in the
  predecessor), and closes the socket on any exception.
- Accepted limits: special ranges IANA marks globally reachable are public; a NAT64 prefix
  chosen by a network cannot be recognised; a certificate may match on its common name;
  strict X.509 refuses a few legacy trust anchors, so a feed whose chain ends only there is
  unreachable.

**Ruled, not yet in `main`.**
- Feeds: a link is usable only when its host is a DNS name of ASCII labels (no IP literal in
  any spelling, no `\`, `@`, `%`); titles and summaries drop control and format characters;
  a body over 2 MiB or nested deeper than 64 is refused; feed text in an error is cut to 120
  characters; block elements never fuse in a summary; Atom `html` and `xhtml` text is
  stripped.
- Feed parser memory: the predecessor's peak of about 400 MiB on a hostile 2 MiB feed is a
  defect, not a limit. Peak memory stays under 64 MiB, with a committed `tracemalloc` test;
  ingest does not merge without it.
- Store: `write_transaction` joins only its own outer transaction; a database with a newer
  schema is refused before any write; bad input is refused with `StoreError` only; a new
  database file is owner-only where the platform supports it.
- Fetch: port 0 is refused; time is spent at `clock >= deadline`; the response is closed on
  every path; one test goes through the real pinned connection with a loopback peer.
- Reactions are `agree`, `disagree`, `seen` (decision 0006, ruling 19); the predecessor's
  four are not carried or migrated. Only a writer comments, shares, starts a thread or
  attaches a story (ruling 18). D2e's slice types on `main` are the contract for route JSON.
- Carried as accepted limits and listed in each PR: sequential ids reveal hidden-group
  counts; a demoted writer still edits their own comment; `link_key` drops the fragment and
  scheme; deleted text stays in the write-ahead log while a connection is open.

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

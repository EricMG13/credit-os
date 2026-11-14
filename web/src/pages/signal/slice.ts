// Signal's slice: what the service will later serve, read by hand. Each reader takes a value and
// its path and returns the value or the first failing path; one malformed record fails the slice.
import type { SliceResult } from "../route-table";

type SignalViewer = {
  name: string | null;
  initials: string | null;
  role: "reader" | "writer";
  roleLabel: string;
};
type SignalTopicChannel = {
  id: string;
  name: string;
  count: string | null;
  followed: boolean;
};
type SignalGroupChannel = { id: string; name: string; unread: string | null };
type SignalDigestChannel = { id: string; name: string; unread: boolean; paused: boolean };
type SignalChannels = {
  topics: SignalTopicChannel[];
  groups: SignalGroupChannel[];
  digests: SignalDigestChannel[];
  savedCount: string | null;
};
export type SignalStory = {
  id: string;
  kind: "regulator" | "news" | "ratings" | "research";
  kindLabel: string;
  headline: string;
  url: string | null;
  source: { name: string; monogram: string };
  time: string | null;
  summary: string | null;
  tags: string[];
  alsoIn: { label: string; monograms: string[]; more: string | null } | null;
  sharedBy: { initials: string; label: string } | null;
  ai: { line: string } | null;
  strength: { marks: 1 | 2 | 3; word: string } | null;
  saved: boolean;
  commentCount: string | null;
  /** A regulatory case's stage; `label` ("Stage 3 of 4") is delivered, `position` (0 to 1) only places the bar. */
  stage: {
    current: string;
    label: string;
    position: number;
    stages: { name: string; current: boolean }[];
  } | null;
  /** Rating moves as delivered (from, to and the word); an affirmed rating keeps from equal to to. */
  ratingMoves: { from: string; to: string; word: string }[];
};
/** A digest card in the feed; with `nothing` set it is the one-sentence card and holds no points. */
export type SignalDigestCard = {
  id: string;
  digestName: string;
  monogram: string;
  title: string;
  date: string | null;
  unread: boolean;
  ai: boolean;
  points: string[];
  summary: string | null;
  nothing: string | null;
};
/**
 * Entry ids (story or digest card) in each order the service supplies; the page orders by them and
 * ranks nothing. `waiting` is the delivered pill label ("4 new stories") with the entries it reveals;
 * `older` holds the entries Show older reveals (none: no button). `top` and `latest` hold the same ids; `waiting` and `older` hold others, and no id repeats (the reader checks).
 */
type SignalFeedView = {
  top: string[];
  latest: string[];
  waiting: { label: string; ids: string[] } | null;
  older: string[];
};
/** The freshness line: `checked` is the delivered time, `failing` and `error` the delivered suffix texts. */
export type SignalFreshness = {
  state: "checking" | "checked" | "not-checked" | "unavailable";
  checked: string | null;
  failing: string | null;
  error: string | null;
};
type SignalFeed = {
  status: "loading" | "ready";
  error: null | "unreachable" | "request" | "unreadable";
  freshness: SignalFreshness;
  stories: SignalStory[];
  digests: SignalDigestCard[];
  views: { "for-you": SignalFeedView; latest: SignalFeedView; saved: SignalFeedView };
  topics: Record<string, SignalFeedView>;
};
type SignalSnapshot = { viewer: SignalViewer; channels: SignalChannels; feed: SignalFeed };
export type SignalScene = { id: string; snapshot: SignalSnapshot };
export type SignalSlice = { scenes: [SignalScene, ...SignalScene[]] };

type Got<T> = { ok: true; value: T } | { ok: false; reason: string };
type Reader<T> = (value: unknown, path: string) => Got<T>;

const good = <T>(value: T): Got<T> => ({ ok: true, value });
const bad = (path: string, expected: string): Got<never> => ({
  ok: false,
  reason: `${path === "" ? "slice" : path}: expected ${expected}`,
});

const str: Reader<string> = (v, path) => (typeof v === "string" ? good(v) : bad(path, "a string"));
const bool: Reader<boolean> = (v, path) =>
  typeof v === "boolean" ? good(v) : bad(path, "true or false");
const strOrNull: Reader<string | null> = (v, path) =>
  typeof v === "string" || v === null ? good(v) : bad(path, "a string or null");

/** A reader for a value that is one of the listed words (`null` may be one of them). */
function oneOf<T extends string | null>(words: readonly T[], expected: string): Reader<T> {
  return (v, path) => {
    const found = words.find((word) => word === v);
    return found === undefined ? bad(path, expected) : good(found);
  };
}

function orNull<T>(each: Reader<T>): Reader<T | null> {
  return (v, path) => (v === null ? good(null) : each(v, path));
}

function list<T>(each: Reader<T>): Reader<T[]> {
  return (v, path) => {
    if (!Array.isArray(v)) return bad(path, "a list");
    const items: T[] = [];
    for (const [index, item] of (v as unknown[]).entries()) {
      const got = each(item, `${path}[${String(index)}]`);
      if (!got.ok) return got;
      items.push(got.value);
    }
    return good(items);
  };
}

/** Members are read in the order given; a missing member reads as `undefined`, which its reader refuses. */
function shape<T extends object>(readers: { [K in keyof T]-?: Reader<T[K]> }): Reader<T> {
  return (v, path) => {
    if (typeof v !== "object" || v === null || Array.isArray(v)) return bad(path, "an object");
    const record = v as Record<string, unknown>;
    const out: Record<string, unknown> = {};
    for (const [key, read] of Object.entries<Reader<unknown>>(readers)) {
      const got = read(
        Object.hasOwn(record, key) ? record[key] : undefined,
        path === "" ? key : `${path}.${key}`,
      );
      if (!got.ok) return got;
      out[key] = got.value;
    }
    return good(out as T);
  };
}

/**
 * A record of readers' values keyed by any name, read in key order. The result has no prototype, so
 * a key such as "__proto__" or "constructor" from the data stays an ordinary own entry, validated
 * like any other; look keys up with `Object.hasOwn`.
 */
function record<T>(each: Reader<T>): Reader<Record<string, T>> {
  return (v, path) => {
    if (typeof v !== "object" || v === null || Array.isArray(v)) return bad(path, "an object");
    const out: Record<string, T> = Object.create(null) as Record<string, T>;
    for (const [key, item] of Object.entries(v)) {
      const got = each(item, `${path}.${key}`);
      if (!got.ok) return got;
      out[key] = got.value;
    }
    return good(out);
  };
}

const unit: Reader<number> = (v, path) =>
  typeof v === "number" && Number.isFinite(v) && v >= 0 && v <= 1
    ? good(v)
    : bad(path, "a number from 0 to 1");

/** A case stage lists its steps (the count is not fixed) and marks exactly one of them as the current one. */
const stageSteps: Reader<{ name: string; current: boolean }[]> = (v, path) => {
  const got = list(shape({ name: str, current: bool }))(v, path);
  if (!got.ok) return got;
  return got.value.filter((step) => step.current).length === 1
    ? got
    : bad(path, "exactly one current step");
};

const marks: Reader<1 | 2 | 3> = (v, path) =>
  v === 1 || v === 2 || v === 3 ? good(v) : bad(path, "1, 2 or 3");

const story = shape<SignalStory>({
  id: str,
  kind: oneOf(["regulator", "news", "ratings", "research"], "regulator, news, ratings or research"),
  kindLabel: str,
  headline: str,
  url: strOrNull,
  source: shape({ name: str, monogram: str }),
  time: strOrNull,
  summary: strOrNull,
  tags: list(str),
  alsoIn: orNull(shape({ label: str, monograms: list(str), more: strOrNull })),
  sharedBy: orNull(shape({ initials: str, label: str })),
  ai: orNull(shape({ line: str })),
  strength: orNull(shape({ marks, word: str })),
  saved: bool,
  commentCount: strOrNull,
  stage: orNull(
    shape({
      current: str,
      label: str,
      position: unit,
      stages: stageSteps,
    }),
  ),
  ratingMoves: list(shape({ from: str, to: str, word: str })),
});
const digestBase = shape<SignalDigestCard>({
  id: str,
  digestName: str,
  monogram: str,
  title: str,
  date: strOrNull,
  unread: bool,
  ai: bool,
  points: list(str),
  summary: strOrNull,
  nothing: strOrNull,
});
/** A nothing-to-report card needs no model and no list: it holds no points and is not marked AI. */
const digestCard: Reader<SignalDigestCard> = (v, path) => {
  const got = digestBase(v, path);
  if (!got.ok || got.value.nothing === null) return got;
  if (got.value.points.length > 0) {
    return bad(`${path}.points`, "no points on a nothing-to-report card");
  }
  if (got.value.ai) return bad(`${path}.ai`, "false on a nothing-to-report card");
  return got;
};
const feedView = shape<SignalFeedView>({
  top: list(str),
  latest: list(str),
  waiting: orNull(shape({ label: str, ids: list(str) })),
  older: list(str),
});
/** Checked sources always come with the delivered time to show. */
const freshness: Reader<SignalFreshness> = (v, path) => {
  const got = shape<SignalFreshness>({
    state: oneOf(
      ["checking", "checked", "not-checked", "unavailable"],
      '"checking", "checked", "not-checked" or "unavailable"',
    ),
    checked: strOrNull,
    failing: strOrNull,
    error: strOrNull,
  })(v, path);
  if (!got.ok) return got;
  return got.value.state === "checked" && got.value.checked === null
    ? bad(`${path}.checked`, "the delivered time when the state is checked")
    : got;
};

const viewer = shape<SignalViewer>({
  name: strOrNull,
  initials: strOrNull,
  role: oneOf(["reader", "writer"], "reader or writer"),
  roleLabel: str,
});
const channels = shape<SignalChannels>({
  topics: list(shape<SignalTopicChannel>({ id: str, name: str, count: strOrNull, followed: bool })),
  groups: list(shape<SignalGroupChannel>({ id: str, name: str, unread: strOrNull })),
  digests: list(shape<SignalDigestChannel>({ id: str, name: str, unread: bool, paused: bool })),
  savedCount: strOrNull,
});
/** Every id a view or topic names must be a story or digest card the feed holds, and no id repeats. */
const feedBase = shape<SignalFeed>({
  status: oneOf(["loading", "ready"], '"loading" or "ready"'),
  error: oneOf(
    [null, "unreachable", "request", "unreadable"],
    'null, "unreachable", "request" or "unreadable"',
  ),
  freshness,
  stories: list(story),
  digests: list(digestCard),
  views: shape({ "for-you": feedView, latest: feedView, saved: feedView }),
  topics: record(feedView),
});
type IdProblem = { at: string; expected: string };

/**
 * One coherent id set per view: every id is in the feed; none repeats inside `top`, `latest`,
 * `waiting.ids` or `older`; `top` and `latest` hold the same ids; `waiting.ids` and `older` are
 * disjoint from them and from each other. The first failing id is named by its list and position.
 */
function viewIdProblem(view: SignalFeedView, known: Set<string>): IdProblem | null {
  const lists: [string, string[]][] = [
    ["top", view.top],
    ["latest", view.latest],
    ["older", view.older],
    ["waiting.ids", view.waiting?.ids ?? []],
  ];
  const found = (name: string, ids: string[], fails: (id: string) => boolean, expected: string) => {
    const index = ids.findIndex((id) => fails(id));
    return index === -1 ? null : { at: `${name}[${String(index)}]`, expected };
  };
  const seen = () => {
    const once = new Set<string>();
    return (id: string) => (once.has(id) ? true : (once.add(id), false));
  };
  const checks: (() => IdProblem | null)[] = [
    ...lists.map(
      ([name, ids]) =>
        () =>
          found(name, ids, (id) => !known.has(id), "the id of a story or digest in the feed"),
    ),
    ...lists.map(
      ([name, ids]) =>
        () =>
          found(name, ids, seen(), "an id the list does not already hold"),
    ),
    () => found("latest", view.latest, (id) => !view.top.includes(id), "an id in the view's top"),
    () => found("top", view.top, (id) => !view.latest.includes(id), "an id in the view's latest"),
    () =>
      found(
        "older",
        view.older,
        (id) => view.top.includes(id),
        "an id the view does not already list",
      ),
    () =>
      found(
        "waiting.ids",
        view.waiting?.ids ?? [],
        (id) => view.top.includes(id),
        "an id the view does not already list",
      ),
    () =>
      found(
        "older",
        view.older,
        (id) => view.waiting?.ids.includes(id) ?? false,
        "an id the view does not already list",
      ),
  ];
  for (const check of checks) {
    const problem = check();
    if (problem !== null) return problem;
  }
  return null;
}

const feed: Reader<SignalFeed> = (v, path) => {
  const got = feedBase(v, path);
  if (!got.ok) return got;
  const known = new Set(got.value.stories.map((s) => s.id));
  for (const [index, card] of got.value.digests.entries()) {
    if (known.has(card.id)) {
      return bad(`${path}.digests[${String(index)}].id`, "an id no story or digest already uses");
    }
    known.add(card.id);
  }
  const views: [string, SignalFeedView][] = [
    ...Object.entries(got.value.views).map(([k, w]): [string, SignalFeedView] => [`views.${k}`, w]),
    ...Object.entries(got.value.topics).map(([k, w]): [string, SignalFeedView] => [
      `topics.${k}`,
      w,
    ]),
  ];
  for (const [where, view] of views) {
    const problem = viewIdProblem(view, known);
    if (problem !== null) {
      return bad(`${path}.${where}.${problem.at}`, problem.expected);
    }
  }
  return got;
};
const snapshotBase = shape<SignalSnapshot>({ viewer, channels, feed });
/** Each channel topic has exactly one order in the feed: a missing order is not an empty topic. */
const snapshot: Reader<SignalSnapshot> = (v, path) => {
  const got = snapshotBase(v, path);
  if (!got.ok) return got;
  const { channels: lists, feed: items } = got.value;
  const where = `${path}.feed.topics`;
  const missing = lists.topics.find((t) => !Object.hasOwn(items.topics, t.id));
  if (missing !== undefined) {
    return bad(`${where}.${missing.id}`, "an order for this channel topic");
  }
  const known = new Set(lists.topics.map((t) => t.id));
  const extra = Object.keys(items.topics).find((id) => !known.has(id));
  if (extra !== undefined) return bad(`${where}.${extra}`, "the id of a channel topic");
  return got;
};
/** The slice always has a first scene, so the unknown-scene page can link home to it. */
function nonEmpty<T>(each: Reader<T>): Reader<[T, ...T[]]> {
  return (v, path) => {
    const got = list(each)(v, path);
    if (!got.ok) return got;
    const [first, ...rest] = got.value;
    return first === undefined ? bad(path, "at least one scene") : good([first, ...rest]);
  };
}

/** The home route names the scene "main", so the slice must hold it. */
function withMain(
  each: Reader<[SignalScene, ...SignalScene[]]>,
): Reader<[SignalScene, ...SignalScene[]]> {
  return (v, path) => {
    const got = each(v, path);
    if (!got.ok) return got;
    return got.value.some((scene) => scene.id === "main")
      ? got
      : bad(path, 'a scene with id "main"');
  };
}

const scenes = shape<SignalSlice>({
  scenes: withMain(nonEmpty(shape<SignalScene>({ id: str, snapshot }))),
});

export function readSlice(source: unknown): SliceResult<SignalSlice> {
  if (source === undefined) return { kind: "absent" };
  const got = scenes(source, "");
  return got.ok ? { kind: "ok", data: got.value } : { kind: "invalid", reason: got.reason };
}

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
type SignalStory = {
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
};
/** Entry ids in each order the service supplies; the page orders by them and ranks nothing. */
type SignalFeedView = { top: string[]; latest: string[] };
type SignalFeed = {
  status: "loading" | "ready";
  error: null | "unreachable" | "request" | "unreadable";
  stories: SignalStory[];
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
});
const feedView = shape<SignalFeedView>({ top: list(str), latest: list(str) });

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
/** Every id a view or topic names must be a story the feed holds. */
const feedBase = shape<SignalFeed>({
  status: oneOf(["loading", "ready"], '"loading" or "ready"'),
  error: oneOf(
    [null, "unreachable", "request", "unreadable"],
    'null, "unreachable", "request" or "unreadable"',
  ),
  stories: list(story),
  views: shape({ "for-you": feedView, latest: feedView, saved: feedView }),
  topics: record(feedView),
});
const feed: Reader<SignalFeed> = (v, path) => {
  const got = feedBase(v, path);
  if (!got.ok) return got;
  const known = new Set(got.value.stories.map((s) => s.id));
  const views: [string, SignalFeedView][] = [
    ...Object.entries(got.value.views).map(([k, w]): [string, SignalFeedView] => [`views.${k}`, w]),
    ...Object.entries(got.value.topics).map(([k, w]): [string, SignalFeedView] => [
      `topics.${k}`,
      w,
    ]),
  ];
  for (const [where, view] of views) {
    for (const order of ["top", "latest"] as const) {
      const at = view[order].findIndex((id) => !known.has(id));
      if (at !== -1) {
        return bad(`${path}.${where}.${order}[${String(at)}]`, "the id of a story in the feed");
      }
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

const scenes = shape<SignalSlice>({
  scenes: nonEmpty(shape<SignalScene>({ id: str, snapshot })),
});

export function readSlice(source: unknown): SliceResult<SignalSlice> {
  if (source === undefined) return { kind: "absent" };
  const got = scenes(source, "");
  return got.ok ? { kind: "ok", data: got.value } : { kind: "invalid", reason: got.reason };
}

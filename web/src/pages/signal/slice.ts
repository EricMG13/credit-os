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
type SignalFeed = {
  status: "loading" | "ready";
  error: null | "unreachable" | "request" | "unreadable";
};
type SignalSnapshot = { viewer: SignalViewer; channels: SignalChannels; feed: SignalFeed };
type SignalScene = { id: string; snapshot: SignalSnapshot };
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
      const got = read(record[key], path === "" ? key : `${path}.${key}`);
      if (!got.ok) return got;
      out[key] = got.value;
    }
    return good(out as T);
  };
}

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
const feed = shape<SignalFeed>({
  status: oneOf(["loading", "ready"], '"loading" or "ready"'),
  error: oneOf(
    [null, "unreachable", "request", "unreadable"],
    'null, "unreachable", "request" or "unreadable"',
  ),
});
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
  scenes: nonEmpty(
    shape<SignalScene>({ id: str, snapshot: shape<SignalSnapshot>({ viewer, channels, feed }) }),
  ),
});

export function readSlice(source: unknown): SliceResult<SignalSlice> {
  if (source === undefined) return { kind: "absent" };
  const got = scenes(source, "");
  return got.ok ? { kind: "ok", data: got.value } : { kind: "invalid", reason: got.reason };
}

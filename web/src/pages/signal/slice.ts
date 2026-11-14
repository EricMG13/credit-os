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
  /** The words the topic follows, drawn as tags in its view's header. */
  keywords: string[];
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
export type SignalFeedView = {
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
  /** False when no source is approved yet (the empty states say so). */
  sources: { approved: boolean };
  freshness: SignalFreshness;
  stories: SignalStory[];
  digests: SignalDigestCard[];
  views: { "for-you": SignalFeedView; latest: SignalFeedView; saved: SignalFeedView };
  topics: Record<string, SignalFeedView>;
};
/** One item shared in a group: a story, a note, or both (a story with the sharer's note). */
export type SignalThreadSummary = {
  id: string;
  /** Names a story in the snapshot's feed (the reader checks). */
  storyId: string | null;
  note: string | null;
  /** The delivered "shared by" line, e.g. "Shared by Tobias O, 1 h ago". */
  sharedBy: { initials: string; label: string };
  commentCount: string | null;
  archived: boolean;
  unread: boolean;
  /** The delivered time of the latest activity. */
  lastActivity: string | null;
};
export type SignalGroup = {
  id: string;
  name: string;
  /** Delivered, e.g. "Open to everyone" or "Invited only". */
  visibility: string;
  /** Delivered, e.g. "6 members". */
  memberSummary: string;
  members: { initials: string; name: string }[];
  /** The delivered "+N" after the shown members. */
  moreMembers: string | null;
  threads: SignalThreadSummary[];
};
/** One reaction a comment holds: the word, the delivered count and whether the viewer's own is set. */
type SignalReaction = { word: "Agree" | "Disagree" | "Seen"; count: string; mine: boolean };
/**
 * A comment. A removed comment holds no text and no reactions; any other holds text. A reply is one
 * level deep: its own `replies` is empty. `time` is delivered ("10:02"); the page adds ", edited".
 */
export type SignalComment = {
  id: string;
  author: { initials: string; name: string };
  own: boolean;
  time: string | null;
  text: string | null;
  edited: boolean;
  removed: boolean;
  reactions: SignalReaction[];
  replies: SignalComment[];
};
/**
 * The thread a group's item opens. Every item of a group names exactly one thread (same group, story,
 * note and archived state) and every thread is named by an item (the reader checks both ways).
 * `title`, `subline` and `archivedLine` are delivered text.
 */
export type SignalThread = {
  id: string;
  groupId: string;
  storyId: string | null;
  note: string | null;
  archived: boolean;
  title: string;
  subline: string;
  archivedLine: string | null;
  comments: SignalComment[];
};
type SignalSnapshot = {
  viewer: SignalViewer;
  channels: SignalChannels;
  feed: SignalFeed;
  groups: SignalGroup[];
  threads: SignalThread[];
};
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

const viewerBase = shape<SignalViewer>({
  name: strOrNull,
  initials: strOrNull,
  role: oneOf(["reader", "writer"], "reader or writer"),
  roleLabel: str,
});
/** A name comes with its initials and no name has none: the chip draws both or neither. */
const viewer: Reader<SignalViewer> = (v, path) => {
  const got = viewerBase(v, path);
  if (!got.ok) return got;
  return (got.value.name === null) === (got.value.initials === null)
    ? got
    : bad(`${path}.initials`, "initials when the viewer has a name, and null when there is none");
};
/** A shared item holds a story, a note or both; a thread with neither has nothing to draw. */
const thread: Reader<SignalThreadSummary> = (v, path) => {
  const got = shape<SignalThreadSummary>({
    id: str,
    storyId: strOrNull,
    note: strOrNull,
    sharedBy: shape({ initials: str, label: str }),
    commentCount: strOrNull,
    archived: bool,
    unread: bool,
    lastActivity: strOrNull,
  })(v, path);
  if (!got.ok) return got;
  return got.value.storyId === null && got.value.note === null
    ? bad(`${path}.note`, "a note when the thread names no story")
    : got;
};
const groupBase = shape<SignalGroup>({
  id: str,
  name: str,
  visibility: str,
  memberSummary: str,
  members: list(shape({ initials: str, name: str })),
  moreMembers: strOrNull,
  threads: list(thread),
});
/** A "+N" counts members after the shown ones, so it needs shown members. */
const group: Reader<SignalGroup> = (v, path) => {
  const got = groupBase(v, path);
  if (!got.ok) return got;
  return got.value.members.length === 0 && got.value.moreMembers !== null
    ? bad(`${path}.moreMembers`, "null when the group lists no members")
    : got;
};
const channels = shape<SignalChannels>({
  topics: list(
    shape<SignalTopicChannel>({
      id: str,
      name: str,
      count: strOrNull,
      followed: bool,
      keywords: list(str),
    }),
  ),
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
  sources: shape({ approved: bool }),
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
  if (got.value.status === "loading") {
    // A loading feed draws a skeleton in place of every list, so an entry would be accepted and never drawn.
    for (const [where, view] of views) {
      const held: [string, string[]][] = [
        ["top", view.top],
        ["latest", view.latest],
        ["waiting.ids", view.waiting?.ids ?? []],
        ["older", view.older],
      ];
      const full = held.find(([, ids]) => ids.length > 0);
      if (full !== undefined) {
        return bad(`${path}.${where}.${full[0]}[0]`, "no entries while the feed is loading");
      }
      if (view.waiting !== null) {
        return bad(`${path}.${where}.waiting`, "no new-story pill while the feed is loading");
      }
    }
  }
  return got;
};

const reaction = shape<SignalReaction>({
  word: oneOf(["Agree", "Disagree", "Seen"], '"Agree", "Disagree" or "Seen"'),
  count: str,
  mine: bool,
});
/** A reply is the last level: it holds no replies of its own. */
const noReplies: Reader<SignalComment[]> = (v, path) =>
  Array.isArray(v) && v.length === 0 ? good([]) : bad(path, "no replies on a reply");
/** A removed comment has no text and no reactions; any other has text; a word is used once. */
function comment(replies: Reader<SignalComment[]>): Reader<SignalComment> {
  const base = shape<SignalComment>({
    id: str,
    author: shape({ initials: str, name: str }),
    own: bool,
    time: strOrNull,
    text: strOrNull,
    edited: bool,
    removed: bool,
    reactions: list(reaction),
    replies,
  });
  return (v, path) => {
    const got = base(v, path);
    if (!got.ok) return got;
    const one = got.value;
    if (one.removed && one.text !== null) return bad(`${path}.text`, "null on a removed comment");
    if (one.removed && one.reactions.length > 0) {
      return bad(`${path}.reactions`, "no reactions on a removed comment");
    }
    if (!one.removed && one.text === null) {
      return bad(`${path}.text`, "the comment's text (only a removed comment has none)");
    }
    const words = new Set<string>();
    for (const [index, held] of one.reactions.entries()) {
      if (words.has(held.word)) {
        return bad(
          `${path}.reactions[${String(index)}].word`,
          "a word the comment does not already hold",
        );
      }
      words.add(held.word);
    }
    return got;
  };
}
const topComment = comment(list(comment(noReplies)));

/** Comment ids are used once in a thread, replies included; an archived line belongs to an archived thread. */
const threadRecord: Reader<SignalThread> = (v, path) => {
  const got = shape<SignalThread>({
    id: str,
    groupId: str,
    storyId: strOrNull,
    note: strOrNull,
    archived: bool,
    title: str,
    subline: str,
    archivedLine: strOrNull,
    comments: list(topComment),
  })(v, path);
  if (!got.ok) return got;
  if (!got.value.archived && got.value.archivedLine !== null) {
    return bad(`${path}.archivedLine`, "null when the thread is not archived");
  }
  const seen = new Set<string>();
  for (const [index, top] of got.value.comments.entries()) {
    const at = `${path}.comments[${String(index)}]`;
    const ones = [
      { one: top, where: `${at}.id` },
      ...top.replies.map((r, i) => ({ one: r, where: `${at}.replies[${String(i)}].id` })),
    ];
    for (const { one, where } of ones) {
      if (seen.has(one.id)) return bad(where, "an id the thread does not already use");
      seen.add(one.id);
    }
  }
  return got;
};
const snapshotBase = shape<SignalSnapshot>({
  viewer,
  channels,
  feed,
  groups: list(group),
  threads: list(threadRecord),
});

/** A thread is named by (group, id); the key is a pair so no id can run into another's. */
const threadKey = (groupId: string, id: string) => JSON.stringify([groupId, id]);

/** Each group item names exactly one thread and each thread is named by an item, with the same story, note and state. */
function threadProblem(snap: SignalSnapshot, path: string): string | null {
  const held = new Map<string, SignalThread>();
  for (const [index, one] of snap.threads.entries()) {
    const key = threadKey(one.groupId, one.id);
    if (held.has(key)) {
      return `${path}.threads[${String(index)}].id: expected an id no other thread in its group uses`;
    }
    held.set(key, one);
  }
  const named = new Set<string>();
  for (const [g, one] of snap.groups.entries()) {
    for (const [t, item] of one.threads.entries()) {
      const at = `${path}.groups[${String(g)}].threads[${String(t)}]`;
      const key = threadKey(one.id, item.id);
      const own = held.get(key);
      if (own === undefined)
        return `${at}.id: expected the id of a thread in the snapshot's threads`;
      named.add(key);
      const same: [string, boolean][] = [
        ["storyId", own.storyId === item.storyId],
        ["note", own.note === item.note],
        ["archived", own.archived === item.archived],
      ];
      const differs = same.find(([, ok]) => !ok);
      if (differs !== undefined) {
        return `${at}.${differs[0]}: expected the ${differs[0]} the thread itself holds`;
      }
    }
  }
  const stray = snap.threads.findIndex((one) => !named.has(threadKey(one.groupId, one.id)));
  return stray === -1
    ? null
    : `${path}.threads[${String(stray)}].id: expected the id of an item in its group's threads`;
}

/** A group id is used once; each thread id once in its group; each thread's story is in the feed. */
function groupProblem(groups: SignalGroup[], stories: Set<string>, path: string): string | null {
  const seen = new Set<string>();
  for (const [g, one] of groups.entries()) {
    const at = `${path}.groups[${String(g)}]`;
    if (seen.has(one.id)) return `${at}.id: expected an id no other group uses`;
    seen.add(one.id);
    const threads = new Set<string>();
    for (const [t, item] of one.threads.entries()) {
      if (threads.has(item.id))
        return `${at}.threads[${String(t)}].id: expected an id the group does not already use`;
      threads.add(item.id);
      if (item.storyId !== null && !stories.has(item.storyId)) {
        return `${at}.threads[${String(t)}].storyId: expected the id of a story in the feed`;
      }
    }
  }
  return null;
}

/** The channel list and the groups name the same groups, in both directions. */
function channelGroupProblem(snap: SignalSnapshot, path: string): string | null {
  const held = new Set(snap.groups.map((g) => g.id));
  const listed = new Set(snap.channels.groups.map((g) => g.id));
  const channel = snap.channels.groups.findIndex((g) => !held.has(g.id));
  if (channel !== -1) {
    return `${path}.channels.groups[${String(channel)}].id: expected the id of a group in the snapshot's groups`;
  }
  const one = snap.groups.findIndex((g) => !listed.has(g.id));
  if (one !== -1) {
    return `${path}.groups[${String(one)}].id: expected the id of a group in the channel list`;
  }
  const named = snap.groups.findIndex(
    (g) => snap.channels.groups.find((c) => c.id === g.id)?.name !== g.name,
  );
  return named === -1
    ? null
    : `${path}.groups[${String(named)}].name: expected the name the channel list gives this group`;
}

/** Each channel topic has exactly one order in the feed: a missing order is not an empty topic. */
const snapshot: Reader<SignalSnapshot> = (v, path) => {
  const got = snapshotBase(v, path);
  if (!got.ok) return got;
  const stories = new Set(got.value.feed.stories.map((s) => s.id));
  const problem =
    groupProblem(got.value.groups, stories, path) ??
    channelGroupProblem(got.value, path) ??
    threadProblem(got.value, path);
  if (problem !== null) return { ok: false, reason: problem };
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

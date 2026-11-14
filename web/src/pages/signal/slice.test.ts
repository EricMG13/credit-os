import fixture from "../../../fixtures/signal.json";
import { readSlice } from "./slice";

type Json = { [key: string]: Json } | Json[] | string | number | boolean | null;
type Members = { [key: string]: Json };

/** A copy of the fixture slice with scene 2 changed at `path` (`undefined` deletes the member). */
function withScene(path: (string | number)[], value: Json | undefined): unknown {
  const copy = structuredClone(fixture.slice) as { scenes: Json[] };
  let at: Json = copy.scenes[2] ?? null;
  for (const step of path.slice(0, -1)) at = (at as Members)[step] ?? null;
  const last = path[path.length - 1] ?? "";
  if (value === undefined) Reflect.deleteProperty(at as Members, last);
  else (at as Members)[last] = value;
  return copy;
}

const STAGES = ["Opened", "Initial review", "In-depth review", "Decision"];

describe("readSlice", () => {
  it("is absent for undefined", () => {
    expect(readSlice(undefined)).toEqual({ kind: "absent" });
  });

  it("reads the fixture file itself", () => {
    const result = readSlice(fixture.slice);
    expect(result.kind).toBe("ok");
    if (result.kind === "ok") {
      expect(result.data.scenes.map((s) => s.id)).toEqual([
        "main",
        "reader",
        "ai-on",
        "no-name",
        "no-topics",
        "not-checked",
        "loading",
        "unreachable",
        "no-sources",
        "nothing-followed",
      ]);
      expect(result.data.scenes[0].snapshot.viewer.name).toBe("Mara L");
      expect(result.data.scenes[3]?.snapshot.viewer.name).toBeNull();
    }
  });

  it("holds no AI digest card in the scene where AI is off (ruling 21), and one where it is on", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error("the fixture reads");
    const cards = (id: string) =>
      result.data.scenes.find((s) => s.id === id)?.snapshot.feed.digests ?? [];
    expect(cards("main").some((c) => c.ai)).toBe(false);
    expect(cards("ai-on").some((c) => c.ai)).toBe(true);
  });

  it.each([
    ["a scene with no id", ["id"], undefined, "scenes[2].id: expected a string"],
    [
      "a topic whose followed is a string",
      ["snapshot", "channels", "topics", 1, "followed"],
      "yes",
      "scenes[2].snapshot.channels.topics[1].followed: expected true or false",
    ],
    [
      "a topic with no keywords list",
      ["snapshot", "channels", "topics", 1, "keywords"],
      undefined,
      "scenes[2].snapshot.channels.topics[1].keywords: expected a list",
    ],
    [
      "a topic keyword that is a number",
      ["snapshot", "channels", "topics", 0, "keywords", 0],
      4,
      "scenes[2].snapshot.channels.topics[0].keywords[0]: expected a string",
    ],
    [
      "a feed with no sources record",
      ["snapshot", "feed", "sources"],
      undefined,
      "scenes[2].snapshot.feed.sources: expected an object",
    ],
    [
      "a feed whose approved is a string",
      ["snapshot", "feed", "sources", "approved"],
      "yes",
      "scenes[2].snapshot.feed.sources.approved: expected true or false",
    ],
    [
      "a viewer role outside the two",
      ["snapshot", "viewer", "role"],
      "admin",
      "scenes[2].snapshot.viewer.role: expected reader or writer",
    ],
    [
      "a feed error outside the three",
      ["snapshot", "feed", "error"],
      "boom",
      'scenes[2].snapshot.feed.error: expected null, "unreachable", "request" or "unreadable"',
    ],
    [
      "a feed status outside the two",
      ["snapshot", "feed", "status"],
      "idle",
      'scenes[2].snapshot.feed.status: expected "loading" or "ready"',
    ],
    [
      "a digest whose paused is missing",
      ["snapshot", "channels", "digests", 0, "paused"],
      undefined,
      "scenes[2].snapshot.channels.digests[0].paused: expected true or false",
    ],
    [
      "a group unread that is a number",
      ["snapshot", "channels", "groups", 0, "unread"],
      3,
      "scenes[2].snapshot.channels.groups[0].unread: expected a string or null",
    ],
    [
      "a saved count that is missing",
      ["snapshot", "channels", "savedCount"],
      undefined,
      "scenes[2].snapshot.channels.savedCount: expected a string or null",
    ],
    [
      "a view naming a story the feed does not hold",
      ["snapshot", "feed", "views", "latest", "top"],
      ["corvane", "ghost"],
      "scenes[2].snapshot.feed.views.latest.top[1]: expected the id of a story or digest in the feed",
    ],
    [
      "a channel topic with no order in the feed",
      ["snapshot", "feed", "topics"],
      { shipping: { top: [], latest: [], waiting: null, older: [] } },
      "scenes[2].snapshot.feed.topics.packaging: expected an order for this channel topic",
    ],
    [
      "an order for a topic the channel list lacks",
      ["snapshot", "feed", "topics", "ghost"],
      { top: [], latest: [], waiting: null, older: [] },
      "scenes[2].snapshot.feed.topics.ghost: expected the id of a channel topic",
    ],
    [
      "a topic order naming a story the feed does not hold",
      ["snapshot", "feed", "topics"],
      { shipping: { top: [], latest: ["ghost"], waiting: null, older: [] } },
      "scenes[2].snapshot.feed.topics.shipping.latest[0]: expected the id of a story or digest in the feed",
    ],
    [
      "a freshness state outside the four",
      ["snapshot", "feed", "freshness", "state"],
      "idle",
      'scenes[2].snapshot.feed.freshness.state: expected "checking", "checked", "not-checked" or "unavailable"',
    ],
    [
      "a freshness with no failing member",
      ["snapshot", "feed", "freshness", "failing"],
      undefined,
      "scenes[2].snapshot.feed.freshness.failing: expected a string or null",
    ],
    [
      "a freshness error that is a number",
      ["snapshot", "feed", "freshness", "error"],
      1,
      "scenes[2].snapshot.feed.freshness.error: expected a string or null",
    ],
    [
      "checked sources with no delivered time",
      ["snapshot", "feed", "freshness", "checked"],
      null,
      "scenes[2].snapshot.feed.freshness.checked: expected the delivered time when the state is checked",
    ],
    [
      "a waiting pill whose label is a number",
      ["snapshot", "feed", "views", "for-you", "waiting"],
      { label: 4, ids: [] },
      "scenes[2].snapshot.feed.views.for-you.waiting.label: expected a string",
    ],
    [
      "a waiting pill naming a story the feed does not hold",
      ["snapshot", "feed", "views", "for-you", "waiting"],
      { label: "1 new story", ids: ["ghost"] },
      "scenes[2].snapshot.feed.views.for-you.waiting.ids[0]: expected the id of a story or digest in the feed",
    ],
    [
      "a waiting pill naming an entry the view already lists",
      ["snapshot", "feed", "views", "for-you", "waiting"],
      { label: "1 new story", ids: ["corvane"] },
      "scenes[2].snapshot.feed.views.for-you.waiting.ids[0]: expected an id the view does not already list",
    ],
    [
      "an older list naming an entry the feed does not hold",
      ["snapshot", "feed", "views", "latest", "older"],
      ["ghost"],
      "scenes[2].snapshot.feed.views.latest.older[0]: expected the id of a story or digest in the feed",
    ],
    [
      "an older list naming an entry the view already lists",
      ["snapshot", "feed", "views", "for-you", "older"],
      ["corvane"],
      "scenes[2].snapshot.feed.views.for-you.older[0]: expected an id the view does not already list",
    ],
    [
      "a view with no older list",
      ["snapshot", "feed", "views", "saved", "older"],
      undefined,
      "scenes[2].snapshot.feed.views.saved.older: expected a list",
    ],
    [
      "a view with no waiting member",
      ["snapshot", "feed", "views", "saved", "waiting"],
      undefined,
      "scenes[2].snapshot.feed.views.saved.waiting: expected an object",
    ],
    [
      "a topic older list naming an entry the feed does not hold",
      ["snapshot", "feed", "topics", "shipping", "older"],
      ["ghost"],
      "scenes[2].snapshot.feed.topics.shipping.older[0]: expected the id of a story or digest in the feed",
    ],
    [
      "an id repeated inside top",
      ["snapshot", "feed", "views", "saved", "top"],
      ["halvorsen", "halvorsen"],
      "scenes[2].snapshot.feed.views.saved.top[1]: expected an id the list does not already hold",
    ],
    [
      "an id repeated inside latest",
      ["snapshot", "feed", "views", "saved", "latest"],
      ["halvorsen", "halvorsen"],
      "scenes[2].snapshot.feed.views.saved.latest[1]: expected an id the list does not already hold",
    ],
    [
      "a latest order holding an id top lacks",
      ["snapshot", "feed", "views", "latest"],
      { top: ["corvane"], latest: ["corvane", "tessaly"], waiting: null, older: [] },
      "scenes[2].snapshot.feed.views.latest.latest[1]: expected an id in the view's top",
    ],
    [
      "a top order holding an id latest lacks",
      ["snapshot", "feed", "views", "latest"],
      { top: ["corvane", "tessaly"], latest: ["corvane"], waiting: null, older: [] },
      "scenes[2].snapshot.feed.views.latest.top[1]: expected an id in the view's latest",
    ],
    [
      "an id repeated inside older",
      ["snapshot", "feed", "views", "latest"],
      { top: [], latest: [], waiting: null, older: ["tessaly", "tessaly"] },
      "scenes[2].snapshot.feed.views.latest.older[1]: expected an id the list does not already hold",
    ],
    [
      "an id repeated inside waiting",
      ["snapshot", "feed", "views", "latest"],
      {
        top: [],
        latest: [],
        waiting: { label: "2 new stories", ids: ["tessaly", "tessaly"] },
        older: [],
      },
      "scenes[2].snapshot.feed.views.latest.waiting.ids[1]: expected an id the list does not already hold",
    ],
    [
      "an id both waiting and older",
      ["snapshot", "feed", "views", "latest"],
      {
        top: [],
        latest: [],
        waiting: { label: "1 new story", ids: ["tessaly"] },
        older: ["tessaly"],
      },
      "scenes[2].snapshot.feed.views.latest.older[0]: expected an id the view does not already list",
    ],
    [
      "signal strength marks of 4",
      ["snapshot", "feed", "stories", 0, "strength", "marks"],
      4,
      "scenes[2].snapshot.feed.stories[0].strength.marks: expected 1, 2 or 3",
    ],
    [
      "a story kind outside the four",
      ["snapshot", "feed", "stories", 0, "kind"],
      "regulatory",
      "scenes[2].snapshot.feed.stories[0].kind: expected regulator, news, ratings or research",
    ],
    [
      "a story whose time is missing",
      ["snapshot", "feed", "stories", 1, "time"],
      undefined,
      "scenes[2].snapshot.feed.stories[1].time: expected a string or null",
    ],
    [
      "a story headline that is a number",
      ["snapshot", "feed", "stories", 0, "headline"],
      7,
      "scenes[2].snapshot.feed.stories[0].headline: expected a string",
    ],
    [
      "an also-in list holding a number",
      ["snapshot", "feed", "stories", 0, "alsoIn", "monograms"],
      ["CL", 4],
      "scenes[2].snapshot.feed.stories[0].alsoIn.monograms[1]: expected a string",
    ],
    [
      "a shared-by line with no initials",
      ["snapshot", "feed", "stories", 0, "sharedBy", "initials"],
      undefined,
      "scenes[2].snapshot.feed.stories[0].sharedBy.initials: expected a string",
    ],
    [
      "an AI line that is a list",
      ["snapshot", "feed", "stories", 0, "ai"],
      ["x"],
      "scenes[2].snapshot.feed.stories[0].ai: expected an object",
    ],
    [
      "a source with no monogram",
      ["snapshot", "feed", "stories", 0, "source", "monogram"],
      undefined,
      "scenes[2].snapshot.feed.stories[0].source.monogram: expected a string",
    ],
    [
      "a saved flag that is a string",
      ["snapshot", "feed", "stories", 0, "saved"],
      "yes",
      "scenes[2].snapshot.feed.stories[0].saved: expected true or false",
    ],
    [
      "a stage position that is a string",
      ["snapshot", "feed", "stories", 2, "stage", "position"],
      "0.75",
      "scenes[2].snapshot.feed.stories[2].stage.position: expected a number from 0 to 1",
    ],
    [
      "a stage position above 1",
      ["snapshot", "feed", "stories", 2, "stage", "position"],
      1.5,
      "scenes[2].snapshot.feed.stories[2].stage.position: expected a number from 0 to 1",
    ],
    [
      "a stage with no delivered label",
      ["snapshot", "feed", "stories", 2, "stage", "label"],
      undefined,
      "scenes[2].snapshot.feed.stories[2].stage.label: expected a string",
    ],
    [
      "a stage name whose current flag is a string",
      ["snapshot", "feed", "stories", 2, "stage", "stages", 1, "current"],
      "yes",
      "scenes[2].snapshot.feed.stories[2].stage.stages[1].current: expected true or false",
    ],
    [
      "a stage with no current step",
      ["snapshot", "feed", "stories", 2, "stage", "stages"],
      STAGES.map((name) => ({ name, current: false })),
      "scenes[2].snapshot.feed.stories[2].stage.stages: expected exactly one current step",
    ],
    [
      "a stage with two current steps",
      ["snapshot", "feed", "stories", 2, "stage", "stages"],
      STAGES.map((name, i) => ({ name, current: i < 2 })),
      "scenes[2].snapshot.feed.stories[2].stage.stages: expected exactly one current step",
    ],
    [
      "a rating move missing its to",
      ["snapshot", "feed", "stories", 3, "ratingMoves", 0, "to"],
      undefined,
      "scenes[2].snapshot.feed.stories[3].ratingMoves[0].to: expected a string",
    ],
    [
      "rating moves that are not a list",
      ["snapshot", "feed", "stories", 3, "ratingMoves"],
      "BB- to B+",
      "scenes[2].snapshot.feed.stories[3].ratingMoves: expected a list",
    ],
    [
      "a digest card whose unread is a string",
      ["snapshot", "feed", "digests", 0, "unread"],
      "yes",
      "scenes[2].snapshot.feed.digests[0].unread: expected true or false",
    ],
    [
      "a digest card whose points hold a number",
      ["snapshot", "feed", "digests", 0, "points"],
      ["One", 2],
      "scenes[2].snapshot.feed.digests[0].points[1]: expected a string",
    ],
    [
      "a nothing-to-report digest card that still has points",
      ["snapshot", "feed", "digests", 2, "points"],
      ["One"],
      "scenes[2].snapshot.feed.digests[2].points: expected no points on a nothing-to-report card",
    ],
    [
      "a nothing-to-report digest card marked AI",
      ["snapshot", "feed", "digests", 2, "ai"],
      true,
      "scenes[2].snapshot.feed.digests[2].ai: expected false on a nothing-to-report card",
    ],
    [
      "a digest card whose id a story already uses",
      ["snapshot", "feed", "digests", 1, "id"],
      "corvane",
      "scenes[2].snapshot.feed.digests[1].id: expected an id no story or digest already uses",
    ],
    [
      "a view naming neither a story nor a digest",
      ["snapshot", "feed", "views", "for-you", "top"],
      ["digest-ghost"],
      "scenes[2].snapshot.feed.views.for-you.top[0]: expected the id of a story or digest in the feed",
    ],
    [
      "tags that are not a list",
      ["snapshot", "feed", "stories", 0, "tags"],
      "Packaging",
      "scenes[2].snapshot.feed.stories[0].tags: expected a list",
    ],
  ] as [string, (string | number)[], Json | undefined, string][])(
    "is invalid for %s, naming the path",
    (_name, path, value, reason) => {
      expect(readSlice(withScene(path, value))).toEqual({ kind: "invalid", reason });
    },
  );

  it.each([
    [null, "slice: expected an object"],
    [{}, "scenes: expected a list"],
    [{ scenes: [] }, "scenes: expected at least one scene"],
    [{ scenes: [3] }, "scenes[0]: expected an object"],
  ])("is invalid for %j", (source, reason) => {
    expect(readSlice(source)).toEqual({ kind: "invalid", reason });
  });

  it("requires a scene called main, naming the path", () => {
    const copy = structuredClone(fixture.slice) as { scenes: { id: string }[] };
    for (const scene of copy.scenes) scene.id = `x-${scene.id}`;
    expect(readSlice(copy)).toEqual({
      kind: "invalid",
      reason: 'scenes: expected a scene with id "main"',
    });
  });
});

describe("a loading feed", () => {
  /** A copy of the fixture whose loading scene holds `change`d views (the story ids come from scene "unreachable"). */
  function loadingWith(change: (views: Record<string, Record<string, unknown>>) => void): unknown {
    const copy = structuredClone(fixture.slice);
    const loading = copy.scenes.find((s) => s.id === "loading");
    const stories = copy.scenes.find((s) => s.id === "unreachable")?.snapshot.feed.stories;
    if (loading === undefined || stories === undefined) throw new Error("the fixture's scenes");
    Object.assign(loading.snapshot.feed, { stories });
    change(loading.snapshot.feed.views);
    return copy;
  }

  it("is accepted by the fixture's loading scenes, which hold no entry", () => {
    expect(readSlice(fixture.slice).kind).toBe("ok");
  });

  it.each([
    ["top", ["corvane"], "top[0]"],
    ["latest", ["corvane"], "top[0]"],
    ["older", ["corvane"], "older[0]"],
    ["waiting", { label: "1 new story", ids: ["corvane"] }, "waiting.ids[0]"],
  ])("rejects an entry held in %s, with its path", (member, value, at) => {
    const result = readSlice(
      loadingWith((views) => {
        const view = views["for-you"];
        if (view === undefined) throw new Error("the loading scene has For you");
        view[member] = value;
        if (member === "top") view["latest"] = ["corvane"];
        if (member === "latest") view["top"] = ["corvane"];
      }),
    );
    expect(result).toEqual({
      kind: "invalid",
      reason: `scenes[6].snapshot.feed.views.for-you.${at}: expected no entries while the feed is loading`,
    });
  });

  it("rejects a waiting pill with a label and no ids while loading, with its path", () => {
    const result = readSlice(
      loadingWith((views) => {
        const view = views["for-you"];
        if (view === undefined) throw new Error("the loading scene has For you");
        view["waiting"] = { label: "3 new stories", ids: [] };
      }),
    );
    expect(result).toEqual({
      kind: "invalid",
      reason:
        "scenes[6].snapshot.feed.views.for-you.waiting: expected no new-story pill while the feed is loading",
    });
  });

  it("rejects an entry in a topic's order while loading", () => {
    const copy = structuredClone(fixture.slice);
    const scene = copy.scenes.find((s) => s.id === "no-name");
    const stories = copy.scenes.find((s) => s.id === "reader")?.snapshot.feed.stories;
    if (scene === undefined || stories === undefined) throw new Error("the fixture's scenes");
    Object.assign(scene.snapshot.feed, { stories });
    Object.assign(scene.snapshot.feed.topics["shipping"] ?? {}, {
      top: ["corvane"],
      latest: ["corvane"],
    });
    expect(readSlice(copy)).toEqual({
      kind: "invalid",
      reason:
        "scenes[3].snapshot.feed.topics.shipping.top[0]: expected no entries while the feed is loading",
    });
  });
});

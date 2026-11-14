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
      ]);
      expect(result.data.scenes[0].snapshot.viewer.name).toBe("Mara L");
      expect(result.data.scenes[3]?.snapshot.viewer.name).toBeNull();
    }
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
      "scenes[2].snapshot.feed.views.latest.top[1]: expected the id of a story in the feed",
    ],
    [
      "a channel topic with no order in the feed",
      ["snapshot", "feed", "topics"],
      { shipping: { top: [], latest: [] } },
      "scenes[2].snapshot.feed.topics.packaging: expected an order for this channel topic",
    ],
    [
      "an order for a topic the channel list lacks",
      ["snapshot", "feed", "topics", "ghost"],
      { top: [], latest: [] },
      "scenes[2].snapshot.feed.topics.ghost: expected the id of a channel topic",
    ],
    [
      "a topic order naming a story the feed does not hold",
      ["snapshot", "feed", "topics"],
      { shipping: { top: [], latest: ["ghost"] } },
      "scenes[2].snapshot.feed.topics.shipping.latest[0]: expected the id of a story in the feed",
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
});

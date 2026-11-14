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

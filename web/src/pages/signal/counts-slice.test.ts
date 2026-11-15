// Whole-branch finding M1: a delivered count beside a page that says there is nothing. A channel
// topic's count and its view agree on emptiness, and so do a group's unread badge and its threads.
// Only emptiness is compared; no list is counted. Expected paths and words come from the controller's
// ruling on M1, not from the reader.
import fixture from "../../../fixtures/signal.json";
import { readSlice } from "./slice";

type View = { top: string[]; latest: string[] };
type Scene = {
  id: string;
  snapshot: {
    feed: { status: string; topics: Record<string, View> };
    channels: {
      topics: { id: string; count: string | null }[];
      groups: { id: string; unread: string | null }[];
    };
    groups: { id: string; threads: unknown[] }[];
  };
};
const MAIN = "scenes[0].snapshot";

/** A copy of the fixture with one scene changed by `change`. */
function changed(id: string, change: (scene: Scene) => void): unknown {
  const copy = structuredClone(fixture.slice) as unknown as { scenes: Scene[] };
  const scene = copy.scenes.find((s) => s.id === id);
  if (scene === undefined) throw new Error(`the fixture has the scene ${id}`);
  change(scene);
  return copy;
}
const invalid = (reason: string) => ({ kind: "invalid", reason });
const at = <T>(items: T[], index: number): T => {
  const one = items[index];
  if (one === undefined) throw new Error(`the fixture list has an item ${String(index)}`);
  return one;
};
const view = (scene: Scene, id: string): View => {
  const one = scene.snapshot.feed.topics[id];
  if (one === undefined) throw new Error(`the scene has a view for ${id}`);
  return one;
};

describe("M1: a topic's count and its view", () => {
  it("refuses a count of 5 beside a view that lists no story", () => {
    const slice = changed("main", (scene) => {
      view(scene, "telecoms").top = [];
      view(scene, "telecoms").latest = [];
    });
    expect(readSlice(slice)).toEqual(
      invalid(
        `${MAIN}.channels.topics[2].count: expected null or "0" while the topic's view lists no stories`,
      ),
    );
  });

  it("refuses a count of 0 beside a view that lists stories", () => {
    const slice = changed("main", (scene) => {
      at(scene.snapshot.channels.topics, 0).count = "0";
    });
    expect(readSlice(slice)).toEqual(
      invalid(
        `${MAIN}.channels.topics[0].count: expected a count other than "0" while the topic's view lists stories`,
      ),
    );
  });

  it.each([null, "0"])("accepts a count of %s beside a view that lists no story", (count) => {
    const slice = changed("main", (scene) => {
      at(scene.snapshot.channels.topics, 1).count = count;
      view(scene, "packaging").top = [];
      view(scene, "packaging").latest = [];
    });
    expect(readSlice(slice).kind).toBe("ok");
  });

  it("does not compare a count while the feed is loading (a loading feed lists nothing)", () => {
    const slice = changed("no-name", (scene) => {
      expect(scene.snapshot.feed.status).toBe("loading");
      expect(at(scene.snapshot.channels.topics, 0).count).not.toBeNull();
    });
    expect(readSlice(slice).kind).toBe("ok");
  });
});

describe("M1: a group's unread badge and its threads", () => {
  it("refuses an unread of 3 beside a group that holds no thread", () => {
    const slice = changed("main", (scene) => {
      const held = scene.snapshot.groups.find((g) => g.id === "shipping-desk");
      expect(held?.threads).toEqual([]);
      at(scene.snapshot.channels.groups, 1).unread = "3";
    });
    expect(readSlice(slice)).toEqual(
      invalid(
        `${MAIN}.channels.groups[1].unread: expected null or "0" while the group holds no thread`,
      ),
    );
  });

  it.each([null, "0"])("accepts an unread of %s beside a group that holds no thread", (unread) => {
    const slice = changed("ai-on", (scene) => {
      at(scene.snapshot.channels.groups, 0).unread = unread;
    });
    expect(readSlice(slice).kind).toBe("ok");
  });
});

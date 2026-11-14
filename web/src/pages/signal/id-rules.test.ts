// Whole-branch findings L1, L2, L3, L5: records the reader used to accept and a page then drew as a
// contradiction, a dead link or a dropped value. Each has a malformed record naming its path; the
// fixture itself reads. Expected paths and words come from the controller's rulings, not the reader.
import fixture from "../../../fixtures/signal.json";
import { readSlice } from "./slice";

type Item = Record<string, unknown>;
type Scene = { id: string; snapshot: Record<string, unknown> };
const IDS = fixture.slice.scenes.map((s) => s.id);

/** A copy of the fixture with the scene `id` changed by `change`; `at` is its index, for paths. */
function changed(id: string, change: (scene: Scene) => void): unknown {
  const copy = structuredClone(fixture.slice) as unknown as { scenes: Scene[] };
  const scene = copy.scenes.find((s) => s.id === id);
  if (scene === undefined) throw new Error(`the fixture has the scene ${id}`);
  change(scene);
  return copy;
}
const at = (id: string) => `scenes[${String(IDS.indexOf(id))}]`;
const invalid = (reason: string) => ({ kind: "invalid", reason });

/** Walk a path of keys and indexes to the record that holds the last key, and set it. */
function set(root: unknown, path: (string | number)[], value: unknown): void {
  let node = root as Record<string | number, unknown>;
  for (const key of path.slice(0, -1)) node = node[key] as Record<string | number, unknown>;
  const last = path[path.length - 1];
  if (last === undefined) throw new Error("a path has a last key");
  node[last] = value;
}
const feedOf = (scene: Scene) => scene.snapshot["feed"] as { digests: Item[] };

describe("the fixture", () => {
  it("reads with every rule below in force", () => {
    expect(readSlice(fixture.slice).kind).toBe("ok");
  });
});

describe("L1: a feed digest card's points are model text", () => {
  it("refuses points on a card marked ai false", () => {
    const slice = changed("ai-on", (scene) => {
      const card = feedOf(scene).digests[0];
      if (card === undefined) throw new Error("ai-on has a digest card");
      card.ai = false;
    });
    expect(readSlice(slice)).toEqual(
      invalid(`${at("ai-on")}.snapshot.feed.digests[0].ai: expected true on a card with points`),
    );
  });
});

describe("L2: the Saved view and the stories marked saved", () => {
  it("refuses a Saved view that lists a story marked not saved", () => {
    const slice = changed("main", (scene) => {
      const stories = (scene.snapshot["feed"] as { stories: Item[] }).stories;
      const held = stories.find((s) => s["id"] === "halvorsen");
      if (held === undefined) throw new Error("main has the Halvorsen story");
      held["saved"] = false;
    });
    expect(readSlice(slice)).toEqual(
      invalid(
        `${at("main")}.snapshot.feed.views.saved.top[0]: expected the id of a story marked saved`,
      ),
    );
  });

  it("refuses a Saved view that lists a digest card, which is no story", () => {
    const slice = changed("ai-on", (scene) => {
      const saved = (
        scene.snapshot["feed"] as { views: { saved: { top: string[]; latest: string[] } } }
      ).views.saved;
      saved.top = ["weekly-brief"];
      saved.latest = ["weekly-brief"];
      (scene.snapshot["channels"] as { savedCount: string }).savedCount = "1";
    });
    expect(readSlice(slice)).toEqual(
      invalid(
        `${at("ai-on")}.snapshot.feed.views.saved.top[0]: expected the id of a story marked saved`,
      ),
    );
  });

  it("refuses a story marked saved while the Saved view lists nothing", () => {
    const slice = changed("reader", (scene) => {
      const first = (scene.snapshot["feed"] as { stories: Item[] }).stories[0];
      if (first === undefined) throw new Error("reader has a story");
      first["saved"] = true;
    });
    expect(readSlice(slice)).toEqual(
      invalid(
        `${at("reader")}.snapshot.feed.stories[0].saved: expected false while the Saved view lists nothing`,
      ),
    );
  });
});

describe("L3: an id is non-empty and fits an address", () => {
  const WHAT = "a non-empty id that an address can hold";
  // [scene, where the id stands in the scene, the reader's path inside the scene]
  const places: [string, string, (string | number)[]][] = [
    ["main", "story", ["snapshot", "feed", "stories", 0, "id"]],
    ["main", "channel topic", ["snapshot", "channels", "topics", 0, "id"]],
    ["main", "channel group", ["snapshot", "channels", "groups", 0, "id"]],
    ["main", "group", ["snapshot", "groups", 0, "id"]],
    ["main", "thread", ["snapshot", "groups", 0, "threads", 0, "id"]],
    ["main", "thread record", ["snapshot", "threads", 0, "id"]],
    [
      "main",
      "story's thread reference",
      ["snapshot", "feed", "stories", 0, "threadRef", "threadId"],
    ],
    ["ai-on", "digest", ["snapshot", "digests", 0, "id"]],
    ["ai-on", "digest issue", ["snapshot", "digests", 0, "issues", 0, "id"]],
    ["ai-on", "feed digest card", ["snapshot", "feed", "digests", 0, "id"]],
    ["ai-on", "channel digest", ["snapshot", "channels", "digests", 0, "id"]],
  ];
  const render = (path: (string | number)[]) =>
    path
      .reduce<string>(
        (text, key) => (typeof key === "number" ? `${text}[${String(key)}]` : `${text}.${key}`),
        "",
      )
      .slice(1);

  it.each(
    places.flatMap(([id, what, path]) => [
      [id, what, "", path] as const,
      [id, what, "\ud800", path] as const,
    ]),
  )("refuses the %s scene's %s id %j", (id, _what, bad, path) => {
    const slice = changed(id, (scene) => {
      set(scene, path, bad);
    });
    expect(readSlice(slice)).toEqual(invalid(`${at(id)}.${render(path)}: expected ${WHAT}`));
  });

  it("refuses a scene with an empty id, and a lone surrogate", () => {
    for (const bad of ["", "\udc00"]) {
      const slice = changed("reader", (scene) => {
        scene.id = bad;
      });
      expect(readSlice(slice)).toEqual(invalid(`${at("reader")}.id: expected ${WHAT}`));
    }
  });

  it("still accepts an id with a pair of surrogates (an emoji is a valid address)", () => {
    const slice = changed("reader", (scene) => {
      scene.id = "reader-\u{1f600}";
    });
    expect(readSlice(slice).kind).toBe("ok");
  });
});

describe("L5: records the reader accepted and the page dropped or contradicted", () => {
  it("refuses a new-stories pill that reveals no entry", () => {
    const slice = changed("reader", (scene) => {
      const views = (scene.snapshot["feed"] as { views: Record<string, { waiting: unknown }> })
        .views;
      const view = views["for-you"];
      if (view === undefined) throw new Error("reader has a For you view");
      view.waiting = { label: "4 new stories", ids: [] };
    });
    expect(readSlice(slice)).toEqual(
      invalid(
        `${at("reader")}.snapshot.feed.views.for-you.waiting.ids: expected at least one id for the new-stories pill`,
      ),
    );
  });

  it("refuses a feed digest card with neither points nor a nothing sentence", () => {
    const slice = changed("ai-on", (scene) => {
      const card = feedOf(scene).digests[0];
      if (card === undefined) throw new Error("ai-on has a digest card");
      card.points = [];
    });
    expect(readSlice(slice)).toEqual(
      invalid(
        `${at("ai-on")}.snapshot.feed.digests[0].points: expected points or a nothing-to-report sentence`,
      ),
    );
  });

  it.each(["checking", "not-checked", "unavailable"])(
    "refuses a checked time on the state %s, which never draws it",
    (state) => {
      const slice = changed("not-checked", (scene) => {
        const freshness = (scene.snapshot["feed"] as { freshness: Item }).freshness;
        freshness["state"] = state;
        freshness["checked"] = "6 min ago";
      });
      expect(readSlice(slice)).toEqual(
        invalid(
          `${at("not-checked")}.snapshot.feed.freshness.checked: expected null unless the state is checked`,
        ),
      );
    },
  );

  it("refuses a feed digest card whose title is not its issue's title", () => {
    const slice = changed("ai-on", (scene) => {
      const card = feedOf(scene).digests[0];
      if (card === undefined) throw new Error("ai-on has a digest card");
      card.title = "Another title";
    });
    expect(readSlice(slice)).toEqual(
      invalid(
        `${at("ai-on")}.snapshot.feed.digests[0].title: expected the title of the issue the card names`,
      ),
    );
  });
});

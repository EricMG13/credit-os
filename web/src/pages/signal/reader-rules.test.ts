// Reader rules the sweep confirmed missing (register rows S2, S3, S4, S6, S7): each has a malformed
// record naming its path, and the fixture itself reads. Expected paths and words come from the
// register's rulings, not from the reader.
import fixture from "../../../fixtures/signal.json";
import { readSlice } from "./slice";

type Item = Record<string, unknown>;
/** The parts of a scene these tests change, loosely typed: a malformed record is the point. */
type Scene = {
  id: string;
  snapshot: {
    feed: { stories: Item[]; digests: Item[] };
    channels: {
      topics: { keywords: string[] }[];
      groups: Item[];
      digests: Item[];
      savedCount: string | null;
    };
  };
};
type Loose = { scenes: Scene[] };
const loose = (): Loose => structuredClone(fixture.slice);

/** A copy of the fixture whose scene `id` (default "main") is changed by `change`. */
function changed(change: (scene: Scene) => void, id = "main"): unknown {
  const copy = loose();
  const index = copy.scenes.findIndex((s) => s.id === id);
  const scene = copy.scenes[index];
  if (scene === undefined) throw new Error(`the fixture has the scene ${id}`);
  change(scene);
  return copy;
}
const invalid = (reason: string) => ({ kind: "invalid", reason });
const first = <T>(items: T[]): T => {
  const one = items[0];
  if (one === undefined) throw new Error("the fixture list has a first item");
  return one;
};
const MAIN = "scenes[0].snapshot";

describe("the fixture", () => {
  it("reads with every rule below in force", () => {
    expect(readSlice(fixture.slice).kind).toBe("ok");
  });
});

describe("S2: ids used once", () => {
  it("refuses two feed stories with one id", () => {
    const slice = changed((scene) => {
      const { stories } = scene.snapshot.feed;
      stories.push({ ...structuredClone(first(stories)), headline: "A second story, same id" });
    });
    expect(readSlice(slice)).toEqual(
      invalid(`${MAIN}.feed.stories[10].id: expected an id no other story uses`),
    );
  });

  it("refuses two scenes with one id", () => {
    const slice = loose();
    const reader = slice.scenes.find((s) => s.id === "reader");
    if (reader === undefined) throw new Error("the fixture has a reader scene");
    slice.scenes.push(structuredClone(reader));
    expect(readSlice(slice)).toEqual(
      invalid(`scenes[${String(slice.scenes.length - 1)}].id: expected an id no other scene uses`),
    );
  });

  it.each(["topics", "groups", "digests"] as const)("refuses a channel %s listed twice", (list) => {
    const slice = changed((scene) => {
      const held: unknown[] = scene.snapshot.channels[list];
      held.push(structuredClone(first(held)));
    });
    const reason = readSlice(slice);
    expect(reason).toEqual(
      invalid(
        `${MAIN}.channels.${list}[${String(fixture.slice.scenes[0]?.snapshot.channels[list].length)}].id: expected an id the list does not repeat`,
      ),
    );
  });
});

describe("S3: a topic's keywords are one fact", () => {
  it("refuses a channel topic whose keywords differ from the same topic's in Settings", () => {
    const slice = changed((scene) => {
      first(scene.snapshot.channels.topics).keywords = ["charter rates"];
    });
    expect(readSlice(slice)).toEqual(
      invalid(
        `${MAIN}.settings.topics[0].keywords: expected the keywords the channel list gives this topic, in order`,
      ),
    );
  });

  it("refuses the same keywords in another order", () => {
    const slice = changed((scene) => {
      first(scene.snapshot.channels.topics).keywords.reverse();
    });
    expect(readSlice(slice).kind).toBe("invalid");
  });
});

describe("S4: the Saved badge and the Saved view", () => {
  it("refuses a badge of 6 beside an empty Saved view", () => {
    const slice = changed((scene) => {
      scene.snapshot.channels.savedCount = "6";
    }, "reader");
    expect(readSlice(slice)).toEqual(
      invalid(
        'scenes[1].snapshot.channels.savedCount: expected null or "0" while the Saved view lists no stories',
      ),
    );
  });

  it.each([null, "0"])("refuses a badge of %s beside a Saved view that lists stories", (count) => {
    const slice = changed((scene) => {
      scene.snapshot.channels.savedCount = count;
    });
    expect(readSlice(slice)).toEqual(
      invalid(
        `${MAIN}.channels.savedCount: expected the delivered count while the Saved view lists stories`,
      ),
    );
  });
});

describe("S6: a comment count needs a thread", () => {
  it("refuses a comment count on a story with no thread", () => {
    const slice = changed((scene) => {
      const story = scene.snapshot.feed.stories.find((s) => s.threadRef === null);
      if (story === undefined) throw new Error("main has a story with no thread");
      story.commentCount = "2";
    });
    expect(readSlice(slice)).toEqual(
      invalid(
        `${MAIN}.feed.stories[1].commentCount: expected null on a story with no thread to open`,
      ),
    );
  });
});

describe("S7: a value the page never draws", () => {
  it("refuses an unread mark on a paused channel digest", () => {
    const slice = changed((scene) => {
      first(scene.snapshot.channels.digests).unread = true;
    });
    expect(readSlice(slice)).toEqual(
      invalid(`${MAIN}.channels.digests[0].unread: expected false on a paused digest`),
    );
  });

  it("refuses a summary on a nothing-to-report card", () => {
    const slice = changed((scene) => {
      const card = scene.snapshot.feed.digests.find((c) => c.nothing !== null);
      if (card === undefined) throw new Error("ai-on has a nothing-to-report card");
      card.summary = "A summary the card never draws.";
    }, "ai-on");
    expect(readSlice(slice)).toEqual(
      invalid(
        "scenes[2].snapshot.feed.digests[2].summary: expected null on a nothing-to-report card",
      ),
    );
  });
});

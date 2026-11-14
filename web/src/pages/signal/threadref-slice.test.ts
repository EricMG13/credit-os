// A story's thread reference: it names a thread of the snapshot that is about this very story.
import fixture from "../../../fixtures/signal.json";
import { readSlice } from "./slice";

type Scene = (typeof fixture.slice.scenes)[number];
type Story = Scene["snapshot"]["feed"]["stories"][number];

/** A copy of the fixture whose "main" scene (index 0) is changed by `change`. */
function withMain(change: (scene: Scene) => void): unknown {
  const copy = structuredClone(fixture.slice);
  const main = copy.scenes[0];
  if (main === undefined) throw new Error("the fixture has a first scene");
  change(main);
  return copy;
}
const story = (scene: Scene, id: string): Story => {
  const one = scene.snapshot.feed.stories.find((s) => s.id === id);
  if (one === undefined) throw new Error(`main has the story ${id}`);
  return one;
};
const invalid = (reason: string) => ({ kind: "invalid", reason });
const AT = "scenes[0].snapshot.feed.stories";
const NAMED = "expected a thread of this story in the snapshot's threads";

describe("a story's threadRef", () => {
  it("reads as the fixture holds it: Corvane has a thread, Pellant has none", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error("the fixture reads");
    const { stories } = result.data.scenes[0].snapshot.feed;
    expect(stories.find((s) => s.id === "corvane")?.threadRef).toEqual({
      groupId: "leveraged-credit",
      threadId: "corvane-thread",
    });
    expect(stories.find((s) => s.id === "tessaly")?.threadRef).toBeNull();
  });

  it("rejects a threadRef naming a thread the snapshot does not hold, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        Object.assign(story(scene, "corvane"), {
          threadRef: { groupId: "leveraged-credit", threadId: "no-such-thread" },
        });
      }),
    );
    expect(result).toEqual(invalid(`${AT}[0].threadRef: ${NAMED}`));
  });

  it("rejects a threadRef naming a group the snapshot does not hold", () => {
    const result = readSlice(
      withMain((scene) => {
        Object.assign(story(scene, "corvane"), {
          threadRef: { groupId: "no-such-group", threadId: "corvane-thread" },
        });
      }),
    );
    expect(result).toEqual(invalid(`${AT}[0].threadRef: ${NAMED}`));
  });

  it("rejects a threadRef naming a thread that is about another story", () => {
    const result = readSlice(
      withMain((scene) => {
        Object.assign(story(scene, "corvane"), {
          threadRef: { groupId: "leveraged-credit", threadId: "halvorsen-thread" },
        });
      }),
    );
    expect(result).toEqual(invalid(`${AT}[0].threadRef: ${NAMED}`));
  });

  it("rejects a threadRef naming a thread that holds no story (a note)", () => {
    const result = readSlice(
      withMain((scene) => {
        Object.assign(story(scene, "corvane"), {
          threadRef: { groupId: "leveraged-credit", threadId: "packaging-note" },
        });
      }),
    );
    expect(result).toEqual(invalid(`${AT}[0].threadRef: ${NAMED}`));
  });

  it.each([
    ["a string", "corvane-thread", "threadRef: expected an object"],
    [
      "an id that is a number",
      { groupId: "leveraged-credit", threadId: 4 },
      "threadRef.threadId: expected a string",
    ],
    ["no group id", { threadId: "corvane-thread" }, "threadRef.groupId: expected a string"],
  ])("rejects a threadRef that is %s, with its path", (_what, value, words) => {
    const result = readSlice(
      withMain((scene) => {
        Object.assign(story(scene, "corvane"), { threadRef: value });
      }),
    );
    expect(result).toEqual(invalid(`${AT}[0].${words}`));
  });

  it("rejects a story with no threadRef member", () => {
    const result = readSlice(
      withMain((scene) => {
        Reflect.deleteProperty(story(scene, "corvane"), "threadRef");
      }),
    );
    expect(result.kind).toBe("invalid");
    expect(JSON.stringify(result)).toContain("threadRef");
  });

  it("looks threads up by value: ids such as constructor are no special case", () => {
    const result = readSlice(
      withMain((scene) => {
        Object.assign(story(scene, "corvane"), {
          threadRef: { groupId: "constructor", threadId: "__proto__" },
        });
      }),
    );
    expect(result).toEqual(invalid(`${AT}[0].threadRef: ${NAMED}`));
  });
});

// The reader's rules for groups, their threads, and the viewer's name and initials.
import fixture from "../../../fixtures/signal.json";
import { readSlice } from "./slice";

type Scene = (typeof fixture.slice.scenes)[number];

/** A copy of the fixture whose "main" scene (index 0) is changed by `change`. */
function withMain(change: (scene: Scene) => void): unknown {
  const copy = structuredClone(fixture.slice);
  const main = copy.scenes[0];
  if (main === undefined) throw new Error("the fixture has a first scene");
  change(main);
  return copy;
}

const lev = (scene: Scene) => {
  const one = scene.snapshot.groups[0];
  if (one === undefined) throw new Error("main has a first group");
  return one;
};
const thread = (scene: Scene, index: number) => {
  const one = lev(scene).threads[index];
  if (one === undefined) throw new Error("the first group has that thread");
  return one;
};
const invalid = (reason: string) => ({ kind: "invalid", reason });

describe("the groups in a snapshot", () => {
  it("reads the fixture's groups, threads and members", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error("the fixture reads");
    const main = result.data.scenes[0].snapshot.groups[0];
    expect(main?.name).toBe("Leveraged credit");
    expect(main?.threads.map((t) => t.id)).toEqual([
      "corvane-thread",
      "packaging-note",
      "halvorsen-thread",
      "brightwell-thread",
    ]);
  });

  it("rejects a thread naming a story the feed does not hold, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        thread(scene, 0).storyId = "no-such-story";
      }),
    );
    expect(result).toEqual(
      invalid(
        "scenes[0].snapshot.groups[0].threads[0].storyId: expected the id of a story in the feed",
      ),
    );
  });

  it("rejects a thread with neither a story nor a note, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        Object.assign(thread(scene, 1), { note: null });
      }),
    );
    expect(result).toEqual(
      invalid(
        "scenes[0].snapshot.groups[0].threads[1].note: expected a note when the thread names no story",
      ),
    );
  });

  it.each([
    ["unread", "yes", "expected true or false"],
    ["archived", 1, "expected true or false"],
    ["lastActivity", 5, "expected a string or null"],
    ["commentCount", 3, "expected a string or null"],
    ["sharedBy", "Tobias", "expected an object"],
  ])("rejects a thread whose %s is malformed, with its path", (member, value, words) => {
    const result = readSlice(
      withMain((scene) => {
        Object.assign(thread(scene, 0), { [member]: value });
      }),
    );
    expect(result).toEqual(invalid(`scenes[0].snapshot.groups[0].threads[0].${member}: ${words}`));
  });

  it("rejects a thread with no unread member, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        Reflect.deleteProperty(thread(scene, 2), "unread");
      }),
    );
    expect(result).toEqual(
      invalid("scenes[0].snapshot.groups[0].threads[2].unread: expected true or false"),
    );
  });

  it("rejects a thread id the group already uses, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        thread(scene, 1).id = "corvane-thread";
      }),
    );
    expect(result).toEqual(
      invalid(
        "scenes[0].snapshot.groups[0].threads[1].id: expected an id the group does not already use",
      ),
    );
  });

  it("rejects a malformed member, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        Object.assign(lev(scene).members[0] ?? {}, { initials: 4 });
      }),
    );
    expect(result).toEqual(
      invalid("scenes[0].snapshot.groups[0].members[0].initials: expected a string"),
    );
  });

  it("rejects a channel group that no group answers, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        scene.snapshot.groups.pop();
      }),
    );
    expect(result).toEqual(
      invalid(
        "scenes[0].snapshot.channels.groups[1].id: expected the id of a group in the snapshot's groups",
      ),
    );
  });

  it("rejects a group that the channel list does not name, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        scene.snapshot.channels.groups.pop();
      }),
    );
    expect(result).toEqual(
      invalid("scenes[0].snapshot.groups[1].id: expected the id of a group in the channel list"),
    );
  });

  it("rejects a +N with no members listed, with its path (probe task-7-dropped, test 1)", () => {
    const result = readSlice(
      withMain((scene) => {
        Object.assign(lev(scene), { members: [], moreMembers: "+6" });
      }),
    );
    expect(result).toEqual(
      invalid(
        "scenes[0].snapshot.groups[0].moreMembers: expected null when the group lists no members",
      ),
    );
  });

  it("rejects a group whose name differs from its channel's, with its path (probe test 2)", () => {
    const result = readSlice(
      withMain((scene) => {
        lev(scene).name = "Distressed desk";
      }),
    );
    expect(result).toEqual(
      invalid(
        "scenes[0].snapshot.groups[0].name: expected the name the channel list gives this group",
      ),
    );
  });

  it("rejects two groups with the same id, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        const second = scene.snapshot.groups[1];
        if (second === undefined) throw new Error("main has a second group");
        second.id = "leveraged-credit";
      }),
    );
    expect(result).toEqual(
      invalid("scenes[0].snapshot.groups[1].id: expected an id no other group uses"),
    );
  });

  it("rejects a snapshot with no groups member, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        Reflect.deleteProperty(scene.snapshot, "groups");
      }),
    );
    expect(result).toEqual(invalid("scenes[0].snapshot.groups: expected a list"));
  });
});

describe("the viewer's name and initials", () => {
  it("rejects a name with null initials, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        Object.assign(scene.snapshot.viewer, { initials: null });
      }),
    );
    expect(result).toEqual(
      invalid(
        "scenes[0].snapshot.viewer.initials: expected initials when the viewer has a name, and null when there is none",
      ),
    );
  });

  it("rejects initials with a null name, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        Object.assign(scene.snapshot.viewer, { name: null });
      }),
    );
    expect(result).toEqual(
      invalid(
        "scenes[0].snapshot.viewer.initials: expected initials when the viewer has a name, and null when there is none",
      ),
    );
  });

  it("accepts a viewer with neither (the no-name scene)", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error("the fixture reads");
    expect(result.data.scenes[3]?.snapshot.viewer).toMatchObject({ name: null, initials: null });
  });
});

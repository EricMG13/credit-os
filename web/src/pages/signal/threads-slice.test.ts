// The reader's rules for threads and their comments (mock frames "Thread panel" and "Thread archived").
import fixture from "../../../fixtures/signal.json";
import { readSlice, type SignalThread } from "./slice";

type Scene = (typeof fixture.slice.scenes)[number];

/** A copy of the fixture whose "main" scene (index 0) is changed by `change`. */
function withMain(change: (scene: Scene) => void): unknown {
  const copy = structuredClone(fixture.slice);
  const main = copy.scenes[0];
  if (main === undefined) throw new Error("the fixture has a first scene");
  change(main);
  return copy;
}

/** The scene's threads; the fixture's empty lists in other scenes type as never[], so the type is stated. */
const threadsOf = (scene: Scene) => scene.snapshot.threads as SignalThread[];
const thread = (scene: Scene, index: number) => {
  const one = threadsOf(scene)[index];
  if (one === undefined) throw new Error("main has that thread");
  return one;
};
/** Comment `index` of thread 0 (the Corvane thread: Tobias O, Jonas W, then the viewer's own). */
const comment = (scene: Scene, index: number) => {
  const one = thread(scene, 0).comments[index];
  if (one === undefined) throw new Error("the first thread has that comment");
  return one;
};
const invalid = (reason: string) => ({ kind: "invalid", reason });
const AT = "scenes[0].snapshot.threads[0]";

describe("the threads in a snapshot", () => {
  it("reads the fixture's threads and their comments as the mock frames draw them", () => {
    const result = readSlice(fixture.slice);
    if (result.kind !== "ok") throw new Error("the fixture reads");
    const { threads } = result.data.scenes[0].snapshot;
    expect(threads.map((t) => t.id)).toEqual([
      "corvane-thread",
      "packaging-note",
      "halvorsen-thread",
      "brightwell-thread",
    ]);
    const [corvane, , , archived] = threads;
    expect(corvane?.subline).toBe("Leveraged credit, 4 comments");
    expect(corvane?.comments.map((c) => c.author.name)).toEqual(["Tobias O", "Jonas W", "Mara L"]);
    expect(corvane?.comments[0]?.replies.map((c) => c.author.name)).toEqual(["Ines K"]);
    expect(archived?.archivedLine).toBe("Archived on 2 Nov 2026");
    expect(result.data.scenes[1]?.snapshot.threads.map((t) => t.id)).toEqual(["corvane-thread"]);
  });

  it("rejects a reply that has replies, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        const reply = comment(scene, 0).replies[0];
        if (reply === undefined) throw new Error("the first comment has a reply");
        const deeper = structuredClone(reply);
        deeper.id = "c9";
        reply.replies.push(deeper);
      }),
    );
    expect(result).toEqual(
      invalid(`${AT}.comments[0].replies[0].replies: expected no replies on a reply`),
    );
  });

  it("rejects a removed comment that still has text, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        Object.assign(comment(scene, 1), { text: "Still here" });
      }),
    );
    expect(result).toEqual(invalid(`${AT}.comments[1].text: expected null on a removed comment`));
  });

  it("rejects a removed comment that still has reactions, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        comment(scene, 1).reactions.push({ word: "Agree", count: "1", mine: false });
      }),
    );
    expect(result).toEqual(
      invalid(`${AT}.comments[1].reactions: expected no reactions on a removed comment`),
    );
  });

  it("rejects a comment that is not removed and has no text, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        Object.assign(comment(scene, 0), { text: null });
      }),
    );
    expect(result).toEqual(
      invalid(
        `${AT}.comments[0].text: expected the comment's text (only a removed comment has none)`,
      ),
    );
  });

  it("rejects a reaction word outside Agree, Disagree and Seen (the mock's Important), with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        Object.assign(comment(scene, 0).reactions[1] ?? {}, { word: "Important" });
      }),
    );
    expect(result).toEqual(
      invalid(`${AT}.comments[0].reactions[1].word: expected "Agree", "Disagree" or "Seen"`),
    );
  });

  it("rejects a reaction word used twice in one comment, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        comment(scene, 0).reactions.push({ word: "Agree", count: "4", mine: false });
      }),
    );
    expect(result).toEqual(
      invalid(
        `${AT}.comments[0].reactions[2].word: expected a word the comment does not already hold`,
      ),
    );
  });

  it("rejects a reply that reuses its parent's id, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        const reply = comment(scene, 0).replies[0];
        if (reply === undefined) throw new Error("the first comment has a reply");
        reply.id = comment(scene, 0).id;
      }),
    );
    expect(result).toEqual(
      invalid(`${AT}.comments[0].replies[0].id: expected an id the thread does not already use`),
    );
  });

  it("rejects an archived line on a thread that is not archived, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        Object.assign(thread(scene, 0), { archivedLine: "Archived on 2 Nov 2026" });
      }),
    );
    expect(result).toEqual(
      invalid(`${AT}.archivedLine: expected null when the thread is not archived`),
    );
  });

  it("rejects an archived thread with no archived line, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        const archived = thread(scene, 3);
        archived.archivedLine = null;
      }),
    );
    expect(result).toEqual(
      invalid(
        "scenes[0].snapshot.threads[3].archivedLine: expected the delivered line when the thread is archived",
      ),
    );
  });

  it("rejects a snapshot with no threads member, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        Reflect.deleteProperty(scene.snapshot, "threads");
      }),
    );
    expect(result).toEqual(invalid("scenes[0].snapshot.threads: expected a list"));
  });
});

describe("a group's items and the threads, in both directions", () => {
  it("rejects a group item whose thread does not exist, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        threadsOf(scene).splice(1, 1);
      }),
    );
    expect(result).toEqual(
      invalid(
        "scenes[0].snapshot.groups[0].threads[1].id: expected the id of a thread in the snapshot's threads",
      ),
    );
  });

  it("rejects a thread no group item names, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        const extra = structuredClone(thread(scene, 0));
        extra.id = "orphan";
        threadsOf(scene).push(extra);
      }),
    );
    expect(result).toEqual(
      invalid(
        "scenes[0].snapshot.threads[4].id: expected the id of an item in its group's threads",
      ),
    );
  });

  it("rejects a thread whose group has no such item even when another group has that id", () => {
    const result = readSlice(
      withMain((scene) => {
        thread(scene, 0).groupId = "shipping-desk";
      }),
    );
    expect(result).toEqual(
      invalid(
        "scenes[0].snapshot.groups[0].threads[0].id: expected the id of a thread in the snapshot's threads",
      ),
    );
  });

  it("rejects two threads with the same group and id, with its path", () => {
    const result = readSlice(
      withMain((scene) => {
        threadsOf(scene).push(structuredClone(thread(scene, 0)));
      }),
    );
    expect(result).toEqual(
      invalid("scenes[0].snapshot.threads[4].id: expected an id no other thread in its group uses"),
    );
  });

  it.each([
    ["storyId", (t: SignalThread) => Object.assign(t, { storyId: "tessaly" })],
    ["note", (t: SignalThread) => Object.assign(t, { note: "Different" })],
    ["archived", (t: SignalThread) => Object.assign(t, { archived: true, archivedLine: "x" })],
  ])("rejects a thread whose %s differs from its group item's, with its path", (member, change) => {
    const result = readSlice(
      withMain((scene) => {
        change(thread(scene, 0));
      }),
    );
    expect(result).toEqual(
      invalid(
        `scenes[0].snapshot.groups[0].threads[0].${member}: expected the ${member} the thread itself holds`,
      ),
    );
  });

  it("reads a thread whose id is __proto__ or constructor like any other id", () => {
    const result = readSlice(
      withMain((scene) => {
        thread(scene, 0).id = "__proto__";
        thread(scene, 1).id = "constructor";
        const items = scene.snapshot.groups[0]?.threads ?? [];
        if (items[0] === undefined || items[1] === undefined) throw new Error("two items");
        items[0].id = "__proto__";
        items[1].id = "constructor";
      }),
    );
    expect(result.kind).toBe("ok");
  });
});

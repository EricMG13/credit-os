// The thread panel (mock frames "Thread panel" and "Thread archived"; behaviour list 2.9; ruling 19, 20).
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import fixture from "../../../fixtures/signal.json";
import { App } from "../../App";
import type { LoadResult } from "../../data";

function show(hash: string, slice: unknown = fixture.slice) {
  window.location.hash = `#${hash}`;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], signal: slice },
  };
  return render(<App result={result} />);
}

const GROUP = "/signal/main/group/leveraged-credit";
const CORVANE_PATH = `${GROUP}/thread/corvane-thread`;
const CORVANE = "Corvane Packaging to close two plants as volumes fall";
const BRIGHTWELL = "Authority clears Brightwell Foods' dairy purchase with conditions";

const panel = () => screen.getByRole("dialog", { name: "Thread" });
const box = () => within(panel()).getByRole("textbox", { name: "Write a comment" });
const type = (value: string) => fireEvent.change(box(), { target: { value } });
const send = () => fireEvent.click(within(panel()).getByRole("button", { name: "Send" }));

/** Lets the animation frames after a close run, where the dialog library restores focus by itself. */
const settled = () =>
  act(async () => {
    for (let i = 0; i < 5; i += 1) {
      await new Promise((resolve) => requestAnimationFrame(resolve));
    }
    await new Promise((resolve) => setTimeout(resolve, 50));
  });

/** A copy of the fixture whose "main" scene is changed by `change`. */
function withMain(change: (main: (typeof fixture.slice.scenes)[number]) => void) {
  const copy = structuredClone(fixture.slice);
  const main = copy.scenes[0];
  if (main === undefined) throw new Error("the fixture has a first scene");
  change(main);
  return copy;
}

describe("the thread panel", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("opens over the group view as a dialog named Thread, with the group's name still the one h1", () => {
    show(CORVANE_PATH);
    expect(panel()).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1, hidden: true })).toHaveLength(1);
    expect(
      screen.getByRole("heading", { level: 1, name: "Leveraged credit", hidden: true }),
    ).toBeInTheDocument();
    expect(within(panel()).getByRole("heading", { level: 2, name: "Thread" })).toBeInTheDocument();
    expect(within(panel()).getByText("Leveraged credit, 4 comments")).toBeInTheDocument();
    expect(
      within(panel())
        .getAllByRole("heading")
        .map((h) => h.tagName),
    ).toEqual(["H2", "H3"]);
  });

  it("draws the overlay lighter than the kit's (ruling 20)", () => {
    show(CORVANE_PATH);
    const overlay = panel().closest("[class*='bg-overlay']");
    expect(overlay?.className).toContain("bg-overlay/30");
    expect(overlay?.className).not.toContain("bg-overlay/70");
  });

  it("quotes the story with its kind, source and time, and links to the source", () => {
    show(CORVANE_PATH);
    const top = within(panel());
    const headline = top.getByRole("heading", { level: 3, name: CORVANE });
    expect(within(headline).getByRole("link")).toHaveAttribute(
      "href",
      "https://example.com/corvane",
    );
    expect(top.getByText("News")).toBeInTheDocument();
    expect(top.getByText("Harbour Wire")).toBeInTheDocument();
    expect(top.getByText("2 h ago")).toBeInTheDocument();
    expect(
      top.getByRole("link", { name: `Open source: ${CORVANE} (opens in a new tab)` }),
    ).toHaveAttribute("href", "https://example.com/corvane");
  });

  it("draws a story with no address as plain text with no source link", () => {
    const slice = withMain((main) => {
      const story = main.snapshot.feed.stories.find((s) => s.id === "corvane");
      if (story === undefined) throw new Error("main has the Corvane story");
      Object.assign(story, { url: null });
    });
    show(CORVANE_PATH, slice);
    expect(within(panel()).getByRole("heading", { level: 3, name: CORVANE })).toBeInTheDocument();
    expect(within(panel()).queryByRole("link", { name: /Open source/ })).toBeNull();
    expect(within(panel()).queryByRole("link")).toBeNull();
  });

  it("draws a note thread's note in place of a story", () => {
    show(`${GROUP}/thread/packaging-note`);
    expect(
      within(panel()).getByText(
        "Has anyone looked at how the packaging closures read across to the two issuers we hold? Worth a slot on Thursday.",
      ),
    ).toBeInTheDocument();
    expect(within(panel()).queryByRole("heading", { level: 3 })).toBeNull();
    expect(within(panel()).getAllByRole("listitem").length).toBeGreaterThan(0);
  });

  it("lists the comments as the frame draws them: reply indented, edited, removed, own", () => {
    show(CORVANE_PATH);
    const comments = within(panel()).getByRole("list", { name: "Comments" });
    const names = within(comments)
      .getAllByRole("article")
      .map((a) => within(a).getAllByText(/^(Tobias O|Ines K|Jonas W|You)$/)[0]?.textContent);
    expect(names).toEqual(["Tobias O", "Ines K", "Jonas W", "You"]);
    const replies = within(comments).getByRole("list", { name: "Replies to Tobias O" });
    expect(
      within(replies).getByText("Agreed. Their covenant test date is the thing to check."),
    ).toBeInTheDocument();
    expect(within(replies).getByText("10:15, edited")).toBeInTheDocument();
    expect(
      within(replies).getByText(
        "Sharing for Thursday. The charge is larger than the saving in year one.",
        { selector: "blockquote" },
      ),
    ).toBeInTheDocument();
    expect(
      within(comments).getByText("This comment was removed by its author."),
    ).toBeInTheDocument();
    expect(within(comments).getByText("10:02")).toBeInTheDocument();
    expect(within(comments).getByText("10:40")).toBeInTheDocument();
    expect(within(comments).queryByText("Mara L")).toBeNull();
  });

  it("names each reaction with its word, delivered count and author, on every comment that is not removed", () => {
    show(CORVANE_PATH);
    const names = within(panel())
      .getAllByRole("button", { name: /^(Agree|Disagree|Seen)/ })
      .map((b) => b.getAttribute("aria-label"));
    expect(names).toEqual([
      "Agree, 2: comment by Tobias O",
      "Disagree: comment by Tobias O",
      "Seen, 1: comment by Tobias O",
      "Agree: comment by Ines K",
      "Disagree: comment by Ines K",
      "Seen: comment by Ines K",
      "Agree: comment by You",
      "Disagree: comment by You",
      "Seen, 3: comment by You",
    ]);
    expect(within(panel()).queryByRole("button", { name: /Jonas W/ })).toBeNull();
    expect(within(panel()).queryByText(/Important/)).toBeNull();
  });

  it("toggles a reaction in memory from the delivered state, never recounting", () => {
    show(CORVANE_PATH);
    const agree = () =>
      within(panel()).getByRole("button", { name: /^Agree, 2: comment by Tobias O/ });
    expect(agree()).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(agree());
    expect(agree()).toHaveAttribute("aria-pressed", "true");
    expect(agree()).toHaveTextContent(/^Agree 2$/);
    fireEvent.click(agree());
    expect(agree()).toHaveAttribute("aria-pressed", "false");
    const disagree = within(panel()).getByRole("button", { name: "Disagree: comment by Tobias O" });
    fireEvent.click(disagree);
    expect(disagree).toHaveAttribute("aria-pressed", "true");
    expect(disagree).toHaveTextContent(/^Disagree$/);
    const seen = within(panel()).getByRole("button", { name: "Seen, 3: comment by You" });
    expect(seen).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(seen);
    expect(seen).toHaveAttribute("aria-pressed", "false");
    expect(seen).toHaveTextContent(/^Seen 3$/);
  });

  it("lets a writer post: the comment is the viewer's own, has no time, the box clears and keeps focus", () => {
    show(CORVANE_PATH);
    expect(box()).toHaveAttribute("placeholder", "Write a comment");
    type("  Checked the filing.  ");
    send();
    const comments = within(panel()).getByRole("list", { name: "Comments" });
    const mine = within(comments).getAllByRole("article").at(-1);
    if (mine === undefined) throw new Error("the list has comments");
    expect(within(mine).getByText("You")).toBeInTheDocument();
    expect(within(mine).getByText("Checked the filing.")).toBeInTheDocument();
    expect(within(mine).queryByText(/\d:\d/)).toBeNull();
    expect(within(mine).getByRole("button", { name: "Seen: comment by You" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(box()).toHaveValue("");
    expect(document.activeElement).toBe(box());
    expect(within(panel()).getByRole("status")).toHaveTextContent("Comment posted");
  });

  it("says Write something first. for an empty send and keeps focus in the box", () => {
    show(CORVANE_PATH);
    send();
    expect(within(panel()).getByText("Write something first.")).toBeInTheDocument();
    expect(document.activeElement).toBe(box());
    expect(within(panel()).getAllByRole("article")).toHaveLength(5);
  });

  it("replies to a top-level comment: Replying to, Cancel, then the reply sits under it", () => {
    show(CORVANE_PATH);
    fireEvent.click(within(panel()).getByRole("button", { name: "Reply to Tobias O" }));
    expect(within(panel()).getByText("Replying to Tobias O")).toBeInTheDocument();
    expect(document.activeElement).toBe(box());
    fireEvent.click(within(panel()).getByRole("button", { name: "Cancel" }));
    expect(within(panel()).queryByText(/Replying to/)).toBeNull();
    expect(document.activeElement).toBe(box());
    fireEvent.click(within(panel()).getByRole("button", { name: "Reply to Tobias O" }));
    type("Same here.");
    send();
    expect(within(panel()).queryByText(/Replying to/)).toBeNull();
    const replies = within(panel()).getByRole("list", { name: "Replies to Tobias O" });
    expect(within(replies).getAllByRole("article")).toHaveLength(2);
    expect(within(replies).getByText("Same here.")).toBeInTheDocument();
    expect(document.activeElement).toBe(box());
    expect(within(panel()).getByRole("status")).toHaveTextContent("Reply to Tobias O posted");
  });

  it("draws Reply on top-level comments only, never on a reply or a removed comment", () => {
    show(CORVANE_PATH);
    expect(
      within(panel())
        .getAllByRole("button", { name: /^Reply/ })
        .map((b) => b.getAttribute("aria-label")),
    ).toEqual(["Reply to Tobias O", "Reply to You"]);
  });

  it("gives a reader the thread to read and react to, with no Reply and no composer", () => {
    show(`/signal/reader/group/leveraged-credit/thread/corvane-thread`);
    expect(
      within(panel()).getByText("Readers see this thread but not the reply box."),
    ).toBeInTheDocument();
    expect(within(panel()).queryByRole("textbox")).toBeNull();
    expect(within(panel()).queryByRole("button", { name: /Reply/ })).toBeNull();
    expect(within(panel()).queryByRole("button", { name: /Send/ })).toBeNull();
    const agree = within(panel()).getByRole("button", { name: /^Agree, 2: comment by Tobias O/ });
    fireEvent.click(agree);
    expect(agree).toHaveAttribute("aria-pressed", "true");
  });

  it("draws an archived thread with its delivered line, the note and no composer or Reply for a writer", () => {
    show(`${GROUP}/thread/brightwell-thread`);
    const top = within(panel());
    expect(top.getByText("Archived on 2 Nov 2026")).toBeInTheDocument();
    expect(top.getByText("Leveraged credit, 2 comments")).toBeInTheDocument();
    expect(top.getByRole("heading", { level: 3, name: BRIGHTWELL })).toBeInTheDocument();
    expect(
      top.getByText("This thread is archived. It can be read but not added to."),
    ).toBeInTheDocument();
    expect(top.queryByRole("textbox")).toBeNull();
    expect(top.queryByRole("button", { name: /Reply/ })).toBeNull();
    expect(top.queryByRole("button", { name: /Send/ })).toBeNull();
    expect(top.getByRole("button", { name: "Agree, 1: comment by Tobias O" })).toBeInTheDocument();
  });

  it("says No comments yet for a thread with none, and draws no list", () => {
    const slice = withMain((main) => {
      const one = main.snapshot.threads[1];
      if (one === undefined) throw new Error("main has a second thread");
      one.comments = [];
    });
    show(`${GROUP}/thread/packaging-note`, slice);
    expect(within(panel()).getByText("No comments yet")).toBeInTheDocument();
    expect(within(panel()).queryByRole("list", { name: "Comments" })).toBeNull();
    expect(box()).toBeInTheDocument();
  });

  it("offers a writer with no name no box, and says why", () => {
    const slice = withMain((main) => {
      Object.assign(main.snapshot.viewer, { name: null, initials: null });
    });
    show(CORVANE_PATH, slice);
    const dialogs = screen.getAllByRole("dialog", { hidden: true });
    expect(dialogs).toHaveLength(2);
    const thread = screen.getByRole("dialog", { name: "Thread", hidden: true });
    expect(within(thread).getByText("Set your name to write a comment.")).toBeInTheDocument();
    expect(within(thread).queryByRole("textbox")).toBeNull();
    expect(within(thread).queryByRole("button", { name: /Reply/ })).toBeNull();
  });

  it("shows the name the viewer typed in this visit under the box", async () => {
    show(CORVANE_PATH);
    fireEvent.click(screen.getByRole("button", { name: /Writer/, hidden: true }));
    const field = await screen.findByRole("textbox", { name: /Display name/ });
    fireEvent.change(field, { target: { value: "Zed Quill" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => {
      expect(within(panel()).getByText("Zed Quill")).toBeInTheDocument();
    });
    expect(within(panel()).queryByText("Mara L")).toBeNull();
  });

  it("says the thread is not found for an unknown thread, over the group view", () => {
    show(`${GROUP}/thread/nowhere`);
    const dialog = screen.getByRole("dialog", { name: "Thread not found" });
    expect(
      within(dialog).getByText("This thread does not exist or is not open to you."),
    ).toBeInTheDocument();
    expect(within(dialog).queryByRole("textbox")).toBeNull();
    expect(
      screen.getByRole("heading", { level: 1, name: "Leveraged credit", hidden: true }),
    ).toBeInTheDocument();
  });

  it("does not offer a thread of another group under this group's address", () => {
    show("/signal/main/group/shipping-desk/thread/corvane-thread");
    expect(screen.getByRole("dialog", { name: "Thread not found" })).toBeInTheDocument();
  });

  it("closes with its Close thread button to the group route and moves focus to that thread's Open thread link", async () => {
    show(CORVANE_PATH);
    fireEvent.click(within(panel()).getByRole("button", { name: "Close thread" }));
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { hidden: true })).toBeNull();
    });
    expect(window.location.hash).toBe(`#${GROUP}`);
    await waitFor(() => {
      expect(document.activeElement).toBe(
        screen.getByRole("link", { name: `Open thread: ${CORVANE}` }),
      );
    });
  });

  it.each([
    [
      "the Close thread button",
      () => fireEvent.click(within(panel()).getByRole("button", { name: "Close thread" })),
    ],
    ["Escape", () => fireEvent.keyDown(panel(), { key: "Escape" })],
  ])(
    "keeps focus on the thread's link after %s when the address was loaded directly and the frames have run",
    async (_how, close) => {
      show(CORVANE_PATH);
      expect(document.activeElement).not.toBe(
        screen.queryByRole("link", { name: `Open thread: ${CORVANE}`, hidden: true }),
      );
      close();
      await waitFor(() => {
        expect(screen.queryByRole("dialog", { hidden: true })).toBeNull();
      });
      await settled();
      expect(document.activeElement).toBe(
        screen.getByRole("link", { name: `Open thread: ${CORVANE}` }),
      );
    },
  );

  it("closes with Escape the same way", async () => {
    show(`${GROUP}/thread/brightwell-thread`);
    fireEvent.keyDown(panel(), { key: "Escape" });
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { hidden: true })).toBeNull();
    });
    expect(window.location.hash).toBe(`#${GROUP}`);
    await waitFor(() => {
      expect(document.activeElement).toBe(
        screen.getByRole("link", { name: `Open thread: ${BRIGHTWELL}` }),
      );
    });
  });

  it("closes the not-found panel to the group route, with focus on the page and not the body", async () => {
    show(`${GROUP}/thread/nowhere`);
    fireEvent.click(screen.getByRole("button", { name: "Close thread" }));
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { hidden: true })).toBeNull();
    });
    expect(window.location.hash).toBe(`#${GROUP}`);
    await settled();
    expect(document.activeElement?.id).toBe("signal-content");
  });

  it("opens the group view again with the panel gone, and its thread links still point at the thread", async () => {
    show(CORVANE_PATH);
    fireEvent.click(within(panel()).getByRole("button", { name: "Close thread" }));
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { hidden: true })).toBeNull();
    });
    expect(screen.getByRole("link", { name: `Open thread: ${CORVANE}` })).toHaveAttribute(
      "href",
      `#${CORVANE_PATH}`,
    );
  });
});

describe("the thread panel across groups", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  /** The "main" scene with a second group holding a thread that has the same id as Corvane's. */
  function twinned() {
    return withMain((main) => {
      const { snapshot } = main;
      const first = snapshot.threads.find((t) => t.id === "corvane-thread");
      if (first === undefined) throw new Error("the fixture has the Corvane thread");
      // The fixture's JSON types give these arrays no common element type, so they are pushed to as lists of anything.
      (snapshot.threads as unknown[]).push({ ...structuredClone(first), groupId: "shipping-desk" });
      const item = snapshot.groups[0]?.threads.find((t) => t.id === "corvane-thread");
      const other = snapshot.groups.find((g) => g.id === "shipping-desk");
      if (item === undefined || other === undefined) throw new Error("the fixture has both groups");
      (other.threads as unknown[]).push(structuredClone(item));
    });
  }

  it("does not carry a posted comment, a reaction or a draft from one group's thread to another's of the same id", async () => {
    show(CORVANE_PATH, twinned());
    type("Checked the filing.");
    send();
    type("A half-written reply");
    const seen = within(panel()).getAllByRole("button", { name: /^Seen: comment by/ })[0];
    if (seen === undefined) throw new Error("the thread has a comment to react to");
    const before = seen.getAttribute("aria-pressed");
    fireEvent.click(seen);
    expect(within(panel()).getByText("Checked the filing.")).toBeInTheDocument();

    window.location.hash = "#/signal/main/group/shipping-desk/thread/corvane-thread";
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { level: 1, name: "Shipping desk", hidden: true }),
      ).toBeInTheDocument();
    });
    expect(within(panel()).queryByText("Checked the filing.")).toBeNull();
    expect(box()).toHaveValue("");
    expect(within(panel()).getByRole("status")).toBeEmptyDOMElement();
    const other = within(panel()).getAllByRole("button", { name: /^Seen: comment by/ })[0];
    expect(other?.getAttribute("aria-pressed")).toBe(before);
  });
});

describe("the thread panel across ids that run into each other", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  /** Two threads, ("leveraged-credit", "x/y") and ("leveraged-credit/x", "y"), that a "/" join would name the same. */
  function colliding() {
    return withMain((main) => {
      const { snapshot } = main;
      const first = snapshot.threads.find((t) => t.id === "corvane-thread");
      const item = snapshot.groups[0]?.threads.find((t) => t.id === "corvane-thread");
      const desk = snapshot.groups.find((g) => g.id === "shipping-desk");
      if (first === undefined || item === undefined || desk === undefined) {
        throw new Error("the fixture has the Corvane thread and the Shipping desk");
      }
      (snapshot.threads as unknown[]).push({ ...structuredClone(first), id: "x/y" });
      (snapshot.groups[0]?.threads as unknown[]).push({ ...structuredClone(item), id: "x/y" });
      (snapshot.threads as unknown[]).push({
        ...structuredClone(first),
        groupId: "leveraged-credit/x",
        id: "y",
      });
      const other = { ...structuredClone(desk), id: "leveraged-credit/x", name: "Overflow desk" };
      (other.threads as unknown[]).push({ ...structuredClone(item), id: "y" });
      (snapshot.groups as unknown[]).push(other);
      (snapshot.channels.groups as unknown[]).push({
        id: other.id,
        name: other.name,
        unread: null,
      });
    });
  }

  it("does not carry a posted comment or a draft between threads whose ids join to the same text", async () => {
    show(`${GROUP}/thread/${encodeURIComponent("x/y")}`, colliding());
    type("Checked the filing.");
    send();
    type("A half-written reply");
    expect(within(panel()).getByText("Checked the filing.")).toBeInTheDocument();

    window.location.hash = `#/signal/main/group/${encodeURIComponent("leveraged-credit/x")}/thread/y`;
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { level: 1, name: "Overflow desk", hidden: true }),
      ).toBeInTheDocument();
    });
    expect(within(panel()).queryByText("Checked the filing.")).toBeNull();
    expect(box()).toHaveValue("");
  });
});

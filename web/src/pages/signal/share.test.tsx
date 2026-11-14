// Share to group and Comment on a story in the feed (mock frame "Share to group", behaviour list 2.6).
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

/** Lets the animation frames after a close run, where the dialog library restores focus by itself. */
const settled = () =>
  act(async () => {
    for (let i = 0; i < 5; i += 1) {
      await new Promise((resolve) => requestAnimationFrame(resolve));
    }
    await new Promise((resolve) => setTimeout(resolve, 50));
  });

const CORVANE = "Corvane Packaging to close two plants as volumes fall";
const TESSALY = "Competition authority opens in-depth review of Tessaly Telecom's tower sale";
const FEED = "/signal/main/feed/for-you";
const shareButton = (headline: string) =>
  screen.getByRole("button", { name: `Share to group: ${headline}` });
const dialog = () => screen.getByRole("dialog", { name: "Share to a group" });
const gone = () =>
  waitFor(() => {
    expect(screen.queryByRole("dialog", { hidden: true })).toBeNull();
  });

/** A copy of the fixture with the "main" scene's groups removed (and the threads that sat in them). */
function withoutGroups(): unknown {
  const copy = structuredClone(fixture.slice);
  const snapshot = copy.scenes[0]?.snapshot;
  if (snapshot === undefined) throw new Error("the fixture has a first scene");
  snapshot.channels.groups = [];
  snapshot.groups = [];
  snapshot.threads = [];
  for (const one of snapshot.feed.stories) Object.assign(one, { threadRef: null });
  return copy;
}

describe("Share to group", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("opens from a story as a form dialog with the story quoted, the Group field and the Note", () => {
    show(FEED);
    fireEvent.click(shareButton(CORVANE));
    const box = within(dialog());
    expect(box.getByText(CORVANE)).toBeInTheDocument();
    expect(box.queryByRole("heading", { level: 1 })).toBeNull();
    expect(box.getByRole("heading", { level: 2, name: "Share to a group" })).toBeInTheDocument();
    expect(
      box.getByText(
        "The story starts a thread in this group, or joins the thread it already has there.",
      ),
    ).toBeInTheDocument();
    expect(box.getByRole("textbox", { name: /Note \(optional\)/ })).toBeInTheDocument();
    expect(box.getByText("Plain text. Members see it as your first comment.")).toBeInTheDocument();
    expect(box.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
    expect(box.getByRole("button", { name: "Share" })).toBeInTheDocument();
  });

  it("lists the snapshot's groups in the Group select", () => {
    show(FEED);
    fireEvent.click(shareButton(CORVANE));
    fireEvent.click(within(dialog()).getByRole("button", { name: /Group/ }));
    const names = screen.getAllByRole("option").map((o) => o.textContent);
    expect(names).toEqual(["Leveraged credit", "Shipping desk"]);
  });

  it("says a group must be chosen when Share is pressed with none, and stays open", () => {
    show(FEED);
    fireEvent.click(shareButton(CORVANE));
    fireEvent.click(within(dialog()).getByRole("button", { name: "Share" }));
    expect(within(dialog()).getByText("Choose a group to share this story to.")).toBeVisible();
    expect(screen.queryByText("Sample data: the story was not shared.")).toBeNull();
  });

  it("moves focus to the Group select on Share with none, and the error is its description", () => {
    show(FEED);
    fireEvent.click(shareButton(CORVANE));
    fireEvent.click(within(dialog()).getByRole("button", { name: "Share" }));
    const trigger = within(dialog()).getByRole("button", { name: /Group/ });
    expect(document.activeElement).toBe(trigger);
    expect(trigger).toHaveAccessibleDescription(/Choose a group to share this story to\./);
  });

  it("closes on Share with a group and the feed says the story was not shared", async () => {
    show(FEED);
    fireEvent.click(shareButton(CORVANE));
    fireEvent.click(within(dialog()).getByRole("button", { name: /Group/ }));
    fireEvent.click(screen.getByRole("option", { name: "Shipping desk" }));
    fireEvent.click(within(dialog()).getByRole("button", { name: "Share" }));
    await gone();
    const note = screen.getByText("Sample data: the story was not shared.");
    expect(note.closest('[role="status"]')).not.toBeNull();
    await settled();
    expect(document.activeElement).toBe(shareButton(CORVANE));
  });

  it("closes on Cancel with focus back on the story's Share to group button", async () => {
    show(FEED);
    fireEvent.click(shareButton(TESSALY));
    fireEvent.click(within(dialog()).getByRole("button", { name: "Cancel" }));
    await gone();
    await settled();
    expect(document.activeElement).toBe(shareButton(TESSALY));
    expect(screen.queryByText("Sample data: the story was not shared.")).toBeNull();
  });

  it("closes on Escape with focus back on the story's Share to group button", async () => {
    show(FEED);
    fireEvent.click(shareButton(CORVANE));
    fireEvent.keyDown(dialog(), { key: "Escape" });
    await gone();
    await settled();
    expect(document.activeElement).toBe(shareButton(CORVANE));
  });

  it("with no groups says so and offers no Share button", () => {
    show(FEED, withoutGroups());
    fireEvent.click(shareButton(CORVANE));
    const box = within(dialog());
    expect(box.getByText("There are no groups yet. Create one to share this story.")).toBeVisible();
    expect(box.queryByRole("button", { name: "Share" })).toBeNull();
    expect(box.queryByRole("button", { name: /Group/ })).toBeNull();
    expect(box.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
  });
});

describe("Comment on a story", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("links to the story's thread when it has one", () => {
    show(FEED);
    const comment = screen.getByRole("link", { name: `Comment 3: ${CORVANE}` });
    expect(comment).toHaveAttribute(
      "href",
      "#/signal/main/group/leveraged-credit/thread/corvane-thread",
    );
  });

  it("opens the Share dialog when the story has no thread, and focus returns to Comment", async () => {
    show(FEED);
    expect(screen.queryByRole("link", { name: `Comment: ${TESSALY}` })).toBeNull();
    const comment = screen.getByRole("button", { name: `Comment: ${TESSALY}` });
    fireEvent.click(comment);
    expect(dialog()).toBeInTheDocument();
    fireEvent.click(within(dialog()).getByRole("button", { name: "Cancel" }));
    await gone();
    await settled();
    expect(document.activeElement).toBe(comment);
  });

  it("gives a reader neither Comment nor Share to group", () => {
    show("/signal/reader/feed/for-you");
    expect(screen.getAllByRole("article").length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: /Share to group/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /Comment/ })).toBeNull();
    expect(screen.queryByRole("link", { name: /Comment/ })).toBeNull();
  });
});

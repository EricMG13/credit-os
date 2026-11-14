// The group view (mock frames "Group view, writer" and "Group view, reader"; behaviour list 2.4, 2.5).
import { render, screen, within } from "@testing-library/react";
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

const LEV = "/signal/main/group/leveraged-credit";
const CORVANE = "Corvane Packaging to close two plants as volumes fall";
const HALVORSEN = "Northgate Ratings downgrades Halvorsen Marine to B+";
const BRIGHTWELL = "Authority clears Brightwell Foods' dairy purchase with conditions";
const NOTE =
  "Has anyone looked at how the packaging closures read across to the two issuers we hold? Worth a slot on Thursday.";

/** The item (article) whose h2 has the given text. */
function item(text: string) {
  const heading = screen.getByRole("heading", { level: 2, name: text });
  const article = heading.closest("article");
  if (article === null) throw new Error("an item's heading sits in an article");
  return article;
}

/** The list item holding an article, which also holds the item's own footer. */
function row(text: string) {
  const li = item(text).closest("li");
  if (li === null) throw new Error("an item sits in a list item");
  return within(li);
}

/** A copy of the fixture whose "main" scene's first group is changed by `change`. */
function withGroup(
  change: (group: (typeof fixture.slice.scenes)[0]["snapshot"]["groups"][0]) => void,
) {
  const copy = structuredClone(fixture.slice);
  const group = copy.scenes[0]?.snapshot.groups[0];
  if (group === undefined) throw new Error("main has a first group");
  change(group);
  return copy;
}

describe("the group view", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("draws the group's name as the one h1, with its member summary and visibility under it", () => {
    show(LEV);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1, name: "Leveraged credit" })).toBeInTheDocument();
    expect(screen.getByText("6 members")).toBeInTheDocument();
    expect(screen.getByText("Open to everyone")).toBeInTheDocument();
  });

  it("draws the members' avatars and the delivered +N, and names the members for a screen reader", () => {
    show(LEV);
    for (const initials of ["TO", "IK", "ML", "JW", "+2"]) {
      expect(screen.getAllByText(initials).length).toBeGreaterThan(0);
    }
    const names = screen.getByRole("list", { name: "Members" });
    expect(
      within(names)
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["Tobias O", "Ines K", "Mara L", "Jonas W"]);
  });

  it("draws no Comment or Share to group on any story item, for a writer", () => {
    show(LEV);
    expect(screen.queryByRole("button", { name: /Comment/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /Share to group/ })).toBeNull();
    expect(screen.getAllByRole("button", { name: /^Save/ })).toHaveLength(3);
  });

  it("draws the users icon on the group's avatar, as the channel list does", () => {
    show(LEV);
    const shape = (svg: Element | null | undefined) =>
      [...(svg?.querySelectorAll("path") ?? [])].map((p) => p.getAttribute("d")).join("|");
    const header = screen.getByRole("heading", { level: 1 }).closest("div")?.parentElement;
    const nav = screen.getByRole("navigation", { name: "Signal" });
    const row = within(nav).getByRole("link", { name: /^Leveraged credit/ });
    const own = shape(header?.querySelector('[aria-hidden="true"] svg'));
    expect(own).not.toBe("");
    expect(own).toBe(shape(row.querySelector("svg")));
  });

  it("marks the group current in the channel list", () => {
    show(LEV);
    expect(
      within(screen.getByRole("navigation", { name: "Signal" })).getByRole("link", {
        name: "Leveraged credit 3",
      }),
    ).toHaveAttribute("aria-current", "page");
  });

  it("gives a writer New thread and Attach story, disabled, with the reason in view", () => {
    show(LEV);
    for (const name of ["New thread", "Attach story"]) {
      const button = screen.getByRole("button", { name });
      expect(button).toBeDisabled();
      expect(button).toHaveAccessibleDescription("Sample data: threads cannot be started here.");
    }
    expect(screen.getByText("Sample data: threads cannot be started here.")).toBeVisible();
  });

  it("gives a reader neither New thread nor Attach story, and no reason", () => {
    show("/signal/reader/group/leveraged-credit");
    expect(screen.queryByRole("button", { name: /New thread/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /Attach story/ })).toBeNull();
    expect(screen.queryByText(/threads cannot be started here/)).toBeNull();
    expect(screen.queryByRole("button", { name: /Share to group/ })).toBeNull();
  });

  it("draws a reader's one shared story, which can be opened and saved", () => {
    show("/signal/reader/group/leveraged-credit");
    expect(screen.getAllByRole("article")).toHaveLength(1);
    const card = within(item(CORVANE));
    expect(card.getByRole("button", { name: `Save: ${CORVANE}` })).toBeInTheDocument();
    expect(card.queryByRole("button", { name: /Comment/ })).toBeNull();
    expect(screen.getByRole("link", { name: `Open thread: ${CORVANE}` })).toHaveAttribute(
      "href",
      "#/signal/reader/group/leveraged-credit/thread/corvane-thread",
    );
  });

  it("draws a shared story on the story card with the thread's shared-by line, count, time and unread mark", () => {
    show(LEV);
    const card = within(item(CORVANE));
    expect(card.getByText("Shared by Tobias O, 1 h ago")).toBeInTheDocument();
    expect(card.getByText("News")).toBeInTheDocument();
    expect(card.getByText("Harbour Wire")).toBeInTheDocument();
    expect(card.getByRole("button", { name: `Save: ${CORVANE}` })).toBeInTheDocument();
    expect(card.queryByRole("button", { name: /Comment/ })).toBeNull();
    expect(card.queryByRole("button", { name: /Share to group/ })).toBeNull();
    expect(
      card.getByRole("link", { name: `Open source: ${CORVANE} (opens in a new tab)` }),
    ).toHaveAttribute("href", "https://example.com/corvane");
    const footer = row(CORVANE);
    expect(footer.getByText("4 comments")).toBeInTheDocument();
    expect(footer.getByText("1 h ago", { selector: "time" })).toBeInTheDocument();
    expect(footer.getByText("Unread")).toBeInTheDocument();
  });

  it("draws a note with no story as its sharer's line and the note text, in a list of items below the h1", () => {
    show(LEV);
    const note = within(item("Ines K started a thread"));
    expect(note.getByText(NOTE)).toBeInTheDocument();
    expect(note.getByText("IK")).toBeInTheDocument();
    expect(note.queryByRole("button", { name: /Save/ })).toBeNull();
    const footer = row("Ines K started a thread");
    expect(footer.getByText("2 comments")).toBeInTheDocument();
    expect(footer.getByText("Yesterday 16:20", { selector: "time" })).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(4);
  });

  it("marks only an unread item as unread", () => {
    show(LEV);
    expect(row(HALVORSEN).queryByText("Unread")).toBeNull();
    expect(screen.getAllByText("Unread").length).toBeGreaterThan(0);
    expect(
      screen.getAllByText("Unread").filter((el) => el.closest("li")?.closest("nav") === null),
    ).toHaveLength(2);
  });

  it("marks an archived thread with the neutral Archived badge and no other thread", () => {
    show(LEV);
    expect(row(BRIGHTWELL).getByText("Archived")).toBeInTheDocument();
    expect(screen.getAllByText("Archived")).toHaveLength(1);
    expect(row(HALVORSEN).queryByText("Archived")).toBeNull();
  });

  it("links every item to its thread, naming the item", () => {
    show(LEV);
    const expected: [string, string][] = [
      [CORVANE, "corvane-thread"],
      ["Ines K started a thread", "packaging-note"],
      [HALVORSEN, "halvorsen-thread"],
      [BRIGHTWELL, "brightwell-thread"],
    ];
    const links = screen.getAllByRole("link", { name: /^Open thread/ });
    expect(links.map((a) => [a.getAttribute("aria-label"), a.getAttribute("href")])).toEqual(
      expected.map(([label, id]) => [
        `Open thread: ${label}`,
        `#/signal/main/group/leveraged-credit/thread/${id}`,
      ]),
    );
  });

  it("draws the items in one list on one card, in the slice's order", () => {
    show(LEV);
    const list = screen.getByRole("list", { name: "Shared in this group" });
    expect(
      within(list)
        .getAllByRole("heading", { level: 2 })
        .map((h) => h.textContent),
    ).toEqual([CORVANE, "Ines K started a thread", HALVORSEN, BRIGHTWELL]);
    expect(list.className).toContain("divide-y");
  });

  it("draws the thread route as the group view under the thread panel, which hides it from the accessibility tree", () => {
    show(`${LEV}/thread/packaging-note`);
    const hidden = { hidden: true };
    expect(
      screen.getByRole("heading", { level: 1, name: "Leveraged credit", ...hidden }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("list", { name: "Shared in this group", ...hidden }),
    ).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Thread" })).toBeInTheDocument();
  });

  it("says a group with no threads has none, with the writer's hint", () => {
    show("/signal/main/group/shipping-desk");
    expect(screen.getByRole("heading", { level: 1, name: "Shipping desk" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "No threads in this group yet" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Share a story from the feed or start a note.")).toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Shared in this group" })).toBeNull();
    expect(screen.getByRole("button", { name: "New thread" })).toBeDisabled();
  });

  it("gives a reader the reader's hint for an empty group and no buttons", () => {
    const copy = structuredClone(fixture.slice);
    const reader = copy.scenes.find((s) => s.id === "reader");
    if (reader === undefined) throw new Error("the fixture has a reader scene");
    const first = reader.snapshot.groups[0];
    if (first === undefined) throw new Error("reader has a first group");
    first.threads = [];
    reader.snapshot.threads = [];
    for (const one of reader.snapshot.feed.stories) Object.assign(one, { threadRef: null });
    show("/signal/reader/group/leveraged-credit", copy);
    expect(
      screen.getByText("Threads appear here when a writer shares a story or starts a note."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Share a story from the feed/)).toBeNull();
    expect(screen.queryByRole("button", { name: /New thread/ })).toBeNull();
  });

  it("draws a group with no members listed without an avatar group", () => {
    show("/signal/ai-on/group/leveraged-credit");
    expect(screen.getByText("No members listed")).toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Members" })).toBeNull();
  });

  it("draws a story's note under the story card, outside it", () => {
    const slice = structuredClone(fixture.slice);
    const snapshot = slice.scenes[0]?.snapshot;
    const first = snapshot?.groups[0]?.threads[0];
    const own = snapshot?.threads[0];
    if (first === undefined || own === undefined) throw new Error("the group has a thread");
    // The item and the thread it opens name the same note.
    first.note = "Read the second paragraph.";
    own.note = "Read the second paragraph.";
    show(LEV, slice);
    expect(within(item(CORVANE)).queryByText("Read the second paragraph.")).toBeNull();
    expect(row(CORVANE).getByText("Read the second paragraph.")).toBeInTheDocument();
  });

  it.each([
    ["an unknown group", "/signal/main/group/nowhere"],
    ["an unknown group on the thread route", "/signal/main/group/nowhere/thread/t"],
  ])("says %s does not exist or is not open, as the one h1, with a way back", (_name, hash) => {
    show(hash);
    expect(screen.getAllByRole("heading", { level: 1 }).map((h) => h.textContent)).toEqual([
      "This group does not exist or is not open to you.",
    ]);
    expect(screen.getByRole("link", { name: "Back to For you" })).toHaveAttribute(
      "href",
      "#/signal/main/feed/for-you",
    );
    expect(
      within(screen.getByRole("navigation", { name: "Signal" })).queryAllByRole("link", {
        current: "page",
      }),
    ).toEqual([]);
  });

  it("says the slice is invalid, with the path, when a thread names an unknown story", () => {
    const slice = withGroup((group) => {
      const first = group.threads[0];
      if (first === undefined) throw new Error("the group has a thread");
      first.storyId = "no-such-story";
    });
    show(LEV, slice);
    expect(
      screen.getByText(
        "scenes[0].snapshot.groups[0].threads[0].storyId: expected the id of a story in the feed",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 1, name: "Leveraged credit" })).toBeNull();
  });
});

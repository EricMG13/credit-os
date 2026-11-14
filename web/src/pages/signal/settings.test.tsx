// The settings page (mock settings frames 1, 2 and 6). Expected wording is the mock's, not the code's.
import { fireEvent, render, screen, within } from "@testing-library/react";
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

const page = () => within(document.getElementById("signal-content") as HTMLElement);
const tabs = () => page().getByRole("tablist", { name: "Settings sections" });
const NAMES = [
  "Groups",
  "Thread rules",
  "Sources",
  "Topics",
  "Digests",
  "Notifications",
  "AI and cost",
];

afterEach(() => {
  window.location.hash = "";
});

describe("the section list", () => {
  it("lists the seven sections as links for a writer, with the current one marked", () => {
    show("/signal/main/settings/thread-rules");
    const items = within(tabs()).getAllByRole("tab");
    expect(items.map((t) => t.textContent)).toEqual(NAMES);
    expect(items.map((t) => t.getAttribute("aria-selected"))).toEqual(
      NAMES.map((n) => String(n === "Thread rules")),
    );
    expect(items.map((t) => t.getAttribute("href"))).toEqual([
      "#/signal/main/settings/groups",
      "#/signal/main/settings/thread-rules",
      "#/signal/main/settings/sources",
      "#/signal/main/settings/topics",
      "#/signal/main/settings/digests",
      "#/signal/main/settings/notifications",
      "#/signal/main/settings/ai",
    ]);
    expect(page().getByRole("heading", { level: 1 }).textContent).toBe("Settings");
    expect(page().getByRole("heading", { level: 2 }).textContent).toBe("Thread rules");
  });

  it("lists Topics and Notifications only for a reader", () => {
    show("/signal/reader/settings/notifications");
    const items = within(tabs()).getAllByRole("tab");
    expect(items.map((t) => t.textContent)).toEqual(["Topics", "Notifications"]);
    expect(items.map((t) => t.getAttribute("aria-selected"))).toEqual(["false", "true"]);
  });

  it("says a reader's address for a writer's section is for writers, with no section marked", () => {
    show("/signal/reader/settings/groups");
    expect(page().getByRole("heading", { level: 1 }).textContent).toBe("Settings");
    expect(page().getByText("This section is for writers")).toBeTruthy();
    expect(page().queryByRole("button", { name: /Visibility/ })).toBeNull();
    expect(page().queryByRole("button", { name: /New group|Edit members/ })).toBeNull();
    expect(
      within(tabs())
        .getAllByRole("tab")
        .map((t) => t.getAttribute("aria-selected")),
    ).toEqual(["false", "false"]);
  });

  it("says an unknown section does not exist, with no section marked", () => {
    show("/signal/main/settings/billing");
    expect(page().getByRole("heading", { level: 1 }).textContent).toBe("Settings");
    expect(page().getByText("No such settings section")).toBeTruthy();
    expect(
      within(tabs())
        .getAllByRole("tab")
        .map((t) => t.getAttribute("aria-selected")),
    ).toEqual(NAMES.map(() => "false"));
  });

  it("says AI and cost is not built yet", () => {
    show("/signal/main/settings/ai");
    expect(page().getByText("Not built yet")).toBeTruthy();
    expect(page().getByRole("heading", { level: 1 }).textContent).toBe("Settings");
  });
});

describe("Groups (frame 1)", () => {
  it("draws each group with its member line, avatars and visibility; the empty group says so", () => {
    show("/signal/main/settings/groups");
    expect(page().getByText("A group has a thread for every story shared to it.")).toBeTruthy();
    const rows = page()
      .getAllByRole("listitem")
      .filter((li) => li.querySelector("button"));
    expect(rows.map((li) => li.querySelector("b, p")?.textContent)).toEqual([
      "Leveraged credit",
      "Shipping desk",
      "Committee prep",
    ]);
    expect(page().getByText("6 members")).toBeTruthy();
    expect(page().getByText("3 members")).toBeTruthy();
    expect(page().getByText("No members yet")).toBeTruthy();
    expect(page().getByText("Add a member to start")).toBeTruthy();
    expect(page().getAllByText("Add a member to start")).toHaveLength(1);
    expect(page().getByText("+2")).toBeTruthy();
    expect(
      page()
        .getAllByRole("list", { name: /^Members of / })
        .map((l) => l.getAttribute("aria-label")),
    ).toEqual(["Members of Leveraged credit", "Members of Shipping desk"]);
    const select = (name: string) =>
      page().getByRole("button", { name: new RegExp(`Visibility: ${name}`) });
    expect(select("Leveraged credit").textContent).toContain("Visible to everyone");
    expect(select("Shipping desk").textContent).toContain("Members only");
    expect(select("Committee prep").textContent).toContain("Members only");
  });

  it("changes a group's visibility in memory and keeps it when moving between sections", async () => {
    show("/signal/main/settings/groups");
    fireEvent.click(page().getByRole("button", { name: /Visibility: Shipping desk/ }));
    fireEvent.click(screen.getByRole("option", { name: "Visible to everyone" }));
    const shipping = () => page().getByRole("button", { name: /Visibility: Shipping desk/ });
    expect(shipping().textContent).toContain("Visible to everyone");
    expect(
      page().getByRole("button", { name: /Visibility: Leveraged credit/ }).textContent,
    ).toContain("Visible to everyone");
    expect(
      page().getByRole("button", { name: /Visibility: Committee prep/ }).textContent,
    ).toContain("Members only");
    window.location.hash = "#/signal/main/settings/thread-rules";
    await screen.findByRole("heading", { level: 2, name: "Thread rules" });
    window.location.hash = "#/signal/main/settings/groups";
    await screen.findByRole("heading", { level: 2, name: "Groups" });
    expect(shipping().textContent).toContain("Visible to everyone");
  });

  it("draws New group and Edit members disabled, with the reason in view", () => {
    show("/signal/main/settings/groups");
    const reason = page().getByText(/Sample data: groups and their members cannot be changed/);
    for (const button of page().getAllByRole("button", { name: /New group|Edit members/ })) {
      expect((button as HTMLButtonElement).disabled).toBe(true);
      expect(button.getAttribute("aria-describedby")).toBe(reason.id);
    }
    expect(
      page()
        .getAllByRole("button", { name: /Edit members/ })
        .map((b) => [b.textContent, b.getAttribute("aria-label")]),
    ).toEqual([
      ["Edit members", "Edit members: Leveraged credit"],
      ["Edit members", "Edit members: Shipping desk"],
      ["Edit members", "Edit members: Committee prep"],
    ]);
    expect(page().getByRole("button", { name: "Edit members: Shipping desk" })).toBeDisabled();
  });
});

describe("empty lists", () => {
  it("draws no empty list beside the no-rules line", () => {
    const slice = structuredClone(fixture.slice);
    const main = slice.scenes[0];
    if (main === undefined) throw new Error("the fixture has scenes");
    main.snapshot.settings.rules = [];
    show("/signal/main/settings/thread-rules", slice);
    expect(page().getByText("No thread rules yet.")).toBeTruthy();
    expect(page().queryAllByRole("list")).toHaveLength(0);
  });

  it("draws no empty list beside the no-groups line", () => {
    const slice = structuredClone(fixture.slice);
    const bare = slice.scenes.find((s) => s.id === "loading");
    if (bare === undefined) throw new Error("the fixture has the loading scene");
    bare.snapshot.settings.groups = [];
    bare.snapshot.channels.groups = [];
    bare.snapshot.groups = [];
    bare.snapshot.threads = [];
    show("/signal/loading/settings/groups", slice);
    expect(page().getByText("No groups yet.")).toBeTruthy();
    expect(page().queryAllByRole("list")).toHaveLength(0);
  });
});

describe("Thread rules (frame 2)", () => {
  it("draws each rule as a switch with its label and hint, set as the fixture holds them", () => {
    show("/signal/main/settings/thread-rules");
    expect(page().getByText("These apply to every group.")).toBeTruthy();
    const rules = [
      ["Comments can be edited", 'An edited comment is marked "edited".', true],
      [
        "Authors can remove their own comments",
        "The thread keeps a line saying a comment was removed.",
        true,
      ],
      ["Readers can react", "Off: only writers react. Readers never comment.", false],
      [
        "Archive a thread after 30 days without a comment",
        "An archived thread can be read but not added to.",
        true,
      ],
    ] as const;
    expect(page().getAllByRole("switch")).toHaveLength(4);
    for (const [label, hint, on] of rules) {
      const one = page().getByRole("switch", { name: new RegExp(label), description: hint });
      expect((one as HTMLInputElement).checked).toBe(on);
      expect(page().getByText(hint)).toBeTruthy();
    }
  });

  it("turns each rule on and off in memory", () => {
    show("/signal/main/settings/thread-rules");
    for (const one of page().getAllByRole("switch")) {
      const before = (one as HTMLInputElement).checked;
      fireEvent.click(one);
      expect((one as HTMLInputElement).checked).toBe(!before);
      fireEvent.click(one);
      expect((one as HTMLInputElement).checked).toBe(before);
    }
  });
});

describe("Notifications (frame 6)", () => {
  it("draws a grid with the two channel headings and a switch named by event and channel", () => {
    show("/signal/main/settings/notifications");
    expect(page().getByText("Choose where each event reaches you.")).toBeTruthy();
    expect(
      page()
        .getAllByRole("columnheader")
        .map((h) => h.textContent),
    ).toEqual(["Event", "In Signal", "On the desktop"]);
    const names = page()
      .getAllByRole("switch")
      .map((s) => s.getAttribute("aria-label"));
    expect(names).toEqual([
      "A comment on a thread I am in, In Signal",
      "A comment on a thread I am in, On the desktop",
      "A story shared to one of my groups, In Signal",
      "A story shared to one of my groups, On the desktop",
      "A new digest, In Signal",
      "A new digest, On the desktop",
      "A rating action in a topic I follow, In Signal",
      "A rating action in a topic I follow, On the desktop",
    ]);
    expect(
      page()
        .getAllByRole("switch")
        .map((s) => (s as HTMLInputElement).checked),
    ).toEqual([true, true, true, false, true, false, false, false]);
  });

  it("changes one switch without touching its neighbour, for a reader too", () => {
    show("/signal/reader/settings/notifications");
    const one = page().getByRole("switch", { name: "A new digest, On the desktop" });
    const other = page().getByRole("switch", { name: "A new digest, In Signal" });
    fireEvent.click(one);
    expect((one as HTMLInputElement).checked).toBe(true);
    expect((other as HTMLInputElement).checked).toBe(true);
  });
});

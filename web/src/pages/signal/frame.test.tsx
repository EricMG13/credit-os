import { fireEvent, render, screen, within } from "@testing-library/react";
import { declaredPaths, fillParams } from "../../../scripts/route-paths.mjs";
import fixture from "../../../fixtures/signal.json";
import { App } from "../../App";
import type { LoadResult } from "../../data";

const ok: LoadResult = {
  kind: "ok",
  data: { schema: "credit-os-data/1", issuers: [], signal: fixture.slice },
};

function show(hash: string, result: LoadResult = ok) {
  window.location.hash = `#${hash}`;
  return render(<App result={result} />);
}

function channels() {
  return screen.getByRole("navigation", { name: "Signal" });
}

/** The h1 each declared path shows for its fixture parameter sets (the view, topic, group, digest or page name). */
const TITLES: Record<string, string> = {
  "/signal/:scene/topic/:topic": "Shipping",
  "/signal/:scene/group/:group": "Leveraged credit",
  "/signal/:scene/group/:group/thread/:thread": "Leveraged credit",
  "/signal/:scene/digest/:digest": "Weekly brief",
  "/signal/:scene/settings/:section": "Settings",
};

const VIEW_TITLES: Record<string, string> = {
  "for-you": "For you",
  latest: "Latest",
  saved: "Saved",
};

/** Headings that sit more than one level below the one before them (the channel list's h2s open the page, before the h1). */
function skippedLevels(): string[] {
  const levels = screen
    .getAllByRole("heading")
    .map((h) => ({ level: Number(h.tagName.slice(1)), text: h.textContent }));
  return levels
    .filter((h, i) => i > 0 && h.level > (levels[i - 1]?.level ?? 0) + 1)
    .map((h) => h.text);
}

describe("the Signal frame", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("lists views, topics, groups, digests and settings for a writer", () => {
    show("/signal/main/feed/for-you");
    const nav = within(channels());
    for (const name of [
      "For you",
      "Latest",
      "Saved",
      "Leveraged credit",
      "Shipping desk",
      "Settings",
    ]) {
      expect(nav.getByRole("link", { name: new RegExp(`^${name}`) })).toBeInTheDocument();
    }
    for (const heading of ["Topics", "Groups", "Digests"]) {
      expect(nav.getByRole("heading", { level: 2, name: heading })).toBeInTheDocument();
    }
    expect(nav.getByRole("link", { name: "Saved 6" })).toBeInTheDocument();
    expect(nav.getByRole("link", { name: "Shipping 12" })).toBeInTheDocument();
    expect(nav.getByRole("link", { name: "Leveraged credit 3" })).toBeInTheDocument();
    expect(screen.getByText("Mara L")).toBeInTheDocument();
    expect(screen.getByText("Writer")).toBeInTheDocument();
  });

  it("marks the current item and shows its title as the h1", () => {
    show("/signal/main/feed/latest");
    expect(within(channels()).getByRole("link", { name: "Latest" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(channels()).getByRole("link", { name: "For you" })).not.toHaveAttribute(
      "aria-current",
    );
    expect(screen.getByRole("heading", { level: 1, name: "Latest" })).toBeInTheDocument();
  });

  it("titles a topic view with the topic's name and marks it current", () => {
    show("/signal/main/topic/telecoms");
    expect(within(channels()).getByRole("link", { name: "Telecoms 5" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("heading", { level: 1, name: "Telecoms" })).toBeInTheDocument();
  });

  it("toggles a follow star in memory", () => {
    show("/signal/main/feed/for-you");
    const star = screen.getByRole("button", { name: "Follow Telecoms" });
    expect(star).toHaveAttribute("aria-pressed", "false");
    expect(star.className).not.toContain("text-action");
    fireEvent.click(star);
    const now = screen.getByRole("button", { name: "Unfollow Telecoms" });
    expect(now.className).toContain("text-action");
    expect(now).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Unfollow Shipping" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.queryByRole("button", { name: "Follow Telecoms" })).toBeNull();
  });

  it("shows the role label of a reader", () => {
    show("/signal/reader/feed/for-you");
    expect(screen.getByText("Reader")).toBeInTheDocument();
    expect(screen.queryByText("Writer")).toBeNull();
  });

  it("offers Set your name when the viewer has none", () => {
    show("/signal/no-name/feed/for-you");
    expect(screen.getByRole("button", { name: "Set your name" })).toBeInTheDocument();
    expect(screen.queryByText("Mara L")).toBeNull();
  });

  it("says there are no topics yet", () => {
    show("/signal/no-topics/feed/for-you");
    expect(within(channels()).getByText("No topics yet")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Follow / })).toBeNull();
  });

  it("shows paused digests with a Paused badge and no unread dot", () => {
    show("/signal/main/feed/for-you");
    expect(within(channels()).getAllByText("Paused")).toHaveLength(2);
    expect(within(channels()).queryByText("Unread")).toBeNull();
  });

  it("shows the unread dot of an unread digest", () => {
    show("/signal/ai-on/feed/for-you");
    expect(within(channels()).getByText("Unread")).toBeInTheDocument();
    expect(within(channels()).queryByText("Paused")).toBeNull();
  });

  it("puts the skip link first and sends focus to the content", () => {
    show("/signal/main/feed/for-you");
    const skip = screen.getByRole("link", { name: "Skip to the feed" });
    const links = screen.getAllByRole("link");
    expect(links.indexOf(skip)).toBeLessThan(
      links.indexOf(within(channels()).getByRole("link", { name: "For you" })),
    );
    expect(skip.className).toContain("focus:outline-2");
    expect(skip.className).toContain("outline-focus-ring");
    fireEvent.click(skip);
    expect(
      screen.getByRole("heading", { level: 1, name: "For you" }).closest("[tabindex='-1']"),
    ).toHaveFocus();
    expect(window.location.hash).toBe("#/signal/main/feed/for-you");
  });

  it("draws one main landmark, with the page's title as the one h1 and the channel list under it", () => {
    show("/signal/main/feed/for-you");
    expect(screen.getAllByRole("main")).toHaveLength(1);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1, name: "For you" })).toBeInTheDocument();
    expect(within(channels()).getByRole("heading", { level: 2, name: "Signal" })).toBeVisible();
    expect(within(channels()).queryByRole("heading", { level: 1 })).toBeNull();
  });

  it("draws the bare #/signal as the first scene's For you with For you current", () => {
    show("/signal");
    expect(window.location.hash).toBe("#/signal");
    expect(screen.getByRole("heading", { level: 1, name: "For you" })).toBeInTheDocument();
    expect(within(channels()).getByRole("link", { name: "For you" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(channels()).getByRole("link", { name: "Latest" })).not.toHaveAttribute(
      "aria-current",
    );
    expect(screen.getAllByRole("article")).toHaveLength(4);
  });

  it("gives the frame its own scrolling columns and the content its padding", () => {
    show("/signal/main/feed/for-you");
    expect(channels().className).toContain("overflow-y-auto");
    expect(channels().className).toContain("w-64");
    const content = screen
      .getByRole("heading", { level: 1, name: "For you" })
      .closest("[tabindex='-1']");
    expect(content?.className).toContain("overflow-y-auto");
    expect(content?.className).toContain("p-8");
  });

  it.each([
    ["/signal/nowhere/feed/for-you", "No such sample scene"],
    ["/signal/main/feed/trending", "No such view"],
    ["/signal/main/topic/nowhere", "No such topic"],
  ])("says so for the unknown address %s", (hash, words) => {
    show(hash);
    expect(screen.getByRole("heading", { level: 1, name: words })).toBeInTheDocument();
    expect(screen.queryByText("Page not found")).toBeNull();
  });

  it("links an unknown scene to the first scene's For you and draws no channel list", () => {
    show("/signal/nowhere/feed/for-you");
    expect(screen.getByRole("link", { name: "Back to the sample scenes" })).toHaveAttribute(
      "href",
      "#/signal/main/feed/for-you",
    );
    expect(screen.queryByRole("navigation", { name: "Signal" })).toBeNull();
  });

  it.each(["/signal/main/topic/nowhere", "/signal/main/feed/trending"])(
    "marks no channel item current on the unknown address %s",
    (hash) => {
      show(hash);
      const links = within(channels()).getAllByRole("link");
      expect(links.filter((a) => a.getAttribute("aria-current") === "page")).toEqual([]);
    },
  );

  it("says Not built yet for pages later tasks add, inside the frame, under the page's own h1", () => {
    show("/signal/main/group/leveraged-credit");
    expect(screen.getByRole("heading", { level: 1, name: "Leveraged credit" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Not built yet" })).toBeInTheDocument();
    expect(within(channels()).getByRole("link", { name: "Leveraged credit 3" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("says the data could not be read when the slice is malformed", () => {
    const bad: LoadResult = { kind: "ok", data: { ...ok.data, signal: { scenes: [{}] } } };
    show("/signal/main/feed/for-you", bad);
    expect(screen.getByText("scenes[0].id: expected a string")).toBeInTheDocument();
  });

  it("says a slice with no scenes could not be read, with the path", () => {
    const empty: LoadResult = { kind: "ok", data: { ...ok.data, signal: { scenes: [] } } };
    show("/signal/main/feed/for-you", empty);
    expect(screen.getByText("scenes: expected at least one scene")).toBeInTheDocument();
  });

  it("says there is no Signal data when the slice is absent", () => {
    show("/signal/main/feed/for-you", {
      kind: "ok",
      data: { schema: "credit-os-data/1", issuers: [] },
    });
    expect(screen.getByText("No Signal data in this library")).toBeInTheDocument();
  });

  it("renders every declared path with every fixture parameter set", () => {
    const declared = declaredPaths(import.meta.dirname);
    expect(declared).toHaveLength(6);
    const params = fixture.params as Record<string, Record<string, string>[]>;
    let visits = 0;
    for (const pattern of declared) {
      for (const set of params[pattern] ?? []) {
        const { hash, missing } = fillParams(pattern, set);
        expect(missing).toEqual([]);
        const view = show(hash);
        expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
        const title = pattern.includes("/feed/") ? VIEW_TITLES[set["view"] ?? ""] : TITLES[pattern];
        if (title === undefined) throw new Error(`no expected title for ${hash}`);
        expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(title);
        expect(skippedLevels()).toEqual([]);
        expect(screen.queryByText("Page not found")).toBeNull();
        expect(screen.queryByText(/^No such /)).toBeNull();
        view.unmount();
        visits += 1;
      }
    }
    expect(visits).toBe(14);
  });
});

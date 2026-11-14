// Task 5: loading, error, the empty states, the Saved and topic views, and focus after Show.
// Wording comes from the predecessor's built behaviour (list 2.2) and mock states frames 2 to 7.
import type { ComponentProps } from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";
import fixture from "../../../fixtures/signal.json";
import { App } from "../../App";
import type { LoadResult } from "../../data";
import { FeedPage, type FeedEntry } from "./FeedPage";
import { readSlice } from "./slice";

function show(hash: string, slice: unknown = fixture.slice) {
  window.location.hash = `#${hash}`;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], signal: slice },
  };
  return render(<App result={result} />);
}

/** A copy of the fixture slice with scene `id` changed by `change`. */
type Changeable = {
  feed: { error: string | null };
  viewer: { role: string };
  channels: { topics: { followed: boolean }[] };
};
function withScene(id: string, change: (snapshot: Changeable) => void): unknown {
  const copy = structuredClone(fixture.slice);
  const scene = copy.scenes.find((s) => s.id === id);
  if (scene === undefined) throw new Error("the fixture holds the scene");
  change(scene.snapshot);
  return copy;
}

const CORVANE = "Corvane Packaging to close two plants as volumes fall";
const BRIGHTWELL = "Brightwell Foods extends its term loan by three years";
const HALVORSEN = "Northgate Ratings downgrades Halvorsen Marine to B+";
const AFFIRM = "Northgate Ratings affirms Oakhaven Lines at BB, outlook to positive";
const NO_SERVICE = "Signal could not be reached. Check your connection and try again.";
const REASON = "Sample data: there is no service to retry.";

const noEmpty = () => {
  expect(screen.queryByRole("heading", { name: /^No stories|^No approved|^Follow a topic/ })).toBe(
    null,
  );
  expect(screen.queryByRole("heading", { name: /^Stories you save/ })).toBe(null);
};

describe("loading", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("draws a static skeleton of three stories in a busy region, with a hidden label", () => {
    show("/signal/loading/feed/for-you");
    expect(screen.getByRole("heading", { level: 1, name: "For you" })).toBeInTheDocument();
    const region = screen.getByRole("region", { name: "Stories" });
    expect(region).toHaveAttribute("aria-busy", "true");
    expect(within(region).getByText("Loading stories")).toHaveClass("sr-only");
    expect(region.querySelectorAll("[data-skeleton-story]")).toHaveLength(3);
    expect(region.querySelector("[class*='animate']")).toBeNull();
    expect(screen.queryByRole("article")).toBeNull();
    noEmpty();
  });

  it("draws no skeleton once the feed is ready", () => {
    show("/signal/main/feed/for-you");
    expect(screen.queryByRole("region", { name: "Stories" })).toBeNull();
    expect(screen.queryByText("Loading stories")).toBeNull();
  });
});

describe("the error alert", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("says the service cannot be reached, keeps the loaded stories and a disabled Retry with its reason", () => {
    show("/signal/unreachable/feed/for-you");
    const alert = screen.getByRole("alert");
    expect(within(alert).getByText(NO_SERVICE)).toBeInTheDocument();
    const retry = within(alert).getByRole("button", { name: "Retry" });
    expect(retry).toBeDisabled();
    expect(within(alert).getByText(REASON)).toBeVisible();
    expect(retry).toHaveAccessibleDescription(REASON);
    expect(screen.getByRole("heading", { level: 2, name: CORVANE })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: BRIGHTWELL })).toBeInTheDocument();
    noEmpty();
  });

  it("draws the alert above the list", () => {
    show("/signal/unreachable/feed/for-you");
    const alert = screen.getByRole("alert");
    const first = screen.getAllByRole("article")[0] as HTMLElement;
    expect(alert.compareDocumentPosition(first) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it.each([
    ["request", "Signal could not complete that request."],
    ["unreadable", "The service sent an unreadable answer."],
  ])("says the %s error in the predecessor's words", (error, sentence) => {
    show(
      "/signal/unreachable/feed/for-you",
      withScene("unreachable", (s) => {
        s.feed.error = error;
      }),
    );
    expect(within(screen.getByRole("alert")).getByText(sentence)).toBeInTheDocument();
    expect(screen.queryByText(NO_SERVICE)).toBeNull();
    expect(screen.getByRole("button", { name: "Retry" })).toBeDisabled();
    expect(screen.getByText(REASON)).toBeVisible();
  });

  it("draws no alert when there is no error", () => {
    show("/signal/main/feed/for-you");
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.queryByRole("button", { name: "Retry" })).toBeNull();
  });
});

describe("the empty states", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  const title = (name: string) => screen.getByRole("heading", { level: 2, name });

  it("says No stories yet on a ready view with no entries and approved sources", () => {
    show("/signal/not-checked/feed/latest");
    expect(title("No stories yet")).toBeInTheDocument();
    expect(screen.getByText("New stories appear here as sources are checked.")).toBeVisible();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("says No approved sources yet on any view when no source is approved", () => {
    for (const view of ["latest", "for-you", "saved"]) {
      const { unmount } = show(`/signal/no-sources/feed/${view}`);
      expect(title("No approved sources yet")).toBeInTheDocument();
      expect(screen.getByText("Stories appear once a source is approved.")).toBeVisible();
      unmount();
    }
  });

  it("gives a writer a Propose a source link to the sources settings of the same scene", () => {
    show("/signal/no-sources/feed/latest");
    expect(screen.getByRole("link", { name: "Propose a source" })).toHaveAttribute(
      "href",
      "#/signal/no-sources/settings/sources",
    );
  });

  it("gives a reader no Propose a source", () => {
    show(
      "/signal/no-sources/feed/latest",
      withScene("no-sources", (s) => {
        s.viewer.role = "reader";
      }),
    );
    expect(title("No approved sources yet")).toBeInTheDocument();
    expect(screen.queryByText(/Propose a source/)).toBeNull();
  });

  /** The button in the page, not the channel list's star, which has the same name. */
  const inPage = (name: string) => {
    const nav = screen.getByRole("navigation", { name: "Signal" });
    const found = screen.getAllByRole("button", { name }).filter((b) => !nav.contains(b));
    if (found.length !== 1) throw new Error(`expected one "${name}" button in the page`);
    return found[0] as HTMLElement;
  };
  const star = (name: string) =>
    within(screen.getByRole("navigation", { name: "Signal" })).getByRole("button", { name });

  it("says Follow a topic to fill this view on For you when no topic is followed, listing every topic", () => {
    show("/signal/nothing-followed/feed/for-you");
    expect(title("Follow a topic to fill this view")).toBeInTheDocument();
    expect(screen.getByText("Stories on the topics you follow appear here.")).toBeVisible();
    for (const name of ["Shipping", "Packaging", "Telecoms", "Rating actions"]) {
      const toggle = inPage(`Follow ${name}`);
      expect(toggle).toHaveAttribute("aria-pressed", "false");
      expect(toggle).toHaveTextContent(new RegExp(`^${name}$`));
    }
  });

  it("follows a topic from the empty state and updates the channel list star", () => {
    show("/signal/nothing-followed/feed/for-you");
    expect(star("Follow Telecoms")).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(inPage("Follow Telecoms"));
    expect(inPage("Unfollow Telecoms")).toHaveAttribute("aria-pressed", "true");
    expect(star("Unfollow Telecoms")).toHaveAttribute("aria-pressed", "true");
    expect(title("Follow a topic to fill this view")).toBeInTheDocument();
  });

  it("follows a topic from the channel list and shows it in the empty state", () => {
    show("/signal/nothing-followed/feed/for-you");
    fireEvent.click(star("Follow Shipping"));
    expect(inPage("Unfollow Shipping")).toHaveAttribute("aria-pressed", "true");
  });

  it("says Stories you save appear here on an empty Saved view", () => {
    show("/signal/nothing-followed/feed/saved");
    expect(title("Stories you save appear here")).toBeInTheDocument();
    expect(screen.getByText("Use Save on a story to keep it.")).toBeVisible();
  });

  it("says No stories in this topic yet on a topic with no stories", () => {
    show("/signal/main/topic/telecoms");
    expect(title("No stories in this topic yet")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Telecoms" })).toBeInTheDocument();
  });

  it("says No stories yet on For you when a topic is followed but nothing is there", () => {
    show(
      "/signal/nothing-followed/feed/for-you",
      withScene("nothing-followed", (s) => {
        const first = s.channels.topics[0];
        if (first === undefined) throw new Error("the scene has topics");
        first.followed = true;
      }),
    );
    expect(title("No stories yet")).toBeInTheDocument();
  });

  it("puts the search and kind messages before the others", () => {
    show("/signal/no-sources/feed/latest");
    fireEvent.change(screen.getByRole("textbox", { name: "Search stories" }), {
      target: { value: "bonds" },
    });
    expect(title("No story matches bonds")).toBeInTheDocument();
    expect(screen.queryByText("No approved sources yet")).toBeNull();
  });

  it("draws the loading scene's views with no empty state", () => {
    show("/signal/loading/feed/saved");
    noEmpty();
  });

  it("keeps the unknown view and unknown topic states", () => {
    const { unmount } = show("/signal/main/feed/trending");
    expect(screen.getByRole("heading", { level: 1, name: "No such view" })).toBeInTheDocument();
    unmount();
    show("/signal/main/topic/nowhere");
    expect(screen.getByRole("heading", { level: 1, name: "No such topic" })).toBeInTheDocument();
  });
});

describe("the Saved and topic views", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("draws the saved stories under the title Saved (mock feed frame 3)", () => {
    show("/signal/main/feed/saved");
    expect(screen.getByRole("heading", { level: 1, name: "Saved" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: HALVORSEN })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Order of stories/ })).toBeNull();
  });

  it("draws the topic's name as the title, a Following button, keywords as tags and its stories (frame 4)", () => {
    show("/signal/main/topic/shipping");
    const title = screen.getByRole("heading", { level: 1, name: "Shipping" });
    const row = title.parentElement as HTMLElement;
    expect(within(row).getByRole("button", { name: "Following" })).toBeInTheDocument();
    const tags = within(screen.getByRole("list", { name: "Topic keywords" }));
    expect(tags.getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "charter rates",
      "tanker",
      "container line",
      "shipowner",
      "Halvorsen Marine",
    ]);
    expect(screen.getByRole("heading", { level: 2, name: HALVORSEN })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: AFFIRM })).toBeInTheDocument();
  });

  it("toggles the header button and the channel star together", () => {
    show("/signal/main/topic/telecoms");
    expect(screen.getByRole("button", { name: "Follow" })).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(screen.getByRole("button", { name: "Follow" }));
    expect(screen.getByRole("button", { name: "Following" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Unfollow Telecoms" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});

describe("a loading feed has no list controls", () => {
  const entry = (id: string): FeedEntry => ({
    kind: "digest",
    href: "#/x",
    digest: {
      id,
      digestId: "weekly-brief",
      issueId: id,
      digestName: "Weekly brief",
      monogram: "WB",
      title: id,
      date: null,
      unread: false,
      ai: false,
      points: [],
      summary: null,
      nothing: "Nothing to report",
    },
  });

  // The reader refuses entries in a loading feed, so the page is rendered directly to prove it
  // draws no pill and no Show older even if it were handed some.
  it("draws neither the new-stories pill nor Show older while loading", () => {
    const entries = {
      top: [],
      latest: [],
      waiting: { label: "2 new stories", entries: [entry("a")] },
      older: [entry("b")],
    };
    const read = readSlice(fixture.slice);
    const scene = read.kind === "ok" ? read.data.scenes[0] : undefined;
    if (scene === undefined) throw new Error("the fixture reads");
    const props: Omit<ComponentProps<typeof FeedPage>, "loading"> = {
      scene,
      title: "For you",
      freshness: { state: "checking", checked: null, failing: null, error: null },
      entries,
      startOn: "top",
      switchable: true,
      writer: true,
      error: null,
      empty: {
        view: "for-you",
        approved: true,
        propose: null,
        noneFollowed: false,
        topics: [],
        onFollow: () => undefined,
      },
      topic: null,
    };
    const { rerender } = render(<FeedPage {...props} loading={false} />);
    expect(screen.getByRole("button", { name: "Show 2 new stories" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Show older" })).toBeInTheDocument();
    rerender(<FeedPage {...props} loading />);
    expect(screen.queryByRole("button", { name: /^Show/ })).toBeNull();
  });

  it("draws none in the loading scene either", () => {
    show("/signal/loading/feed/for-you");
    expect(screen.queryByRole("button", { name: /^Show/ })).toBeNull();
  });
});

describe("focus after Show with everything revealed hidden", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("moves to the page title when the search hides every newly shown story", () => {
    show("/signal/main/feed/for-you");
    fireEvent.change(screen.getByRole("textbox", { name: "Search stories" }), {
      target: { value: "Corvane" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Show 4 new stories" }));
    const title = screen.getByRole("heading", { level: 1, name: "For you" });
    expect(title).toHaveAttribute("tabindex", "-1");
    expect(document.activeElement).toBe(title);
  });

  it("moves to the page title when the kind filter hides every story Show older brings in", () => {
    show("/signal/main/feed/for-you");
    fireEvent.click(screen.getByRole("tab", { name: "Research" }));
    fireEvent.click(screen.getByRole("button", { name: "Show older" }));
    expect(document.activeElement).toBe(screen.getByRole("heading", { level: 1 }));
  });
});

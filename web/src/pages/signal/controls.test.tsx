// The feed controls: freshness line, Top or Latest, kind tabs, search, new stories, Show older.
// Expected headlines and wording come from the mock and predecessor documents and the fixture's id
// lists (main For you: top corvane, tessaly, halvorsen, brightwell; latest corvane, tessaly,
// brightwell, halvorsen; waiting oakhaven, pellant, brightwell-clearance, oakhaven-affirm; older
// lenmark, karsten).
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

/** A copy of the fixture slice with scene `id`'s freshness replaced. */
function withFreshness(id: string, freshness: Record<string, unknown>): unknown {
  const copy = structuredClone(fixture.slice);
  const scene = copy.scenes.find((s) => s.id === id);
  if (scene === undefined) throw new Error("the fixture holds the scene");
  Object.assign(scene.snapshot.feed.freshness, freshness);
  return copy;
}

const CORVANE = "Corvane Packaging to close two plants as volumes fall";
const TESSALY = "Competition authority opens in-depth review of Tessaly Telecom's tower sale";
const HALVORSEN = "Northgate Ratings downgrades Halvorsen Marine to B+";
const BRIGHTWELL = "Brightwell Foods extends its term loan by three years";
const OAKHAVEN = "Notice of initial review: Oakhaven Lines and Pellant Terminals";
const PELLANT = "Pellant Terminals plans first bond issue";
const CLEARANCE = "Authority clears Brightwell Foods' dairy purchase with conditions";
const AFFIRM = "Northgate Ratings affirms Oakhaven Lines at BB, outlook to positive";
const LENMARK = "Lenmark Retail secures a covenant waiver from its banks";
const KARSTEN = "Karsten Power files its annual report with the securities regulator";
const WEEKLY = "Leveraged credit: the week to 13 November";

/** The headlines drawn, in order. */
const headlines = () =>
  screen
    .getAllByRole("article")
    .map((a) => within(a).getByRole("heading", { level: 2 }).textContent);
const noArticles = () => expect(screen.queryByRole("article")).not.toBeInTheDocument();
const tab = (name: string) => screen.getByRole("tab", { name });
const search = () => screen.getByRole("textbox", { name: "Search stories" });
const type = (value: string) => fireEvent.change(search(), { target: { value } });

describe("the freshness line", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("says Sources checked with the delivered time, with a filled circle", () => {
    const { container } = show("/signal/main/feed/for-you");
    expect(screen.getByText("Sources checked 6 min ago")).toBeInTheDocument();
    expect(container.querySelector("[data-shape='filled circle']")).not.toBeNull();
  });

  it("draws the title row as the title, then the freshness, then the order buttons", () => {
    show("/signal/main/feed/for-you");
    const title = screen.getByRole("heading", { level: 1, name: "For you" });
    const row = title.parentElement;
    expect(row?.textContent).toMatch(/^For youSources checked 6 min agoTopLatest$/);
  });

  it("says Checking sources with a ring while the first check runs", () => {
    const { container } = show("/signal/no-name/feed/for-you");
    expect(screen.getByText("Checking sources")).toBeInTheDocument();
    expect(container.querySelector("[data-shape='ring']")).not.toBeNull();
    expect(container.querySelector("[class*='animate']")).toBeNull();
  });

  it("says Sources not checked yet with a ring", () => {
    const { container } = show("/signal/not-checked/feed/for-you");
    expect(screen.getByText("Sources not checked yet")).toBeInTheDocument();
    expect(container.querySelector("[data-shape='ring']")).not.toBeNull();
  });

  it("says Source status unavailable with a warning triangle", () => {
    const { container } = show(
      "/signal/main/feed/for-you",
      withFreshness("main", { state: "unavailable", checked: null }),
    );
    expect(screen.getByText("Source status unavailable")).toBeInTheDocument();
    expect(container.querySelector("[data-shape='triangle']")).not.toBeNull();
  });

  it("appends the delivered failing text and the delivered error text, with a triangle", () => {
    const { container } = show(
      "/signal/main/feed/for-you",
      withFreshness("main", {
        failing: "2 sources failing",
        error: "the check reported an error",
      }),
    );
    expect(
      screen.getByText(
        "Sources checked 6 min ago · 2 sources failing · the check reported an error",
      ),
    ).toBeInTheDocument();
    expect(container.querySelector("[data-shape='triangle']")).not.toBeNull();
  });

  it("appends only the failing text when there is no error text", () => {
    show("/signal/main/feed/for-you", withFreshness("main", { failing: "1 source failing" }));
    expect(screen.getByText("Sources checked 6 min ago · 1 source failing")).toBeInTheDocument();
  });

  it("draws the page title at the mock's heading size", () => {
    show("/signal/main/feed/for-you");
    expect(screen.getByRole("heading", { level: 1 }).className).toContain("text-h2");
  });
});

describe("Top or Latest", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("starts on Top for For you, and Latest reorders by the view's latest ids", () => {
    show("/signal/main/feed/for-you");
    const group = screen.getByRole("radiogroup", { name: "Order of stories" });
    const top = within(group).getByRole("radio", { name: "Top" });
    const latest = within(group).getByRole("radio", { name: "Latest" });
    expect(top).toBeChecked();
    expect(headlines()).toEqual([CORVANE, TESSALY, HALVORSEN, BRIGHTWELL]);
    fireEvent.click(latest);
    expect(latest).toBeChecked();
    expect(headlines()).toEqual([CORVANE, TESSALY, BRIGHTWELL, HALVORSEN]);
    fireEvent.click(top);
    expect(headlines()).toEqual([CORVANE, TESSALY, HALVORSEN, BRIGHTWELL]);
  });

  it("starts the Latest route on Latest", () => {
    show("/signal/main/feed/latest");
    expect(screen.getByRole("radio", { name: "Latest" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Top" })).not.toBeChecked();
  });

  it("is reachable and operable from the keyboard", () => {
    show("/signal/main/feed/for-you");
    const top = screen.getByRole("radio", { name: "Top" });
    top.focus();
    fireEvent.keyDown(top, { key: "ArrowRight" });
    const latest = screen.getByRole("radio", { name: "Latest" });
    expect(latest).toHaveFocus();
    fireEvent.keyDown(latest, { key: " " });
    fireEvent.keyUp(latest, { key: " " });
    expect(latest).toBeChecked();
    expect(headlines()).toEqual([CORVANE, TESSALY, BRIGHTWELL, HALVORSEN]);
  });

  it("starts each view afresh: moving to another view resets the order, kind and search", () => {
    show("/signal/main/feed/for-you");
    fireEvent.click(screen.getByRole("radio", { name: "Latest" }));
    fireEvent.click(tab("News"));
    type("Corvane");
    window.location.hash = "#/signal/main/feed/saved";
    fireEvent(window, new HashChangeEvent("hashchange"));
    expect(screen.getByRole("radio", { name: "Top" })).toBeChecked();
    expect(tab("All")).toHaveAttribute("aria-selected", "true");
    expect(search()).toHaveValue("");
  });
});

describe("the kind tabs", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("offers All, Regulators, News, Ratings and Research, All selected", () => {
    show("/signal/main/feed/for-you");
    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual([
      "All",
      "Regulators",
      "News",
      "Ratings",
      "Research",
    ]);
    expect(tab("All")).toHaveAttribute("aria-selected", "true");
  });

  it.each([
    ["Regulators", [TESSALY]],
    ["News", [CORVANE, BRIGHTWELL]],
    ["Ratings", [HALVORSEN]],
    ["All", [CORVANE, TESSALY, HALVORSEN, BRIGHTWELL]],
  ])("%s shows its stories only, in the view's order", (name, expected) => {
    show("/signal/main/feed/for-you");
    fireEvent.click(tab(name));
    expect(tab(name)).toHaveAttribute("aria-selected", "true");
    expect(headlines()).toEqual(expected);
  });

  it("gives the kind empty state for Research", () => {
    show("/signal/main/feed/for-you");
    fireEvent.click(tab("Research"));
    noArticles();
    expect(
      screen.getByRole("heading", { level: 2, name: "No stories of this kind here" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Choose All to see every kind.")).toBeInTheDocument();
  });

  it("shows a digest card under All only", () => {
    show("/signal/ai-on/feed/for-you");
    expect(screen.getByText(WEEKLY)).toBeInTheDocument();
    fireEvent.click(tab("News"));
    expect(screen.queryByText(WEEKLY)).not.toBeInTheDocument();
    fireEvent.click(tab("All"));
    expect(screen.getByText(WEEKLY)).toBeInTheDocument();
  });

  it("is operable from the keyboard: arrows move focus, Enter selects", () => {
    show("/signal/main/feed/for-you");
    const all = tab("All");
    all.focus();
    fireEvent.keyDown(all, { key: "ArrowRight" });
    const regulators = tab("Regulators");
    expect(regulators).toHaveFocus();
    fireEvent.keyDown(regulators, { key: "Enter" });
    fireEvent.keyUp(regulators, { key: "Enter" });
    expect(regulators).toHaveAttribute("aria-selected", "true");
    expect(headlines()).toEqual([TESSALY]);
  });
});

describe("the search", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("is a field named Search stories with that placeholder", () => {
    show("/signal/main/feed/for-you");
    expect(search()).toHaveAttribute("placeholder", "Search stories");
  });

  it.each([
    ["a headline word, any case", "tESSALY", [TESSALY]],
    ["a summary word", "margin rises", [BRIGHTWELL]],
    ["a source name", "northgate", [HALVORSEN]],
    ["a tag", "DISPOSALS", [TESSALY]],
  ])("matches %s", (_name, query, expected) => {
    show("/signal/main/feed/for-you");
    type(query);
    expect(headlines()).toEqual(expected);
  });

  it("combines with the kind tab", () => {
    show("/signal/main/feed/for-you");
    fireEvent.click(tab("News"));
    type("credit ledger");
    expect(headlines()).toEqual([BRIGHTWELL]);
  });

  it("gives the search empty state with the query in the title", () => {
    show("/signal/main/feed/for-you");
    type("zzzz");
    noArticles();
    expect(
      screen.getByRole("heading", { level: 2, name: "No story matches zzzz" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Check the spelling or clear the search.")).toBeInTheDocument();
  });

  it("names the search before the kind when both leave nothing", () => {
    show("/signal/main/feed/for-you");
    fireEvent.click(tab("Research"));
    type("zzzz");
    expect(screen.getByRole("heading", { name: "No story matches zzzz" })).toBeInTheDocument();
    expect(screen.queryByText("No stories of this kind here")).not.toBeInTheDocument();
  });

  it("hides a digest card while a search is typed", () => {
    show("/signal/ai-on/feed/for-you");
    type("Corvane");
    expect(screen.queryByText(WEEKLY)).not.toBeInTheDocument();
  });

  it("clears with Escape when it holds text", () => {
    show("/signal/main/feed/for-you");
    type("zzzz");
    fireEvent.keyDown(search(), { key: "Escape" });
    expect(search()).toHaveValue("");
    expect(headlines()).toHaveLength(4);
  });

  it("is focused by the / key, except from another field or while a dialog is open", () => {
    show("/signal/main/feed/for-you");
    fireEvent.keyDown(document.body, { key: "/" });
    expect(search()).toHaveFocus();
    search().blur();
    const other = document.createElement("textarea");
    document.body.append(other);
    other.focus();
    fireEvent.keyDown(other, { key: "/" });
    expect(search()).not.toHaveFocus();
    other.remove();
    const dialog = document.createElement("div");
    dialog.setAttribute("role", "dialog");
    document.body.append(dialog);
    fireEvent.keyDown(document.body, { key: "/" });
    expect(search()).not.toHaveFocus();
    dialog.remove();
  });
});

describe("new stories and Show older", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("draws the pill with the delivered label; Show puts the waiting entries on top and removes it", () => {
    show("/signal/main/feed/for-you");
    expect(screen.getByText("4 new stories")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show 4 new stories" }));
    expect(headlines()).toEqual([
      OAKHAVEN,
      PELLANT,
      CLEARANCE,
      AFFIRM,
      CORVANE,
      TESSALY,
      HALVORSEN,
      BRIGHTWELL,
    ]);
    expect(screen.queryByText("4 new stories")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Show 4 new stories/ })).not.toBeInTheDocument();
  });

  it("filters the revealed entries too", () => {
    show("/signal/main/feed/for-you");
    fireEvent.click(screen.getByRole("button", { name: "Show 4 new stories" }));
    fireEvent.click(tab("Ratings"));
    expect(headlines()).toEqual([AFFIRM, HALVORSEN]);
  });

  it("draws no pill where nothing waits", () => {
    show("/signal/main/feed/latest");
    expect(screen.queryByRole("button", { name: /new stor/ })).not.toBeInTheDocument();
  });

  it("draws Show older under the list; it appends the older entries and goes away", () => {
    show("/signal/main/feed/for-you");
    fireEvent.click(screen.getByRole("button", { name: "Show older" }));
    expect(headlines()).toEqual([CORVANE, TESSALY, HALVORSEN, BRIGHTWELL, LENMARK, KARSTEN]);
    expect(screen.queryByRole("button", { name: "Show older" })).not.toBeInTheDocument();
  });

  it("draws no Show older when the view has no older entries", () => {
    show("/signal/reader/feed/for-you");
    expect(screen.queryByRole("button", { name: /Show older/ })).not.toBeInTheDocument();
    show("/signal/main/feed/latest");
    expect(screen.queryByRole("button", { name: /Show older/ })).not.toBeInTheDocument();
  });
});

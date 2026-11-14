// Whole-branch findings L4 and I1: the feed's kind tabs and Settings' section tabs each have a tab
// panel the selected tab's aria-controls names, and an issue's data id is not a DOM id.
import { fireEvent, render, screen, within } from "@testing-library/react";
import fixture from "../../../fixtures/signal.json";
import { App } from "../../App";
import type { LoadResult } from "../../data";

function show(hash: string) {
  window.location.hash = `#${hash}`;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], signal: fixture.slice },
  };
  return render(<App result={result} />);
}
const selected = () => {
  const tab = screen.getAllByRole("tab").find((t) => t.getAttribute("aria-selected") === "true");
  if (tab === undefined) throw new Error("a tab is selected");
  return tab;
};
/** The panel the selected tab names: it exists, is a tabpanel, and is labelled by that tab. */
function panelOf(tab: HTMLElement): HTMLElement {
  const id = tab.getAttribute("aria-controls");
  const panel = id === null ? null : document.getElementById(id);
  if (panel === null) throw new Error("the selected tab names a panel that is on the page");
  expect(panel).toHaveAttribute("role", "tabpanel");
  expect(panel).toHaveAttribute("aria-labelledby", tab.id);
  return panel;
}

describe("the feed's kind tabs have a panel", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("holds the filtered list in the panel the selected tab names", () => {
    show("/signal/main/feed/for-you");
    const panel = within(panelOf(selected()));
    expect(panel.getAllByRole("article").length).toBeGreaterThan(0);
  });

  it("follows the selection: the Regulators panel holds only regulator stories, and is the one named", () => {
    show("/signal/main/feed/for-you");
    fireEvent.click(screen.getByRole("tab", { name: "Regulators" }));
    const tab = selected();
    expect(tab).toHaveTextContent("Regulators");
    const panel = within(panelOf(tab));
    expect(panel.getByRole("heading", { level: 2, name: /Tessaly Telecom/ })).toBeInTheDocument();
    expect(panel.queryByRole("heading", { level: 2, name: /Corvane/ })).toBeNull();
  });

  it("holds the no-match and empty states too, so every state sits in the named panel", () => {
    show("/signal/main/feed/for-you");
    fireEvent.click(screen.getByRole("tab", { name: "Research" }));
    expect(
      within(panelOf(selected())).getByRole("heading", { name: "No stories of this kind here" }),
    ).toBeInTheDocument();
  });

  it("leaves the search field and the tab list outside the panel", () => {
    show("/signal/main/feed/for-you");
    const panel = panelOf(selected());
    expect(within(panel).queryByRole("textbox", { name: "Search stories" })).toBeNull();
    expect(within(panel).queryByRole("tablist")).toBeNull();
  });
});

describe("Settings' section tabs have a panel", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("holds the section in the panel the selected tab names", () => {
    show("/signal/main/settings/topics");
    const tab = selected();
    expect(tab).toHaveTextContent("Topics");
    expect(within(panelOf(tab)).getByText("Shipping")).toBeInTheDocument();
  });

  it("draws a reader's two sections, and the panel of the one chosen", () => {
    show("/signal/reader/settings/notifications");
    expect(screen.getAllByRole("tab")).toHaveLength(2);
    expect(selected()).toHaveTextContent("Notifications");
    expect(panelOf(selected())).toBeInTheDocument();
  });

  it("selects no tab and names no panel for a section that does not exist", () => {
    show("/signal/main/settings/nowhere");
    expect(
      screen.getAllByRole("tab").every((t) => t.getAttribute("aria-selected") === "false"),
    ).toBe(true);
    expect(screen.queryByRole("tabpanel")).toBeNull();
    expect(screen.getByText("No such settings section")).toBeInTheDocument();
  });

  it("selects no tab for a section a reader may not open, and says so", () => {
    show("/signal/reader/settings/sources");
    expect(screen.queryByRole("tabpanel")).toBeNull();
    expect(screen.getByText("This section is for writers")).toBeInTheDocument();
  });
});

describe("I1: an issue heading carries its id as data, not as a DOM id", () => {
  afterEach(() => {
    window.location.hash = "";
  });

  it("marks the heading with a data attribute and leaves the id attribute off", () => {
    show("/signal/ai-on/digest/weekly-brief");
    const title = document.querySelector('[data-issue="week-6-nov"]');
    expect(title?.tagName).toBe("H3");
    expect(document.getElementById("week-6-nov")).toBeNull();
  });
});

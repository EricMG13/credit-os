// The Sources section (mock settings frame 3). Expected wording, order and ranks are the mock's and
// the fixture's, not the code's.
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

const page = () => within(document.getElementById("signal-content") as HTMLElement);
const table = () => page().getByRole("grid", { name: "Sources" });
const names = () =>
  within(table())
    .getAllByRole("row")
    .slice(1)
    .map((r) => within(r).getAllByRole("rowheader")[0]?.querySelector("b")?.textContent ?? "");
const rows = () => within(table()).getAllByRole("row").slice(1);
const header = (name: string) => within(table()).getByRole("columnheader", { name });

const MOCK_ORDER = [
  "Harbour Wire",
  "Regulatory Gazette",
  "Northgate Ratings",
  "The Meridian Post",
  "Freight Monitor",
];

afterEach(() => {
  window.location.hash = "";
});

describe("Sources (frame 3)", () => {
  it("draws the heading, the intro line and the columns the mock draws", () => {
    show("/signal/main/settings/sources");
    expect(page().getByRole("heading", { level: 1 }).textContent).toBe("Settings");
    expect(page().getByRole("heading", { level: 2 }).textContent).toBe("Sources");
    expect(
      page().getByText(
        "Stories come only from approved sources. Anyone who writes can propose one; the owner approves.",
      ),
    ).toBeTruthy();
    const heads = within(table()).getAllByRole("columnheader");
    expect(heads.map((h) => h.textContent)).toEqual([
      "Source",
      "State",
      "Health",
      "Last check and item",
      "Items per week, 6 weeks",
    ]);
    expect(names()).toEqual(MOCK_ORDER);
  });

  it("draws the six states as badges with their words, and the failing reason as text", () => {
    show("/signal/main/settings/sources");
    const text = rows().map((r) => r.textContent);
    expect(text[0]).toContain("Approved");
    expect(text[0]).toContain("Healthy");
    expect(text[1]).toContain("Quiet");
    expect(text[1]).toContain("No item for 9 days");
    expect(text[2]).toContain("Failing");
    expect(text[2]).toContain("The feed returned an error at the last 3 checks");
    expect(text[3]).toContain("Paused");
    expect(text[3]).toContain("By the owner, 2 Nov");
    expect(text[4]).toContain("Proposed");
    expect(text[4]).toContain("By Tobias O, yesterday");
    for (const word of ["Proposed", "Approved", "Paused", "Healthy", "Quiet", "Failing"]) {
      expect(within(table()).getAllByText(word).length).toBeGreaterThan(0);
    }
    // the last check is in the DOM twice (the column from xl up, the Source cell below it)
    expect(within(rows()[0] as HTMLElement).getByText("6 min ago")).toBeTruthy();
    expect(within(rows()[0] as HTMLElement).getByText("Last check 6 min ago")).toBeTruthy();
    expect(text[0]).toContain("Last item 2 h ago");
    expect(text[2]).toContain("Last item yesterday");
  });

  it("reads n.a. for the health, last check and weeks a source does not have", () => {
    show("/signal/main/settings/sources");
    const meridian = rows()[3] as HTMLElement;
    expect(within(meridian).getAllByText("n.a.")).toHaveLength(1);
    const freight = rows()[4] as HTMLElement;
    expect(within(freight).getAllByText("n.a.")).toHaveLength(3);
    expect(within(freight).queryByRole("img")).toBeNull();
  });

  it("draws a zero week as a stub and a week with no reading as an empty slot, never alike", () => {
    show("/signal/main/settings/sources");
    const slots = (row: number) =>
      Array.from((rows()[row] as HTMLElement).querySelectorAll("[data-week-state]"), (e) =>
        e.getAttribute("data-week-state"),
      );
    expect(slots(0)).toEqual(["value", "value", "value", "value", "value", "value"]);
    expect(slots(1)).toEqual(["value", "value", "value", "value", "value", "zero"]);
    expect(slots(2)).toEqual(["value", "value", "value", "value", "empty", "value"]);
    expect(slots(3)).toEqual(["value", "value", "value", "value", "empty", "empty"]);
    const gazette = within(rows()[1] as HTMLElement).getByRole("img");
    expect(gazette.getAttribute("aria-label")).toBe(
      "Items per week. Week of 6 Oct: 4; Week of 13 Oct: 6; Week of 20 Oct: 3; Week of 27 Oct: 5; Week of 3 Nov: 1; Week of 10 Nov: 0",
    );
    const northgate = within(rows()[2] as HTMLElement).getByRole("img");
    expect(northgate.getAttribute("aria-label")).toContain("Week of 3 Nov: no reading");
  });

  it("sorts by Source, State and Health by the delivered ranks, both ways, with aria-sort", () => {
    show("/signal/main/settings/sources");
    expect(header("Items per week, 6 weeks").getAttribute("aria-sort")).toBeNull();
    const cases: [string, string[], string[]][] = [
      [
        "Source",
        // name ranks 1..5: Freight, Harbour, Northgate, Regulatory, Meridian
        [
          "Freight Monitor",
          "Harbour Wire",
          "Northgate Ratings",
          "Regulatory Gazette",
          "The Meridian Post",
        ],
        [
          "The Meridian Post",
          "Regulatory Gazette",
          "Northgate Ratings",
          "Harbour Wire",
          "Freight Monitor",
        ],
      ],
      [
        "State",
        // state ranks: Approved 1 (three, slice order), Paused 2, Proposed 3
        [
          "Harbour Wire",
          "Regulatory Gazette",
          "Northgate Ratings",
          "The Meridian Post",
          "Freight Monitor",
        ],
        [
          "Freight Monitor",
          "The Meridian Post",
          "Harbour Wire",
          "Regulatory Gazette",
          "Northgate Ratings",
        ],
      ],
      [
        "Health",
        // health ranks Healthy 1, Quiet 2, Failing 3; no health last both ways
        [
          "Harbour Wire",
          "Regulatory Gazette",
          "Northgate Ratings",
          "The Meridian Post",
          "Freight Monitor",
        ],
        [
          "Northgate Ratings",
          "Regulatory Gazette",
          "Harbour Wire",
          "The Meridian Post",
          "Freight Monitor",
        ],
      ],
    ];
    for (const [name, up, down] of cases) {
      fireEvent.click(header(name));
      expect(header(name).getAttribute("aria-sort")).toBe("ascending");
      expect(names()).toEqual(up);
      fireEvent.click(header(name));
      expect(header(name).getAttribute("aria-sort")).toBe("descending");
      expect(names()).toEqual(down);
    }
    expect(header("State").getAttribute("aria-sort")).toBe("none");
  });

  it("fits 1024px by class contract: one column below xl, wrapping tab row, last check moves into the Source cell", () => {
    show("/signal/main/settings/sources");
    const list = page().getByRole("tablist", { name: "Settings sections" });
    expect(list.className).toMatch(/(^| )flex-row( |$)/);
    expect(list.className).toContain("flex-wrap");
    expect(list.className).toContain("xl:flex-col");
    expect(list.parentElement?.className).toContain("xl:grid-cols-[200px_minmax(0,1fr)]");
    // the column and its copy under the kind are never both shown: each hidden by display
    const column = header("Last check and item");
    expect(column.className).toContain("max-xl:hidden");
    const first = rows()[0] as HTMLElement;
    const own = within(first).getAllByRole("rowheader")[0] as HTMLElement;
    const copy = own.querySelector("[data-last-check]");
    expect(copy?.className).toContain("xl:hidden");
    expect(copy?.textContent).toBe("Last check 6 min agoLast item 2 h ago");
    expect(within(first).getAllByRole("gridcell")[2]?.className).toContain("max-xl:hidden");
    // the source name wraps
    expect(within(own).getByText("Harbour Wire").className).not.toContain("nowrap");
    const freight = within(rows()[4] as HTMLElement).getAllByRole("rowheader")[0] as HTMLElement;
    expect(freight.querySelector("[data-last-check]")?.textContent).toBe("Last check n.a.");
  });

  it("has the propose button disabled with its reason in view and tied to it", () => {
    show("/signal/main/settings/sources");
    const button = page().getByRole("button", { name: "Propose a source" });
    expect((button as HTMLButtonElement).disabled).toBe(true);
    const reason = page().getByText("Sample data: sources cannot be proposed here.");
    expect(button.getAttribute("aria-describedby")).toBe(reason.id);
  });

  it("says a reader's address for Sources is for writers", () => {
    show("/signal/reader/settings/sources");
    expect(page().getByText("This section is for writers")).toBeTruthy();
    expect(page().queryByRole("grid")).toBeNull();
    expect(page().queryByRole("button", { name: /Propose/ })).toBeNull();
  });

  it("states there are no sources when the list is empty, with no table", () => {
    show("/signal/no-sources/settings/sources");
    expect(page().getByText("No sources yet.")).toBeTruthy();
    expect(page().queryByRole("grid")).toBeNull();
  });

  it("draws a scene's single source with no weeks as n.a.", () => {
    show("/signal/ai-on/settings/sources");
    expect(within(table()).getAllByText("n.a.")).toHaveLength(1);
    expect(screen.queryByRole("img")).toBeNull();
  });
});

import { readFileSync } from "node:fs";
import path from "node:path";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import type { LibraryData } from "@/data";
import { SourceContext } from "../source";
import { routes } from "./routes";

type Json = Record<string, unknown>;

const fixture = JSON.parse(
  readFileSync(
    path.resolve(import.meta.dirname, "..", "..", "..", "fixtures", "library.json"),
    "utf8",
  ),
) as { issuers: LibraryData["issuers"]; slice: Json; params: Record<string, Json[]> };

const PATH = "/library/:issuer/:run/changes";

function renderChanges(
  run: string,
  library: unknown = fixture.slice,
  issuer = "halden-aerostructures",
) {
  const data: LibraryData = { schema: "credit-os-data/1", issuers: fixture.issuers, library };
  const route = routes.find((r) => r.path === PATH);
  if (route === undefined) throw new Error("no changes route");
  return render(
    <SourceContext.Provider value={data}>{route.render({ issuer, run })}</SourceContext.Provider>,
  );
}

const cards = () => screen.getAllByRole("listitem").filter((li) => li.tagName === "LI");
const cardOf = (measure: string) => {
  const card = screen.getByText(measure, { selector: "strong" }).closest("li");
  if (card === null) throw new Error(`no card for ${measure}`);
  return card;
};
const click = (element: HTMLElement) => {
  fireEvent.click(element);
};
const presentation = () => screen.getByRole("radiogroup", { name: "Presentation" });

describe("the changes route", () => {
  it("is titled Changes, full bleed, and the fixture visits every state of the page", () => {
    const route = routes.find((r) => r.path === PATH);
    expect(route?.title).toBe("Changes");
    expect(route?.layout).toBe("bleed");
    expect(fixture.params[PATH]?.map((p) => p["run"])).toEqual([
      "2026-09-30",
      "2026-06-30",
      "2026-03-31",
      "2025-09-30",
    ]);
  });
});

describe("Changes, the mock's compared run", () => {
  it("draws the issuer as the one h1, the Changes tab as current, and the delivered heading", () => {
    renderChanges("2026-09-30");
    expect(screen.getByRole("heading", { level: 1, name: "Halden Aerostructures" })).toBeVisible();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Changes" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Changes" })).toHaveAttribute(
      "href",
      "#/library/halden-aerostructures/2026-09-30/changes",
    );
    expect(
      screen.getByRole("heading", { level: 2, name: "What changed since 30 June 2026" }),
    ).toBeVisible();
    expect(
      screen.getByText("Six changes to the credit profile, three modules with a changed finding."),
    ).toBeVisible();
  });

  it("draws one card per change in the module's order, with value, from and cause then effect", () => {
    renderChanges("2026-09-30");
    const measures = screen
      .getAllByText(/./, { selector: "strong" })
      .map((strong) => strong.textContent);
    expect(measures).toEqual([
      "Net leverage",
      "EBITDA margin",
      "Liquidity",
      "Interest cover",
      "Rating outlook",
      "Refinancing of the 2028 notes",
    ]);
    const leverage = cardOf("Net leverage");
    expect(within(leverage).getByText("4.6x")).toBeVisible();
    expect(leverage).toHaveTextContent("from 4.9x");
    expect(within(leverage).getByText("Value")).toBeVisible();
    expect(leverage).toHaveTextContent(
      "EBITDA grew 10% while net debt rose 3%. The outlook moves from negative to stable.",
    );
    expect(cardOf("Liquidity")).toHaveTextContent("USD 412m");
    expect(cardOf("Rating outlook")).toHaveTextContent("Conclusion");
  });

  it("draws the delivered direction text with the mock's chevrons, a flat mark, and none for none", () => {
    renderChanges("2026-09-30");
    const mark = (card: HTMLElement) => card.querySelector("[data-direction]");
    const down = cardOf("Net leverage");
    expect(down).toHaveTextContent("Lower by 0.3x");
    expect(mark(down)).toHaveAttribute("data-direction", "down");
    expect(mark(down)).toHaveClass("rotate-45", "border-r-[1.5px]", "border-b-[1.5px]");
    const up = cardOf("EBITDA margin");
    expect(up).toHaveTextContent("Higher by 0.6 points");
    expect(mark(up)).toHaveAttribute("data-direction", "up");
    expect(mark(up)).toHaveClass("-rotate-135", "border-r-[1.5px]", "border-b-[1.5px]");
    for (const measure of ["Rating outlook", "Refinancing of the 2028 notes"]) {
      const flat = cardOf(measure);
      expect(mark(flat)).toHaveAttribute("data-direction", "flat");
      expect(mark(flat)).toHaveClass("h-[1.5px]", "w-3.5", "bg-current");
      expect(mark(flat)).not.toHaveClass("rotate-45");
      expect(mark(flat)).not.toHaveClass("-rotate-135");
    }
    for (const m of [mark(down), mark(up), mark(cardOf("Rating outlook"))]) {
      expect(m).toHaveClass("mx-1");
    }
    expect(cardOf("Rating outlook")).toHaveTextContent("Changed");
    expect(cardOf("Refinancing of the 2028 notes")).toHaveTextContent("Later by six months");
    expect(document.querySelectorAll("svg[aria-hidden='true'][class*='size-3']")).toHaveLength(0);
  });

  it("draws the card's figure at the mock's weight 500", () => {
    renderChanges("2026-09-30");
    const figure = within(cardOf("Net leverage")).getByText("4.6x");
    expect(figure).toHaveClass("font-medium");
    expect(figure).not.toHaveClass("font-semibold");
  });

  it("reads from n.a. with no direction mark and no direction text when the earlier figure is missing", () => {
    renderChanges("2026-09-30");
    const cover = cardOf("Interest cover");
    expect(cover).toHaveTextContent("2.4x");
    expect(within(cover).getByText("n.a.")).toBeVisible();
    expect(cover).toHaveTextContent(/from\s*n\.a\./);
    expect(cover.querySelectorAll("[data-direction]")).toHaveLength(0);
    expect(cover).not.toHaveTextContent(/Lower|Higher|Changed|Later/);
    expect(cover).toHaveTextContent(
      "The earlier run did not establish cash interest. No comparison can be made; the figure is new.",
    );
  });

  it("gives each change one trace control named for the change, and none for a change with no trace", () => {
    renderChanges("2026-09-30");
    expect(screen.getAllByRole("button", { name: "Show sources for this change" })).toHaveLength(6);
    cleanup();
    renderChanges("2026-03-31");
    expect(screen.queryAllByRole("button", { name: "Show sources for this change" })).toHaveLength(
      0,
    );
  });

  it("opens the trace drawer of a change", () => {
    renderChanges("2026-09-30");
    const control = within(cardOf("Net leverage")).getByRole("button", {
      name: "Show sources for this change",
    });
    click(control);
    expect(screen.getByRole("dialog", { name: "Sources for net leverage" })).toBeVisible();
  });
});

describe("Changes, the Table side", () => {
  const openTable = () => {
    click(within(presentation()).getByRole("radio", { name: "Table" }));
  };

  it("draws the toggle Presentation with Cards chosen first and no Chart side", () => {
    renderChanges("2026-09-30");
    const radios = within(presentation()).getAllByRole("radio");
    expect(radios.map((r) => r.textContent)).toEqual(["Cards", "Table"]);
    expect(within(presentation()).getByRole("radio", { name: "Cards" })).toBeChecked();
    expect(cards().length).toBeGreaterThan(0);
  });

  it("switches by pointer to the table, headed by the delivered labels, and back", () => {
    renderChanges("2026-09-30");
    openTable();
    expect(
      screen.getByRole("heading", { level: 3, name: "Earlier against current" }),
    ).toBeVisible();
    expect(screen.getByText("All six changes, in the order the module wrote them.")).toBeVisible();
    const table = screen.getByRole("table", { name: "Earlier against current" });
    const heads = within(table)
      .getAllByRole("columnheader")
      .map((h) => h.textContent);
    expect(heads).toEqual(["Change", "30 Jun 2026", "30 Sep 2026", "Sources"]);
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(7);
    const cells = (row: HTMLElement) =>
      [within(row).getByRole("rowheader"), ...within(row).getAllByRole("cell")].map(
        (c) => c.textContent,
      );
    expect(cells(rows[1] as HTMLElement).slice(0, 3)).toEqual(["Net leverage", "4.9x", "4.6x"]);
    expect(cells(rows[3] as HTMLElement).slice(0, 3)).toEqual([
      "Liquidity",
      "USD 455m",
      "USD 412m",
    ]);
    expect(cells(rows[6] as HTMLElement).slice(0, 3)).toEqual([
      "Refinancing of the 2028 notes",
      "By 31 Dec 2026",
      "By 30 Jun 2027",
    ]);
    click(within(presentation()).getByRole("radio", { name: "Cards" }));
    expect(screen.queryByRole("table")).toBeNull();
    expect(cards().length).toBeGreaterThan(0);
  });

  it("switches by keyboard: focus the Table choice and press Space", () => {
    renderChanges("2026-09-30");
    const table = within(presentation()).getByRole("radio", { name: "Table" });
    table.focus();
    expect(table).toHaveFocus();
    fireEvent.keyDown(table, { key: " " });
    fireEvent.keyUp(table, { key: " " });
    expect(screen.getByRole("table", { name: "Earlier against current" })).toBeVisible();
    expect(table).toBeChecked();
  });

  it("draws n.a. in the earlier column of Interest cover, as missing and not zero", () => {
    renderChanges("2026-09-30");
    openTable();
    const row = within(screen.getByRole("table")).getByRole("row", { name: /Interest cover/ });
    const [earlier, current] = within(row).getAllByRole("cell");
    expect(earlier).toHaveTextContent("n.a.");
    expect(earlier).not.toHaveTextContent("0");
    expect(current).toHaveTextContent("2.4x");
    expect(earlier).toHaveClass("text-right");
  });

  it("keeps one trace control per row, shown by the row's hover through the card's selector", () => {
    const { container } = renderChanges("2026-09-30");
    openTable();
    const wrapper = container.querySelector("table")?.closest("[class*='tbody_tr:hover_button']");
    expect(wrapper?.className).toContain("[&_tbody_tr:hover_button]:opacity-100");
    expect(screen.getAllByRole("button", { name: "Show sources for this change" })).toHaveLength(6);
  });

  it("keeps no skipped heading level in either presentation", () => {
    renderChanges("2026-09-30");
    const levels = () => screen.getAllByRole("heading").map((h) => Number(h.tagName.slice(1)));
    expect(levels().slice(0, 2)).toEqual([1, 2]);
    openTable();
    expect(levels().slice(0, 3)).toEqual([1, 2, 3]);
  });
});

describe("Changes, a withheld value and a zero", () => {
  it("draws Withheld with its reason in the card and the table, and zero as 0", () => {
    renderChanges("2026-03-31");
    const margin = cardOf("EBITDA margin");
    expect(within(margin).getByText("Withheld")).toBeVisible();
    expect(margin).toHaveTextContent(
      "Withheld until the financial performance module is delivered",
    );
    expect(margin).toHaveTextContent("from 22.0%");
    const drawn = cardOf("Drawn on the facility, USD m");
    expect(drawn).toHaveTextContent("0");
    expect(drawn).toHaveTextContent("from 40");
    click(within(presentation()).getByRole("radio", { name: "Table" }));
    const row = within(screen.getByRole("table")).getByRole("row", { name: /EBITDA margin/ });
    expect(within(row).getByText("Withheld")).toBeVisible();
    const zero = within(screen.getByRole("table")).getByRole("row", { name: /Drawn on/ });
    expect(within(zero).getAllByRole("cell")[1]).toHaveTextContent("0");
    expect(within(zero).getAllByRole("cell")[1]).not.toHaveTextContent("n.a.");
  });
});

describe("Changes, the Modules section", () => {
  it("draws the delivered summary and each module's change state", () => {
    renderChanges("2026-09-30");
    expect(screen.getByRole("heading", { level: 2, name: "Modules" })).toBeVisible();
    expect(screen.getByText("3 changed, 9 unchanged, 1 not assessable")).toBeVisible();
    const list = screen.getByRole("heading", { level: 2, name: "Modules" }).closest("section");
    const items = within(list as HTMLElement).getAllByRole("listitem");
    expect(items).toHaveLength(5);
    expect(items[0]).toHaveTextContent("Capital structure");
    expect(items[0]).toHaveTextContent("Changed");
    expect(items[0]).toHaveTextContent(
      "Now: secured debt is long-dated and the unsecured notes mature first. Before: the 2028 notes were expected to be refinanced within the year.",
    );
    expect(within(items[0] as HTMLElement).getByRole("link")).toHaveAttribute(
      "href",
      "#/library/halden-aerostructures/2026-09-30/modules/capital-structure",
    );
    expect(items[4]).toHaveTextContent("Recovery");
    expect(items[4]).toHaveTextContent("Not assessable");
    expect(items[4]).toHaveTextContent(
      "Not assessable in this run or the earlier one, so there is nothing to compare.",
    );
  });

  it("collapses the nine unchanged modules to one plain item with the delivered count", () => {
    renderChanges("2026-09-30");
    const item = screen.getByText("9 modules unchanged").closest("li") as HTMLElement;
    expect(item).toHaveTextContent("Unchanged");
    expect(item).toHaveTextContent(
      "Business profile, Industry and competition, Financial performance, Covenants and documentation, Management and governance, Peer comparison, Environmental, social and governance, Forecast, Credit snapshot.",
    );
    expect(within(item).queryByRole("link")).toBeNull();
  });
});

describe("Changes, the first run on the issuer", () => {
  it("says No earlier run to compare, with the mock's sentence and a way to the Overview", () => {
    renderChanges("2025-09-30");
    expect(
      screen.getByRole("heading", { level: 2, name: "No earlier run to compare" }),
    ).toBeVisible();
    expect(
      screen.getByText(
        "This is the first run on Halden Aerostructures. What changed will appear here after the next run.",
      ),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Open the Overview" })).toHaveAttribute(
      "href",
      "#/library/halden-aerostructures/2025-09-30/overview",
    );
    expect(screen.queryByRole("radiogroup", { name: "Presentation" })).toBeNull();
    expect(screen.queryByRole("heading", { name: "Modules" })).toBeNull();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });
});

describe("Changes, the other states of the frame", () => {
  it("draws the skeleton for a run still loading", () => {
    const { container } = renderChanges("2026-06-30");
    expect(container.querySelector("[aria-busy='true']")).not.toBeNull();
    expect(screen.queryByRole("radiogroup", { name: "Presentation" })).toBeNull();
  });

  it.each([
    ["issuer", "nobody", "2026-09-30", "No such issuer"],
    ["run", "halden-aerostructures", "1999-01-01", "No such run"],
  ])(
    "says which %s the library does not hold, under the page name as the h1",
    (_, issuer, run, title) => {
      renderChanges(run, fixture.slice, issuer);
      expect(screen.getByRole("heading", { level: 1, name: "Changes" })).toBeVisible();
      expect(screen.getByRole("heading", { level: 2, name: title })).toBeVisible();
      expect(screen.getByRole("link", { name: "Back to the library" })).toBeVisible();
    },
  );

  it("shows the reader's notice, not a partial page, when a change is malformed", () => {
    const slice = structuredClone(fixture.slice) as { issuers: { runs: Json[] }[] };
    const changes = slice.issuers[0]?.runs[0]?.["changes"] as { changes: Json[] };
    (changes.changes[0] as Json)["direction"] = "sideways";
    renderChanges("2026-09-30", slice);
    expect(
      screen.getByText(/issuers\[0\]\.runs\[0\]\.changes\.changes\[0\]\.direction/),
    ).toBeVisible();
    expect(screen.queryByRole("radiogroup", { name: "Presentation" })).toBeNull();
  });

  it("keeps every trace control hidden at rest until the frame's Show sources is on", () => {
    renderChanges("2026-09-30");
    const first = screen.getAllByRole("button", { name: "Show sources for this change" })[0];
    expect(first?.className).toContain("opacity-0");
    expect(first?.className).toContain("in-data-[sources=on]:opacity-100");
    fireEvent.click(screen.getByRole("switch"));
    expect(document.querySelector("[data-sources='on']")).not.toBeNull();
  });
});

describe("Changes, another run", () => {
  it("sweep SW-05: opens at Cards again when the run changes under the page", () => {
    const view = renderChanges("2026-09-30");
    click(within(presentation()).getByRole("radio", { name: "Table" }));
    expect(within(presentation()).getByRole("radio", { name: "Table" })).toBeChecked();
    const route = routes.find((r) => r.path === PATH);
    if (route === undefined) throw new Error("no changes route");
    const data: LibraryData = {
      schema: "credit-os-data/1",
      issuers: fixture.issuers,
      library: fixture.slice,
    };
    view.rerender(
      <SourceContext.Provider value={data}>
        {route.render({ issuer: "halden-aerostructures", run: "2026-03-31" })}
      </SourceContext.Provider>,
    );
    expect(within(presentation()).getByRole("radio", { name: "Cards" })).toBeChecked();
  });
});

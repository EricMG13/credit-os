import { fireEvent, render, screen, within } from "@testing-library/react";
import { App } from "@/App";
import type { LoadResult } from "@/data";
import { edited, fixtureSlice, must } from "./slice/test-fixture";

const ADDRESS = "#/library/transdigm/2025-06-30/evidence";
const A = ["runs", 0, "analysis"] as const;

const FINDINGS = [
  [
    "01",
    "Deleveraging depends on keeping the cash",
    "Gross debt stays at USD 29.7 billion in both cases. Net leverage falls from 5.9x to 3.8x by FY27 only because free cash flow is left on the balance sheet.",
  ],
  [
    "02",
    "Earnings quality is high",
    "Margins have risen every year since FY22, and aftermarket sales, the most profitable part of the business, are over half of revenue.",
  ],
  [
    "03",
    "Interest is covered with room to spare",
    "Cover stays between 2.3x and 3.6x across both cases. The low point is FY26 in the downside case.",
  ],
  [
    "04",
    "Refinancing is concentrated in 2028 to 2030",
    "About USD 17 billion, 57% of debt, falls due in those three years. The model assumes it is refinanced at current spreads.",
  ],
] as const;
const STATS = [
  [
    "Net leverage",
    "5.9x",
    "↗ from 4.5x in FY24",
    "The 2024 special dividend was funded with new debt; a year of earnings growth has not yet absorbed it.",
  ],
  [
    "Interest cover",
    "2.9x",
    "↗ from 2.8x in FY24",
    "Higher earnings have more than offset the larger debt load.",
  ],
  [
    "Free cash flow to debt",
    "6.6%",
    "↘ from 7.1% in FY24",
    "Cash generation grew more slowly than debt.",
  ],
  [
    "Secured net leverage",
    "n.a.",
    "3.1x in FY24",
    "The secured share of debt was not split out in the latest sources, so no change can be stated.",
  ],
] as const;
const INDEX = [
  ["Key findings", "Key findings"],
  ["Measures", "Measures and what they mean"],
  ["Headroom", "Headroom to covenants and rating triggers"],
  ["Segment margins", "EBITDA margin by segment"],
  ["Contrary evidence", "Contrary evidence"],
  ["What would change the view", "What would change the view"],
  ["Limitations", "Limitations"],
] as const;

function renderAt(slice: unknown, issuer = "transdigm", run = "2025-06-30") {
  window.location.hash = `#/model/${issuer}/${run}/analysis`;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], model: slice },
  };
  return render(<App result={result} />);
}

function reducedMotion(reduce: boolean) {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: reduce && query.includes("prefers-reduced-motion"),
  }));
}

describe("Analysis page", () => {
  beforeEach(() => {
    reducedMotion(false);
    Element.prototype.scrollIntoView = vi.fn();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("orders the headings h1 (the issuer), h2 (the sections), h3 (the chart titles)", () => {
    renderAt(fixtureSlice());
    const levels = screen.getAllByRole("heading").map((h) => [h.tagName, h.textContent]);
    expect(levels).toEqual([
      ["H1", "TransDigm Group"],
      ["H2", "Key findings"],
      ["H2", "Measures and what they mean"],
      ["H3", "Headroom to covenants and rating triggers"],
      ["H3", "EBITDA margin by segment"],
      ["H2", "Contrary evidence"],
      ["H2", "What would change the view"],
      ["H2", "Limitations"],
    ]);
  });

  it("marks the Analysis tab current", () => {
    renderAt(fixtureSlice());
    const tabs = within(screen.getByRole("navigation", { name: "Pages" }));
    expect(tabs.getByRole("link", { name: "Analysis" })).toHaveAttribute("aria-current", "page");
  });

  it("draws the key findings as a numbered list with the delivered numbers", () => {
    renderAt(fixtureSlice());
    const items = within(screen.getByRole("list", { name: "Key findings" })).getAllByRole(
      "listitem",
    );
    expect(items).toHaveLength(4);
    FINDINGS.forEach(([number, lead, body], i) => {
      const item = within(must(items[i]));
      expect(item.getByText(number)).toBeInTheDocument();
      expect(item.getByText(lead).tagName).toBe("B");
      expect(item.getByText(body)).toBeInTheDocument();
      expect(item.getByRole("link", { name: `Show the sources for ${lead}` })).toHaveAttribute(
        "href",
        ADDRESS,
      );
    });
  });

  it("draws the four measures with the delivered delta text and one trace control each", () => {
    renderAt(fixtureSlice());
    expect(screen.getByText("Latest twelve months against FY24")).toBeInTheDocument();
    const stats = screen.getAllByRole("article");
    expect(stats).toHaveLength(4);
    STATS.forEach(([label, value, delta, consequence], i) => {
      const stat = within(must(stats[i]));
      expect(stat.getByText(label)).toBeInTheDocument();
      expect(stat.getByText(delta)).toBeInTheDocument();
      expect(stat.getByText(consequence)).toBeInTheDocument();
      expect(stat.getByRole("link", { name: `Show the sources for ${label}` })).toHaveAttribute(
        "href",
        ADDRESS,
      );
      if (value === "n.a.") expect(stat.getByText("not available")).toBeInTheDocument();
      else expect(stat.getByText(value)).toBeInTheDocument();
    });
  });

  it("draws a missing measure as n.a. and states its earlier value without an arrow", () => {
    renderAt(fixtureSlice());
    const stat = within(must(screen.getAllByRole("article")[3]));
    expect(stat.getByText("n.a.")).toBeInTheDocument();
    expect(stat.getByText("3.1x in FY24").textContent).toBe("3.1x in FY24");
    expect(stat.queryByText(/[↗↘→↑↓]/)).toBeNull();
  });

  it("draws the headroom bars with a dashed target on every row and the covenant row empty", () => {
    renderAt(fixtureSlice());
    const chart = must(
      screen
        .getByRole("heading", { name: "Headroom to covenants and rating triggers" })
        .closest<HTMLElement>("figure"),
    );
    expect(
      within(chart).getByText("Latest twelve months; the dashed line is the level that matters"),
    ).toBeInTheDocument();
    expect(
      within(chart).getByText(
        "Secured net leverage could not be measured, so no bar is drawn against its covenant.",
      ),
    ).toBeInTheDocument();
    for (const text of [
      "5.9x of 7.0x",
      "2.9x against 2.0x",
      "6.6% of 10%",
      "Downgrade trigger above 7.0x",
      "Covenant limit 7.25x",
    ]) {
      expect(within(chart).getByText(text)).toBeInTheDocument();
    }
    expect(chart.querySelectorAll("[data-bar]")).toHaveLength(3);
    expect(chart.querySelectorAll("[data-target]")).toHaveLength(4);
    const covenant = must(
      within(chart).getByText("Secured net leverage").closest<HTMLElement>("[data-row]"),
    );
    expect(covenant.querySelector("[data-bar]")).toBeNull();
    expect(covenant.querySelector("[data-missing]")).not.toBeNull();
    expect(covenant.querySelector("[data-target]")?.getAttribute("data-left")).toBe("90.625");
  });

  it("draws the headroom table with n.a. for the missing value", () => {
    renderAt(fixtureSlice());
    const chart = must(
      screen
        .getByRole("heading", { name: "Headroom to covenants and rating triggers" })
        .closest<HTMLElement>("figure"),
    );
    fireEvent.click(within(chart).getByRole("radio", { name: "Table" }));
    const row = within(within(chart).getByRole("row", { name: /Secured net leverage/ }));
    expect(row.getAllByRole("cell").map((c) => c.textContent.replace("not available", ""))).toEqual(
      ["n.a.", "Covenant limit 7.25x"],
    );
    expect(
      within(chart)
        .getAllByRole("columnheader")
        .map((h) => h.textContent),
    ).toEqual(["Measure", "Latest twelve months", "Level that matters"]);
  });

  it("draws the segment dumbbells with the legend, and one mark only for the acquired businesses", () => {
    renderAt(fixtureSlice());
    const chart = must(
      screen
        .getByRole("heading", { name: "EBITDA margin by segment" })
        .closest<HTMLElement>("figure"),
    );
    expect(within(chart).getByText("FY24 against the latest twelve months")).toBeInTheDocument();
    expect(
      within(chart).getByText(
        "The acquired businesses were not owned in FY24: only the latest mark is drawn.",
      ),
    ).toBeInTheDocument();
    for (const text of ["55.8% to 57.5%", "51.9% to 53.4%", "41.2% to 38.6%", "n.a. to 44.0%"]) {
      expect(within(chart).getByText(text)).toBeInTheDocument();
    }
    expect(
      within(within(chart).getByRole("list", { name: "Legend" }))
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["FY24", "Latest twelve months"]);
    const acquired = must(
      within(chart).getByText("Acquired businesses").closest<HTMLElement>("[data-row]"),
    );
    expect(acquired.querySelector("[data-mark=from]")).toBeNull();
    expect(acquired.querySelector("[data-line]")).toBeNull();
    expect(acquired.querySelector("[data-mark=to]")).not.toBeNull();
    expect(acquired.querySelector("[data-missing]")).not.toBeNull();
    expect(chart.querySelectorAll("[data-line]")).toHaveLength(3);
  });

  it("draws the contrary evidence as a warning that cannot be dismissed, with a trace control", () => {
    renderAt(fixtureSlice());
    const alert = screen.getByRole("region", { name: "The cash may not stay" });
    expect(within(alert).getByText("The cash may not stay")).toBeInTheDocument();
    expect(
      within(alert).getByText(
        "The company has paid out its cash build three times in five years. If it does so again, leverage stays near 6x and the base case deleveraging does not happen.",
      ),
    ).toBeInTheDocument();
    expect(within(alert).queryByRole("button")).toBeNull();
    expect(
      within(alert).getByRole("link", {
        name: "Show the sources for The cash may not stay",
      }),
    ).toHaveAttribute("href", ADDRESS);
  });

  it("draws what would change the view as a standout note with a trace control", () => {
    renderAt(fixtureSlice());
    const note = screen.getByRole("region", { name: "Two levels to watch" });
    expect(within(note).getByText("Two levels to watch")).toBeInTheDocument();
    expect(
      within(note).getByText(
        "Net leverage above 7.0x for two quarters, or interest cover below 2.0x, would turn this view negative. A public commitment to hold leverage below 5x would improve it.",
      ),
    ).toBeInTheDocument();
    expect(
      within(note).getByRole("link", {
        name: "Show the sources for Two levels to watch",
      }),
    ).toHaveAttribute("href", ADDRESS);
  });

  it("draws the two passages as plain regions without an alert role, body text at 16px, the control in the title row", () => {
    renderAt(fixtureSlice());
    expect(screen.queryByRole("alert")).toBeNull();
    for (const [title, body] of [
      ["The cash may not stay", /^The company has paid out/],
      ["Two levels to watch", /^Net leverage above 7.0x/],
    ] as const) {
      const region = screen.getByRole("region", { name: title });
      expect(within(region).getByText(body).className).toMatch(/\btext-body\b/);
      const row = must(within(region).getByText(title).closest<HTMLElement>("[data-title-row]"));
      // The mock's `.al`: the title row aligns to the first line, the title is 14px (small), and
      // the body sits under the title, past the 24px mark and the 8px gap.
      expect(row).toHaveClass("items-start");
      expect(within(region).getByText(title).className).toMatch(/\btext-small\b/);
      expect(within(region).getByText(body)).toHaveClass("ps-8");
      expect(
        within(row).getByRole("link", { name: `Show the sources for ${title}` }),
      ).toBeInTheDocument();
    }
  });

  it("sets the limitations count at the caption size", () => {
    renderAt(fixtureSlice());
    expect(screen.getByText("2 of 6").className).toMatch(/\btext-caption\b/);
  });

  it("draws the delivered count, the link to all limitations and two open collapsibles", () => {
    renderAt(fixtureSlice());
    const heading = screen.getByRole("heading", { level: 2, name: "Limitations" });
    expect(within(must(heading.parentElement)).getByText("2 of 6")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "See all six limitations" })).toHaveAttribute(
      "href",
      "#/model/transdigm/2025-06-30/limitations",
    );
    const details = Array.from(document.querySelectorAll("details"));
    expect(details.map((d) => d.open)).toEqual([true, true]);
    expect(details.map((d) => d.querySelector("summary")?.textContent)).toEqual([
      "EBITDA is the company’s own measure",
      "FY23 cash interest is missing",
    ]);
    expect(
      screen.getByText(
        "EBITDA as defined adds back items the company chooses. No independent adjustment was made, so leverage on a stricter measure would be higher.",
      ),
    ).toBeInTheDocument();
    for (const title of ["EBITDA is the company’s own measure", "FY23 cash interest is missing"]) {
      expect(screen.getByRole("link", { name: `Show the sources for ${title}` })).toHaveAttribute(
        "href",
        ADDRESS,
      );
    }
  });

  it("has one trace control per finding, measure, chart, passage and limitation, none sharing a name", () => {
    renderAt(fixtureSlice());
    const names = screen
      .getAllByRole("link", { name: /^Show the sources for / })
      .map((l) => l.getAttribute("aria-label"));
    expect(names).toHaveLength(4 + 4 + 2 + 2 + 2);
    expect(new Set(names).size).toBe(names.length);
  });

  it("draws no trace control for a null address", () => {
    renderAt(edited([...A, "findings", 0, "trace"], null));
    expect(
      screen.queryByRole("link", {
        name: "Show the sources for Deleveraging depends on keeping the cash",
      }),
    ).toBeNull();
    expect(screen.getAllByRole("link", { name: /^Show the sources for / })).toHaveLength(13);
  });

  describe("the section index", () => {
    it("lists the seven sections as buttons in a menu named On this page", () => {
      renderAt(fixtureSlice());
      const menu = within(screen.getByRole("navigation", { name: "On this page" }));
      expect(menu.getAllByRole("button").map((b) => b.textContent)).toEqual(
        INDEX.map(([label]) => label),
      );
      expect(menu.queryByRole("link")).toBeNull();
    });

    it("marks no entry before one is used", () => {
      renderAt(fixtureSlice());
      const menu = within(screen.getByRole("navigation", { name: "On this page" }));
      expect(menu.getAllByRole("button").some((b) => b.hasAttribute("aria-current"))).toBe(false);
    });

    it.each(INDEX)(
      "%s moves focus to its section, scrolls it into view and leaves the hash alone",
      (label, heading) => {
        renderAt(fixtureSlice());
        const hash = window.location.hash;
        const scroll = vi.fn();
        Element.prototype.scrollIntoView = scroll;
        const menu = within(screen.getByRole("navigation", { name: "On this page" }));
        fireEvent.click(menu.getByRole("button", { name: label }));
        const target = document.activeElement;
        expect(target).not.toBe(document.body);
        expect(target?.id).not.toBe("");
        const named =
          target?.tagName.startsWith("H") === true
            ? target.textContent
            : within(must(target as HTMLElement)).queryByRole("heading", { name: heading })
                ?.textContent;
        expect(named).toBe(heading);
        expect(target).toHaveAttribute("tabindex", "-1");
        // A margin above the target keeps its focus outline off the top edge of the viewport.
        expect(target).toHaveClass("scroll-mt-4");
        expect(scroll).toHaveBeenCalledTimes(1);
        expect(scroll.mock.contexts[0]).toBe(target);
        expect(window.location.hash).toBe(hash);
        expect(menu.getByRole("button", { name: label })).toHaveAttribute("aria-current", "true");
        expect(
          menu.getAllByRole("button").filter((b) => b.hasAttribute("aria-current")),
        ).toHaveLength(1);
      },
    );

    it("scrolls smoothly, and not at all smoothly under reduced motion", () => {
      renderAt(fixtureSlice());
      const scroll = vi.fn();
      Element.prototype.scrollIntoView = scroll;
      const button = screen.getByRole("button", { name: "Measures" });
      fireEvent.click(button);
      expect(scroll).toHaveBeenLastCalledWith({ behavior: "smooth", block: "start" });
      reducedMotion(true);
      fireEvent.click(button);
      expect(scroll).toHaveBeenLastCalledWith({ behavior: "auto", block: "start" });
    });

    it("moves the mark to the entry last used", () => {
      renderAt(fixtureSlice());
      fireEvent.click(screen.getByRole("button", { name: "Measures" }));
      fireEvent.click(screen.getByRole("button", { name: "Limitations" }));
      const marked = screen
        .getAllByRole("button")
        .filter((b) => b.getAttribute("aria-current") === "true");
      expect(marked.map((b) => b.textContent)).toEqual(["Limitations"]);
    });
  });

  it("puts the trace addresses only in href, never in text, title or aria-label", () => {
    const { container } = renderAt(fixtureSlice());
    for (const el of Array.from(container.querySelectorAll("[title], [aria-label]"))) {
      expect(`${el.getAttribute("title") ?? ""}${el.getAttribute("aria-label") ?? ""}`).not.toMatch(
        /#\/|evidence|\.json|\.pdf/i,
      );
    }
    expect(container.textContent).not.toContain(ADDRESS);
  });

  it("draws the not found state for an issuer or run the slice does not hold", () => {
    renderAt(fixtureSlice(), "nobody");
    expect(screen.getByText("Not found for this run")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it.each([
    ["a finding", [...A, "findings", 0, "title"], 5, "findings[0].title: expected a string"],
    [
      "a measure",
      [...A, "measures", "stats", 0, "delta"],
      null,
      "measures.stats[0].delta: expected a string",
    ],
    [
      "a headroom row",
      [...A, "headroom", "rows", 0, "value"],
      "5.9",
      "headroom.rows[0].value: expected a number",
    ],
    [
      "a segment row",
      [...A, "segments", "rows", 0, "to"],
      "57.5",
      "segments.rows[0].to: expected a number",
    ],
    ["a passage", [...A, "contrary", "text"], 1, "contrary.text: expected a string"],
    [
      "a limitation",
      [...A, "limitations", "items", 0, "text"],
      1,
      "limitations.items[0].text: expected a string",
    ],
  ] as const)(
    "leaves an invalid slice with %s to the app, naming the failing path",
    (_n, steps, value, reason) => {
      renderAt(edited(steps, value));
      expect(screen.getByText("This part of the library could not be read")).toBeInTheDocument();
      expect(screen.getByText(`runs[0].analysis.${reason}`)).toBeInTheDocument();
    },
  );
});

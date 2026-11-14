import { fireEvent, render, screen, within } from "@testing-library/react";
import { App } from "@/App";
import type { LoadResult } from "@/data";
import { edited, fixtureSlice, must } from "./slice/test-fixture";

const ADDRESS = "#/library/transdigm/2025-06-30/evidence";
const LIMITATIONS = [
  [
    "EBITDA is the company’s own measure",
    "Earnings",
    "EBITDA as defined adds back items the company chooses. No independent adjustment was made, so leverage on a stricter measure would be higher.",
  ],
  [
    "FY23 cash interest is missing",
    "Data",
    "Cash interest for FY23 was not split out in the sources. Interest cover and free cash flow for that year are shown as n.a., not estimated.",
  ],
  [
    "FY22 inventories are missing",
    "Data",
    "The FY22 balance sheet in the sources does not show inventories separately. The figure is n.a. and FY22 working capital ratios are not stated.",
  ],
  [
    "No acquisitions or shareholder returns after FY25",
    "Forecast",
    "Both cases assume no acquisitions and forecast no dividends or buybacks. The company has made both in most years, so cash and leverage are likely to be worse than shown.",
  ],
  [
    "The downside case is a single scenario",
    "Downside case",
    "One traffic shock was modelled. It does not combine lower traffic with a loss of pricing power, and it assumes the 2028 maturities can still be refinanced.",
  ],
  [
    "Revolver terms are withheld",
    "Downside case",
    "The amount drawn and the terms of the revolving facility are shown to the deal team only. Liquidity under the downside case could not be measured.",
  ],
] as const;
const GAPS = [
  "Pension deficit. No source in this run states the funded position of the pension plans.",
  "Quarterly cash flow. The sources give annual figures only, so no quarter-by-quarter path was built.",
  "Months of liquidity, downside case. The revolver terms are withheld, so the chart could not be drawn.",
];

function renderAt(slice: unknown, issuer = "transdigm", run = "2025-06-30") {
  window.location.hash = `#/model/${issuer}/${run}/limitations`;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], model: slice },
  };
  return render(<App result={result} />);
}

describe("Limitations page", () => {
  it("orders the headings h1 (the issuer), h2 (the sections)", () => {
    renderAt(fixtureSlice());
    const levels = screen.getAllByRole("heading").map((h) => [h.tagName, h.textContent]);
    expect(levels).toEqual([
      ["H1", "TransDigm Group"],
      ["H2", "Limitations"],
      ["H2", "Not established for this run"],
    ]);
  });

  it("restores the shell's padding on the bleed layout", () => {
    renderAt(fixtureSlice());
    expect(must(screen.getByRole("main").firstElementChild)).toHaveClass("p-8");
  });

  it("draws two limitations that share a title without a duplicate key warning", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const slice = fixtureSlice() as {
      runs: { limitations: { items: { title: string; trace: string | null }[] } }[];
    };
    const items = must(slice.runs[0]).limitations.items;
    // The reader refuses a repeated title only where both draw a trace control; this one draws none.
    must(items[1]).title = must(items[0]).title;
    must(items[1]).trace = null;
    renderAt(slice);
    expect(screen.getAllByText("EBITDA is the company’s own measure")).toHaveLength(2);
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });

  it("draws the not established heading and its delivered count when the run has no gap to state", () => {
    renderAt(edited(["runs", 0, "limitations", "notEstablished", "items"], []));
    const heading = screen.getByRole("heading", { name: "Not established for this run" });
    expect(heading).toBeInTheDocument();
    expect(must(heading.parentElement)).toHaveTextContent("Not established for this run3");
  });

  it("draws two gaps that share a title without a duplicate key warning", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const slice = fixtureSlice() as {
      runs: { limitations: { notEstablished: { items: { title: string }[] } } }[];
    };
    const items = must(slice.runs[0]).limitations.notEstablished.items;
    must(items[1]).title = must(items[0]).title;
    renderAt(slice);
    expect(screen.getAllByText(/^Pension deficit\. /)).toHaveLength(2);
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });

  it("takes the Library crumb's address from the slice", () => {
    renderAt(edited(["runs", 0, "links", "library"], "#/library-home"));
    const crumbs = within(screen.getByRole("navigation", { name: "Breadcrumb" }));
    expect(crumbs.getByRole("link", { name: "Library" })).toHaveAttribute("href", "#/library-home");
  });

  it("sets both count badges at the caption size, not text-xs", () => {
    renderAt(fixtureSlice());
    for (const count of ["6", "3"]) {
      const badge = screen.getAllByText(count).find((el) => el.className.includes("rounded-full"));
      expect(must(badge).className).toMatch(/\btext-caption\b/);
      expect(must(badge).className).not.toMatch(/\btext-xs\b/);
    }
  });

  it("draws the delivered count beside the heading and the lead sentence", () => {
    renderAt(fixtureSlice());
    const section = must(
      screen.getByRole("heading", { level: 2, name: "Limitations" }).parentElement,
    );
    expect(within(section).getByText("6")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Six qualifications apply to this model. Each is stated in full and stays open; none changes the bottom line on its own.",
      ),
    ).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "See the 3 gaps in Evidence" });
    expect(link).toHaveAttribute("href", ADDRESS);
  });

  it("draws the header badges, the action and the breadcrumb", () => {
    renderAt(fixtureSlice());
    for (const text of ["As of 30 June 2025", "Annual review", "Finished", "Sample data"]) {
      expect(screen.getByText(text)).toBeInTheDocument();
    }
    expect(screen.getByRole("link", { name: "Back to the report" })).toHaveAttribute(
      "href",
      "#/library/transdigm/2025-06-30/overview",
    );
    const crumbs = within(screen.getByRole("navigation", { name: "Breadcrumb" }));
    expect(crumbs.getByRole("link", { name: "Library" })).toHaveAttribute("href", "#/");
    expect(crumbs.getByRole("link", { name: "TransDigm Group" })).toBeInTheDocument();
    expect(crumbs.getByText("Financial model")).toHaveAttribute("aria-current", "page");
  });

  it("leaves out the sample badge when the run is not a sample", () => {
    renderAt(edited(["runs", 0, "header", "sample"], false));
    expect(screen.queryByText("Sample data")).toBeNull();
  });

  it("marks the current tab and sends the Evidence tab out of the model", () => {
    renderAt(fixtureSlice());
    const tabs = within(screen.getByRole("navigation", { name: "Pages" }));
    const names = tabs.getAllByRole("link").map((a) => a.textContent);
    expect(names).toEqual([
      "Front page",
      "Analysis",
      "Model",
      "Portfolio fit",
      "Limitations6",
      "Evidence",
    ]);
    const current = tabs
      .getAllByRole("link")
      .filter((a) => a.getAttribute("aria-current") === "page");
    expect(current.map((a) => a.textContent)).toEqual(["Limitations6"]);
    expect(tabs.getByRole("link", { name: "Front page" })).toHaveAttribute(
      "href",
      "#/model/transdigm/2025-06-30/front",
    );
    expect(tabs.getByRole("link", { name: "Model" })).toHaveAttribute(
      "href",
      "#/model/transdigm/2025-06-30/statements",
    );
    expect(tabs.getByRole("link", { name: "Evidence" })).toHaveAttribute("href", ADDRESS);
  });

  it("draws six limitations, open by default, with title, label and full text", () => {
    renderAt(fixtureSlice());
    const cards = document.querySelectorAll("details");
    expect(cards).toHaveLength(6);
    LIMITATIONS.forEach(([title, label, text], index) => {
      const card = must(cards[index]);
      expect(card.open).toBe(true);
      const summary = must(card.querySelector("summary"));
      expect(within(summary).getByText(title)).toBeInTheDocument();
      expect(within(summary).getByText(label)).toBeInTheDocument();
      expect(within(card).getByText(text)).toBeVisible();
    });
  });

  it("collapses and reopens a limitation, and its summary takes keyboard focus", () => {
    renderAt(fixtureSlice());
    const card = must(document.querySelector("details"));
    const summary = must(card.querySelector("summary"));
    summary.focus();
    expect(document.activeElement).toBe(summary);
    fireEvent.click(summary);
    expect(card.open).toBe(false);
    fireEvent.click(summary);
    expect(card.open).toBe(true);
  });

  it("draws the three gaps with the not established count", () => {
    renderAt(fixtureSlice());
    const heading = screen.getByRole("heading", { level: 2, name: "Not established for this run" });
    expect(within(must(heading.parentElement)).getByText("3")).toBeInTheDocument();
    for (const reason of GAPS) expect(screen.getByText(reason)).toBeInTheDocument();
  });

  it("wraps a long limitation in full", () => {
    const long = `${"Revolver terms remain withheld for the deal team. ".repeat(12)}Liquidity_could_not_be_measured_in_the_downside_case_${"x".repeat(80)}`;
    renderAt(edited(["runs", 0, "limitations", "items", 5, "text"], long));
    const paragraph = screen.getByText(long);
    expect(paragraph.className).toContain("break-words");
    expect(must(paragraph.closest("details")).className).not.toMatch(
      /truncate|line-clamp|overflow-hidden/,
    );
  });

  describe("trace controls", () => {
    it("draws one per limitation, named by what it traces, hidden until revealed", () => {
      renderAt(fixtureSlice());
      const controls = LIMITATIONS.map(([title]) =>
        screen.getByRole("link", { name: `Show the sources for ${title}` }),
      );
      expect(controls).toHaveLength(6);
      expect(new Set(controls.map((c) => c.getAttribute("aria-label"))).size).toBe(6);
      for (const control of controls) {
        expect(control).toHaveAttribute("href", ADDRESS);
        expect(control.className).toContain("opacity-0");
        expect(control.className).not.toMatch(/(^|\s)opacity-100/);
        expect(control.className).toContain("focus-visible:opacity-100");
        expect(control.className).toContain("hover:opacity-100");
        expect(control.getAttribute("tabindex")).not.toBe("-1");
        expect(control.className).not.toMatch(/hidden|invisible/);
      }
    });

    it("shows every control under Show sources and hides them again when it is off", () => {
      renderAt(fixtureSlice());
      const toggle = screen.getByRole("switch", { name: "Show sources" });
      expect(toggle).not.toBeChecked();
      fireEvent.click(toggle);
      expect(toggle).toBeChecked();
      for (const control of screen.getAllByRole("link", { name: /Show the sources for/ })) {
        expect(control.className).toMatch(/(^|\s)opacity-100/);
        expect(control.className).not.toMatch(/(^|\s)opacity-0/);
      }
      fireEvent.click(toggle);
      for (const control of screen.getAllByRole("link", { name: /Show the sources for/ })) {
        expect(control.className).toMatch(/(^|\s)opacity-0/);
      }
    });

    it("draws no control for a null trace", () => {
      renderAt(edited(["runs", 0, "limitations", "items", 0, "trace"], null));
      expect(screen.getAllByRole("link", { name: /Show the sources for/ })).toHaveLength(5);
    });
  });

  it("shows no address or audit name in text, titles or labels", () => {
    renderAt(fixtureSlice());
    expect(document.body.textContent).not.toContain("#/library");
    for (const element of document.querySelectorAll("[title], [aria-label]")) {
      const named = `${element.getAttribute("title") ?? ""} ${element.getAttribute("aria-label") ?? ""}`;
      expect(named).not.toMatch(/#\/|evidence|2025-06-30|transdigm/i);
    }
  });

  it("draws a not found state for an unknown issuer or run", () => {
    renderAt(fixtureSlice(), "nobody");
    expect(screen.getByText("Not found for this run")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 1, name: "TransDigm Group" })).toBeNull();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("link", { name: "All financial models" })).toHaveAttribute(
      "href",
      "#/model/runs",
    );
    document.body.innerHTML = "";
  });

  it("draws a not found state for an unknown run of a known issuer", () => {
    renderAt(fixtureSlice(), "transdigm", "2024-06-30");
    expect(screen.getByText("Not found for this run")).toBeInTheDocument();
  });

  it("leaves an invalid slice to the app, naming the failing path", () => {
    renderAt(edited(["runs", 0, "limitations", "items", 0, "title"], 5));
    expect(screen.getByText("This part of the library could not be read")).toBeInTheDocument();
    expect(
      screen.getByText("runs[0].limitations.items[0].title: expected a string"),
    ).toBeInTheDocument();
  });
});

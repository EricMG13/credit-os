import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { App } from "@/App";
import type { LoadResult } from "@/data";
import { fixtureSlice, must } from "./slice/test-fixture";

const ADDRESS = "#/library/transdigm/2025-06-30/evidence";
const BASE = "#/model/transdigm/2025-06-30";
const METRICS = [
  ["Revenue", "$8,580m", "↗ 8.1% on FY24", "Net sales, latest twelve months"],
  [
    "EBITDA as defined",
    "$4,560m",
    "↗ 9.3% on FY24",
    "EBITDA as the company defines it in its credit agreement",
  ],
  ["EBITDA margin", "53.1%", "↗ 0.5 pts on FY24", "EBITDA as defined divided by revenue"],
  ["Net leverage", "5.9x", "↗ from 4.5x", "Net debt divided by EBITDA as defined"],
  ["Interest cover", "2.9x", "↗ from 2.8x", "EBITDA as defined divided by cash interest"],
  [
    "Free cash flow",
    "$1,950m",
    "↗ 10.3% on FY24",
    "EBITDA as defined less cash interest, cash tax, working capital and capital expenditure",
  ],
] as const;
const FACTS = [
  ["Currency and units", "US dollars, millions"],
  ["Fiscal year end", "30 September"],
  ["Historic periods", "FY22 to FY24, as reported"],
  ["Latest twelve months", "To 30 June 2025"],
  ["Forecast periods", "FY25 to FY27"],
  ["Cases", "Base and downside"],
  ["Earnings measure", "EBITDA as the company defines it"],
] as const;

function renderFrom(slice: unknown, issuer = "transdigm", run = "2025-06-30") {
  window.location.hash = `#/model/${issuer}/${run}/front`;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], model: slice },
  };
  return render(<App result={result} />);
}
function renderFront(issuer = "transdigm", run = "2025-06-30") {
  return renderFrom(fixtureSlice(), issuer, run);
}

const tile = (label: string): HTMLElement =>
  must(screen.getByText(label, { selector: "p" }).closest("article"));

describe("Front page", () => {
  it("orders the headings h1 (the issuer), h2 (the sections)", () => {
    renderFront();
    const levels = screen.getAllByRole("heading").map((h) => [h.tagName, h.textContent]);
    expect(levels).toEqual([
      ["H1", "TransDigm Group"],
      ["H2", "Headline figures"],
      ["H2", "What the model covers"],
      ["H2", "Parts of the model"],
    ]);
  });

  it("draws the bottom line with one trace control", () => {
    renderFront();
    const band = screen.getByRole("region", { name: "Bottom line" });
    expect(band).toHaveTextContent(
      "Leverage falls only if the cash is kept: net debt drops from 5.9x to 3.8x EBITDA by FY27 in the base case, and cash flow covers interest about three times throughout.",
    );
    expect(band).toHaveTextContent(
      "The downside case holds leverage above 5x and still funds interest from operations. Debt is not repaid in either case, and about USD 17 billion falls due between 2028 and 2030.",
    );
    const link = within(band).getByRole("link", { name: "Show the sources for the bottom line" });
    expect(link).toHaveAttribute("href", ADDRESS);
    expect(within(band).queryByRole("button")).toBeNull();
  });

  it.each(METRICS)(
    "draws the %s tile with its value, delta and trace control",
    (label, value, delta) => {
      renderFront();
      const t = tile(label);
      expect(within(t).getByText(value)).toBeInTheDocument();
      expect(within(t).getByText(delta)).toBeInTheDocument();
      expect(
        within(t).getByRole("link", { name: `Show the sources for ${label}` }),
      ).toHaveAttribute("href", ADDRESS);
      const figure = within(t).getByText(value);
      expect(figure.className).toContain("font-body");
      expect(figure.className).not.toContain("font-display");
    },
  );

  it("shows the period note beside the headline figures heading", () => {
    renderFront();
    expect(screen.getByText("Latest twelve months to 30 June 2025")).toBeInTheDocument();
  });

  it("draws the missing tile as n.a. with its reason and no delta", () => {
    renderFront();
    const t = tile("Secured net leverage");
    const na = within(t).getByText("n.a.");
    expect(na).toBeInTheDocument();
    expect(must(must(na.closest("span.tabular-nums")).parentElement).className).not.toContain(
      "font-display",
    );
    expect(within(t).queryByText("0")).toBeNull();
    expect(
      within(t).getByText("The secured share of debt was not split out in the sources."),
    ).toBeInTheDocument();
    expect(t.textContent).not.toContain("↗");
    expect(within(t).getAllByRole("link")).toHaveLength(1);
  });

  it("draws the withheld tile with its reason and no delta", () => {
    renderFront();
    const t = tile("Revolver drawn");
    expect(within(t).getByText("Withheld")).toBeInTheDocument();
    expect(within(t).getByText("Shown to the deal team only.")).toBeInTheDocument();
    expect(within(t).queryByText("n.a.")).toBeNull();
    expect(t.textContent).not.toContain("↗");
  });

  it("gives each tile a definition tooltip that is the definition", async () => {
    renderFront();
    const trigger = within(tile("Net leverage")).getByRole("button", {
      name: "About Net leverage",
    });
    fireEvent.keyDown(document.body, { key: "Tab" });
    act(() => {
      trigger.focus();
    });
    expect(await screen.findByRole("tooltip")).toHaveTextContent(
      "Net debt divided by EBITDA as defined",
    );
  });

  it("lists the seven facts in a details list, one trace control each", () => {
    renderFront();
    const section = must(
      screen.getByRole("heading", { level: 2, name: "What the model covers" }).parentElement,
    );
    const terms = within(section)
      .getAllByRole("term")
      .map((t) => t.textContent);
    expect(terms).toEqual(FACTS.map(([k]) => k));
    for (const [k, v] of FACTS) {
      const row = must(within(section).getByText(k).closest("div"));
      expect(within(row).getByText(v)).toBeInTheDocument();
      expect(within(row).getByRole("link", { name: `Show the sources for ${k}` })).toHaveAttribute(
        "href",
        ADDRESS,
      );
    }
  });

  it("links three parts to their pages, each with a trace control", () => {
    renderFront();
    const parts = must(
      screen.getByRole("heading", { level: 2, name: "Parts of the model" }).parentElement,
    );
    for (const [name, text, to] of [
      ["Analysis", "Deleveraging depends on keeping the cash, not on repaying debt.", "analysis"],
      [
        "Model",
        "Statements for FY22 to FY27, two cases, bridges and the debt stack.",
        "statements",
      ],
      [
        "Portfolio fit",
        "Within every limit that could be tested, with 0.9 points of room under the single-issuer limit.",
        "portfolio-fit",
      ],
    ] as const) {
      const link = within(parts).getByRole("link", { name: new RegExp(`^${name}`) });
      expect(link).toHaveAttribute("href", `${BASE}/${to}`);
      expect(link).toHaveTextContent(text);
    }
    for (const name of ["Analysis", "Model", "Portfolio fit", "Relative value"]) {
      expect(screen.getByRole("link", { name: `Show the sources for ${name}` })).toHaveAttribute(
        "href",
        ADDRESS,
      );
    }
  });

  it("keeps Relative value in place as a non-link with the Not assessable badge", () => {
    renderFront();
    const title = screen.getByText("Relative value");
    const item = must(title.closest<HTMLElement>("div[data-item]"));
    expect(item.tagName).toBe("DIV");
    expect(item.closest("a")).toBeNull();
    expect(within(item).getByText("Not assessable")).toBeInTheDocument();
    expect(
      within(item).getByText(
        "The pricing comparison failed in this run, so the model's spread view is missing.",
      ),
    ).toBeInTheDocument();
    const names = Array.from(document.querySelectorAll("[data-item] b")).map((b) => b.textContent);
    expect(names).toEqual(["Analysis", "Model", "Portfolio fit", "Relative value"]);
  });

  it("puts the trace addresses only in href, never in text, title or aria-label", () => {
    const { container } = renderFront();
    expect(container.textContent).not.toContain("library/transdigm");
    for (const el of Array.from(container.querySelectorAll("[title], [aria-label]"))) {
      expect(`${el.getAttribute("title") ?? ""}${el.getAttribute("aria-label") ?? ""}`).not.toMatch(
        /#\/library|evidence/i,
      );
    }
  });

  it("draws metrics, facts and parts that share a label or title without a duplicate key warning", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const slice = fixtureSlice() as {
      runs: {
        front: {
          headline: { metrics: { label: string; trace: string | null }[] };
          covers: { facts: { label: string; trace: string | null }[] };
          parts: { title: string; trace: string | null }[];
        };
      }[];
    };
    const front = must(slice.runs[0]).front;
    // The reader refuses a repeated name only where both draw a trace control; these draw none.
    must(front.headline.metrics[1]).label = "Revenue";
    must(front.headline.metrics[1]).trace = null;
    must(front.covers.facts[1]).label = "Currency and units";
    must(front.covers.facts[1]).trace = null;
    must(front.parts[1]).title = "Analysis";
    must(front.parts[1]).trace = null;
    renderFrom(slice);
    expect(screen.getAllByText("Revenue", { selector: "p" })).toHaveLength(2);
    expect(screen.getAllByText("Currency and units")).toHaveLength(2);
    expect(screen.getAllByText("Analysis", { selector: "[data-item] b" })).toHaveLength(2);
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });

  it("draws the not found state for an issuer or run the slice does not hold", () => {
    renderFront("nobody", "2025-06-30");
    expect(screen.getByText("Not found for this run")).toBeInTheDocument();
  });
});

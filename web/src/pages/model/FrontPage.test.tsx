import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { App } from "@/App";
import type { LoadResult } from "@/data";
import { fixtureSlice, must } from "./slice/test-fixture";

const ADDRESS = "#/library/transdigm/2025-06-30/evidence";
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
});

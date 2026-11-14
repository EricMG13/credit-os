import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { WaterfallChart, type WaterfallStep } from "./WaterfallChart";

// Steps, labels, ticks and table strings are copied from the mock's script blocks
// (Forecast: walk W; Model 3 Model: net debt walk).
const BASE: WaterfallStep[] = [
  { label: "EBITDA", kind: "total", from: 0, to: 5080, text: "5,080" },
  { label: "Interest", kind: "down", from: 5080, to: 3520, text: "-1,560" },
  { label: "Tax", kind: "down", from: 3520, to: 2910, text: "-610" },
  { label: "Working capital", kind: "down", from: 2910, to: 2740, text: "-170" },
  { label: "Capex", kind: "down", from: 2740, to: 2540, text: "-200" },
  { label: "Other", kind: "missing" },
  { label: "Free cash flow", kind: "total", from: 0, to: 2540, text: "2,540" },
];
const DOWNSIDE: WaterfallStep[] = [
  { label: "EBITDA", kind: "total", from: 0, to: 4120, text: "4,120" },
  { label: "Interest", kind: "down", from: 4120, to: 2330, text: "-1,790" },
  { label: "Tax", kind: "down", from: 2330, to: 1900, text: "-430" },
  { label: "Working capital", kind: "up", from: 1900, to: 1960, text: "+60" },
  { label: "Capex", kind: "down", from: 1960, to: 1810, text: "-150" },
  { label: "Other", kind: "missing" },
  { label: "Free cash flow", kind: "total", from: 0, to: 1810, text: "1,810" },
];
const NET_DEBT: WaterfallStep[] = [
  { label: "FY25E", kind: "total", from: 0, to: 26300, text: "26,300" },
  { label: "Cash flow FY26", kind: "down", from: 26300, to: 23760, text: "-2,540" },
  { label: "Cash flow FY27", kind: "down", from: 23760, to: 20924, text: "-2,836" },
  { label: "Acquisitions", kind: "up", from: 20924, to: 20924, text: "0" },
  { label: "Shareholder returns", kind: "missing" },
  { label: "FY27E", kind: "total", from: 0, to: 20924, text: "20,924" },
];
const TICKS = [
  { value: 0, label: "0" },
  { value: 1500, label: "1,500" },
  { value: 3000, label: "3,000" },
  { value: 4500, label: "4,500" },
  { value: 6000, label: "6,000" },
];
const ND_TICKS = [
  { value: 0, label: "0" },
  { value: 7500, label: "7,500" },
  { value: 15000, label: "15,000" },
  { value: 22500, label: "22,500" },
  { value: 30000, label: "30,000" },
];
const TABLE = {
  head: ["FY26, USD millions", "Base case", "Downside case"],
  rows: [
    { label: "EBITDA as defined", cells: ["5,080", "4,120"] },
    { label: "Cash interest", cells: ["-1,560", "-1,790"] },
    { label: "Cash tax", cells: ["-610", "-430"] },
    { label: "Change in working capital", cells: ["-170", "60"] },
    { label: "Capital expenditure", cells: ["-200", "-150"] },
    { label: "Other cash items", cells: [null, null] },
    { label: "Free cash flow", cells: ["2,540", "1,810"] },
  ],
};
const ND_TABLE = {
  head: ["USD millions", "Base case", "Downside case"],
  rows: [
    { label: "Net debt, FY25E", cells: ["26,300", "26,320"] },
    { label: "Free cash flow, FY26", cells: ["-2,540", "-1,810"] },
    { label: "Free cash flow, FY27", cells: ["-2,836", "-1,870"] },
    { label: "Acquisitions", cells: ["0", "0"] },
    { label: "Shareholder returns", cells: [null, null] },
    { label: "Net debt, FY27E", cells: ["20,924", "22,640"] },
  ],
};
const FORECAST_LEGEND = { total: "Total", down: "Cash out (minus)", up: "Cash in (plus)" };
const MODEL_LEGEND = { total: "Total", up: "Increase (plus)", down: "Decrease (minus)" };

function renderWalk(steps = BASE) {
  return render(
    <WaterfallChart
      title="From EBITDA to free cash flow"
      subtitle="FY26, USD millions"
      steps={steps}
      yTicks={TICKS}
      legend={FORECAST_LEGEND}
      table={TABLE}
    />,
  );
}
function renderNetDebt() {
  return render(
    <WaterfallChart
      title="Net debt walk"
      steps={NET_DEBT}
      yTicks={ND_TICKS}
      legend={MODEL_LEGEND}
      table={ND_TABLE}
    />,
  );
}
function bars(c: HTMLElement) {
  return [...c.querySelectorAll(".recharts-wrapper [data-bar]")];
}
function barOf(c: HTMLElement, step: string): Element {
  const found = bars(c).find((b) => b.getAttribute("data-step") === step);
  if (found === undefined) throw new Error(`no bar for ${step}`);
  return found;
}
const top = (b: Element) => Number(b.getAttribute("data-y"));
const bottom = (b: Element) =>
  Number(b.getAttribute("data-y")) + Number(b.getAttribute("data-height"));

describe("WaterfallChart chart side", () => {
  it("draws a column per present step with its exact label, none for the missing one", () => {
    const { container } = renderWalk();
    expect(bars(container).map((b) => b.getAttribute("data-step"))).toEqual([
      "EBITDA",
      "Interest",
      "Tax",
      "Working capital",
      "Capex",
      "Free cash flow",
    ]);
    const labels = [...container.querySelectorAll(".recharts-wrapper [data-label]")];
    expect(labels.map((t) => t.textContent)).toEqual([
      "5,080",
      "-1,560",
      "-610",
      "-170",
      "-200",
      "2,540",
    ]);
  });

  it("draws n.a. for Other, in text-tertiary, with no column", () => {
    const { container } = renderWalk();
    const na = [...container.querySelectorAll(".recharts-wrapper [data-missing]")];
    expect(na.map((t) => t.textContent)).toEqual(["n.a."]);
    expect(na[0]?.getAttribute("data-step")).toBe("Other");
    expect(na[0]?.getAttribute("fill")).toBe("var(--color-text-tertiary)");
    expect(na[0]?.hasAttribute("data-bar")).toBe(false);
  });

  it("floats each column from its own supplied positions", () => {
    const { container } = renderWalk();
    const [ebitda, interest, tax, wc, capex, fcf] = [
      "EBITDA",
      "Interest",
      "Tax",
      "Working capital",
      "Capex",
      "Free cash flow",
    ].map((s) => barOf(container, s));
    if (!ebitda || !interest || !tax || !wc || !capex || !fcf) throw new Error("missing bar");
    // Totals sit on the baseline: Free cash flow and EBITDA bottoms are equal.
    expect(bottom(ebitda)).toBeCloseTo(bottom(fcf), 1);
    // Each decrease starts where the supplied "from" is: its top meets the previous "to".
    expect(top(interest)).toBeCloseTo(top(ebitda), 1);
    expect(top(tax)).toBeCloseTo(bottom(interest), 1);
    expect(top(wc)).toBeCloseTo(bottom(tax), 1);
    expect(top(capex)).toBeCloseTo(bottom(wc), 1);
    // The column after the missing step floats from its own value: 2,540 of a 6,000 axis.
    const plotHeight = bottom(ebitda) - top(ebitda);
    expect(Number(fcf.getAttribute("data-height")) / plotHeight).toBeCloseTo(2540 / 5080, 2);
    expect(Number(interest.getAttribute("data-height")) / plotHeight).toBeCloseTo(1560 / 5080, 2);
  });

  it("floats an increase from its own values in the downside walk", () => {
    const { container } = renderWalk(DOWNSIDE);
    const wc = barOf(container, "Working capital");
    const tax = barOf(container, "Tax");
    expect(wc.getAttribute("data-kind")).toBe("up");
    expect(bottom(wc)).toBeCloseTo(bottom(tax), 1);
    expect(Number(wc.getAttribute("data-height"))).toBeGreaterThan(0);
    expect(wc.hasAttribute("data-zero")).toBe(false);
  });

  it("tells total, up and down apart by data attribute and fill", () => {
    const { container } = renderWalk(DOWNSIDE);
    const kind = (s: string) => barOf(container, s).getAttribute("data-kind");
    expect(kind("EBITDA")).toBe("total");
    expect(kind("Interest")).toBe("down");
    expect(kind("Working capital")).toBe("up");
    expect(barOf(container, "EBITDA").getAttribute("fill")).toBe("var(--color-chart-1)");
    expect(barOf(container, "Interest").getAttribute("fill")).toBe("var(--color-chart-3)");
    expect(barOf(container, "Working capital").getAttribute("fill")).toBe("var(--color-brand-400)");
  });

  it("labels a zero step 0 with a hairline, not n.a.", () => {
    const { container } = renderNetDebt();
    const zero = barOf(container, "Acquisitions");
    expect(zero.hasAttribute("data-zero")).toBe(true);
    expect(Number(zero.getAttribute("data-height"))).toBe(1);
    const label = [...container.querySelectorAll("[data-label]")].find(
      (t) => t.getAttribute("data-step") === "Acquisitions",
    );
    expect(label?.textContent).toBe("0");
    const na = [...container.querySelectorAll("[data-missing]")];
    expect(na.map((t) => t.getAttribute("data-step"))).toEqual(["Shareholder returns"]);
    // The hairline sits at 20,924 on the axis: level with the previous step's bottom.
    expect(top(zero)).toBeCloseTo(bottom(barOf(container, "Cash flow FY27")), 0);
  });

  it("draws bars at most 32px wide", () => {
    const { container } = renderWalk();
    for (const b of bars(container)) {
      expect(Number(b.getAttribute("data-width"))).toBeLessThanOrEqual(32);
    }
  });

  it("puts the y ticks as supplied", () => {
    const { container } = renderWalk();
    const ticks = [
      ...container.querySelectorAll(
        ".recharts-yAxis-tick-labels .recharts-cartesian-axis-tick-value",
      ),
    ].map((t) => t.textContent);
    expect(ticks).toEqual(["0", "1,500", "3,000", "4,500", "6,000"]);
  });

  it("shows the legend with the supplied words, in the order given", () => {
    const first = renderWalk();
    const items = (c: HTMLElement) =>
      within(within(c).getByRole("list", { name: "Legend" }))
        .getAllByRole("listitem")
        .map((li) => li.textContent);
    expect(items(first.container)).toEqual(["Total", "Cash out (minus)", "Cash in (plus)"]);
    const second = renderNetDebt();
    expect(items(second.container)).toEqual(["Total", "Increase (plus)", "Decrease (minus)"]);
  });

  it("mounts a readout on focus and ArrowRight with the exact strings", () => {
    const { container } = renderWalk();
    const surface = screen.getByRole("application", { name: "From EBITDA to free cash flow" });
    act(() => {
      surface.focus();
    });
    fireEvent.keyDown(surface, { key: "ArrowRight" });
    const tip = () => container.querySelector(".recharts-tooltip-wrapper");
    expect(tip()).toHaveTextContent("Interest");
    expect(tip()?.querySelector("li")?.textContent).toMatch(/^Interest\s+-1,560$/);
    for (let i = 0; i < 4; i++) fireEvent.keyDown(surface, { key: "ArrowRight" });
    expect(tip()?.querySelector("li")?.textContent).toMatch(/^Other\s+n\.a\.$/);
  });
});

describe("WaterfallChart table side", () => {
  it("shows the mock's strings, n.a. for Other cash items", () => {
    renderWalk();
    fireEvent.click(screen.getByRole("radio", { name: "Table" }));
    const cells = (name: RegExp) =>
      within(screen.getByRole("row", { name }))
        .getAllByRole("cell")
        .map((c) => c.textContent.replace("not available", ""));
    expect(cells(/Cash interest/)).toEqual(["-1,560", "-1,790"]);
    expect(cells(/Other cash items/)).toEqual(["n.a.", "n.a."]);
    expect(cells(/Free cash flow/)).toEqual(["2,540", "1,810"]);
  });
});

describe("WaterfallChart check", () => {
  function throwsOn(steps: WaterfallStep[], pattern: RegExp, table = TABLE) {
    const quiet = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() =>
      render(
        <WaterfallChart
          title="T"
          steps={steps}
          yTicks={[]}
          legend={FORECAST_LEGEND}
          table={table}
        />,
      ),
    ).toThrow(pattern);
    quiet.mockRestore();
  }
  const rest = BASE.slice(2);
  it("throws on empty steps", () => {
    throwsOn([], /at least one step/, { head: ["Step"], rows: [] });
  });
  it("throws on repeated labels", () => {
    throwsOn([BASE[0] as WaterfallStep, BASE[0] as WaterfallStep, ...rest], /distinct.*"EBITDA"/);
  });
  it("throws when an increase falls", () => {
    throwsOn(
      [
        BASE[0] as WaterfallStep,
        { label: "Interest", kind: "up", from: 5080, to: 3520, text: "+1,560" },
        ...rest,
      ],
      /"Interest".*up/,
    );
  });
  it("throws when a decrease rises", () => {
    throwsOn(
      [
        BASE[0] as WaterfallStep,
        { label: "Interest", kind: "down", from: 3520, to: 5080, text: "-1,560" },
        ...rest,
      ],
      /"Interest".*down/,
    );
  });
  it("throws when a total does not start at the baseline", () => {
    throwsOn(
      [{ label: "EBITDA", kind: "total", from: 100, to: 5080, text: "5,080" }, ...BASE.slice(1)],
      /"EBITDA".*total.*baseline/,
    );
  });
  it("throws when the table has a different number of rows than steps", () => {
    throwsOn(BASE, /table.*one row per step/, { ...TABLE, rows: TABLE.rows.slice(1) });
  });
  it("throws when a row has the wrong number of cells", () => {
    throwsOn(BASE, /"Cash tax".*cells/, {
      ...TABLE,
      rows: TABLE.rows.map((r) => (r.label === "Cash tax" ? { ...r, cells: ["-610"] } : r)),
    });
  });
});

describe("WaterfallChart x-axis", () => {
  it("names every step under its column and wraps a long name onto lines, never cutting it", () => {
    const { container } = renderNetDebt();
    const ticks = [...container.querySelectorAll(".recharts-wrapper [data-tick]")];
    expect(ticks.map((t) => t.getAttribute("data-tick"))).toEqual(NET_DEBT.map((s) => s.label));
    const lines = (label: string) =>
      [
        ...(ticks.find((t) => t.getAttribute("data-tick") === label)?.querySelectorAll("tspan") ??
          []),
      ].map((l) => l.textContent);
    expect(lines("Shareholder returns")).toEqual(["Shareholder", "returns"]);
    expect(lines("FY25E")).toEqual(["FY25E"]);
  });
});

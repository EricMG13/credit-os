import { createElement } from "react";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { BarLegend, ColumnsChart, topRounded } from "./ColumnsChart";
import { barOf, bars, renderMat, renderRec } from "./ColumnsChart.fixtures";
import { assignSeries } from "./series";

describe("ColumnsChart keys", () => {
  it("draws n.a. for series 'A/B' x group 'C' and series 'A' x group 'B/C' without a duplicate key", () => {
    const seen: string[] = [];
    const spy = vi.spyOn(console, "error").mockImplementation((...args: unknown[]) => {
      seen.push(args.map(String).join(" "));
    });
    const { container } = render(
      createElement(ColumnsChart, {
        title: "Keys",
        groups: ["C", "B/C"],
        series: [
          { name: "A/B", values: [null, 10], labels: [null, "10"] },
          { name: "A", values: [10, null], labels: ["10", null] },
        ],
        yTicks: [
          { value: 0, label: "0" },
          { value: 10, label: "10" },
        ],
        table: {
          head: ["Group", "A/B", "A"],
          rows: [
            { label: "C", cells: [null, "10"] },
            { label: "B/C", cells: ["10", null] },
          ],
        },
      }),
    );
    spy.mockRestore();
    expect(seen.filter((m) => m.includes("same key"))).toEqual([]);
    expect(
      [...container.querySelectorAll("[data-missing]")].map(
        (t) => `${t.getAttribute("data-series") ?? ""}|${t.getAttribute("data-group") ?? ""}`,
      ),
    ).toEqual(["A/B|C", "A|B/C"]);
  });
});

describe("ColumnsChart chart side", () => {
  it("draws a bar for every present value, zeros included, and none for the missing one", () => {
    const { container } = renderMat();
    expect(bars(container)).toHaveLength(17);
    const rec = renderRec();
    expect(bars(rec.container)).toHaveLength(5);
  });

  it("draws n.a. in the missing slot only, in text-tertiary", () => {
    const { container } = renderMat();
    const na = [...container.querySelectorAll(".recharts-wrapper [data-missing]")];
    expect(na.map((t) => t.textContent)).toEqual(["n.a."]);
    expect(na[0]?.getAttribute("fill")).toBe("var(--color-text-tertiary)");
    expect(na[0]?.getAttribute("data-series")).toBe("Term loans");
    const rec = renderRec();
    const recNa = rec.container.querySelectorAll(".recharts-wrapper [data-missing]");
    expect(recNa).toHaveLength(1);
    expect(recNa[0]?.getAttribute("data-series")).toBe("Downside case");
  });

  it("labels zero as 0 and distinguishes it from a missing value", () => {
    const { container } = renderMat();
    const zeros = [...container.querySelectorAll(".recharts-wrapper [data-zero]")];
    expect(zeros).toHaveLength(7);
    const zeroLabels = [...container.querySelectorAll(".recharts-wrapper [data-label]")].filter(
      (t) => t.textContent === "0",
    );
    expect(zeroLabels).toHaveLength(7);
    expect(Number(zeros[0]?.getAttribute("height"))).toBeGreaterThan(0);
    const missing = container.querySelector("[data-missing]");
    expect(missing?.hasAttribute("data-bar")).toBe(false);
    expect(missing?.hasAttribute("data-zero")).toBe(false);
  });

  it("draws labels exactly as given", () => {
    const { container } = renderRec();
    const labels = [...container.querySelectorAll(".recharts-wrapper [data-label]")].map(
      (t) => t.textContent,
    );
    expect([...labels].sort()).toEqual(["100%", "100%", "100%", "31%", "62%"]);
  });

  it("keeps the slot of a missing bar: the n.a. sits to the right of the present base bar", () => {
    const { container } = renderRec();
    const na = container.querySelector("[data-missing]");
    const base = barOf(container, "Base case", "Receivables facility");
    expect(base).toBeDefined();
    const baseCentre = Number(base?.getAttribute("x")) + Number(base?.getAttribute("width")) / 2;
    // One bar width (32) plus the gap (2) beyond the base bar's centre.
    expect(Number(na?.getAttribute("x"))).toBeCloseTo(baseCentre + 34, 0);
  });

  it("scales bar heights by the supplied values", () => {
    const { container } = renderRec();
    const h = (series: string, group: string) =>
      Number(barOf(container, series, group)?.getAttribute("height"));
    const full = h("Base case", "Term loans and secured notes");
    expect(full).toBeGreaterThan(0);
    expect(h("Base case", "Senior subordinated notes")).toBeCloseTo(full * 0.62, 0);
    expect(h("Downside case", "Senior subordinated notes")).toBeCloseTo(full * 0.31, 0);
  });

  it("draws bars at most 32px wide, narrower for three series", () => {
    const mat = renderMat();
    const rec = renderRec();
    const widths = (c: HTMLElement) => bars(c).map((b) => Number(b.getAttribute("width")));
    expect(Math.max(...widths(rec.container))).toBeLessThanOrEqual(32);
    expect(Math.max(...widths(mat.container))).toBeLessThan(Math.max(...widths(rec.container)));
  });

  it("puts the y ticks as supplied", () => {
    const { container } = renderMat();
    const ticks = [
      ...container.querySelectorAll(
        ".recharts-yAxis-tick-labels .recharts-cartesian-axis-tick-value",
      ),
    ].map((t) => t.textContent);
    expect(ticks).toEqual(["0", "1,250", "2,500", "3,750", "5,000"]);
  });

  it("shows the legend in bar order for two or more series", () => {
    renderMat();
    const legend = screen.getByRole("list", { name: "Legend" });
    expect(
      within(legend)
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["Term loans", "Secured notes", "Subordinated notes"]);
  });

  it("shows no legend for one series", () => {
    render(
      <ColumnsChart
        title="One"
        groups={["A"]}
        series={[{ name: "S", values: [1], labels: ["1"] }]}
        yTicks={[]}
        table={{ head: ["G", "S"], rows: [{ label: "A", cells: ["1"] }] }}
      />,
    );
    expect(screen.queryByRole("list", { name: "Legend" })).toBeNull();
  });

  it("mounts a readout on focus and ArrowRight with the exact strings", () => {
    const { container } = renderMat();
    const surface = screen.getByRole("application", { name: "Maturities by year" });
    act(() => {
      surface.focus();
    });
    fireEvent.keyDown(surface, { key: "ArrowRight" });
    const tip = () => container.querySelector(".recharts-tooltip-wrapper");
    expect(tip()).not.toBeNull();
    expect(tip()).toHaveTextContent("2027");
    fireEvent.keyDown(surface, { key: "ArrowLeft" });
    expect(tip()).toHaveTextContent("2026");
    expect(tip()).toHaveTextContent("Term loans");
    expect(tip()).toHaveTextContent("n.a.");
    expect(tip()?.querySelector("li")?.textContent).toMatch(/^Term loans\s+n\.a\.$/);
    fireEvent.keyDown(surface, { key: "ArrowRight" });
    expect(tip()).toHaveTextContent("2027");
    expect(tip()).toHaveTextContent("550");
  });
});

describe("ColumnsChart table side", () => {
  it("shows the mock's maturities strings, n.a. for the missing loan repayment", () => {
    renderMat();
    fireEvent.click(screen.getByRole("radio", { name: "Table" }));
    const cells = (name: string) =>
      within(screen.getByRole("row", { name: new RegExp(name) }))
        .getAllByRole("cell")
        .map((c) => c.textContent.replace("not available", ""));
    expect(cells("2026")).toEqual(["n.a.", "0", "0"]);
    expect(cells("2031 on")).toEqual(["3,200", "4,150", "4,100"]);
  });

  it("shows the mock's recovery strings", () => {
    renderRec();
    fireEvent.click(screen.getByRole("radio", { name: "Table" }));
    const row = screen.getByRole("row", { name: /Receivables facility/ });
    expect(
      within(row)
        .getAllByRole("cell")
        .map((c) => c.textContent.replace("not available", "")),
    ).toEqual(["100%", "n.a."]);
  });
});

describe("ColumnsChart measured pass", () => {
  it("draws the n.a. mark once the chart is measured", () => {
    const { container } = renderMat();
    expect(container.querySelectorAll("[data-missing]")).toHaveLength(1);
  });
});

describe("topRounded", () => {
  it("rounds the top corners of a 20 by 10 bar at the origin with radius 6", () => {
    expect(topRounded(0, 0, 20, 10, 6)).toBe("M0,10V6Q0,0 6,0H14Q20,0 20,6V10Z");
  });

  it("offsets every coordinate by the bar's origin", () => {
    expect(topRounded(5, 2, 20, 10, 6)).toBe("M5,12V8Q5,2 11,2H19Q25,2 25,8V12Z");
  });

  it("limits the radius to half the width", () => {
    expect(topRounded(0, 0, 8, 10, 6)).toBe("M0,10V4Q0,0 4,0H4Q8,0 8,4V10Z");
  });

  it("limits the radius to the height of a short bar", () => {
    expect(topRounded(0, 0, 20, 3, 6)).toBe("M0,3V3Q0,0 3,0H17Q20,0 20,3V3Z");
  });
});

describe("BarLegend", () => {
  const names = ["Base case", "Downside case"];

  it("lists each name in order with one colour swatch each", () => {
    render(<BarLegend names={names} styles={assignSeries(names)} />);
    const list = screen.getByRole("list", { name: "Legend" });
    const items = within(list).getAllByRole("listitem");
    expect(items.map((li) => li.textContent)).toEqual(names);
    for (const li of items) expect(li.querySelectorAll("svg rect")).toHaveLength(1);
  });

  it("centres the entries only when asked", () => {
    const styles = assignSeries(names);
    const plain = render(<BarLegend names={names} styles={styles} />);
    expect(screen.getByRole("list", { name: "Legend" }).className).not.toContain("justify-center");
    plain.unmount();
    render(<BarLegend names={names} styles={styles} centered />);
    expect(screen.getByRole("list", { name: "Legend" }).className).toContain("justify-center");
  });
});

describe("ColumnsChart x-axis", () => {
  it("names every group under its bars, the whole text of each", () => {
    const { container } = renderRec();
    const ticks = [...container.querySelectorAll(".recharts-wrapper [data-tick]")];
    expect(ticks.map((t) => t.getAttribute("data-tick"))).toEqual([
      "Term loans and secured notes",
      "Senior subordinated notes",
      "Receivables facility",
    ]);
    const words = (tick: Element | undefined) =>
      [...(tick?.querySelectorAll("tspan") ?? [])].map((l) => l.textContent).join(" ");
    expect(ticks.map((t) => words(t))).toEqual([
      "Term loans and secured notes",
      "Senior subordinated notes",
      "Receivables facility",
    ]);
  });
});

import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { PERIOD_INSET, PathChart, ReadoutRow, axisHeight, cellText } from "./PathChart";

const PERIODS = ["FY22", "FY23", "FY24", "LTM", "FY25E", "FY26E", "FY27E"];
const BASE = [2646, 3395, 4173, 4560, 4690, 5080, 5460];
const DOWN: (number | null)[] = [null, null, null, null, 4560, 4120, 4350];
const TICKS = [
  { value: 0, label: "0" },
  { value: 1500, label: "1,500" },
  { value: 3000, label: "3,000" },
  { value: 4500, label: "4,500" },
  { value: 6000, label: "6,000" },
];
const TABLE = {
  head: ["EBITDA as defined", ...PERIODS],
  rows: [
    { label: "Base case", cells: ["2,646", "3,395", "4,173", "4,560", "4,690", "5,080", "5,460"] },
    {
      label: "Downside case",
      cells: ["2,646", "3,395", "4,173", "4,560", "4,560", "4,120", "4,350"],
    },
  ],
};
const BASE_LABELS = ["2,646", null, null, "4,560", null, null, "5,460"];
const DOWN_LABELS = [null, null, null, null, null, "4,120", "4,350"];

function renderEbitda() {
  return render(
    <PathChart
      title="EBITDA by case"
      periods={PERIODS}
      series={[
        { name: "Actual, then base case", values: BASE, labels: BASE_LABELS },
        { name: "Downside case", values: DOWN, labels: DOWN_LABELS },
      ]}
      divider={{ period: "LTM", at: "on", label: "Last actual" }}
      yTicks={TICKS}
      table={TABLE}
    />,
  );
}

const COVER_PERIODS = PERIODS;
const COVER = [2.6, null, 2.8, 2.9, 3.0, 3.3, 3.6];
const COVER_LABELS = ["2.6x", null, "2.8x", "2.9x", "3.0x", "3.3x", "3.6x"];
const COVER_TABLE = {
  head: ["Interest cover", ...PERIODS],
  rows: [{ label: "Base case", cells: ["2.6x", null, "2.8x", "2.9x", "3.0x", "3.3x", "3.6x"] }],
};

function renderCover() {
  return render(
    <PathChart
      title="Interest cover"
      periods={COVER_PERIODS}
      series={[{ name: "Base case", values: COVER, labels: COVER_LABELS }]}
      yTicks={[
        { value: 0, label: "0" },
        { value: 4, label: "4x" },
      ]}
      table={COVER_TABLE}
    />,
  );
}

function markerAt(container: HTMLElement, name: string, index: number): Element {
  const found = [...container.querySelectorAll(".recharts-wrapper [data-marker]")].filter(
    (el) => el.getAttribute("data-series") === name,
  )[index];
  if (found === undefined) throw new Error(`no marker ${String(index)} for ${name}`);
  return found;
}

function markers(container: HTMLElement, name: string): number {
  return [...container.querySelectorAll(".recharts-wrapper [data-marker]")].filter(
    (el) => el.getAttribute("data-series") === name,
  ).length;
}

describe("PathChart chart side", () => {
  it("draws one marker per present value and none for a missing one", () => {
    const { container } = renderEbitda();
    expect(markers(container, "Actual, then base case")).toBe(7);
    expect(markers(container, "Downside case")).toBe(3);
    const cover = renderCover();
    expect(markers(cover.container, "Base case")).toBe(6);
  });

  it("breaks the line at the missing period", () => {
    const { container } = renderCover();
    const paths = [...container.querySelectorAll("path.recharts-line-curve")];
    expect(paths).toHaveLength(1);
    expect(paths[0]?.getAttribute("d")?.match(/M/g)).toHaveLength(2);
  });

  it("draws the downside line as one run of three points: one move and two line segments", () => {
    const { container } = renderEbitda();
    const paths = [...container.querySelectorAll("path.recharts-line-curve")];
    expect(paths).toHaveLength(2);
    expect(paths[1]?.getAttribute("d")?.match(/M/g)).toHaveLength(1);
    expect(paths[1]?.getAttribute("d")?.match(/L/g)).toHaveLength(2);
  });

  it("shows n.a. at the baseline for a period where every series is missing", () => {
    const { container } = renderCover();
    const na = [...container.querySelectorAll(".recharts-wrapper text")].filter(
      (t) => t.textContent === "n.a.",
    );
    expect(na).toHaveLength(1);
  });

  it("draws no n.a. when every period has a value", () => {
    const { container } = renderEbitda();
    const na = [...container.querySelectorAll(".recharts-wrapper text")].filter(
      (t) => t.textContent === "n.a.",
    );
    expect(na).toHaveLength(0);
  });

  it("draws direct labels exactly as given", () => {
    const { container } = renderEbitda();
    const texts = [...container.querySelectorAll(".recharts-wrapper [data-label]")].map(
      (t) => t.textContent,
    );
    expect([...texts].sort()).toEqual(["2,646", "4,120", "4,350", "4,560", "5,460"].sort());
  });

  it("places the second series' labels below their markers and the first's above", () => {
    const { container } = renderEbitda();
    const label = (text: string, series: string) =>
      [
        ...container.querySelectorAll(`.recharts-wrapper [data-label][data-series="${series}"]`),
      ].find((t) => t.textContent === text);
    const mark = (series: string, i: number) =>
      [...container.querySelectorAll(`.recharts-wrapper [data-marker][data-series="${series}"]`)][
        i
      ];
    const num = (el: Element | undefined, attr: string) => Number(el?.getAttribute(attr));
    const base = mark("Actual, then base case", 6);
    expect(num(label("5,460", "Actual, then base case"), "y")).toBeLessThan(num(base, "cy"));
    const down = mark("Downside case", 1);
    const downCentre = num(down, "y") + num(down, "height") / 2;
    expect(num(label("4,120", "Downside case"), "y")).toBeGreaterThan(downCentre);
  });

  it("draws the divider with its label, dashed", () => {
    const { container } = renderEbitda();
    expect(within(container).getByText("Last actual")).toBeInTheDocument();
    expect(
      container.querySelector("[data-divider]")?.getAttribute("stroke-dasharray"),
    ).toBeTruthy();
  });

  it("draws an 'on' divider at the period's point (mock: Last actual at 3.5 of 7)", () => {
    const { container } = renderEbitda();
    const ltm = Number(markerAt(container, "Actual, then base case", 3).getAttribute("cx"));
    expect(Number(container.querySelector("[data-divider]")?.getAttribute("x1"))).toBeCloseTo(
      ltm,
      1,
    );
  });

  it("draws an 'after' divider at the boundary after the period (mock: Forecast at 4 of 7)", () => {
    const { container } = render(
      <PathChart
        title="Interest cover"
        periods={PERIODS}
        series={[{ name: "Base case", values: COVER, labels: COVER_LABELS }]}
        divider={{ period: "LTM", at: "after", label: "Forecast" }}
        yTicks={[
          { value: 0, label: "0" },
          { value: 4, label: "4x" },
        ]}
        table={COVER_TABLE}
      />,
    );
    // The markers are the six present values; FY23 has none, so LTM is the third and FY25E the fourth.
    const x = (i: number) => Number(markerAt(container, "Base case", i).getAttribute("cx"));
    const line = Number(container.querySelector("[data-divider]")?.getAttribute("x1"));
    expect(line).toBeGreaterThan(x(2));
    expect(line).toBeLessThan(x(3));
    expect(line).toBeCloseTo((x(2) + x(3)) / 2, 1);
  });

  it("colours point labels text-primary and the chart's n.a. text-tertiary", () => {
    const { container } = renderCover();
    const label = container.querySelector("[data-label]");
    expect(label?.getAttribute("fill")).toBe("var(--color-text-primary)");
    const na = [...container.querySelectorAll(".recharts-wrapper text")].find(
      (t) => t.textContent === "n.a.",
    );
    expect(na?.getAttribute("fill")).toBe("var(--color-text-tertiary)");
  });

  it("mounts a readout on focus and ArrowRight, with the exact strings, n.a. for a missing value", () => {
    const { container } = renderCover();
    const surface = screen.getByRole("application", { name: "Interest cover" });
    act(() => {
      surface.focus();
    });
    fireEvent.keyDown(surface, { key: "ArrowRight" });
    const tip = () => container.querySelector(".recharts-tooltip-wrapper");
    expect(tip()).not.toBeNull();
    expect(tip()).toHaveTextContent("FY23");
    expect(tip()).toHaveTextContent("Base case");
    expect(tip()).toHaveTextContent("n.a.");
    fireEvent.keyDown(surface, { key: "ArrowLeft" });
    expect(tip()).toHaveTextContent("FY22");
    expect(tip()).toHaveTextContent("2.6x");
    expect(tip()?.querySelector("li")?.textContent).toMatch(/^Base case\s+2\.6x$/);
    expect(tip()?.querySelector("li")).toHaveClass("flex", "justify-between", "gap-4");
  });

  it("reads withheld and gap cells in words in the readout", () => {
    const { container } = render(
      <PathChart
        title="W"
        periods={["P1", "P2"]}
        series={[{ name: "A", values: [1, 2], labels: [null, null] }]}
        yTicks={[]}
        table={{
          head: ["W", "P1", "P2"],
          rows: [{ label: "A", cells: [{ withheld: true }, { gap: true }] }],
        }}
      />,
    );
    const surface = screen.getByRole("application", { name: "W" });
    act(() => {
      surface.focus();
    });
    fireEvent.keyDown(surface, { key: "ArrowRight" });
    const tip = () => container.querySelector(".recharts-tooltip-wrapper");
    expect(tip()).toHaveTextContent("Not established for this run");
    fireEvent.keyDown(surface, { key: "ArrowLeft" });
    expect(tip()).toHaveTextContent("Withheld");
  });

  it("puts the y ticks as supplied", () => {
    const { container } = renderEbitda();
    const ticks = [
      ...container.querySelectorAll(
        ".recharts-yAxis-tick-labels .recharts-cartesian-axis-tick-value",
      ),
    ].map((t) => t.textContent);
    expect(ticks).toEqual(["0", "1,500", "3,000", "4,500", "6,000"]);
  });

  it("shows a legend for two series and none for one", () => {
    renderEbitda();
    const legend = screen.getByRole("list", { name: "Legend" });
    expect(
      within(legend)
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["Actual, then base case", "Downside case"]);
  });

  it("shows no legend for one series", () => {
    renderCover();
    expect(screen.queryByRole("list", { name: "Legend" })).toBeNull();
  });
});

describe("PathChart table side", () => {
  it("switches to the mock's table strings, n.a. for the missing period", () => {
    renderCover();
    fireEvent.click(screen.getByRole("radio", { name: "Table" }));
    const row = screen.getByRole("row", { name: /Base case/ });
    expect(
      within(row)
        .getAllByRole("cell")
        .map((c) => c.textContent.replace("not available", "")),
    ).toEqual(["2.6x", "n.a.", "2.8x", "2.9x", "3.0x", "3.3x", "3.6x"]);
  });

  it("shows the EBITDA by case strings", () => {
    renderEbitda();
    fireEvent.click(screen.getByRole("radio", { name: "Table" }));
    const row = screen.getByRole("row", { name: /Downside case/ });
    expect(
      within(row)
        .getAllByRole("cell")
        .map((c) => c.textContent),
    ).toEqual(["2,646", "3,395", "4,173", "4,560", "4,560", "4,120", "4,350"]);
  });
});

describe("PathChart check", () => {
  const props = {
    title: "T",
    periods: ["P1", "P2"],
    yTicks: [],
    table: { head: ["T", "P1", "P2"], rows: [{ label: "A", cells: ["1", "2"] }] },
  };
  function throwsOn(ui: React.ReactElement, pattern: RegExp) {
    const quiet = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() => render(ui)).toThrow(pattern);
    quiet.mockRestore();
  }
  it("throws when the table's columns are not the periods, in order", () => {
    throwsOn(
      <PathChart
        {...props}
        series={[{ name: "A", values: [1, 2], labels: [null, null] }]}
        table={{ head: ["T", "P1", "P3"], rows: [{ label: "A", cells: ["1", "2"] }] }}
      />,
      /columns.*periods/,
    );
  });
  it("throws when the table has the periods in another order", () => {
    throwsOn(
      <PathChart
        {...props}
        series={[{ name: "A", values: [1, 2], labels: [null, null] }]}
        table={{ head: ["T", "P2", "P1"], rows: [{ label: "A", cells: ["1", "2"] }] }}
      />,
      /columns.*periods/,
    );
  });
  it("throws when values do not match the periods", () => {
    throwsOn(
      <PathChart {...props} series={[{ name: "A", values: [1], labels: [null, null] }]} />,
      /"A".*per period/,
    );
  });
  it("throws when labels do not match the periods", () => {
    throwsOn(
      <PathChart {...props} series={[{ name: "A", values: [1, 2], labels: [null] }]} />,
      /"A".*per period/,
    );
  });
  it("throws when two series share a name", () => {
    const s = { name: "A", values: [1, 2], labels: [null, null] };
    throwsOn(<PathChart {...props} series={[s, s]} />, /distinct/);
  });
  it("throws when the divider period is not one of the periods", () => {
    throwsOn(
      <PathChart
        {...props}
        series={[{ name: "A", values: [1, 2], labels: [null, null] }]}
        divider={{ period: "P9", at: "on", label: "x" }}
      />,
      /P9/,
    );
  });
  it("throws when an 'after' divider names the last period", () => {
    throwsOn(
      <PathChart
        {...props}
        series={[{ name: "A", values: [1, 2], labels: [null, null] }]}
        divider={{ period: "P2", at: "after", label: "x" }}
      />,
      /last period/,
    );
  });
});

describe("cellText", () => {
  it("returns a string cell unchanged", () => {
    expect(cellText("2.6x")).toBe("2.6x");
  });
  it("draws a missing cell as n.a.", () => {
    expect(cellText(null)).toBe("n.a.");
  });
  it("names a withheld cell", () => {
    expect(cellText({ withheld: true })).toBe("Withheld");
  });
  it("names a gap cell", () => {
    expect(cellText({ gap: true })).toBe("Not established for this run");
  });
  it("throws for an undefined cell", () => {
    expect(() => cellText(undefined)).toThrow(/no cell/);
  });
});

describe("ReadoutRow", () => {
  it("renders the name and the value as one row of text", () => {
    const { container } = render(
      <ul>
        <ReadoutRow name="Base case" values={["2.6x"]} />
      </ul>,
    );
    expect(container.querySelector("li")?.textContent).toBe("Base case 2.6x");
  });
});

describe("PathChart x-axis", () => {
  it("names every period under its point", () => {
    const { container } = renderEbitda();
    const ticks = [...container.querySelectorAll(".recharts-wrapper [data-tick]")];
    expect(ticks.map((t) => t.getAttribute("data-tick"))).toEqual(PERIODS);
  });
});

describe("PathChart room", () => {
  it("insets the first and last period from the plot's edges by a label's half width", () => {
    expect(PERIOD_INSET).toEqual({ left: 24, right: 16 });
  });

  it("reserves one tick line for single-word periods and one more per extra word", () => {
    expect(axisHeight(PERIODS)).toBe(32);
    expect(axisHeight(["FY22", "Last actual"])).toBe(46);
    expect(axisHeight(["A b c", "D"])).toBe(60);
  });
});

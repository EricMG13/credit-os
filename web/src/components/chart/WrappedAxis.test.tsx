import { act, render, renderHook } from "@testing-library/react";
import { ColumnsChart } from "./ColumnsChart";
import { PathChart, WRAPPED_AXIS_HEIGHT, WrappedTick, useWrappedAxis } from "./PathChart";
import { WaterfallChart } from "./WaterfallChart";

// Six ten-word labels at the test's 600px chart width break into five lines or more in a band of about 90px.
const LONG = [
  "Cash flow from operating activities before tax and interest",
  "Cash flow from investing activities net of disposals made",
  "Cash flow from financing activities net of new borrowings",
  "Cash paid for interest and fees on all debt classes",
  "Cash received from asset disposals made in the year",
  "Cash and equivalents held at period end after all items",
];
const YTICKS = [
  { value: 0, label: "0" },
  { value: 100, label: "100" },
];

/** Every line of every tick must sit inside the chart's svg, three pixels above its bottom edge. */
function expectTicksInsideSvg(container: HTMLElement) {
  const svg = container.querySelector("svg.recharts-surface");
  const svgHeight = Number(svg?.getAttribute("height"));
  const ticks = [...container.querySelectorAll(".recharts-wrapper [data-tick]")];
  expect(ticks.map((t) => t.getAttribute("data-tick"))).toEqual(LONG);
  for (const tick of ticks) {
    const lines = tick.querySelectorAll("tspan");
    expect([...lines].map((l) => l.textContent).join(" ")).toBe(tick.getAttribute("data-tick"));
    const last = Number(tick.getAttribute("y")) + (lines.length - 1) * 14;
    expect(last).toBeLessThanOrEqual(svgHeight - 3);
  }
}

describe("the value axis room the wrapped axis allows for", () => {
  it("counts Recharts' 6px tick size: at width 195 'Bond loans' breaks over two lines, so 46px", () => {
    // Recharts 3.10.1 sizes a y-axis as text + tick size 6 + tick margin 8 even with tick lines off:
    // plot = 195 - 24 - (5 chars * 6.5 + 6 + 8) = 124.5; a band of 62.25 holds 9 characters, so
    // "Bond loans" (10) breaks to "Bond" / "loans": 14 * 2 + 18 = 46.
    const ticks = [
      { value: 0, label: "0" },
      { value: 1000, label: "1,000" },
    ];
    const { result } = renderHook(() => useWrappedAxis(["Bond loans", "Cash"], ticks));
    act(() => {
      result.current.onResize(195);
    });
    expect(result.current.height).toBe(46);
  });
});

describe("category axis room for wrapped labels", () => {
  it("fits the waterfall's longest label", () => {
    const { container } = render(
      <WaterfallChart
        title="Walk"
        steps={LONG.map((label) => ({
          label,
          kind: "total" as const,
          from: 0,
          to: 50,
          text: "50",
        }))}
        yTicks={YTICKS}
        legend={{ total: "Total", up: "Up", down: "Down" }}
        table={{ head: ["Step", "Value"], rows: LONG.map((label) => ({ label, cells: ["50"] })) }}
      />,
    );
    expectTicksInsideSvg(container);
  });

  it("fits the columns chart's longest group name", () => {
    const { container } = render(
      <ColumnsChart
        title="Columns"
        groups={LONG}
        series={[{ name: "A", values: LONG.map(() => 50), labels: LONG.map(() => "50") }]}
        yTicks={YTICKS}
        table={{ head: ["Group", "A"], rows: LONG.map((label) => ({ label, cells: ["50"] })) }}
      />,
    );
    expectTicksInsideSvg(container);
  });

  it("fits the path chart's longest period name", () => {
    const { container } = render(
      <PathChart
        title="Path"
        periods={LONG}
        series={[{ name: "A", values: LONG.map(() => 50), labels: LONG.map(() => "50") }]}
        yTicks={YTICKS}
        table={{ head: ["Series", ...LONG], rows: [{ label: "A", cells: LONG.map(() => "50") }] }}
      />,
    );
    expectTicksInsideSvg(container);
  });

  it("widens a label's lines rather than clip it when the axis it is given holds three", () => {
    const label = "Cash flow from operations before tax";
    const props = {
      x: 100,
      y: 214,
      width: 346,
      height: WRAPPED_AXIS_HEIGHT,
      visibleTicksCount: 6,
      payload: { value: label, coordinate: 100, index: 0, offset: 0 },
    } as unknown as Parameters<typeof WrappedTick>[0];
    const { container } = render(
      <svg>
        <WrappedTick {...props} />
      </svg>,
    );
    const lines = [...container.querySelectorAll("tspan")].map((l) => l.textContent);
    expect(lines).toEqual(["Cash flow from", "operations", "before tax"]);
  });
});

import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { ScatterPlot, type ScatterPoint } from "./ScatterPlot";

// Values and strings are copied from the mock's script block (Model 4 Portfolio fit, "Leverage and
// margin against holdings"): H gives each holding's leverage and margin, the issuer is TransDigm.
const POINTS: ScatterPoint[] = [
  { name: "TransDigm", x: 5.9, y: 53.1, xText: "5.9x", yText: "53.1%", emphasis: true },
  { name: "Holding A", x: 3.1, y: 22, xText: "3.1x", yText: "22%" },
  { name: "Holding B", x: 4.2, y: 31, xText: "4.2x", yText: "31%" },
  { name: "Holding C", x: 2.6, y: 14, xText: "2.6x", yText: "14%" },
  { name: "Holding D", x: 5.1, y: 27, xText: "5.1x", yText: "27%" },
  { name: "Holding E", x: 6.8, y: 19, xText: "6.8x", yText: "19%" },
  { name: "Holding F", x: 3.8, y: 41, xText: "3.8x", yText: "41%" },
  { name: "Holding G", x: 4.6, y: 9, xText: "4.6x", yText: "9%" },
  { name: "Holding H", x: 5.6, y: 36, xText: "5.6x", yText: "36%" },
  { name: "Holding I", x: 2.4, y: 18, xText: "2.4x", yText: "18%" },
  { name: "Holding J", x: 4.4, y: null, xText: "4.4x", yText: null },
  { name: "Holding K", x: null, y: 24, xText: null, yText: "24%" },
];
const TABLE = {
  head: ["Issuer", "Net leverage", "EBITDA margin"],
  rows: [
    { label: "TransDigm", cells: ["5.9x", "53.1%"] },
    { label: "Holding A", cells: ["3.1x", "22%"] },
    { label: "Holding B", cells: ["4.2x", "31%"] },
    { label: "Holding C", cells: ["2.6x", "14%"] },
    { label: "Holding D", cells: ["5.1x", "27%"] },
    { label: "Holding E", cells: ["6.8x", "19%"] },
    { label: "Holding F", cells: ["3.8x", "41%"] },
    { label: "Holding G", cells: ["4.6x", "9%"] },
    { label: "Holding H", cells: ["5.6x", "36%"] },
    { label: "Holding I", cells: ["2.4x", "18%"] },
    { label: "Holding J", cells: ["4.4x", null] },
    { label: "Holding K", cells: [null, "24%"] },
  ],
};
const X = {
  title: "Net leverage",
  short: "net leverage",
  ticks: [2, 3, 4, 5, 6, 7, 8].map((v) => ({ value: v, label: `${String(v)}x` })),
};
const Y = {
  title: "EBITDA margin",
  short: "EBITDA margin",
  ticks: [
    { value: 0, label: "0" },
    { value: 15, label: "15%" },
    { value: 30, label: "30%" },
    { value: 45, label: "45%" },
    { value: 60, label: "60%" },
  ],
};
type Props = Parameters<typeof ScatterPlot>[0];
const base = {
  title: "Leverage and margin against holdings",
  subtitle: "Latest twelve months, one mark per issuer held",
  x: X,
  y: Y,
  othersName: "Other holdings",
  points: POINTS,
  table: TABLE,
} satisfies Props;

describe("ScatterPlot chart side", () => {
  it("draws one mark per complete point, the issuer apart, and both axis titles", () => {
    const { container } = render(<ScatterPlot {...base} />);
    const marks = [...container.querySelectorAll(".recharts-wrapper [data-point]")];
    expect(marks.map((m) => m.getAttribute("data-point"))).toEqual([
      "TransDigm",
      ...["A", "B", "C", "D", "E", "F", "G", "H", "I"].map((n) => `Holding ${n}`),
    ]);
    expect(
      screen.getByText("Net leverage", { selector: "svg tspan, svg text" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("EBITDA margin", { selector: "svg tspan, svg text" }),
    ).toBeInTheDocument();
    expect(screen.getByText("TransDigm", { selector: "svg tspan, svg text" })).toBeInTheDocument();
  });

  it("keeps the x-axis title inside the drawing, under the tick labels", () => {
    const { container } = render(<ScatterPlot {...base} />);
    const title = screen.getByText("Net leverage", { selector: "svg tspan, svg text" });
    const label = title.closest("text");
    const height = Number(container.querySelector("svg.recharts-surface")?.getAttribute("height"));
    expect(Number(label?.getAttribute("y"))).toBeLessThanOrEqual(height - 4);
  });

  it("lists the incomplete holdings as not plotted, with the missing measure", () => {
    render(<ScatterPlot {...base} />);
    expect(
      screen.getByText(
        "Not plotted: Holding J (EBITDA margin n.a.), Holding K (net leverage n.a.).",
      ),
    ).toBeInTheDocument();
  });

  it("shows the legend and subtitle", () => {
    render(<ScatterPlot {...base} />);
    expect(screen.getByRole("list", { name: "Legend" })).toHaveTextContent("Other holdings");
    expect(screen.getByText(base.subtitle)).toBeInTheDocument();
  });

  it("draws each legend key as the marker alone, with no line through it, the list centred", () => {
    render(<ScatterPlot {...base} />);
    const legend = screen.getByRole("list", { name: "Legend" });
    const items = within(legend).getAllByRole("listitem");
    expect(items.map((li) => li.textContent)).toEqual(["TransDigm", "Other holdings"]);
    expect(legend.querySelector("line")).toBeNull();
    expect(items[0]?.querySelector("circle")).not.toBeNull();
    expect(items[1]?.querySelector("[data-marker='square']")).not.toBeNull();
    expect(legend).toHaveClass("justify-center");
  });

  it("mounts a readout on focus and ArrowRight with the point's name and exact strings", () => {
    const { container } = render(<ScatterPlot {...base} />);
    const surface = screen.getByRole("application", { name: base.title });
    act(() => {
      surface.focus();
    });
    const readout = () => {
      const tip = container.querySelector(".recharts-tooltip-wrapper");
      return [
        tip?.querySelector("p")?.textContent ?? "",
        ...(tip?.querySelectorAll("li") ?? []),
      ].map((e) => (typeof e === "string" ? e : e.textContent.replace(/\s+/g, " ")));
    };
    fireEvent.keyDown(surface, { key: "ArrowRight" });
    expect(readout()).toEqual(["Holding A", "Net leverage 3.1x", "EBITDA margin 22%"]);
    fireEvent.keyDown(surface, { key: "ArrowLeft" });
    expect(readout()).toEqual(["TransDigm", "Net leverage 5.9x", "EBITDA margin 53.1%"]);
  });
});

describe("ScatterPlot table side", () => {
  it("lists every point with n.a. in the missing cell", () => {
    render(<ScatterPlot {...base} />);
    fireEvent.click(screen.getByRole("radio", { name: "Table" }));
    const row = screen.getByRole("row", { name: /Holding J/ });
    expect(
      within(row)
        .getAllByRole("cell")
        .map((c) => c.textContent),
    ).toEqual(["4.4x", "n.a.not available"]);
  });
});

describe("ScatterPlot check", () => {
  const bad = (props: Partial<Props>) => expect(() => render(<ScatterPlot {...base} {...props} />));
  const first = POINTS[0] as ScatterPoint;
  it("throws for no points and for a NaN position", () => {
    bad({ points: [], table: { ...TABLE, rows: [] } }).toThrow(/at least one point/);
    bad({ points: [{ ...first, x: Number.NaN }, ...POINTS.slice(1)] }).toThrow(/TransDigm/);
  });
  it("throws for a text that disagrees with its value", () => {
    bad({ points: [{ ...first, xText: null }, ...POINTS.slice(1)] }).toThrow(/TransDigm/);
    bad({ points: [{ ...first, y: null }, ...POINTS.slice(1)] }).toThrow(/TransDigm/);
  });
  it("throws for repeats, two emphasised points, a point off the axes and a wrong table", () => {
    bad({ points: [first, first] }).toThrow(/distinct/);
    bad({ points: POINTS.map((p) => ({ ...p, emphasis: true })) }).toThrow(/one emphasised/);
    bad({ points: [{ ...first, x: 9 }, ...POINTS.slice(1)] }).toThrow(/axis/);
    bad({ table: { ...TABLE, rows: TABLE.rows.slice(1) } }).toThrow(/table/);
    bad({
      table: {
        ...TABLE,
        rows: [{ label: "TransDigm", cells: ["5.8x", "53.1%"] }, ...TABLE.rows.slice(1)],
      },
    }).toThrow(/table/);
  });
});

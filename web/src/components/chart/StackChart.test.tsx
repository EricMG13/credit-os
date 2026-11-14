import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { StackChart, type StackPart } from "./StackChart";

// Values and strings are copied from the mock's script block (Model 3 Model, "Debt by instrument").
const PARTS: StackPart[] = [
  { name: "Term loans", value: 38.0, text: "11,300", share: "38%" },
  { name: "Senior secured notes", value: 35.2, text: "10,450", share: "35%" },
  { name: "Senior subordinated notes", value: 24.6, text: "7,300", share: "25%" },
  { name: "Receivables facility", value: 2.2, text: "650", share: "2%" },
];
const TABLE = {
  head: ["Instrument", "USD millions", "Share"],
  rows: [
    { label: "Term loans", cells: ["11,300", "38%"] },
    { label: "Senior secured notes", cells: ["10,450", "35%"] },
    { label: "Senior subordinated notes", cells: ["7,300", "25%"] },
    { label: "Receivables facility", cells: ["650", "2%"] },
  ],
};

function renderStack() {
  return render(
    <StackChart
      title="Debt by instrument"
      subtitle="30 June 2025, USD 29,700 million in all"
      parts={PARTS}
      table={TABLE}
    />,
  );
}

function segments(container: HTMLElement) {
  return [...container.querySelectorAll(".recharts-wrapper [data-segment]")];
}

describe("StackChart chart side", () => {
  it("draws one segment per part, in order, with widths in proportion to the values", () => {
    const { container } = renderStack();
    const segs = segments(container);
    expect(segs.map((s) => s.getAttribute("data-part"))).toEqual(PARTS.map((p) => p.name));
    const [w0 = 0, w1 = 0, , w3 = 0] = segs.map((s) => Number(s.getAttribute("data-width")));
    expect(w0).toBeGreaterThan(0);
    expect(w1 / w0).toBeCloseTo(35.2 / 38.0, 1);
    expect(w3 / w0).toBeCloseTo(2.2 / 38.0, 1);
  });

  it("colours the segments from the series palette in rank order", () => {
    const { container } = renderStack();
    expect(segments(container).map((s) => s.getAttribute("fill"))).toEqual([
      "var(--color-chart-1)",
      "var(--color-chart-2)",
      "var(--color-chart-3)",
      "var(--color-chart-4)",
    ]);
  });

  it("rounds only the end segment", () => {
    const { container } = renderStack();
    const segs = segments(container);
    expect(segs.map((s) => s.hasAttribute("data-end"))).toEqual([false, false, false, true]);
  });

  it("gives a seventh and later part Other's style", () => {
    const many: StackPart[] = Array.from({ length: 8 }, (_, i) => ({
      name: `P${String(i)}`,
      value: 10 - i,
      text: String(10 - i),
      share: `${String(i)}%`,
    }));
    const { container } = render(
      <StackChart
        title="Many"
        parts={many}
        table={{
          head: ["Instrument", "USD millions", "Share"],
          rows: many.map((p) => ({ label: p.name, cells: [p.text, p.share ?? ""] })),
        }}
      />,
    );
    const fills = segments(container).map((s) => s.getAttribute("fill"));
    expect(fills[5]).toBe("var(--color-chart-6)");
    expect(fills[6]).toBe("var(--color-chart-other)");
    expect(fills[7]).toBe("var(--color-chart-other)");
  });

  it("lists the ranked legend with exact strings, in order", () => {
    renderStack();
    const legend = screen.getByRole("list", { name: "Ranked legend" });
    const rows = within(legend)
      .getAllByRole("listitem")
      .map((li) => [...li.children].map((c) => c.textContent).filter((t) => t !== ""));
    expect(rows).toEqual([
      ["Term loans", "11,300", "38%"],
      ["Senior secured notes", "10,450", "35%"],
      ["Senior subordinated notes", "7,300", "25%"],
      ["Receivables facility", "650", "2%"],
    ]);
  });

  it("draws each legend name in the primary text colour", () => {
    renderStack();
    const legend = screen.getByRole("list", { name: "Ranked legend" });
    const name = within(legend).getByText("Term loans");
    expect(name).toHaveClass("text-text-primary");
    expect(name).not.toHaveClass("text-text-secondary");
  });

  it("shows the subtitle", () => {
    renderStack();
    expect(screen.getByText("30 June 2025, USD 29,700 million in all")).toBeInTheDocument();
  });

  it("mounts a readout on focus and ArrowRight with the exact strings", () => {
    const { container } = renderStack();
    const surface = screen.getByRole("application", { name: "Debt by instrument" });
    act(() => {
      surface.focus();
    });
    fireEvent.keyDown(surface, { key: "ArrowRight" });
    const tip = container.querySelector(".recharts-tooltip-wrapper");
    expect(tip).not.toBeNull();
    const items = [...(tip?.querySelectorAll("li") ?? [])].map((li) =>
      li.textContent.replace(/\s+/g, " "),
    );
    expect(items).toEqual([
      "Term loans 11,300 38%",
      "Senior secured notes 10,450 35%",
      "Senior subordinated notes 7,300 25%",
      "Receivables facility 650 2%",
    ]);
  });
});

describe("StackChart table side", () => {
  it("shows the mock's strings", () => {
    renderStack();
    fireEvent.click(screen.getByRole("radio", { name: "Table" }));
    const row = screen.getByRole("row", { name: /Receivables facility/ });
    expect(
      within(row)
        .getAllByRole("cell")
        .map((c) => c.textContent),
    ).toEqual(["650", "2%"]);
  });
});

describe("StackChart check", () => {
  const one = { name: "A", value: 1, text: "1", share: "50%" };
  const two = { name: "B", value: 1, text: "1", share: "50%" };
  const table = {
    head: ["I", "USD", "Share"],
    rows: [
      { label: "A", cells: ["1", "50%"] },
      { label: "B", cells: ["1", "50%"] },
    ],
  };
  function throwsOn(ui: React.ReactElement, pattern: RegExp) {
    const quiet = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() => render(ui)).toThrow(pattern);
    quiet.mockRestore();
  }
  it("throws on a repeated name", () => {
    throwsOn(<StackChart title="T" parts={[one, one]} table={table} />, /distinct/);
  });
  it("throws on a zero or negative value", () => {
    throwsOn(
      <StackChart title="T" parts={[one, { ...two, value: 0 }]} table={table} />,
      /"B".*more than zero/,
    );
    throwsOn(
      <StackChart title="T" parts={[one, { ...two, value: -1 }]} table={table} />,
      /"B".*more than zero/,
    );
  });
  it("throws when only some parts carry a share", () => {
    const bare: StackPart = { name: two.name, value: two.value, text: two.text };
    throwsOn(<StackChart title="T" parts={[one, bare]} table={table} />, /share/);
  });
  it("throws when the table rows are not the parts in order", () => {
    throwsOn(
      <StackChart
        title="T"
        parts={[one, two]}
        table={{ ...table, rows: [...table.rows].reverse() }}
      />,
      /table.*part/,
    );
  });
  it("throws when a table cell differs from the part's text", () => {
    throwsOn(
      <StackChart
        title="T"
        parts={[one, two]}
        table={{
          ...table,
          rows: [
            { label: "A", cells: ["9", "50%"] },
            { label: "B", cells: ["1", "50%"] },
          ],
        }}
      />,
      /"A".*text/,
    );
  });
  it("throws on no parts", () => {
    throwsOn(
      <StackChart title="T" parts={[]} table={{ head: ["I", "U"], rows: [] }} />,
      /at least one/,
    );
  });
});

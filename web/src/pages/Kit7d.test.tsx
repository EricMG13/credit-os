import { readFileSync } from "node:fs";
import path from "node:path";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { ProgressBar } from "@/components/base/progress-indicators/progress-indicators";
import { Kit } from "./Kit";

const designSystem = readFileSync(
  path.resolve(import.meta.dirname, "..", "..", "..", "docs", "design", "design-system.md"),
  "utf8",
).replace(/\r\n/g, "\n");
const row = (name: string): string =>
  designSystem.split("\n").find((l) => l.startsWith(`| ${name} |`)) ?? "";

describe("design system rows", () => {
  it("names the table, progress bar and loading indicator forms", () => {
    expect(row("Table")).toContain("`md` rows");
    expect(row("Table")).toContain("`sm` rows");
    expect(row("Table")).toContain("sortable heads");
    expect(row("Table")).toContain("row hover `surface-subtle`");
    expect(row("Progress bar")).toContain("8px by default");
    expect(row("Loading indicator")).toContain("`line-simple` spinner");
  });
});

function bodyNames(table: HTMLElement): string[] {
  return within(table)
    .getAllByRole("row")
    .slice(1)
    .map((r) => within(r).getAllByRole("rowheader")[0]?.textContent ?? "");
}

describe("Table on the kit page", () => {
  it("shows an md table and an sm table", () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "Table" });
    expect(within(region).getAllByRole("grid")).toHaveLength(2);
    const md = within(region).getByRole("grid", { name: "Modules, md rows" });
    const sm = within(region).getByRole("grid", { name: "Sources, sm rows" });
    expect(within(md).getAllByRole("row")[1]).toHaveClass("h-18");
    expect(within(sm).getAllByRole("row")[1]).toHaveClass("h-14");
  });

  it("renders a null cell as n.a. and never as 0", () => {
    render(<Kit />);
    const md = screen.getByRole("grid", { name: "Modules, md rows" });
    expect(within(md).getAllByText("not available")).toHaveLength(1);
    expect(within(md).getByText("n.a.")).toBeInTheDocument();
  });

  it("right-aligns the numeric column with tabular numerals", () => {
    render(<Kit />);
    const md = screen.getByRole("grid", { name: "Modules, md rows" });
    const cell = within(within(md).getByRole("row", { name: /Capital structure/ })).getByText("12");
    expect(cell).toHaveTextContent("12");
    expect(cell).toHaveClass("text-right", "tabular-nums");
  });

  it("reports a sort request: aria-sort and the row order change", () => {
    render(<Kit />);
    const md = screen.getByRole("grid", { name: "Modules, md rows" });
    const head = within(md).getByRole("columnheader", { name: /Findings/ });
    expect(head).not.toHaveAttribute("aria-sort", "ascending");
    const before = bodyNames(md);
    fireEvent.click(head);
    expect(head).toHaveAttribute("aria-sort", "ascending");
    const asc = bodyNames(md);
    expect(asc).not.toEqual(before);
    fireEvent.click(head);
    expect(head).toHaveAttribute("aria-sort", "descending");
    expect(bodyNames(md)).toEqual([
      "Peer comparison",
      "Capital structure",
      "Liquidity",
      "Covenants",
    ]);
  });

  it("draws the sortable head's focus ring with a token that resolves", () => {
    render(<Kit />);
    const md = screen.getByRole("grid", { name: "Modules, md rows" });
    const head = within(md).getByRole("columnheader", { name: /Findings/ });
    expect(head.className).toContain("focus-visible:ring-2");
    expect(head.className).toContain("focus-visible:ring-focus-ring");
    const css = readFileSync(
      path.resolve(import.meta.dirname, "..", "styles", "theme.css"),
      "utf8",
    );
    expect(css).toContain("--ring-color-focus-ring: var(--color-focus)");
  });

  it("hovers rows in the subtle surface", () => {
    render(<Kit />);
    const md = screen.getByRole("grid", { name: "Modules, md rows" });
    expect(within(md).getByRole("row", { name: /Liquidity/ }).className).toContain(
      "hover:bg-secondary",
    );
    const css = readFileSync(
      path.resolve(import.meta.dirname, "..", "styles", "theme.css"),
      "utf8",
    );
    expect(css).toContain("--background-color-secondary: var(--color-surface-subtle)");
  });
});

describe("Progress bar on the kit page", () => {
  it("shows 3 of 8 with its value, maximum and label", () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "Progress bar" });
    const bar = within(region).getByRole("progressbar", { name: "3 of 8" });
    expect(bar).toHaveAttribute("aria-valuenow", "3");
    expect(bar).toHaveAttribute("aria-valuemax", "8");
    expect(within(region).getByText("3 of 8")).toBeInTheDocument();
    expect(bar).toHaveClass("h-2", "bg-action-subtle");
  });

  it("eases the fill in 200ms on the design system's curve", () => {
    render(<Kit />);
    const bar = screen.getByRole("progressbar", { name: "3 of 8" });
    const fill = bar.firstElementChild as HTMLElement;
    expect(fill).toHaveClass("bg-action", "duration-200");
    expect(fill.className).toContain("ease-[cubic-bezier(.2,0,0,1)]");
    expect(fill.style.transform).toBe("translateX(-62.5%)");
  });
});

describe("ProgressBar guards", () => {
  it.each([
    ["not finite", Number.NaN],
    ["infinite", Number.POSITIVE_INFINITY],
    ["negative", -1],
    ["above max", 9],
  ])("throws a RangeError for a value that is %s", (_name, value) => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() => render(<ProgressBar value={value} max={8} label="x" />)).toThrow(RangeError);
    spy.mockRestore();
  });

  it("accepts the bounds 0 and max", () => {
    render(<ProgressBar value={0} max={8} label="none" />);
    render(<ProgressBar value={8} max={8} label="all" />);
    expect(screen.getByRole("progressbar", { name: "none" })).toHaveAttribute("aria-valuenow", "0");
    expect(screen.getByRole("progressbar", { name: "all" })).toHaveAttribute("aria-valuenow", "8");
  });
});

describe("Loading indicator on the kit page", () => {
  it("is a labelled spinner inside the live run state block", () => {
    render(<Kit />);
    const live = screen.getByRole("group", { name: "Live run state" });
    expect(within(live).getByText("Live run state only")).toBeInTheDocument();
    const spinner = within(live).getByRole("status", { name: "Waiting for the first module" });
    expect(spinner.querySelector("svg")).toHaveClass("animate-spin");
  });

  it("adds no looping animation outside the live block", () => {
    const { container } = render(<Kit />);
    const live = screen.getByRole("group", { name: "Live run state" });
    const loops = [...container.querySelectorAll("*")].filter(
      (el) =>
        !live.contains(el) &&
        (el.getAttribute("class") ?? "")
          .split(/\s+/)
          .some((token) => /animate-(?!in\b|out\b)|status-halo|queued-shimmer/.test(token)),
    );
    expect(loops).toEqual([]);
    expect(within(live).getByRole("status").querySelectorAll("[class*='animate-']")).toHaveLength(
      1,
    );
  });

  it("shows the loading button demo inside the live block, captioned", () => {
    render(<Kit />);
    const live = screen.getByRole("group", { name: "Live run state" });
    expect(within(live).getByText("Loading button")).toBeInTheDocument();
    expect(within(live).getByRole("button", { name: "Loading" })).toBeInTheDocument();
  });
});

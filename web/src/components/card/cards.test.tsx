import { readFileSync } from "node:fs";
import path from "node:path";
import { render, screen, within } from "@testing-library/react";
import { Card, Tile } from "./Card";
import { MetricCard } from "@/components/metric/MetricCard";
import { Timeline } from "@/components/timeline/Timeline";

const designSystem = readFileSync(
  path.resolve(import.meta.dirname, "..", "..", "..", "..", "docs", "design", "design-system.md"),
  "utf8",
).replace(/\r\n/g, "\n");
const row = (name: string): string =>
  designSystem.split("\n").find((l) => l.startsWith(`| ${name} |`)) ?? "";

// "Card (`radius-lg`, padding 32, `shadow-1`) and tile (`radius-md`, padding 24)"
const cardRow = row("Card and tile");
const [cardPart = "", tilePart = ""] = cardRow.split(") and tile (");
const radius = (part: string) => /`radius-(\w+)`/.exec(part)?.[1] ?? "";
const padding = (part: string) => String(Number(/padding (\d+)/.exec(part)?.[1]) / 4);

describe("Card and tile", () => {
  it("reads its sizes from the design system", () => {
    expect([radius(cardPart), padding(cardPart), radius(tilePart), padding(tilePart)]).toEqual([
      "lg",
      "8",
      "md",
      "6",
    ]);
    expect(cardPart).toContain("`shadow-1`");
  });

  it("draws a card with radius, padding, shadow and a subtle border", () => {
    render(<Card title="Leverage">Body</Card>);
    const card = screen.getByRole("group", { name: "Leverage" });
    for (const c of [
      "bg-surface-card",
      `rounded-ds-${radius(cardPart)}`,
      `p-${padding(cardPart)}`,
      "shadow-1",
      "border",
      "border-border-subtle",
    ]) {
      expect(card).toHaveClass(c);
    }
    expect(within(card).getByRole("heading", { level: 3, name: "Leverage" })).toHaveClass(
      "text-h3",
    );
    expect(card).toHaveTextContent("Body");
  });

  it("draws a card without a title as an unnamed container", () => {
    render(<Card>Body</Card>);
    expect(screen.queryByRole("heading")).toBeNull();
    expect(screen.getByText("Body")).toHaveClass("rounded-ds-lg");
  });

  it("draws a tile with radius and padding and no shadow", () => {
    render(<Tile>Tile body</Tile>);
    const tile = screen.getByText("Tile body");
    for (const c of [
      "bg-surface-card",
      `rounded-ds-${radius(tilePart)}`,
      `p-${padding(tilePart)}`,
      "border-border-subtle",
    ]) {
      expect(tile).toHaveClass(c);
    }
    expect(tile.className).not.toMatch(/shadow/);
  });
});

describe("MetricCard", () => {
  it("shows the label and the value the caller supplies", () => {
    render(<MetricCard label="Net leverage" value="4.2x" />);
    const card = screen.getByRole("article");
    expect(within(card).getByText("Net leverage")).toBeInTheDocument();
    const value = within(card).getByText("4.2x");
    expect(value).toHaveClass("tabular-nums");
    expect(card).toHaveClass("rounded-lg", "border-border-subtle", "p-6");
  });

  it("shows n.a. for a missing value, not zero", () => {
    render(<MetricCard label="Net leverage" value={null} />);
    const card = screen.getByRole("article");
    expect(within(card).getByText("n.a.")).toBeInTheDocument();
    expect(within(card).getByText("not available")).toBeInTheDocument();
    expect(card).not.toHaveTextContent("0");
  });

  it("shows a from value, and from n.a. when it is missing", () => {
    const { rerender } = render(<MetricCard label="Revenue" value="1,204" from="1,150" />);
    expect(screen.getByText("from 1,150")).toBeInTheDocument();
    rerender(<MetricCard label="Revenue" value="1,204" from={null} />);
    expect(
      screen.getByText(
        (_, el) => el?.tagName === "SPAN" && el.textContent === "from n.a.not available",
      ),
    ).toBeInTheDocument();
    rerender(<MetricCard label="Revenue" value="1,204" />);
    expect(screen.queryByText(/from/)).toBeNull();
  });

  it("shows the definition in a tooltip on a named info trigger", async () => {
    render(<MetricCard label="Net leverage" value="4.2x" note="Net debt over EBITDA." />);
    const trigger = screen.getByRole("button", { name: "About Net leverage" });
    expect(screen.queryByText("Net debt over EBITDA.")).toBeNull();
    trigger.focus();
    expect(await screen.findByText("Net debt over EBITDA.")).toBeInTheDocument();
  });

  it("has no info trigger without a note", () => {
    render(<MetricCard label="Net leverage" value="4.2x" />);
    expect(screen.queryByRole("button")).toBeNull();
  });
});

// "Dated records | Past: filled circle, neutral. Next: half-filled circle, action. Later: ring, neutral"
const datedCell = row("Dated records").split("|")[2] ?? "";
const dated = [...datedCell.matchAll(/(\w+): ([a-z -]+), (\w+)/g)].map((m) => ({
  word: m[1] ?? "",
  shape: m[2] ?? "",
  tone: m[3] ?? "",
}));

function entriesOf(): HTMLElement[] {
  return within(screen.getByRole("list")).getAllByRole("listitem");
}

describe("Timeline", () => {
  const items = [
    { date: "12 Feb 2025", title: "Filed", text: "Annual report.", state: "Past" },
    { date: "15 Mar 2025", title: "Call", state: "Next" },
    { date: "24 Apr 2025", title: "Maturity", state: "Later" },
  ] as const;

  it("reads three dated-record states from the design system", () => {
    expect(dated.map((d) => d.word)).toEqual(["Past", "Next", "Later"]);
  });

  it("lists each item with date, title, optional text and the state word", () => {
    render(<Timeline items={items} />);
    const entries = entriesOf();
    expect(entries).toHaveLength(3);
    const [first = document.body, second = document.body] = entries;
    expect(within(first).getByText("12 Feb 2025")).toBeInTheDocument();
    expect(within(first).getByRole("heading", { level: 3, name: "Filed" })).toBeVisible();
    expect(within(first).getByText("Annual report.")).toBeInTheDocument();
    expect(within(second).queryByText("Annual report.")).toBeNull();
    entries.forEach((entry, i) => {
      expect(within(entry).getByText(items[i]?.state ?? "")).toBeInTheDocument();
    });
  });

  it("marks each state with its shape and tone from the design system", () => {
    render(<Timeline items={items} />);
    const entries = entriesOf();
    dated.forEach((d, i) => {
      const shapes = [...(entries[i]?.querySelectorAll("[data-shape]") ?? [])];
      expect(shapes.length).toBeGreaterThan(0);
      for (const s of shapes) expect(s.getAttribute("data-shape")).toBe(d.shape);
    });
    expect(entries[1]?.querySelector(".text-action")).not.toBeNull();
  });

  it("draws the connector in the connector token and does not loop", () => {
    render(<Timeline items={items} />);
    const list = screen.getByRole("list");
    expect(list.className).toContain("before:bg-connector");
    expect(list.innerHTML).not.toMatch(/animate-|status-halo|shimmer/);
  });
});

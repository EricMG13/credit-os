import { readFileSync } from "node:fs";
import path from "node:path";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { Kit } from "./Kit";

const designSystem = readFileSync(
  path.resolve(import.meta.dirname, "..", "..", "..", "docs", "design", "design-system.md"),
  "utf8",
).replace(/\r\n/g, "\n");

// The hex of a colour role in the design system's tables, and the hex a theme variable resolves to.
const roleHex = (role: string): string => {
  const line = designSystem.split("\n").find((l) => l.startsWith(`| \`${role}\` |`)) ?? "";
  return /#[0-9A-Fa-f]{6}/.exec(line)?.[0].toLowerCase() ?? "";
};
const themeCss = readFileSync(
  path.resolve(import.meta.dirname, "..", "styles", "theme.css"),
  "utf8",
);
function resolveVar(name: string): string {
  const m = new RegExp(`${name}:\\s*([^;]+);`).exec(themeCss);
  const value = m?.[1]?.trim() ?? "";
  const ref = /^var\((--[\w-]+)\)$/.exec(value);
  return ref?.[1] ? resolveVar(ref[1]) : value.toLowerCase();
}

describe("colour mapping against the design system", () => {
  it("draws the field focus ring in the focus colour", () => {
    expect(roleHex("focus")).toMatch(/^#/);
    expect(resolveVar("--ring-color-brand")).toBe(roleHex("focus"));
    expect(resolveVar("--ring-color-focus-ring")).toBe(roleHex("focus"));
  });

  it("draws the invalid edge at rest and focused in the error mark colour, which clears 3:1 on white", () => {
    const mark = statusHex("error", "Mark");
    expect(resolveVar("--ring-color-error_subtle")).toBe(mark);
    expect(resolveVar("--ring-color-error")).toBe(mark);
    expect(contrast(mark, roleHex("surface-card"))).toBeGreaterThanOrEqual(3);
  });
});

// The Status table's colour for a family, by column name.
function statusHex(family: string, column: "Mark" | "Edge"): string {
  const lines = designSystem.split("\n");
  const head = lines.find((l) => /^\| Status \|/.test(l) || /^\| Family \|/.test(l)) ?? "";
  const cols = head.split("|").map((c) => c.trim());
  const idx = cols.findIndex((c) => c.toLowerCase().includes(column.toLowerCase()));
  const line = lines.find((l) => l.toLowerCase().startsWith(`| ${family} |`)) ?? "";
  const hex = line.split("|")[idx]?.match(/#[0-9A-Fa-f]{6}/)?.[0];
  return (hex ?? `${family}-${column}-not-found`).toLowerCase();
}

function contrast(a: string, b: string): number {
  const lum = (h: string): number => {
    const c = [1, 3, 5].map((i) => Number.parseInt(h.slice(i, i + 2), 16) / 255);
    const [r = 0, g = 0, bl = 0] = c.map((x) =>
      x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4,
    );
    return 0.2126 * r + 0.7152 * g + 0.0722 * bl;
  };
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
  return ((hi ?? 0) + 0.05) / ((lo ?? 0) + 0.05);
}

describe("Input on the kit page", () => {
  it("shows a default input with a hint, an invalid one with its message and a disabled one", () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "Input" });
    const inputs = within(region).getAllByRole("textbox");
    expect(inputs).toHaveLength(3);

    const normal = within(region).getByRole("textbox", { name: /^Issuer name/ });
    expect(normal).toBeEnabled();
    expect(normal).not.toBeInvalid();
    expect(normal).toHaveAccessibleDescription("As it appears on the cover page.");

    const invalid = within(region).getByRole("textbox", { name: /^Reporting currency/ });
    expect(invalid).toBeInvalid();
    expect(invalid).toHaveAccessibleDescription("Error: Use a three-letter code, for example USD.");

    expect(within(region).getByRole("textbox", { name: /^Registry number/ })).toBeDisabled();
  });

  it("changes its value when typed into", () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "Input" });
    const input = within(region).getByRole("textbox", { name: /^Issuer name/ });
    fireEvent.change(input, { target: { value: "Example Holdings" } });
    expect(input).toHaveValue("Example Holdings");
  });

  it("marks the invalid input with the error diamond, not an info glyph", () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "Input" });
    const group = within(region).getByRole("textbox", { name: /^Reporting currency/ })
      .parentElement as HTMLElement;
    expect(group.querySelector('[data-shape="diamond"]')).not.toBeNull();
    expect(group.querySelector("svg:not([data-shape])")).toBeNull();
    expect(group.querySelector(".text-error-mark")).not.toBeNull();
    expect(group).toHaveClass("ring-error_subtle");
    // only the invalid field reserves room for the mark
    const normal = within(region).getByRole("textbox", { name: /^Issuer name/ });
    expect(normal).not.toHaveClass("pr-9");
    expect(within(region).getByRole("textbox", { name: /^Reporting currency/ })).toHaveClass(
      "pr-9",
    );
  });
});

describe("Select on the kit page", () => {
  it("shows a default, a disabled and an invalid select", () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "Select" });
    const triggers = within(region).getAllByRole("button");
    expect(triggers).toHaveLength(3);
    expect(within(region).getByRole("button", { name: /Update schedule/ })).toBeEnabled();
    expect(within(region).getByRole("button", { name: /Archive window/ })).toBeDisabled();
    const invalid = within(region).getByRole("button", { name: /Review cycle/ });
    expect(invalid).toHaveAccessibleDescription("Error: Choose a cycle to continue.");
  });

  it("lists the options when opened and shows the chosen one in the trigger", async () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "Select" });
    const trigger = within(region).getByRole("button", { name: /Update schedule/ });
    fireEvent.click(trigger);
    const list = await screen.findByRole("listbox");
    const options = within(list).getAllByRole("option");
    expect(options.map((o) => o.textContent)).toEqual(["Quarterly", "Semi-annual", "Annual"]);
    fireEvent.click(within(list).getByRole("option", { name: "Semi-annual" }));
    expect(trigger).toHaveTextContent("Semi-annual");
    expect(screen.queryByRole("listbox")).toBeNull();
  });

  it("adds no style element when opened", async () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "Select" });
    fireEvent.click(within(region).getByRole("button", { name: /Update schedule/ }));
    await screen.findByRole("listbox");
    expect(document.querySelector("style")).toBeNull();
  });
});

describe("Invalid select", () => {
  it("carries the error mark and ring on its trigger and names the error in text", () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "Select" });
    const trigger = within(region).getByRole("button", { name: /Review cycle/ });
    expect(trigger.querySelector('[data-shape="diamond"]')).not.toBeNull();
    expect(trigger).toHaveClass("ring-error_subtle");
    expect(trigger).toHaveAccessibleDescription("Error: Choose a cycle to continue.");
    const normal = within(region).getByRole("button", { name: /Update schedule/ });
    expect(normal.querySelector('[data-shape="diamond"]')).toBeNull();
  });
});

import { readFileSync } from "node:fs";
import path from "node:path";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { Kit } from "./Kit";

const designSystem = readFileSync(
  path.resolve(import.meta.dirname, "..", "..", "..", "docs", "design", "design-system.md"),
  "utf8",
).replace(/\r\n/g, "\n");
const row = (name: string): string =>
  designSystem.split("\n").find((l) => l.startsWith(`| ${name} |`)) ?? "";

describe("design system rows", () => {
  it("names the input and select states", () => {
    expect(row("Input")).toContain("Label, hint, error with message, disabled");
    expect(row("Select")).toContain("Default, focus, disabled, invalid");
  });
});

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
    expect(invalid).toHaveAccessibleDescription("Use a three-letter code, for example USD.");

    expect(within(region).getByRole("textbox", { name: /^Registry number/ })).toBeDisabled();
  });

  it("changes its value when typed into", () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "Input" });
    const input = within(region).getByRole("textbox", { name: /^Issuer name/ });
    fireEvent.change(input, { target: { value: "Example Holdings" } });
    expect(input).toHaveValue("Example Holdings");
  });

  it("draws the focus ring in the focus token and the invalid ring in the error edge", () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "Input" });
    const group = within(region).getByRole("textbox", {
      name: /^Reporting currency/,
    }).parentElement;
    expect(group).toHaveClass("ring-error_subtle");
    const css = readFileSync(
      path.resolve(import.meta.dirname, "..", "styles", "theme.css"),
      "utf8",
    );
    expect(css).toContain("--ring-color-brand: var(--color-focus)");
    expect(css).toContain("--ring-color-error_subtle: var(--color-error-edge)");
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
    expect(invalid).toHaveAccessibleDescription("Choose a cycle to continue.");
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

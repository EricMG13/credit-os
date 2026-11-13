import { readFileSync } from "node:fs";
import path from "node:path";
import { render, screen } from "@testing-library/react";
import { Kit } from "./Kit";

const designSystem = readFileSync(
  path.resolve(import.meta.dirname, "..", "..", "..", "docs", "design", "design-system.md"),
  "utf8",
);

// The Button row of the Components table: the colours are the quoted words before the first ";".
const buttonRow = designSystem.split(/\r?\n/).find((line) => line.startsWith("| Button |")) ?? "";
const colours = [...(buttonRow.split(";")[0] ?? "").matchAll(/`([a-z-]+)`/g)].map(
  (m) => m[1] ?? "",
);
const SIZES = ["sm", "md", "lg", "xl"];

function label(slug: string): string {
  const words = slug.replace("-", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

describe("Kit", () => {
  it("has the page heading and one heading per component", () => {
    render(<Kit />);
    expect(screen.getByRole("heading", { level: 1, name: "Component kit" })).toBeInTheDocument();
    for (const name of ["Button", "Tooltip"]) {
      expect(screen.getByRole("heading", { level: 2, name })).toBeInTheDocument();
    }
  });

  it("reads the four button colours from the design system", () => {
    expect(colours).toEqual(["primary", "secondary", "tertiary", "primary-destructive"]);
  });

  it("shows every button colour by its name", () => {
    render(<Kit />);
    for (const colour of colours) {
      expect(screen.getByRole("button", { name: label(colour) }), colour).toBeEnabled();
    }
  });

  it("shows every button size", () => {
    render(<Kit />);
    for (const size of SIZES) {
      expect(screen.getByRole("button", { name: `Size ${size}` }), size).toBeEnabled();
    }
  });

  it("shows the disabled, loading and icon states", () => {
    render(<Kit />);
    expect(screen.getByRole("button", { name: "Disabled" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Loading" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    expect(screen.getByRole("button", { name: "Leading icon" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Trailing icon" })).toBeEnabled();
  });

  it("gives the tooltip trigger an accessible name", () => {
    render(<Kit />);
    expect(screen.getByRole("button", { name: "Tooltip trigger" })).toBeInTheDocument();
  });
});

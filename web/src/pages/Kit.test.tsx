import { readFileSync } from "node:fs";
import path from "node:path";
import { fireEvent, render, screen, within } from "@testing-library/react";
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

// The button names the page shows, in the order of the colours above.
const BUTTON_NAMES = ["Primary", "Secondary", "Tertiary", "Primary destructive"];

describe("Kit", () => {
  it("has the page heading and one heading per component", () => {
    render(<Kit />);
    expect(screen.getByRole("heading", { level: 1, name: "Component kit" })).toBeInTheDocument();
    for (const name of ["Button", "Tooltip", "Badge", "Tabs", "Button group", "Page header"]) {
      expect(screen.getByRole("heading", { level: 2, name })).toBeInTheDocument();
    }
  });

  it("reads the four button colours from the design system", () => {
    expect(colours).toEqual(["primary", "secondary", "tertiary", "primary-destructive"]);
  });

  it("shows every button colour by its name", () => {
    render(<Kit />);
    for (const name of BUTTON_NAMES) {
      expect(screen.getByRole("button", { name }), name).toBeEnabled();
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

  it("shows each badge colour with and without the dot, in each size", () => {
    render(<Kit />);
    const badges = screen.getByRole("region", { name: "Badge" });
    for (const word of ["Gray", "Brand", "Error", "Warning", "Success", "Sky"]) {
      expect(within(badges).getAllByText(word), word).toHaveLength(2);
    }
    for (const word of ["Size sm", "Size md", "Size lg"]) {
      expect(within(badges).getByText(word), word).toBeInTheDocument();
    }
    expect(badges.querySelectorAll("svg")).toHaveLength(6);
  });

  it("shows each status set by name and the live run state", () => {
    render(<Kit />);
    const status = screen.getByRole("region", { name: "Status badge" });
    for (const name of [
      "Status",
      "Run states",
      "Signal source states",
      "Dated records",
      "Answer state",
      "Met or not met",
      "Freshness",
      "Module state",
      "Change state",
      "Gap severity",
      "File state",
      "Approval",
      "Activity that cannot be read",
    ]) {
      expect(within(status).getByRole("heading", { level: 3, name }), name).toBeInTheDocument();
    }
    const live = within(status).getByRole("group", { name: "Live run state" });
    expect(within(live).getByText("Running")).toBeInTheDocument();
    expect(live.querySelector(".queued-shimmer")).not.toBeNull();
  });

  it("shows the count on a tab and the panel of the tab selected", () => {
    render(<Kit />);
    const tabs = screen.getByRole("region", { name: "Tabs" });
    const horizontal = within(tabs).getAllByRole("tablist")[0];
    expect(horizontal).toHaveAttribute("aria-orientation", "horizontal");
    const changes = within(horizontal as HTMLElement).getByRole("tab", { name: /^Changes/ });
    expect(changes).toHaveTextContent(/^Changes\s*12$/);
    expect(within(tabs).getAllByRole("tab", { name: /^(Overview|Evidence)$/ })).toHaveLength(2);
    expect(within(tabs).getByText("Overview panel")).toBeVisible();
    fireEvent.click(within(tabs).getByRole("tab", { name: "Evidence" }));
    expect(within(tabs).getByText("Evidence panel")).toBeVisible();
    expect(within(tabs).queryByText("Overview panel")).not.toBeInTheDocument();
  });

  it("shows a vertical tab list that switches panel", () => {
    render(<Kit />);
    const tabs = screen.getByRole("region", { name: "Tabs" });
    const vertical = within(tabs).getAllByRole("tablist")[1];
    expect(vertical).toHaveAttribute("aria-orientation", "vertical");
    fireEvent.click(within(vertical as HTMLElement).getByRole("tab", { name: "Forecast" }));
    expect(within(tabs).getByText("Forecast panel")).toBeVisible();
  });

  it("changes the selected segment of the Chart or Table toggle", () => {
    render(<Kit />);
    const chart = screen.getByRole("radio", { name: "Chart" });
    const table = screen.getByRole("radio", { name: "Table" });
    expect(chart).toHaveAttribute("aria-checked", "true");
    expect(table).toHaveAttribute("aria-checked", "false");
    fireEvent.click(table);
    expect(table).toHaveAttribute("aria-checked", "true");
    expect(chart).toHaveAttribute("aria-checked", "false");
  });

  it("shows the five gap states", () => {
    render(<Kit />);
    const gaps = screen.getByRole("region", { name: "Gap states" });
    expect(within(gaps).getAllByText("Not established for this run")).toHaveLength(2);
    expect(within(gaps).getByText("not available")).toBeInTheDocument();
    expect(within(gaps).getByText("Withheld")).toBeInTheDocument();
    expect(within(gaps).getByText("Not assessable")).toBeInTheDocument();
    expect(gaps.querySelector('[aria-hidden="true"].flex-col')).not.toBeNull();
  });
});

import { readFileSync } from "node:fs";
import path from "node:path";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { Kit } from "./Kit";

const root = path.resolve(import.meta.dirname, "..", "..", "..");
const designSystem = readFileSync(
  path.join(root, "docs", "design", "design-system.md"),
  "utf8",
).replace(/\r\n/g, "\n");
const row = (name: string): string =>
  designSystem.split("\n").find((l) => l.startsWith(`| ${name} |`)) ?? "";

describe("design system rows", () => {
  it("names the drawer and progress steps forms", () => {
    expect(row("Drawer")).toContain("header, scrolling body, pinned footer");
    expect(row("Progress steps")).toContain("complete, current, incomplete");
    expect(designSystem).toContain("Up to 200ms, `cubic-bezier(.2,0,0,1)`");
  });
});

async function open(name: string): Promise<HTMLElement> {
  fireEvent.click(screen.getByRole("button", { name }));
  return screen.findByRole("dialog");
}

async function closed(): Promise<void> {
  await waitFor(() => {
    expect(screen.queryByRole("dialog")).toBeNull();
  });
}

describe("Drawer on the kit page", () => {
  it("opens from its trigger with header, scrolling body and pinned footer", async () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "Drawer" });
    expect(screen.queryByRole("dialog")).toBeNull();
    fireEvent.click(within(region).getByRole("button", { name: "Open drawer" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByRole("banner")).toHaveTextContent("Source detail");
    expect(within(dialog).getByRole("main")).toHaveClass("overflow-y-auto");
    expect(within(dialog).getByRole("contentinfo")).toBeInTheDocument();
    expect(document.querySelector("style")).toBeNull();
  });

  it("moves focus into the dialog and closes by the close button", async () => {
    render(<Kit />);
    const dialog = await open("Open drawer");
    await waitFor(() => {
      expect(dialog.contains(document.activeElement)).toBe(true);
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Close" }));
    await closed();
  });

  it("closes by Escape and by its footer action", async () => {
    render(<Kit />);
    const dialog = await open("Open drawer");
    fireEvent.keyDown(dialog, { key: "Escape" });
    await closed();
    const again = await open("Open drawer");
    fireEvent.click(within(again).getByRole("button", { name: "Done" }));
    await closed();
  });

  it("opens and closes in 200ms or less on the slide-in classes", async () => {
    render(<Kit />);
    await open("Open drawer");
    const classes = [...document.querySelectorAll("[class*='duration-']")].map((el) =>
      el.getAttribute("class"),
    );
    for (const c of classes) {
      expect(c).not.toMatch(/duration-(?!200\b|100\b)\d+/);
    }
  });

  it("draws the close button's focus outline as a solid line", async () => {
    render(<Kit />);
    const dialog = await open("Open drawer");
    const close = within(dialog).getByRole("button", { name: "Close" });
    expect(close).toHaveClass("focus-visible:outline-2", "focus-visible:outline-solid");
  });
});

describe("Modal on the kit page", () => {
  it("shows a warning confirmation stating the cap", async () => {
    render(<Kit />);
    const dialog = await open("Start run");
    expect(dialog).toHaveAccessibleName("Confirm a paid run");
    expect(within(dialog).getByText(/cap of USD 20/)).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Cancel" })).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Start the run" })).toBeInTheDocument();
    expect(dialog.querySelector("[data-featured-icon]")).toHaveClass("bg-warning-secondary");
    await waitFor(() => {
      expect(dialog.contains(document.activeElement)).toBe(true);
    });
    expect(document.querySelector("style")).toBeNull();
  });

  it("shows a form dialog with one input and no warning style", async () => {
    render(<Kit />);
    const dialog = await open("Rename issuer");
    expect(within(dialog).getAllByRole("textbox")).toHaveLength(1);
    expect(within(dialog).getByRole("textbox", { name: /Display name/ })).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Save" })).toBeInTheDocument();
    expect(dialog.querySelector("[data-featured-icon]")).toBeNull();
    expect(within(dialog).queryByText(/cap of/)).toBeNull();
    expect(document.querySelector("style")).toBeNull();
  });

  it.each(["Start run", "Rename issuer"])("%s closes by Cancel and by Escape", async (trigger) => {
    render(<Kit />);
    const dialog = await open(trigger);
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
    await closed();
    const again = await open(trigger);
    fireEvent.keyDown(again, { key: "Escape" });
    await closed();
  });
});

describe("Progress steps on the kit page", () => {
  it("lists four steps with one current step and a word for each state", () => {
    render(<Kit />);
    const region = screen.getByRole("region", { name: "Progress steps" });
    const items = within(region).getAllByRole("listitem");
    expect(items).toHaveLength(4);
    expect(within(region).getByRole("list").tagName).toBe("OL");
    expect(items.filter((li) => li.getAttribute("aria-current") === "step")).toHaveLength(1);
    expect(items[2]).toHaveAttribute("aria-current", "step");
    expect(items.map((li) => li.textContent.split(",").pop()?.trim())).toEqual([
      "complete",
      "complete",
      "current",
      "not started",
    ]);
  });

  it("marks complete with a check and the rest with their number", () => {
    render(<Kit />);
    const items = within(screen.getByRole("region", { name: "Progress steps" })).getAllByRole(
      "listitem",
    );
    expect(items[0]?.querySelector("svg")).not.toBeNull();
    expect(items[1]?.querySelector("svg")).not.toBeNull();
    expect(items[2]?.querySelector("svg")).toBeNull();
    expect(items[2]?.querySelector("[aria-hidden]")).toHaveTextContent("3");
    expect(items[3]?.querySelector("[aria-hidden]")).toHaveTextContent("4");
    expect(items[3]?.querySelector("[aria-hidden]")).toHaveClass("bg-surface-subtle");
    expect(items[2]?.querySelector("[aria-hidden]")).toHaveClass("bg-action");
  });
});

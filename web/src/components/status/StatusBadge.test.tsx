import { readFileSync } from "node:fs";
import path from "node:path";
import { render, screen } from "@testing-library/react";
import { StatusShape, SHAPES } from "./shapes";
import { STATUS_SETS } from "./sets";
import { StatusBadge } from "./StatusBadge";

const designSystem = readFileSync(
  path.resolve(import.meta.dirname, "..", "..", "..", "..", "docs", "design", "design-system.md"),
  "utf8",
).replace(/\r\n/g, "\n");

// The "Status shapes" table lists the ten shapes, first column.
const tableStart = designSystem.indexOf("| Shape | Meaning |");
const SHAPE_NAMES = designSystem
  .slice(tableStart)
  .split("\n")
  .slice(2)
  .filter((l, i, all) => l.startsWith("|") && all.slice(0, i).every((p) => p.startsWith("|")))
  .map((l) => (l.split("|")[1] ?? "").trim().toLowerCase());

describe("status shapes", () => {
  it("has the ten shapes of the design system", () => {
    expect(SHAPE_NAMES).toHaveLength(10);
    expect([...SHAPES].sort()).toEqual([...SHAPE_NAMES].sort());
  });

  it("draws each shape as different markup", () => {
    const markup = SHAPES.map((shape) => {
      const { container, unmount } = render(<StatusShape shape={shape} />);
      const html = container.innerHTML;
      unmount();
      return html;
    });
    expect(new Set(markup).size).toBe(10);
  });
});

describe("StatusBadge", () => {
  it("shows Running live with its word and a half-filled shape and the halo", () => {
    const { container } = render(<StatusBadge set="Run states" state="Running" live />);
    expect(screen.getByText("Running")).toBeVisible();
    expect(container.querySelector("svg")).toHaveAttribute("data-shape", "half-filled circle");
    expect(container.querySelector(".status-halo")).not.toBeNull();
  });

  it("adds no halo to Running without live, to Finished or to Queued", () => {
    for (const state of ["Running", "Finished", "Queued"] as const) {
      const { container, unmount } = render(
        <StatusBadge set="Run states" state={state} live={state !== "Running"} />,
      );
      expect(container.querySelector(".status-halo"), state).toBeNull();
      unmount();
    }
  });

  it("gives every state of every set visible text and a shape", () => {
    for (const [name, set] of Object.entries(STATUS_SETS)) {
      for (const state of Object.values(set)) {
        const { container, unmount } = render(
          <StatusBadge set={name as "Status"} state={state.word as "Success"} />,
        );
        expect(container.textContent, `${name}: ${state.word}`).toBe(state.word);
        expect(container.querySelector("svg")).toHaveAttribute("data-shape", state.shape);
        unmount();
      }
    }
  });

  it("throws on an unknown set or state", () => {
    expect(() => render(<StatusBadge set={"Nope" as "Status"} state="Success" />)).toThrow();
    expect(() => render(<StatusBadge set="Status" state={"Nope" as "Success"} />)).toThrow();
  });
});

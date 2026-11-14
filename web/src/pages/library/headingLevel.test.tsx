import { render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import path from "node:path";
import type { LibraryData } from "@/data";
import { SourceContext } from "../source";
import { routes } from "./routes";

// The section level is moved one step from the real one; nothing may keep the old literal.
vi.mock("./parts/heading", () => ({
  ISSUER_HEADING: "h2",
  SECTION_HEADING: "h3",
  SUBSECTION_HEADING: "h4",
}));

const fixture = JSON.parse(
  readFileSync(
    path.resolve(import.meta.dirname, "..", "..", "..", "fixtures", "library.json"),
    "utf8",
  ),
) as { issuers: LibraryData["issuers"]; slice: unknown };

function renderChanges(issuer: string, run: string) {
  const data: LibraryData = {
    schema: "credit-os-data/1",
    issuers: fixture.issuers,
    library: fixture.slice,
  };
  const route = routes.find((r) => r.path === "/library/:issuer/:run/changes");
  if (route === undefined) throw new Error("no changes route");
  render(
    <SourceContext.Provider value={data}>{route.render({ issuer, run })}</SourceContext.Provider>,
  );
}

describe("the empty states follow SECTION_HEADING", () => {
  it("draws the first run's state title at the section level", () => {
    renderChanges("halden-aerostructures", "2025-09-30");
    expect(
      screen.getByRole("heading", { level: 3, name: "No earlier run to compare" }),
    ).toBeVisible();
    expect(
      screen.queryByRole("heading", { level: 2, name: "No earlier run to compare" }),
    ).toBeNull();
  });

  it("draws the not-held state title at the section level", () => {
    renderChanges("nobody", "2026-09-30");
    expect(screen.getByRole("heading", { level: 3, name: "No such issuer" })).toBeVisible();
    expect(screen.queryByRole("heading", { level: 2, name: "No such issuer" })).toBeNull();
  });
});

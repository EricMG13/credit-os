import { readFileSync } from "node:fs";
import path from "node:path";
import { render, screen } from "@testing-library/react";
import { App } from "@/App";
import type { LibraryData } from "@/data";
import { routes } from "./routes";

type Json = Record<string, unknown>;

const fixture = JSON.parse(
  readFileSync(
    path.resolve(import.meta.dirname, "..", "..", "..", "fixtures", "library.json"),
    "utf8",
  ),
) as { issuers: LibraryData["issuers"]; slice: Json; params: Record<string, Json[]> };

const data = (library: unknown): LibraryData => ({
  schema: "credit-os-data/1",
  issuers: fixture.issuers,
  library,
});

function visit(hash: string, library: unknown = fixture.slice) {
  window.location.hash = hash;
  return render(<App result={{ kind: "ok", data: data(library) }} />);
}

const fill = (pattern: string, params: Json) =>
  pattern.replace(/:(\w+)/g, (_, name: string) => String(params[name]));

/** The heading levels in document order. */
const levels = () => screen.getAllByRole("heading").map((h) => Number(h.tagName.slice(1)));

function expectOneH1AndNoSkip() {
  expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  const all = levels();
  expect(all[0]).toBe(1);
  all.forEach((level, i) => {
    if (i > 0) expect(level - (all[i - 1] ?? 0)).toBeLessThanOrEqual(1);
  });
}

afterEach(() => {
  window.location.hash = "";
});

describe("the library routes adopt the shell", () => {
  it("makes every route full bleed, and declares one home: the library home", () => {
    expect(routes.every((r) => r.layout === "bleed")).toBe(true);
    expect(routes.filter((r) => r.home !== undefined).map((r) => [r.path, r.home])).toEqual([
      ["/library/home", "/library/home"],
    ]);
  });

  it.each(["#", "#/", "#/library", "#/library/"])("draws the library home at %j", (hash) => {
    visit(hash);
    expect(screen.getByRole("heading", { level: 1, name: "Library" })).toBeVisible();
    expect(screen.getByText("Five issuers, each opening on its latest finished run")).toBeVisible();
    expect(screen.getByRole("link", { name: "Start a run" })).toHaveAttribute("href", "#/run");
    expectOneH1AndNoSkip();
  });

  it("draws one h1 and no skipped level at /library/home", () => {
    visit("#/library/home");
    expectOneH1AndNoSkip();
  });

  it.each(
    routes.flatMap((route) =>
      route.path.includes(":")
        ? (fixture.params[route.path] ?? []).map((p) => [route.path, p] as const)
        : [],
    ),
  )("draws one h1 and no skipped level at %s %j", (pattern, params) => {
    visit(`#${fill(pattern, params)}`);
    expectOneH1AndNoSkip();
  });

  it.each([
    ["history of an unknown issuer", "#/library/nobody/history", "Report history"],
    ["overview of an unknown issuer", "#/library/nobody/2026-09-30/overview", "Overview"],
    [
      "overview of an unknown run",
      "#/library/halden-aerostructures/1999-01-01/overview",
      "Overview",
    ],
  ])("keeps one h1, the page name, for the %s", (_, hash, name) => {
    visit(hash);
    expect(screen.getByRole("heading", { level: 1, name })).toBeVisible();
    expectOneH1AndNoSkip();
  });

  it("keeps one h1 and the notice when the library member is absent", () => {
    window.location.hash = "#/library/home";
    render(
      <App
        result={{ kind: "ok", data: { schema: "credit-os-data/1", issuers: fixture.issuers } }}
      />,
    );
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByText("This data file holds no library pages")).toBeVisible();
  });

  it("keeps one h1 when the library member is invalid", () => {
    visit("#/library/home", null);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByText("This part of the library could not be read")).toBeVisible();
  });

  it("rules the home header under title, subtitle and action like the mock's .u-ph", () => {
    visit("#/library/home");
    const h1 = screen.getByRole("heading", { level: 1, name: "Library" });
    const header = h1.parentElement?.parentElement;
    expect(header).toHaveClass("border-b", "border-secondary", "pb-4", "items-start");
  });

  it("pads the page itself with p-8 on one wrapper", () => {
    const { container } = visit("#/library/home");
    expect(container.querySelector("main > .p-8")).not.toBeNull();
    expect(container.querySelector("main")).not.toHaveClass("p-8");
  });
});

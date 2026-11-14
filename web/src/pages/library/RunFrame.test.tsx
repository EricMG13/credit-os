import { readFileSync } from "node:fs";
import path from "node:path";
import { fireEvent, render, screen, within } from "@testing-library/react";
import type { LibraryData } from "@/data";
import { SourceContext } from "../source";
import { RunFrame } from "./parts/RunFrame";

type Json = Record<string, unknown>;
type Run = Json & { head: Json; traces: Record<string, Json & { derivation: Json }> };
type Slice = { home: Json; issuers: (Json & { runs: Run[] })[] };

const fixture = JSON.parse(
  readFileSync(
    path.resolve(import.meta.dirname, "..", "..", "..", "fixtures", "library.json"),
    "utf8",
  ),
) as { issuers: LibraryData["issuers"]; slice: Slice };

const fresh = (): Slice => structuredClone(fixture.slice);
const HALDEN = "halden-aerostructures";

function renderFrame(
  opts: { issuer?: string; run?: string; tab?: "overview" | "modules"; library?: unknown } = {},
) {
  const data: LibraryData = {
    schema: "credit-os-data/1",
    issuers: fixture.issuers,
    library: opts.library ?? fixture.slice,
  };
  return render(
    <SourceContext.Provider value={data}>
      <RunFrame
        issuer={opts.issuer ?? HALDEN}
        run={opts.run ?? "2026-09-30"}
        tab={opts.tab ?? "overview"}
      >
        <p>Page body</p>
      </RunFrame>
    </SourceContext.Provider>,
  );
}

describe("RunFrame header", () => {
  it("draws the Library link, the h2 name, the three badges and both actions as in the mock", () => {
    renderFrame();
    expect(screen.getByRole("link", { name: "Library" })).toHaveAttribute("href", "#/library/home");
    expect(screen.getByRole("heading", { level: 2, name: "Halden Aerostructures" })).toBeVisible();
    expect(screen.getByText("As of 30 Sep 2026")).toBeVisible();
    expect(screen.getByText("Full review")).toBeVisible();
    expect(screen.getByText("Finished")).toBeVisible();
    expect(screen.getByRole("link", { name: "Report history" })).toHaveAttribute(
      "href",
      "#/library/halden-aerostructures/history",
    );
    expect(screen.getByRole("link", { name: "New run" })).toHaveAttribute("href", "#/run");
    expect(screen.getByText("Page body")).toBeVisible();
  });
});

describe("RunFrame tabs", () => {
  const tabs = () => within(screen.getByRole("navigation", { name: "Run pages" }));

  it("draws five real links, the current page marked, with the delivered module count", () => {
    const slice = fresh();
    (slice.issuers[0]?.runs[0] as Run).head["forecastHref"] = "#/derived/forecast";
    renderFrame({ library: slice });
    const hrefs = tabs()
      .getAllByRole("link")
      .map((a) => [a.textContent, a.getAttribute("href"), a.getAttribute("aria-current")]);
    expect(hrefs).toEqual([
      ["Overview", "#/library/halden-aerostructures/2026-09-30/overview", "page"],
      ["Changes", "#/library/halden-aerostructures/2026-09-30/changes", null],
      ["Modules13", "#/library/halden-aerostructures/2026-09-30/modules/capital-structure", null],
      ["Forecast", "#/derived/forecast", null],
      ["Evidence", "#/library/halden-aerostructures/2026-09-30/evidence/summary", null],
    ]);
  });

  it("marks Modules current on a module page", () => {
    renderFrame({ tab: "modules" });
    expect(tabs().getByRole("link", { name: /^Modules/ })).toHaveAttribute("aria-current", "page");
    expect(tabs().getByRole("link", { name: "Overview" })).not.toHaveAttribute("aria-current");
  });

  it("draws Forecast as disabled text with its hint when the slice has no address", () => {
    renderFrame();
    expect(tabs().queryByRole("link", { name: "Forecast" })).toBeNull();
    expect(tabs().getByText("Forecast")).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByText("Not built yet")).toBeInTheDocument();
  });

  it("draws Modules as disabled text when the run has no first module", () => {
    const slice = fresh();
    (slice.issuers[0]?.runs[0] as Run).head["firstModule"] = null;
    renderFrame({ library: slice });
    expect(tabs().queryByRole("link", { name: /^Modules/ })).toBeNull();
    expect(tabs().getByText("Modules")).toHaveAttribute("aria-disabled", "true");
  });
});

describe("Show sources", () => {
  it("is an off switch named Show sources; the frame says so for the controls' stylesheet", () => {
    const { container } = renderFrame();
    const toggle = screen.getByRole("switch", { name: "Show sources" });
    expect(toggle).not.toBeChecked();
    expect(container.querySelector("[data-sources]")).toHaveAttribute("data-sources", "off");
  });

  it("turns every control on at once and off again", () => {
    const { container } = renderFrame();
    fireEvent.click(screen.getByRole("switch", { name: "Show sources" }));
    expect(screen.getByRole("switch", { name: "Show sources" })).toBeChecked();
    expect(container.querySelector("[data-sources]")).toHaveAttribute("data-sources", "on");
    fireEvent.click(screen.getByRole("switch", { name: "Show sources" }));
    expect(container.querySelector("[data-sources]")).toHaveAttribute("data-sources", "off");
  });
});

describe("RunFrame states", () => {
  it("draws the busy skeleton and no page body for a loading run, header and tabs kept", () => {
    const { container } = renderFrame({ run: "2026-06-30" });
    expect(container.querySelector("[aria-busy='true']")).not.toBeNull();
    expect(screen.queryByText("Page body")).toBeNull();
    expect(screen.getByRole("heading", { level: 2, name: "Halden Aerostructures" })).toBeVisible();
    expect(screen.getByRole("navigation", { name: "Run pages" })).toBeVisible();
  });

  it.each([
    ["issuer", { issuer: "nobody" }, "No such issuer"],
    ["run", { run: "1999-01-01" }, "No such run"],
  ])("says which %s is missing, with a way back to the library", (_, opts, title) => {
    renderFrame(opts);
    expect(screen.getByRole("heading", { level: 2, name: title })).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to the library" })).toHaveAttribute(
      "href",
      "#/library/home",
    );
    expect(screen.queryByText("Page body")).toBeNull();
    expect(document.body.textContent).not.toMatch(/Page not found|could not be read/);
  });

  it("says the library data is malformed instead of drawing a partial frame", () => {
    const slice = fresh();
    delete (slice.issuers[0] as Json)["runs"];
    renderFrame({ library: slice });
    expect(screen.getByText(/issuers\[0\]\.runs/)).toBeVisible();
    expect(screen.queryByText("Page body")).toBeNull();
  });
});

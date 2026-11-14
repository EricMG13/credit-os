import { readFileSync } from "node:fs";
import path from "node:path";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { LibraryData } from "@/data";
import { SourceContext } from "../source";
import { RunFrame } from "./parts/RunFrame";
import { TRACE_HOST, TraceControl } from "./parts/TraceControl";

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
        <div data-testid="figure" className={TRACE_HOST}>
          <TraceControl trace="net-leverage" label="Show sources for this figure" />
        </div>
        <div data-testid="plain">
          <TraceControl trace={null} label="Show sources for this figure" />
        </div>
      </RunFrame>
    </SourceContext.Provider>,
  );
}

const control = () => screen.getByRole("button", { name: "Show sources for this figure" });
const openDrawer = () => fireEvent.click(control());

describe("RunFrame header", () => {
  it("draws the Library link, the h1 name, the three badges and both actions as in the mock", () => {
    renderFrame();
    expect(screen.getByRole("link", { name: "Library" })).toHaveAttribute("href", "#/library/home");
    expect(screen.getByRole("heading", { level: 1, name: "Halden Aerostructures" })).toBeVisible();
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
    expect(control()).toHaveClass("opacity-0");
  });

  it("turns every control on at once and off again", () => {
    const { container } = renderFrame();
    fireEvent.click(screen.getByRole("switch", { name: "Show sources" }));
    expect(screen.getByRole("switch", { name: "Show sources" })).toBeChecked();
    expect(container.querySelector("[data-sources]")).toHaveAttribute("data-sources", "on");
    fireEvent.click(screen.getByRole("switch", { name: "Show sources" }));
    expect(container.querySelector("[data-sources]")).toHaveAttribute("data-sources", "off");
  });

  it("reveals a control on hover, keyboard focus and touch, by class", () => {
    renderFrame();
    expect(screen.getByTestId("figure")).toHaveClass("group/trace", "relative");
    expect(control().className).toMatch(/group-hover\/trace:opacity-100/);
    expect(control().className).toMatch(/focus-visible:opacity-100/);
    expect(control().className).toMatch(/\[@media\(hover:none\)\]:opacity-100/);
    expect(control().className).toMatch(/in-data-\[sources=on\]:opacity-100/);
  });

  it("draws no control for a null trace and throws for a key the run does not hold", () => {
    renderFrame();
    expect(within(screen.getByTestId("plain")).queryByRole("button")).toBeNull();
    const slice = fresh();
    const runs = slice.issuers[0]?.runs as Run[];
    // The capped run's overview and changes point at no trace, so the slice stays valid without any.
    (runs[0] as Run)["overview"] = runs[2]?.["overview"];
    (runs[0] as Run)["changes"] = runs[2]?.["changes"];
    (runs[0] as Run)["modules"] = runs[2]?.["modules"];
    (runs[0] as Run).traces = {};
    expect(() => renderFrame({ library: slice })).toThrow(RangeError);
  });
});

describe("Trace drawer, keyboard", () => {
  it("draws the design focus ring on a branch's summary row", () => {
    renderFrame();
    openDrawer();
    const summary = screen.getAllByText(/^Result/)[0]?.closest("summary");
    expect(summary).toHaveClass(
      "focus-visible:ring-2",
      "focus-visible:ring-brand",
      "rounded-ds-xs",
    );
  });
});

describe("Trace drawer", () => {
  it("is closed at rest and holds no audit text in the page", () => {
    const { container } = renderFrame();
    expect(screen.queryByRole("dialog")).toBeNull();
    for (const audit of [
      "T-0014",
      "C-0412",
      "C-0398",
      "annual-report-2026.pdf",
      "lender-presentation",
    ]) {
      expect(container.innerHTML).not.toContain(audit);
    }
    expect(within(screen.getByRole("navigation")).queryByText(/T-00/)).toBeNull();
  });

  it("opens on the control with the statement and the whole derivation, ids included", () => {
    renderFrame();
    openDrawer();
    const drawer = screen.getByRole("dialog", { name: "Sources for net leverage" });
    expect(within(drawer).getByRole("heading", { name: "Net leverage 4.6x" })).toBeVisible();
    expect(
      within(drawer).getByText(
        "Net debt of USD 2,236m against company-adjusted EBITDA of USD 486m for the year to 30 September 2026.",
      ),
    ).toBeVisible();
    for (const text of [
      "Result",
      "Net leverage 4.6x",
      "T-0014 · C-0412",
      "Formula",
      "Net debt ÷ EBITDA",
      "2,236 ÷ 486",
      "Input",
      "Net debt 2,236",
      "C-0398 · gross debt − cash",
      "Gross debt 2,398",
      "annual-report-2026.pdf · p. 112",
      "Cash 162",
      "annual-report-2026.pdf · p. 84",
      "EBITDA 486",
      "company-adjusted",
      "lender-presentation-nov-2026.pdf · p. 9",
    ]) {
      expect(within(drawer).getAllByText(text).length).toBeGreaterThan(0);
    }
  });

  it("draws the subtitle, the source excerpt and the qualification as in the mock", () => {
    renderFrame();
    openDrawer();
    const drawer = within(screen.getByRole("dialog"));
    expect(drawer.getByText("Capital structure · figure · as of 30 Sep 2026")).toBeVisible();
    expect(drawer.getByText("Source excerpt")).toBeVisible();
    expect(
      drawer.getByText(
        "“Adjusted EBITDA for the twelve months ended 30 September 2026 was USD 486 million (2025: USD 441 million).”",
      ),
    ).toBeVisible();
    expect(drawer.getAllByText("lender-presentation-nov-2026.pdf · p. 9").length).toBe(2);
    expect(drawer.getByText("Qualification")).toBeVisible();
    expect(
      drawer.getByText(
        "EBITDA is on the company-adjusted basis. The reported figure is not established for this run.",
      ),
    ).toBeVisible();
  });

  it("draws neither block when the trace has no excerpt and no qualification", () => {
    const slice = fresh();
    const trace = (slice.issuers[0]?.runs[0] as Run).traces["net-leverage"] as Json;
    trace["excerpt"] = null;
    trace["qualification"] = null;
    renderFrame({ library: slice });
    openDrawer();
    expect(screen.queryByText("Source excerpt")).toBeNull();
    expect(screen.queryByText("Qualification")).toBeNull();
  });

  it("collapses and expands a branch with a click on its summary", () => {
    renderFrame();
    openDrawer();
    const drawer = screen.getByRole("dialog");
    const formula = within(drawer).getByText("Formula").closest("details");
    expect(formula?.open).toBe(true);
    fireEvent.click(formula?.querySelector("summary") as Element);
    expect(formula?.open).toBe(false);
    fireEvent.click(formula?.querySelector("summary") as Element);
    expect(formula?.open).toBe(true);
    expect(within(drawer).getAllByText("Source").length).toBe(3);
  });

  it.each([
    [
      "the header Close",
      () => fireEvent.click(screen.getAllByRole("button", { name: "Close" })[0] as HTMLElement),
    ],
    [
      "the footer Close",
      () => fireEvent.click(screen.getAllByRole("button", { name: "Close" })[1] as HTMLElement),
    ],
    ["Escape", () => fireEvent.keyDown(document.activeElement as Element, { key: "Escape" })],
  ])("closes on %s and returns focus to the control", async (_, close) => {
    renderFrame();
    control().focus();
    openDrawer();
    await waitFor(() => {
      expect(screen.getByRole("dialog").contains(document.activeElement)).toBe(true);
    });
    expect(screen.getAllByRole("button", { name: "Close" })).toHaveLength(2);
    close();
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    await waitFor(() => {
      expect(control()).toHaveFocus();
    });
  });

  it("offers Open in Evidence, which goes to the run's Evidence Trace page and closes the drawer", async () => {
    renderFrame();
    openDrawer();
    const link = screen.getByRole("link", { name: "Open in Evidence" });
    expect(link).toHaveAttribute(
      "href",
      "#/library/halden-aerostructures/2026-09-30/evidence/trace",
    );
    fireEvent.click(link);
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
  });

  it("draws n.a. for a tree value that is not recorded", () => {
    const slice = fresh();
    const tree = (slice.issuers[0]?.runs[0] as Run).traces["net-leverage"]?.derivation as Json & {
      children: Json[];
    };
    (tree.children[0] as Json)["value"] = null;
    renderFrame({ library: slice });
    openDrawer();
    expect(within(screen.getByRole("dialog")).getByText("n.a.")).toBeInTheDocument();
  });
});

describe("RunFrame details", () => {
  it("draws the tabs with the mock's 6px side padding", () => {
    renderFrame();
    expect(screen.getByRole("link", { name: "Overview" })).toHaveClass("px-1.5", "pb-2.5");
  });

  it("keeps Show sources on across frames for the session", () => {
    const first = renderFrame();
    fireEvent.click(screen.getByRole("switch", { name: "Show sources" }));
    first.unmount();
    renderFrame({ tab: "modules" });
    expect(screen.getByRole("switch", { name: "Show sources" })).toBeChecked();
    fireEvent.click(screen.getByRole("switch", { name: "Show sources" }));
    expect(screen.getByRole("switch", { name: "Show sources" })).not.toBeChecked();
  });

  it("lays the loading skeleton out as x.css: 24px stack, three separate 12px cards 16px apart, bordered items", () => {
    const { container } = renderFrame({ run: "2026-06-30" });
    const busy = container.querySelector("[aria-busy='true']");
    expect(busy).toHaveClass("gap-6");
    const row = busy?.querySelector(".grid") as HTMLElement;
    expect(row).toHaveClass("gap-4");
    for (const joined of ["overflow-hidden", "rounded-xl", "border"]) {
      expect(row).not.toHaveClass(joined);
    }
    expect(row.children).toHaveLength(3);
    for (const card of row.children) {
      expect(card).toHaveClass("rounded-xl", "border", "border-border-subtle", "bg-surface-card");
      expect(card.className).not.toMatch(/border-(t|l|hairline)/);
    }
    expect(busy?.querySelectorAll(".border.p-4")).toHaveLength(2);
  });
});

describe("RunFrame states", () => {
  it("draws the busy skeleton and no page body for a loading run, header and tabs kept", () => {
    const { container } = renderFrame({ run: "2026-06-30" });
    expect(container.querySelector("[aria-busy='true']")).not.toBeNull();
    expect(screen.queryByText("Page body")).toBeNull();
    expect(screen.getByRole("heading", { level: 1, name: "Halden Aerostructures" })).toBeVisible();
    expect(screen.getByRole("navigation", { name: "Run pages" })).toBeVisible();
  });

  it.each([
    ["issuer", { issuer: "nobody" }, "No such issuer"],
    ["run", { run: "1999-01-01" }, "No such run"],
  ])("says which %s is missing, with a way back to the library", (_, opts, title) => {
    renderFrame(opts);
    expect(screen.getByRole("heading", { level: 1, name: "Overview" })).toBeVisible();
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

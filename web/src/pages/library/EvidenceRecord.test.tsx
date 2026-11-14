import { readFileSync } from "node:fs";
import path from "node:path";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import type { LibraryData } from "@/data";
import { SourceContext } from "../source";
import { routes } from "./routes";

type Json = Record<string, unknown>;

const fixture = JSON.parse(
  readFileSync(
    path.resolve(import.meta.dirname, "..", "..", "..", "fixtures", "library.json"),
    "utf8",
  ),
) as { issuers: LibraryData["issuers"]; slice: Json; params: Record<string, Json[]> };

const RECORD = "/library/:issuer/:run/evidence/record";
const FULL = "2026-09-30";

function renderRecord(run: string, library: unknown = fixture.slice) {
  const data: LibraryData = { schema: "credit-os-data/1", issuers: fixture.issuers, library };
  const found = routes.find((r) => r.path === RECORD);
  if (found === undefined) throw new Error("no record route");
  return render(
    <SourceContext.Provider value={data}>
      {found.render({ issuer: "halden-aerostructures", run })}
    </SourceContext.Provider>,
  );
}

afterEach(cleanup);

const table = (name: string) => screen.getByRole("table", { name });
/** The text a cell draws: what a screen reader alone is told (the visually hidden words) is left out. */
const drawn = (cell: Element) => {
  const copy = cell.cloneNode(true) as Element;
  for (const hidden of copy.querySelectorAll(".sr-only")) hidden.remove();
  return copy.textContent;
};
const textOf = (name: string) =>
  within(table(name))
    .getAllByRole("row")
    .slice(1)
    .map((row) => [...row.querySelectorAll("th,td")].map(drawn));

describe("the Record route", () => {
  it("is titled Evidence, full bleed, and the fixture visits each run", () => {
    const found = routes.find((r) => r.path === RECORD);
    expect(found?.title).toBe("Evidence");
    expect(found?.layout).toBe("bleed");
    expect(fixture.params[RECORD]?.map((p) => p["run"])).toEqual([
      FULL,
      "2026-06-30",
      "2026-03-31",
      "2025-09-30",
    ]);
  });
});

describe("Evidence, Record", () => {
  it("is the current tab, under the one h1 and the Evidence heading", () => {
    renderRecord(FULL);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Record" })).toHaveAttribute("aria-current", "page");
    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual([
      "Module timings",
      "Hashes and instructions",
      "Spend against the cap",
      "Model calls 41",
      "Registers as written 5",
    ]);
  });

  it("draws the module timings as the mock's table side, with no Chart or Table toggle", () => {
    renderRecord(FULL);
    expect(
      screen.getByText("From start to accepted, 13 Nov 2026. Six of thirteen shown."),
    ).toBeVisible();
    expect(screen.queryByRole("button", { name: /^Chart$|^Table$/ })).toBeNull();
    const head = within(table("Module timings")).getAllByRole("columnheader");
    expect(head.map((h) => h.textContent)).toEqual([
      "Module",
      "Started, min",
      "Accepted, min",
      "Took, min",
      "State",
    ]);
    expect(textOf("Module timings")).toEqual([
      ["Business profile", "0.0", "6.0", "6.0", "Delivered"],
      ["Financial performance", "1.6", "9.6", "8.0", "Delivered"],
      ["Capital structure", "5.6", "16.0", "10.4", "Delivered with gaps"],
      ["Recovery", "14.4", "n.a.", "n.a.", "Not assessable"],
      ["Peer comparison", "16.8", "25.6", "8.8", "Delivered with gaps"],
      ["Forecast", "26.4", "37.6", "11.2", "Delivered"],
    ]);
  });

  it("says n.a. for a module that never ran, and not a zero", () => {
    renderRecord("2026-03-31");
    expect(textOf("Module timings")).toEqual([
      ["Financial performance", "n.a.", "n.a.", "n.a.", "Not run"],
    ]);
  });

  it("copies a value and names it in the toast", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    renderRecord(FULL);
    fireEvent.click(screen.getByRole("button", { name: "Copy configuration name" }));
    expect(writeText).toHaveBeenCalledWith("copilot-sol-medium · gpt-6-sol");
    expect(
      await screen.findByText("The model configuration name is on your clipboard."),
    ).toBeVisible();
    Reflect.deleteProperty(navigator, "clipboard");
  });

  it("draws the hashes as copyable snippets, with their delivered captions and copy names", () => {
    renderRecord(FULL);
    expect(screen.getByText("Method texts")).toBeVisible();
    expect(
      screen.getByText("71c0e5a9d3b84f2607e1c9a5d3b7f1e9058c6a4e2d0b9f7d5c3a1e9f7b5d3c1a"),
    ).toBeVisible();
    expect(screen.getByText("copilot-sol-medium · gpt-6-sol")).toBeVisible();
    expect(screen.getByText("SHA-256")).toBeVisible();
    expect(screen.getByText("Config")).toBeVisible();
    expect(screen.getByRole("button", { name: "Copy hash" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Copy configuration name" })).toBeVisible();
  });

  it("draws the spend as the bar with the delivered text, and the delivered sentence", () => {
    renderRecord(FULL);
    const bar = screen.getByRole("progressbar", { name: "USD 11.40 of USD 20.00" });
    expect(bar).toHaveAttribute("aria-valuenow", "11.4");
    expect(bar).toHaveAttribute("aria-valuemax", "20");
    expect(
      screen.getByText(
        "The run finished inside its cap. Spend by module is in the model calls register below.",
      ),
    ).toBeVisible();
  });

  it("draws the model calls right-aligned with the mock's rows, n.a. for a missing count, and the delivered total", () => {
    renderRecord(FULL);
    const head = within(table("Model calls")).getAllByRole("columnheader");
    expect(head.map((h) => h.textContent)).toEqual([
      "Module",
      "Code",
      "Calls",
      "Retries",
      "Tokens in",
      "Tokens out",
      "Cost, USD",
    ]);
    expect(textOf("Model calls")).toEqual([
      ["Business profile", "CP-1A", "3", "0", "182,400", "9,150", "0.92"],
      ["Capital structure", "CP-2C", "5", "1", "264,900", "14,720", "1.38"],
      ["Recovery", "CP-3B", "2", "1", "58,300", "1,040", "0.27"],
      ["Peer comparison", "CP-2E", "4", "0", "n.a.", "n.a.", "0.81"],
      ["Total", "All", "41", "6", "n.a.", "n.a.", "11.40"],
    ]);
    // the mock's figures are right-aligned; its code and module are left
    const first = within(table("Model calls")).getAllByRole("row")[1] as HTMLElement;
    expect(within(first).getAllByRole("cell")[1]).toHaveClass("tabular-nums");
    expect(table("Model calls").closest("section")).toHaveClass("rounded-xl");
  });

  it("lists the registers, each with Open as a link, and Download all", () => {
    renderRecord(FULL);
    expect(textOf("Registers as written").map((r) => r.slice(0, 4))).toEqual([
      ["Source register", "Every module", "212", "registers/sources.md"],
      ["Calculation register", "Financial kernel", "148", "registers/calculations.md"],
      ["Gap ledger", "Every module", "7", "registers/gaps.md"],
      ["Assumption register", "Forecast", "23", "registers/assumptions.md"],
      ["Withheld register", "Delivery", "2", "registers/withheld.md"],
    ]);
    expect(screen.getByRole("link", { name: "Download all" })).toHaveAttribute(
      "href",
      "downloads/halden-aerostructures-2026-09-30-registers.zip",
    );
    const opens = screen.getAllByRole("link", { name: "Open" });
    expect(opens.map((a) => a.getAttribute("href"))).toEqual(
      ["sources", "calculations", "gaps", "assumptions"].map(
        (n) => `downloads/halden-aerostructures-2026-09-30-registers/${n}.md`,
      ),
    );
  });

  it("right-aligns the register's Rows and Open columns, as the mock draws them", () => {
    renderRecord(FULL);
    const heads = within(table("Registers as written")).getAllByRole("columnheader");
    expect(heads[2]).toHaveClass("text-right");
    expect(heads[4]).toHaveClass("text-right");
    expect(heads[1]).not.toHaveClass("text-right");
    const row = within(table("Registers as written")).getAllByRole("row")[1] as HTMLElement;
    const cells = within(row).getAllByRole("cell");
    expect(cells[1]).toHaveClass("text-right");
    expect(cells[3]).toHaveClass("text-right");
  });

  it("draws an Open with no address as a disabled button beside its reason, and nothing is generated", () => {
    renderRecord(FULL);
    const row = within(table("Registers as written")).getByRole("row", {
      name: /Withheld register/,
    });
    const open = within(row).getByRole("button", { name: "Open" });
    expect(open).toBeDisabled();
    const reason =
      "The withheld register lists figures the sources marked confidential, so it is not published.";
    expect(within(row).getByText(reason)).toBeVisible();
    expect(open).toHaveAccessibleDescription(reason);
    expect(open.parentElement).toHaveClass("justify-end");
    expect(within(row).queryByRole("link", { name: "Open" })).toBeNull();
  });

  it("draws Download all disabled with its reason on a run whose registers were not packed", () => {
    renderRecord("2026-03-31");
    expect(screen.getByRole("button", { name: "Download all" })).toBeDisabled();
    expect(
      screen.getByText("The run's registers were not packed, so there is nothing to download."),
    ).toBeVisible();
  });

  it("says a run that holds no module has no time, with no table", () => {
    const slice = structuredClone(fixture.slice) as {
      issuers: {
        runs: {
          modules: unknown[];
          head: Json;
          overview: Json;
          evidence: Json & {
            moduleFilter: unknown[];
            sources: { files: { readers: unknown }[] };
            gaps: { groups: unknown[] };
            jump: unknown[];
            record: { timings: Json };
            tabs: Json;
          };
        }[];
      }[];
    };
    const run = slice.issuers[0]?.runs[3] as (typeof slice.issuers)[0]["runs"][0];
    run.modules = [];
    run.evidence.moduleFilter = [];
    for (const file of run.evidence.sources.files) file.readers = { shown: [], more: null };
    run.evidence.gaps.groups = [];
    run.evidence.jump = [];
    run.evidence.tabs["gaps"] = "0";
    run.evidence.record.timings["rows"] = [];
    run.evidence.record.timings["emptyText"] = "No module ran, so no module has a time.";
    (run.overview["limitations"] as { gapsLink: Json }).gapsLink["label"] =
      "See the 0 gaps in Evidence";
    run.head["firstModule"] = null;
    (run.overview["modules"] as { items: Json[] }).items = [
      { title: "Nothing", lead: "No module ran.", state: "Not run", module: null },
    ];
    renderRecord("2025-09-30", slice);
    expect(screen.getByText("No module ran, so no module has a time.")).toBeVisible();
    expect(screen.queryByRole("table", { name: "Module timings" })).toBeNull();
  });
});

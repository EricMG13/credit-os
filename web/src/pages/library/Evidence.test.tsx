import { readFileSync } from "node:fs";
import path from "node:path";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
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

const SUMMARY = "/library/:issuer/:run/evidence/summary";
const INDEX = "/library/:issuer/:run/evidence";
const SOURCES = "/library/:issuer/:run/evidence/sources";
const BASE = "#/library/halden-aerostructures/2026-09-30/evidence";
const RUN_CODE = "HAE-20260930-FR-0003";
const HASH = "9f2c41d07ab35e88c1e4f6a2b9d03c57e1a84f60b7d2c9153ea06f48d1b7c2a0";

function renderEvidence(
  run: string,
  route = SUMMARY,
  library: unknown = fixture.slice,
  issuer = "halden-aerostructures",
) {
  const data: LibraryData = { schema: "credit-os-data/1", issuers: fixture.issuers, library };
  const found = routes.find((r) => r.path === route);
  if (found === undefined) throw new Error(`no ${route} route`);
  return render(
    <SourceContext.Provider value={data}>{found.render({ issuer, run })}</SourceContext.Provider>,
  );
}

const tabs = () => within(screen.getByRole("navigation", { name: "Evidence sections" }));

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  Reflect.deleteProperty(navigator, "clipboard");
});

describe("the Evidence routes", () => {
  it.each([SUMMARY, INDEX, SOURCES])(
    "%s is titled Evidence and the fixture visits every state",
    (route) => {
      expect(routes.find((r) => r.path === route)?.title).toBe("Evidence");
      const runs = fixture.params[route]?.map((p) => p["run"]);
      expect(runs).toEqual(
        route !== INDEX
          ? ["2026-09-30", "2026-06-30", "2026-03-31", "2025-09-30"]
          : ["2026-09-30", "2026-06-30"],
      );
    },
  );

  it("draws the Summary tab at the index address, and at /summary", () => {
    const index = renderEvidence("2026-09-30", INDEX).container.textContent;
    cleanup();
    expect(renderEvidence("2026-09-30", SUMMARY).container.textContent).toBe(index);
    expect(index).toContain("Modules delivered");
  });
});

describe("the Evidence frame", () => {
  it("draws the issuer as the one h1, Evidence as h2 with its sentence, and h3 sections", () => {
    renderEvidence("2026-09-30");
    expect(screen.getAllByRole("heading", { level: 1 }).map((h) => h.textContent)).toEqual([
      "Halden Aerostructures",
    ]);
    expect(screen.getByRole("heading", { level: 2, name: "Evidence" })).toBeVisible();
    expect(screen.getByText("Where every figure and claim in this run comes from.")).toBeVisible();
    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual([
      "Modules delivered",
      "This run",
      "Take it with you",
    ]);
  });

  it("draws the five tabs with their delivered counts, Summary current, on the run's own addresses", () => {
    renderEvidence("2026-09-30");
    const links = tabs().getAllByRole("link");
    expect(links.map((l) => l.textContent)).toEqual([
      "Summary",
      "Trace58",
      "Sources9",
      "Gaps7",
      "Record",
    ]);
    expect(links.map((l) => l.getAttribute("href"))).toEqual(
      ["summary", "trace", "sources", "gaps", "record"].map((page) => `${BASE}/${page}`),
    );
    expect(links.map((l) => l.getAttribute("aria-current"))).toEqual([
      "page",
      null,
      null,
      null,
      null,
    ]);
    expect(
      within(screen.getByRole("navigation", { name: "Run pages" })).getByRole("link", {
        name: "Evidence",
      }),
    ).toHaveAttribute("aria-current", "page");
  });

  it("draws no module filter on Summary, where it would narrow nothing", () => {
    renderEvidence("2026-09-30");
    expect(screen.queryByRole("button", { name: /Module/ })).toBeNull();
    expect(screen.queryByText("Jump to an item")).toBeNull();
  });

  it("draws the run's counts on the capped run and the first run", () => {
    renderEvidence("2026-03-31");
    expect(tabs().getByRole("link", { name: /^Gaps/ })).toHaveTextContent("Gaps3");
    cleanup();
    renderEvidence("2025-09-30");
    expect(tabs().getByRole("link", { name: /^Sources/ })).toHaveTextContent("Sources2");
  });

  it("draws the loading run as the skeleton, and a run or issuer the slice lacks as its own state", () => {
    const { container } = renderEvidence("2026-06-30");
    expect(container.querySelector("[aria-busy='true']")).not.toBeNull();
    expect(screen.queryByRole("heading", { name: "Evidence" })).toBeNull();
    cleanup();
    renderEvidence("1999-01-01");
    expect(screen.getByRole("heading", { level: 1, name: "Evidence" })).toBeVisible();
    expect(screen.getByText("No such run")).toBeVisible();
    cleanup();
    renderEvidence("2026-09-30", SUMMARY, fixture.slice, "nobody");
    expect(screen.getByText("No such issuer")).toBeVisible();
  });
});

describe("Evidence, Summary", () => {
  it("draws Modules delivered with its bar, delivered text and note", () => {
    renderEvidence("2026-09-30");
    const bar = screen.getByRole("progressbar", { name: "12 of 13" });
    expect(bar).toHaveAttribute("aria-valuenow", "12");
    expect(bar).toHaveAttribute("aria-valuemax", "13");
    expect(screen.getByText("Recovery was not assessable")).toBeVisible();
  });

  it("draws the three counts, the file note as the fixture words it (a departure from the mock)", () => {
    renderEvidence("2026-09-30");
    const tiles = within(screen.getByRole("region", { name: "Counts" })).getAllByRole("listitem");
    expect(tiles.map((t) => t.textContent)).toEqual([
      "Source files97 read in full, 1 read in part, 1 unreadable",
      "Calculations58Each one traceable to its inputs",
      "Gaps72 high, 3 medium, 2 low",
    ]);
    expect(within(screen.getByRole("region", { name: "Counts" })).queryByRole("button")).toBeNull();
  });

  it("draws the run code and the hash in full, each with its copy button", () => {
    renderEvidence("2026-09-30");
    expect(screen.getByText("Run code")).toBeVisible();
    expect(screen.getByText("Hash of the handoff set")).toBeVisible();
    expect(screen.getByText(RUN_CODE).tagName).toBe("PRE");
    const hash = screen.getByText(HASH);
    expect(hash).toHaveClass("whitespace-pre-wrap", "break-all");
    expect(hash).not.toHaveClass("truncate");
    expect(screen.getByRole("button", { name: "Copy run code" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Copy hash" })).toBeVisible();
  });

  it("draws Take it with you: the delivered sentence, a download link and the link to Sources", () => {
    renderEvidence("2026-09-30");
    expect(
      screen.getByText(
        "The module handoffs are the record this library was written from. Download them to read a module exactly as it was delivered.",
      ),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Download handoffs" })).toHaveAttribute(
      "href",
      "downloads/halden-aerostructures-2026-09-30-handoffs.zip",
    );
    expect(screen.getByRole("link", { name: "See which files were used" })).toHaveAttribute(
      "href",
      `${BASE}/sources`,
    );
  });

  it("draws the download in the secondary look, with and without an address", () => {
    renderEvidence("2026-09-30");
    expect(screen.getByRole("link", { name: "Download handoffs" })).toHaveClass("bg-primary");
    expect(screen.getByRole("link", { name: "Download handoffs" })).not.toHaveClass(
      "bg-brand-solid",
    );
    cleanup();
    renderEvidence("2026-03-31");
    expect(screen.getByRole("button", { name: "Download handoffs" })).toHaveClass("bg-primary");
    expect(screen.getByRole("button", { name: "Download handoffs" })).not.toHaveClass(
      "bg-brand-solid",
    );
  });

  it("gives the delivered section a heading id of its own", () => {
    renderEvidence("2026-09-30");
    const region = screen.getByRole("region", { name: "Modules delivered" });
    const heading = screen.getByRole("heading", { name: "Modules delivered" });
    expect(region.getAttribute("aria-labelledby")).toBe(heading.id);
    expect(heading.id).not.toBe("delivered-heading");
    expect(heading.id).not.toBe("");
  });

  it("draws a download with no address as a disabled button with its delivered reason beside it", () => {
    renderEvidence("2026-03-31");
    expect(screen.queryByRole("link", { name: "Download handoffs" })).toBeNull();
    const button = screen.getByRole("button", { name: "Download handoffs" });
    expect(button).toBeDisabled();
    const reason =
      "The run reached its cost cap before its handoffs were packed, so there is nothing to download.";
    expect(screen.getByText(reason)).toBeVisible();
    expect(button).toHaveAccessibleDescription(reason);
  });
});

/** A clipboard stub: `writeText` resolves or rejects as the test says. */
function stubClipboard(writeText: ((text: string) => Promise<void>) | undefined) {
  Object.defineProperty(navigator, "clipboard", {
    value: writeText === undefined ? undefined : { writeText },
    configurable: true,
  });
}

describe("Evidence, copying", () => {
  it("copies the run code and shows the Copied toast as a status", async () => {
    const writeText = vi.fn<(text: string) => Promise<void>>().mockResolvedValue(undefined);
    stubClipboard(writeText);
    renderEvidence("2026-09-30");
    fireEvent.click(screen.getByRole("button", { name: "Copy run code" }));
    const toast = await screen.findByRole("status");
    expect(writeText).toHaveBeenCalledWith(RUN_CODE);
    expect(toast).toHaveTextContent("CopiedThe run code is on your clipboard.");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("copies the hash exactly", async () => {
    const writeText = vi.fn<(text: string) => Promise<void>>().mockResolvedValue(undefined);
    stubClipboard(writeText);
    renderEvidence("2026-09-30");
    fireEvent.click(screen.getByRole("button", { name: "Copy hash" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "CopiedThe hash of the handoff set is on your clipboard.",
    );
    expect(writeText).toHaveBeenCalledWith(HASH);
  });

  it("shows Could not copy in the error form when the clipboard refuses", async () => {
    stubClipboard(vi.fn().mockRejectedValue(new Error("denied")));
    renderEvidence("2026-09-30");
    fireEvent.click(screen.getByRole("button", { name: "Copy hash" }));
    const toast = await screen.findByRole("alert");
    expect(toast).toHaveTextContent("Could not copy");
    expect(toast).toHaveTextContent("The hash of the handoff set was not copied.");
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("shows Could not copy when the page has no clipboard at all", async () => {
    stubClipboard(undefined);
    renderEvidence("2026-09-30");
    fireEvent.click(screen.getByRole("button", { name: "Copy run code" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not copy");
  });

  it("removes the toast after a few seconds with one timer, and clears it on leaving", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    stubClipboard(vi.fn<(text: string) => Promise<void>>().mockResolvedValue(undefined));
    const { unmount } = renderEvidence("2026-09-30");
    const before = vi.getTimerCount();
    fireEvent.click(screen.getByRole("button", { name: "Copy run code" }));
    await screen.findByRole("status");
    expect(vi.getTimerCount()).toBe(before + 1);
    act(() => {
      vi.advanceTimersByTime(4100);
    });
    expect(screen.queryByRole("status")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Copy run code" }));
    await screen.findByRole("status");
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("starts no timer for a copy that settles after the page has gone", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    let settle: () => void = () => undefined;
    const pending = new Promise<void>((resolve) => {
      settle = resolve;
    });
    stubClipboard(() => pending);
    const { unmount } = renderEvidence("2026-09-30");
    fireEvent.click(screen.getByRole("button", { name: "Copy run code" }));
    unmount();
    await act(async () => {
      settle();
      await pending;
    });
    expect(vi.getTimerCount()).toBe(0);
  });

  it("draws the toast with no motion and no loop", async () => {
    stubClipboard(vi.fn<(text: string) => Promise<void>>().mockResolvedValue(undefined));
    renderEvidence("2026-09-30");
    fireEvent.click(screen.getByRole("button", { name: "Copy run code" }));
    const toast = await screen.findByRole("status");
    expect(toast.className).not.toMatch(/transition|animate|duration/);
  });
});

const rows = () => within(screen.getByRole("list")).getAllByRole("listitem");
const names = () => rows().map((r) => r.querySelector("p")?.textContent);
const FIVE = [
  "annual-report-2026.pdf",
  "lender-presentation-nov-2026.pdf",
  "credit-agreement-2023.pdf",
  "q4-2026-kpi-pack.xlsx",
  "rating-report-oct-2026.pdf",
];
const OTHERS = [
  "sustainability-report-2026.pdf",
  "bond-prospectus-2028-notes.pdf",
  "peer-benchmark-extract.xlsx",
  "interim-results-q3-2026.pdf",
];

/** Chooses a module in the filter through the hidden native select React Aria keeps beside it. */
function pick(name: string) {
  const trigger = screen.getByRole("button", { name: /^Module:/ });
  const select = trigger.closest("div")?.querySelector("select");
  if (!select) throw new Error("no module select");
  fireEvent.change(select, { target: { value: name === "All" ? "all" : `option:${name}` } });
}

describe("Evidence, Sources", () => {
  it("draws the Sources tab as current, with the module filter at 'Module: All' and no dead field", () => {
    renderEvidence("2026-09-30", SOURCES);
    expect(tabs().getByRole("link", { name: /^Sources/ })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("button", { name: /^Module: All/ })).toBeVisible();
    expect(screen.queryByText("Jump to an item")).toBeNull();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("draws the first five files in the mock's order, then the delivered label for the rest", () => {
    renderEvidence("2026-09-30", SOURCES);
    expect(names()).toEqual(FIVE);
    expect(screen.getByRole("button", { name: "Show the other 4 files" })).toBeVisible();
  });

  it("draws a file's type, size, state, readers and hash as the mock does", () => {
    renderEvidence("2026-09-30", SOURCES);
    const first = rows()[0] as HTMLElement;
    expect(within(first).getByText("PDF")).toBeVisible();
    expect(within(first).getByText("8.4 MB · 214 pages")).toBeVisible();
    expect(within(first).getByText("Read in full")).toBeVisible();
    expect(within(first).getByText("Read by 11 modules")).toBeVisible();
    expect(
      within(first).getByText("3a7f0c92e15d8b46f0a1c7e39d524b8806fe1d2c4a95b7e3018f6d2ac59e4b71"),
    ).toBeVisible();
    expect(within(first).getByText("SHA-256")).toBeVisible();
  });

  it("draws the readers as initials with +N, named by the module names", () => {
    renderEvidence("2026-09-30", SOURCES);
    const group = within(rows()[0] as HTMLElement).getByRole("img");
    expect(group).toHaveAccessibleName(
      "Business profile, Financial performance, Capital structure, Cash flow and liquidity, 7 more modules",
    );
    expect(group.textContent).toBe("BPFPCSCL+7");
    expect(within(rows()[2] as HTMLElement).getByRole("img").textContent).toBe("CSCD");
  });

  it("draws the three states by word and shape, and the reason beside Read in part and Unreadable", () => {
    renderEvidence("2026-09-30", SOURCES);
    const [, , part, , unreadable] = rows() as [
      HTMLElement,
      HTMLElement,
      HTMLElement,
      HTMLElement,
      HTMLElement,
    ];
    expect(within(part).getByText("Read in part")).toBeVisible();
    expect(
      within(part).getByText(
        "Schedules 4 to 9 are scanned images with no text layer and were not read.",
      ),
    ).toBeVisible();
    expect(within(unreadable).getByText("Unreadable")).toBeVisible();
    expect(
      within(unreadable).getByText(
        "The file is password-protected. Nothing in this run rests on it.",
      ),
    ).toBeVisible();
    expect(within(unreadable).getByText("Read by 0 modules")).toBeVisible();
    expect(within(unreadable).queryByRole("img")).toBeNull();
  });

  it("wraps a long name and hash and cuts nothing", () => {
    renderEvidence("2026-09-30", SOURCES);
    const first = rows()[0] as HTMLElement;
    expect(within(first).getByText("annual-report-2026.pdf")).toHaveClass("break-words");
    expect(first.innerHTML).not.toMatch(/truncate|text-ellipsis|overflow-hidden text-ellipsis/);
  });

  it("reveals the other four files in memory and takes the button away", () => {
    renderEvidence("2026-09-30", SOURCES);
    fireEvent.click(screen.getByRole("button", { name: "Show the other 4 files" }));
    expect(names()).toEqual([...FIVE, ...OTHERS]);
    expect(screen.queryByRole("button", { name: /Show the other/ })).toBeNull();
    expect(rows()[5]).toHaveFocus();
  });

  it("draws every file of a run with nothing held back, and no button", () => {
    renderEvidence("2026-03-31", SOURCES);
    expect(names()).toEqual([
      "annual-report-2025.pdf",
      "credit-agreement-2023.pdf",
      "rating-report-feb-2026.pdf",
    ]);
    expect(screen.queryByRole("button", { name: /Show the other/ })).toBeNull();
    cleanup();
    renderEvidence("2025-09-30", SOURCES);
    expect(rows()).toHaveLength(2);
  });

  it("narrows the rows to the files a module read, comparing ids, and holds none back", () => {
    renderEvidence("2026-09-30", SOURCES);
    pick("Capital structure");
    expect(names()).toEqual([
      "annual-report-2026.pdf",
      "lender-presentation-nov-2026.pdf",
      "credit-agreement-2023.pdf",
      "bond-prospectus-2028-notes.pdf",
      "interim-results-q3-2026.pdf",
    ]);
    expect(screen.queryByRole("button", { name: /Show the other/ })).toBeNull();
    pick("Forecast");
    expect(names()).toEqual(["annual-report-2026.pdf", "interim-results-q3-2026.pdf"]);
    pick("All");
    expect(names()).toEqual(FIVE);
    expect(screen.getByRole("button", { name: "Show the other 4 files" })).toBeVisible();
  });

  it("draws an empty state when the module read no file, and a control that clears the filter", () => {
    renderEvidence("2026-09-30", SOURCES);
    pick("Recovery");
    expect(
      screen.getByRole("heading", { level: 3, name: "No file was read by Recovery" }),
    ).toBeVisible();
    expect(screen.queryByRole("list")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Show all files" }));
    expect(names()).toEqual(FIVE);
  });

  it("copies a file's hash and names the file in the toast", async () => {
    const writeText = vi.fn<(text: string) => Promise<void>>().mockResolvedValue(undefined);
    stubClipboard(writeText);
    renderEvidence("2026-09-30", SOURCES);
    fireEvent.click(screen.getByRole("button", { name: "Copy hash of annual-report-2026.pdf" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "CopiedThe hash of annual-report-2026.pdf is on your clipboard.",
    );
    expect(writeText).toHaveBeenCalledWith(
      "3a7f0c92e15d8b46f0a1c7e39d524b8806fe1d2c4a95b7e3018f6d2ac59e4b71",
    );
  });

  it("draws the loading run as the skeleton only", () => {
    const { container } = renderEvidence("2026-06-30", SOURCES);
    expect(container.querySelector("[aria-busy='true']")).not.toBeNull();
    expect(screen.queryByRole("list")).toBeNull();
  });
});

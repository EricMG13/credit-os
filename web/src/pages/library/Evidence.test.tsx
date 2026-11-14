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
  it.each([SUMMARY, INDEX])("%s is titled Evidence and the fixture visits every state", (route) => {
    expect(routes.find((r) => r.path === route)?.title).toBe("Evidence");
    const runs = fixture.params[route]?.map((p) => p["run"]);
    expect(runs).toEqual(
      route === SUMMARY
        ? ["2026-09-30", "2026-06-30", "2026-03-31", "2025-09-30"]
        : ["2026-09-30", "2026-06-30"],
    );
  });

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
      "Trace148",
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

  it("draws the three counts as the mock words them", () => {
    renderEvidence("2026-09-30");
    const tiles = within(screen.getByRole("region", { name: "Counts" })).getAllByRole("listitem");
    expect(tiles.map((t) => t.textContent)).toEqual([
      "Source files97 read in full, 1 read in part, 1 unreadable",
      "Calculations148Each one traceable to its inputs",
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

  it("draws the toast with no motion and no loop", async () => {
    stubClipboard(vi.fn<(text: string) => Promise<void>>().mockResolvedValue(undefined));
    renderEvidence("2026-09-30");
    fireEvent.click(screen.getByRole("button", { name: "Copy run code" }));
    const toast = await screen.findByRole("status");
    expect(toast.className).not.toMatch(/transition|animate|duration/);
  });
});

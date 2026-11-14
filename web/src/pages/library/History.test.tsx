import { readFileSync } from "node:fs";
import path from "node:path";
import { render, screen, within } from "@testing-library/react";
import type { LibraryData } from "@/data";
import { STATUS_SETS } from "@/components/status/sets";
import { SourceContext } from "../source";
import { routes } from "./routes";

type Json = Record<string, unknown>;
type Slice = { home: Json; issuers: (Json & { history: Json & { entries: Json[] } })[] };

const fixture = JSON.parse(
  readFileSync(
    path.resolve(import.meta.dirname, "..", "..", "..", "fixtures", "library.json"),
    "utf8",
  ),
) as { issuers: LibraryData["issuers"]; slice: Slice; params: Record<string, Json[]> };

const fresh = (): Slice => structuredClone(fixture.slice);

function renderHistory(issuer: string, library: unknown = fixture.slice) {
  const data: LibraryData = { schema: "credit-os-data/1", issuers: fixture.issuers, library };
  const route = routes.find((r) => r.path === "/library/:issuer/history");
  if (route === undefined) throw new Error("no history route");
  return render(
    <SourceContext.Provider value={data}>{route.render({ issuer })}</SourceContext.Provider>,
  );
}

/** The feed entries, newest first. */
const entries = () => within(screen.getByRole("list")).getAllByRole("listitem");

describe("the history route", () => {
  it("is titled Report history and the fixture visits both states", () => {
    expect(routes.find((r) => r.path === "/library/:issuer/history")?.title).toBe("Report history");
    expect(fixture.params["/library/:issuer/history"]).toEqual([
      { issuer: "halden-aerostructures" },
      { issuer: "corvane-fasteners" },
    ]);
  });
});

describe("Report history, a normal issuer", () => {
  it("draws the back link, the h1 name, the subtitle and both actions", () => {
    renderHistory("halden-aerostructures");
    expect(screen.getByRole("link", { name: "Library" })).toHaveAttribute("href", "#/library/home");
    expect(screen.getByRole("heading", { level: 1, name: "Halden Aerostructures" })).toBeVisible();
    expect(screen.getByText("Report history: seven runs since September 2025")).toBeVisible();
    expect(screen.getByRole("link", { name: "Open latest report" })).toHaveAttribute(
      "href",
      "#/library/halden-aerostructures/2026-09-30/overview",
    );
    expect(screen.getByRole("link", { name: "New run" })).toHaveAttribute("href", "#/run");
  });

  it("draws seven entries newest first with the mock's dates, states, pathways and sentences", () => {
    renderHistory("halden-aerostructures");
    const rows = entries();
    expect(rows).toHaveLength(7);
    const first = within(rows[0] as HTMLElement);
    expect(first.getByText("Run as of 30 Sep 2026")).toBeVisible();
    expect(first.getByText("Ran 13 Nov 2026")).toBeVisible();
    expect(first.getByText("Finished")).toBeVisible();
    expect(first.getByText("Full review")).toBeVisible();
    expect(
      first.getByText(
        "Stable credit with thin headroom. Twelve of thirteen modules delivered; recovery was not assessable.",
      ),
    ).toBeVisible();
    const last = within(rows[6] as HTMLElement);
    expect(last.getByText("Run as of 30 Sep 2025")).toBeVisible();
    expect(
      last.getByText("Stable. First run on this issuer, so there is no earlier run to compare."),
    ).toBeVisible();
  });

  it("links a finished run to its report and to what changed since the run before", () => {
    renderHistory("halden-aerostructures");
    const first = within(entries()[1] as HTMLElement);
    expect(first.getByRole("link", { name: "Open report" })).toHaveAttribute(
      "href",
      "#/library/halden-aerostructures/2026-06-30/overview",
    );
    expect(first.getByRole("link", { name: "What changed since 31 Mar 2026" })).toHaveAttribute(
      "href",
      "#/library/halden-aerostructures/2026-06-30/changes",
    );
  });

  it("links a capped run: its delivered modules can be read", () => {
    renderHistory("halden-aerostructures");
    const capped = within(entries()[2] as HTMLElement);
    expect(capped.getByText("Capped")).toBeVisible();
    expect(capped.getByRole("link", { name: "Open report" })).toBeVisible();
    expect(capped.getByRole("link", { name: "What changed since 31 Dec 2025" })).toBeVisible();
  });

  it.each([
    [3, "Rejected"],
    [4, "Failed"],
    [5, "Interrupted"],
  ])("draws entry %i as %s with no link", (index, word) => {
    renderHistory("halden-aerostructures");
    const row = within(entries()[index] as HTMLElement);
    expect(row.getByText(word)).toBeVisible();
    expect(row.queryByRole("link")).toBeNull();
  });

  it("gives the first run an Open report link and no what-changed link", () => {
    renderHistory("halden-aerostructures");
    const row = within(entries()[6] as HTMLElement);
    expect(row.getByRole("link", { name: "Open report" })).toBeVisible();
    expect(row.queryByRole("link", { name: /What changed/ })).toBeNull();
  });

  it("draws the five run states with five different shapes", () => {
    renderHistory("halden-aerostructures");
    const shapes = ["Finished", "Capped", "Rejected", "Failed", "Interrupted"].map((word) => {
      const badge = screen.getAllByText(word)[0]?.closest("span");
      return badge?.parentElement?.querySelector("svg")?.getAttribute("data-shape") ?? null;
    });
    expect(shapes).toEqual(
      ["Finished", "Capped", "Rejected", "Failed", "Interrupted"].map(
        (word) => STATUS_SETS["Run states"][word as "Finished"].shape,
      ),
    );
    expect(new Set(shapes).size).toBe(5);
  });

  it("shows no run code or id, in text or attributes, beyond the routing links", () => {
    const { container } = renderHistory("halden-aerostructures");
    expect(container.textContent).not.toMatch(/CP-\d|RUN-|sha|\.pdf|\d{4}-\d{2}-\d{2}/);
    for (const el of container.querySelectorAll("*")) {
      for (const attr of el.attributes) {
        if (attr.name === "id" || attr.name === "title" || /^(aria|data)-/.test(attr.name)) {
          expect(attr.value, `${el.tagName} ${attr.name}`).not.toMatch(/\d{4}-\d{2}-\d{2}/);
        }
      }
      expect(el.getAttribute("title")).toBeNull();
    }
  });
});

describe("Report history, an issuer with no report yet", () => {
  it("draws the mock's sentence with Back to the library and Start a run, and no feed", () => {
    renderHistory("corvane-fasteners");
    expect(screen.getByRole("heading", { level: 1, name: "Corvane Fasteners" })).toBeVisible();
    expect(screen.getByText("One run, not finished")).toBeVisible();
    expect(screen.getByText("No report yet")).toBeVisible();
    expect(
      screen.getByText(
        "The only run on this issuer failed on 11 Nov 2026 before any module was delivered, so there is nothing to read. Start a new run to write the first report.",
      ),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to the library" })).toHaveAttribute(
      "href",
      "#/library/home",
    );
    expect(screen.getByRole("link", { name: "Start a run" })).toHaveAttribute("href", "#/run");
    expect(screen.queryByRole("list")).toBeNull();
    expect(screen.queryByRole("link", { name: "Open latest report" })).toBeNull();
  });
});

describe("Report history, an unknown issuer", () => {
  it("says which issuer is missing and links to the library, without the route-check strings", () => {
    const { container } = renderHistory("no-such-issuer");
    expect(screen.getByText("No such issuer")).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to the library" })).toHaveAttribute(
      "href",
      "#/library/home",
    );
    expect(container.textContent).not.toContain("Page not found");
    expect(container.textContent).not.toContain("This part of the library could not be read");
  });
});

describe("Report history, a malformed entry", () => {
  it("draws nothing of the page and names the path", () => {
    const slice = fresh();
    const bad = slice.issuers[0];
    if (bad === undefined) throw new Error("no issuer");
    bad.history.entries[2] = { ...bad.history.entries[2], state: "Unfinished" };
    renderHistory("halden-aerostructures", slice);
    expect(screen.getByText(/issuers\[0\]\.history\.entries\[2\]\.state/)).toBeVisible();
    expect(screen.queryByText("Run as of 30 Sep 2026")).toBeNull();
  });
});

describe("Report history, heading levels", () => {
  it("draws the issuer at h1 and its empty state one level below at h2", () => {
    renderHistory("corvane-fasteners");
    expect(screen.getByRole("heading", { level: 1, name: "Corvane Fasteners" })).toBeVisible();
    expect(screen.getByRole("heading", { level: 2, name: "No report yet" })).toBeVisible();
    expect(screen.queryByRole("heading", { level: 3, name: "No report yet" })).toBeNull();
  });

  it("draws an unknown issuer's empty state at h2, directly under the page h1", () => {
    renderHistory("no-such-issuer");
    expect(screen.getByRole("heading", { level: 1, name: "Report history" })).toBeVisible();
    expect(screen.getByRole("heading", { level: 2, name: "No such issuer" })).toBeVisible();
  });
});

describe("Report history, fixture against the Library home cards", () => {
  it("gives every carded issuer a history that opens the card's run, in the card's state", () => {
    const cards = (fixture.slice.home["cards"] as Json[]).filter((c) => c["kind"] === "issuer");
    expect(cards.length).toBeGreaterThan(0);
    for (const card of cards) {
      const issuer = fixture.slice.issuers.find((i) => i["id"] === card["issuer"]);
      const list = issuer?.history.entries ?? [];
      const opened = list.find((e) => e["report"] === card["href"]);
      expect(opened, `${String(card["issuer"])} opens ${String(card["href"])}`).toBeDefined();
      expect(["Failed", "Running"]).not.toContain(opened?.["state"]);
      expect(
        list.map((e) => e["state"]),
        String(card["issuer"]),
      ).toContain(card["state"]);
    }
  });
});

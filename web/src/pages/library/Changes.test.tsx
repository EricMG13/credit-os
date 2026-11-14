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

const PATH = "/library/:issuer/:run/changes";

function renderChanges(
  run: string,
  library: unknown = fixture.slice,
  issuer = "halden-aerostructures",
) {
  const data: LibraryData = { schema: "credit-os-data/1", issuers: fixture.issuers, library };
  const route = routes.find((r) => r.path === PATH);
  if (route === undefined) throw new Error("no changes route");
  return render(
    <SourceContext.Provider value={data}>{route.render({ issuer, run })}</SourceContext.Provider>,
  );
}

const cardOf = (measure: string) => {
  const card = screen.getByText(measure, { selector: "strong" }).closest("li");
  if (card === null) throw new Error(`no card for ${measure}`);
  return card;
};
const click = (element: HTMLElement) => {
  fireEvent.click(element);
};

describe("the changes route", () => {
  it("is titled Changes, full bleed, and the fixture visits every state of the page", () => {
    const route = routes.find((r) => r.path === PATH);
    expect(route?.title).toBe("Changes");
    expect(route?.layout).toBe("bleed");
    expect(fixture.params[PATH]?.map((p) => p["run"])).toEqual([
      "2026-09-30",
      "2026-06-30",
      "2026-03-31",
      "2025-09-30",
    ]);
  });
});

describe("Changes, the mock's compared run", () => {
  it("draws the issuer as the one h1, the Changes tab as current, and the delivered heading", () => {
    renderChanges("2026-09-30");
    expect(screen.getByRole("heading", { level: 1, name: "Halden Aerostructures" })).toBeVisible();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Changes" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Changes" })).toHaveAttribute(
      "href",
      "#/library/halden-aerostructures/2026-09-30/changes",
    );
    expect(
      screen.getByRole("heading", { level: 2, name: "What changed since 30 June 2026" }),
    ).toBeVisible();
    expect(
      screen.getByText("Six changes to the credit profile, three modules with a changed finding."),
    ).toBeVisible();
  });

  it("draws one card per change in the module's order, with value, from and cause then effect", () => {
    renderChanges("2026-09-30");
    const measures = screen
      .getAllByText(/./, { selector: "strong" })
      .map((strong) => strong.textContent);
    expect(measures).toEqual([
      "Net leverage",
      "EBITDA margin",
      "Liquidity",
      "Interest cover",
      "Rating outlook",
      "Refinancing of the 2028 notes",
    ]);
    const leverage = cardOf("Net leverage");
    expect(within(leverage).getByText("4.6x")).toBeVisible();
    expect(leverage).toHaveTextContent("from 4.9x");
    expect(within(leverage).getByText("Value")).toBeVisible();
    expect(leverage).toHaveTextContent(
      "EBITDA grew 10% while net debt rose 3%. The outlook moves from negative to stable.",
    );
    expect(cardOf("Liquidity")).toHaveTextContent("USD 412m");
    expect(cardOf("Rating outlook")).toHaveTextContent("Conclusion");
  });

  it("draws the delivered direction text, with a mark only for up and down", () => {
    renderChanges("2026-09-30");
    const down = cardOf("Net leverage");
    expect(down).toHaveTextContent("Lower by 0.3x");
    expect(down.querySelectorAll("svg[aria-hidden='true']").length).toBeGreaterThanOrEqual(1);
    const up = cardOf("EBITDA margin");
    expect(up).toHaveTextContent("Higher by 0.6 points");
    const none = cardOf("Rating outlook");
    expect(none).toHaveTextContent("Changed");
    // The up and down cards carry one more arrow than a card whose direction is "none".
    const arrows = (card: HTMLElement) => card.querySelectorAll("span > svg").length;
    expect(arrows(down)).toBe(arrows(none) + 1);
    expect(arrows(up)).toBe(arrows(none) + 1);
  });

  it("reads from n.a. with no direction mark and no direction text when the earlier figure is missing", () => {
    renderChanges("2026-09-30");
    const cover = cardOf("Interest cover");
    expect(cover).toHaveTextContent("2.4x");
    expect(within(cover).getByText("n.a.")).toBeVisible();
    expect(cover).toHaveTextContent(/from\s*n\.a\./);
    expect(cover.querySelectorAll("span > svg")).toHaveLength(0);
    expect(cover).not.toHaveTextContent(/Lower|Higher|Changed|Later/);
    expect(cover).toHaveTextContent(
      "The earlier run did not establish cash interest. No comparison can be made; the figure is new.",
    );
  });

  it("gives each change one trace control named for the change, and none for a change with no trace", () => {
    renderChanges("2026-09-30");
    expect(screen.getAllByRole("button", { name: "Show sources for this change" })).toHaveLength(6);
    cleanup();
    renderChanges("2026-03-31");
    expect(screen.queryAllByRole("button", { name: "Show sources for this change" })).toHaveLength(
      0,
    );
  });

  it("opens the trace drawer of a change", () => {
    renderChanges("2026-09-30");
    const control = within(cardOf("Net leverage")).getByRole("button", {
      name: "Show sources for this change",
    });
    click(control);
    expect(screen.getByRole("dialog", { name: "Sources for net leverage" })).toBeVisible();
  });
});

describe("Changes, a withheld value and a zero", () => {
  it("draws Withheld with its reason in the card, and zero as 0", () => {
    renderChanges("2026-03-31");
    const margin = cardOf("EBITDA margin");
    expect(within(margin).getByText("Withheld")).toBeVisible();
    expect(margin).toHaveTextContent(
      "Withheld until the financial performance module is delivered",
    );
    expect(margin).toHaveTextContent("from 22.0%");
    const drawn = cardOf("Drawn on the facility, USD m");
    expect(drawn).toHaveTextContent("0");
    expect(drawn).toHaveTextContent("from 40");
  });
});

describe("Changes, the first run on the issuer", () => {
  it("says No earlier run to compare, with the mock's sentence and a way to the Overview", () => {
    renderChanges("2025-09-30");
    expect(
      screen.getByRole("heading", { level: 2, name: "No earlier run to compare" }),
    ).toBeVisible();
    expect(
      screen.getByText(
        "This is the first run on Halden Aerostructures. What changed will appear here after the next run.",
      ),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Open the Overview" })).toHaveAttribute(
      "href",
      "#/library/halden-aerostructures/2025-09-30/overview",
    );
    expect(screen.queryByRole("radiogroup", { name: "Presentation" })).toBeNull();
    expect(screen.queryByRole("heading", { name: "Modules" })).toBeNull();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });
});

describe("Changes, the other states of the frame", () => {
  it("draws the skeleton for a run still loading", () => {
    const { container } = renderChanges("2026-06-30");
    expect(container.querySelector("[aria-busy='true']")).not.toBeNull();
    expect(screen.queryByRole("radiogroup", { name: "Presentation" })).toBeNull();
  });

  it.each([
    ["issuer", "nobody", "2026-09-30", "No such issuer"],
    ["run", "halden-aerostructures", "1999-01-01", "No such run"],
  ])(
    "says which %s the library does not hold, under the page name as the h1",
    (_, issuer, run, title) => {
      renderChanges(run, fixture.slice, issuer);
      expect(screen.getByRole("heading", { level: 1, name: "Changes" })).toBeVisible();
      expect(screen.getByRole("heading", { level: 2, name: title })).toBeVisible();
      expect(screen.getByRole("link", { name: "Back to the library" })).toBeVisible();
    },
  );

  it("shows the reader's notice, not a partial page, when a change is malformed", () => {
    const slice = structuredClone(fixture.slice) as { issuers: { runs: Json[] }[] };
    const changes = slice.issuers[0]?.runs[0]?.["changes"] as { changes: Json[] };
    (changes.changes[0] as Json)["direction"] = "sideways";
    renderChanges("2026-09-30", slice);
    expect(
      screen.getByText(/issuers\[0\]\.runs\[0\]\.changes\.changes\[0\]\.direction/),
    ).toBeVisible();
    expect(screen.queryByRole("radiogroup", { name: "Presentation" })).toBeNull();
  });
});

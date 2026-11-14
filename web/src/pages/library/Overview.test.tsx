import { readFileSync } from "node:fs";
import path from "node:path";
import { fireEvent, render, screen, within } from "@testing-library/react";
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

const PATH = "/library/:issuer/:run/overview";

function renderOverview(
  run: string,
  library: unknown = fixture.slice,
  issuer = "halden-aerostructures",
) {
  const data: LibraryData = { schema: "credit-os-data/1", issuers: fixture.issuers, library };
  const route = routes.find((r) => r.path === PATH);
  if (route === undefined) throw new Error("no overview route");
  return render(
    <SourceContext.Provider value={data}>{route.render({ issuer, run })}</SourceContext.Provider>,
  );
}

const tiles = () =>
  within(screen.getByRole("region", { name: "Headline figures" })).getAllByRole("listitem");
const traces = () => screen.queryAllByRole("button", { name: "Show sources for this figure" });

describe("the overview route", () => {
  it("is titled Overview and the fixture visits the full, loading and capped runs", () => {
    expect(routes.find((r) => r.path === PATH)?.title).toBe("Overview");
    expect(fixture.params[PATH]?.map((p) => p["run"])).toEqual([
      "2026-09-30",
      "2026-06-30",
      "2026-03-31",
    ]);
  });
});

describe("Overview, the mock's run", () => {
  it("draws the bottom line band: label, lead as an h3, the rest and one trace control", () => {
    renderOverview("2026-09-30");
    const band = screen.getByRole("region", { name: "Bottom line" });
    expect(within(band).getByText("Bottom line")).toBeVisible();
    expect(
      within(band).getByRole("heading", {
        level: 3,
        name: "Stable credit with thin headroom: leverage is falling, but the 2028 notes need refinancing before the engine programme pays back.",
      }),
    ).toBeVisible();
    expect(within(band).getByText(/^Halden converts a strong order book/)).toBeVisible();
    expect(within(band).getAllByRole("button")).toHaveLength(1);
  });

  it("draws six headline tiles with the mock's labels, figures and notes", () => {
    renderOverview("2026-09-30");
    expect(tiles().map((tile) => tile.textContent)).toEqual([
      "Revenue, USD m2,105Year to 30 Sep 2026",
      "EBITDA margin23.1%Company-adjusted basis",
      "Net leverage4.6xNet debt to EBITDA",
      "Interest cover2.4xEBITDA to cash interest",
      "Liquidity, USD m412Cash and undrawn facility",
      "Recovery, senior notesn.a.not availableRecovery was not assessable",
    ]);
    expect(within(tiles()[5] as HTMLElement).getByText("n.a.").parentElement).toHaveClass(
      "text-text-tertiary",
    );
    expect(within(tiles()[5] as HTMLElement).queryByRole("button")).toBeNull();
  });

  it("draws For and against: h3, its note, two h4 columns of three tiles each", () => {
    renderOverview("2026-09-30");
    expect(screen.getByRole("heading", { level: 3, name: "For and against" })).toBeVisible();
    expect(
      screen.getByText("Three points on each side, as the modules weighed them"),
    ).toBeVisible();
    const sides = screen.getAllByRole("heading", { level: 4 });
    expect(sides.map((h) => h.textContent)).toEqual(["Supports the view", "Against the view"]);
    const against = within(sides[1]?.parentElement as HTMLElement).getAllByRole("listitem");
    expect(against.map((item) => item.textContent)).toEqual([
      "USD 310mUnsecured notes fall due in 2028 with no refinancing agreed and coupons likely to reset higher.Reported",
      "2.4xInterest cover leaves little room if floating rates stay where they are.Unhedged portion estimated",
      "34%Revenue from one engine programme whose ramp has slipped twice.Management disclosure",
    ]);
    expect(
      within(sides[0]?.parentElement as HTMLElement).getAllByRole("listitem")[0]?.textContent,
    ).toBe(
      "4.6xNet leverage fell from 4.9x a year earlier as EBITDA grew faster than debt.Reported",
    );
  });

  it("never skips a heading level under the frame's h2", () => {
    renderOverview("2026-09-30");
    expect(screen.getAllByRole("heading").map((h) => h.tagName)).toEqual([
      "H2",
      "H3",
      "H3",
      "H4",
      "H4",
    ]);
  });

  it("draws one trace control per traced figure: the band, five metrics, six points", () => {
    renderOverview("2026-09-30");
    expect(traces()).toHaveLength(12);
    for (const tile of tiles().slice(0, 5))
      expect(within(tile).getAllByRole("button")).toHaveLength(1);
  });

  it("opens the trace drawer of the figure whose control is pressed", () => {
    renderOverview("2026-09-30");
    fireEvent.click(within(tiles()[2] as HTMLElement).getByRole("button"));
    expect(screen.getByRole("dialog", { name: "Sources for net leverage" })).toBeVisible();
  });

  it("turns every control on with Show sources", () => {
    const { container } = renderOverview("2026-09-30");
    fireEvent.click(screen.getByRole("switch", { name: "Show sources" }));
    expect(container.querySelector("[data-sources]")).toHaveAttribute("data-sources", "on");
    fireEvent.click(screen.getByRole("switch", { name: "Show sources" }));
  });

  it("shows no audit material: ids, files, hashes, run codes or module timings", () => {
    const { container } = renderOverview("2026-09-30");
    const all = [container.innerHTML, container.textContent].join(" ");
    expect(all).not.toMatch(/T-\d{4}|C-\d{4}|\.pdf|hash|run code|net-leverage|interest-cover/i);
    expect(all).not.toMatch(/\d+ ?ms|seconds/i);
  });
});

describe("Overview, states", () => {
  it("draws the loading run as a skeleton only", () => {
    const { container } = renderOverview("2026-06-30");
    expect(container.querySelector("[aria-busy='true']")).not.toBeNull();
    expect(screen.queryByRole("region", { name: "Bottom line" })).toBeNull();
    expect(traces()).toHaveLength(0);
  });

  it("draws a zero as 0, a withheld figure as Withheld, a gap and a missing figure apart", () => {
    renderOverview("2026-03-31");
    const [zero, withheld, gap, missing] = tiles() as [
      HTMLElement,
      HTMLElement,
      HTMLElement,
      HTMLElement,
    ];
    expect(within(zero).getByText("0")).toBeVisible();
    expect(within(zero).queryByText("n.a.")).toBeNull();
    expect(within(withheld).getByText("Withheld")).toBeVisible();
    expect(
      within(withheld).getByText("Withheld until the financial performance module is delivered"),
    ).toBeVisible();
    expect(within(gap).getByText("Not established for this run")).toBeVisible();
    expect(within(gap).getByText("No net debt figure was delivered before the cap.")).toBeVisible();
    expect(within(missing).getByText("n.a.")).toBeVisible();
    expect(traces()).toHaveLength(0);
  });

  it("draws a long point in full, and a missing figure in a point as n.a.", () => {
    renderOverview("2026-03-31");
    const long = screen.getByText(/^The financial performance, cash flow and recovery modules/);
    expect(long.textContent).toMatch(/that did run\.$/);
    expect(long).not.toHaveClass("truncate");
    expect(within(long.closest("li") as HTMLElement).getByText("n.a.")).toBeVisible();
    expect(screen.getByText("Not assessable")).toBeVisible();
  });

  it("says which part is missing for a run or an issuer the slice does not hold", () => {
    renderOverview("1999-01-01");
    expect(screen.getByText("No such run")).toBeVisible();
  });

  it("says no such issuer, with the way back to the library", () => {
    renderOverview("2026-09-30", fixture.slice, "nobody");
    expect(screen.getByText("No such issuer")).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to the library" })).toBeVisible();
  });
});

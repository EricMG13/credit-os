import { readFileSync } from "node:fs";
import path from "node:path";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import type { LibraryData } from "@/data";
import { SourceContext } from "../source";
import { routes } from "./routes";

const fixture = JSON.parse(
  readFileSync(
    path.resolve(import.meta.dirname, "..", "..", "..", "fixtures", "library.json"),
    "utf8",
  ),
) as { issuers: LibraryData["issuers"]; slice: unknown };

const BASE = "/library/:issuer/:run/evidence";
const P = { issuer: "halden-aerostructures", run: "2026-09-30" };
const data: LibraryData = {
  schema: "credit-os-data/1",
  issuers: fixture.issuers,
  library: fixture.slice,
};

function page(route: string, params: Record<string, string>) {
  const found = routes.find((r) => r.path === `${BASE}/${route}`);
  if (found === undefined) throw new Error(`no ${route} route`);
  return <SourceContext.Provider value={data}>{found.render(params)}</SourceContext.Provider>;
}

function pick(name: string) {
  const select = screen
    .getByRole("button", { name: /^Module:/ })
    .closest("div")
    ?.querySelector("select");
  if (!select) throw new Error("no module select");
  fireEvent.change(select, { target: { value: `option:${name}` } });
}

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});
afterEach(cleanup);

describe("an item address reached while the module filter is set", () => {
  it("draws, marks and focuses the gap, with the filter back at All", () => {
    const view = render(page("gaps", P));
    pick("Recovery");
    view.rerender(page("gaps/:item", { ...P, item: "G-03" }));
    const row = within(screen.getByRole("table", { name: "Gaps" }))
      .getByRole("rowheader", { name: "G-03" })
      .closest("tr");
    expect(row).toHaveAttribute("aria-current", "location");
    expect(row).toHaveFocus();
    expect(screen.getByRole("button", { name: /^Module: All/ })).toBeVisible();
  });

  it("draws and focuses the Trace row, with the filter back at All", () => {
    const view = render(page("trace", P));
    pick("Recovery");
    view.rerender(page("trace/:item", { ...P, item: "T-0001" }));
    const row = screen.getByRole("rowheader", { name: "T-0001" }).closest("tr");
    expect(row).toHaveFocus();
    expect(screen.getByRole("button", { name: /^Module: All/ })).toBeVisible();
  });

  it("keeps the filter when the address does not change", () => {
    const view = render(page("gaps", P));
    pick("Recovery");
    view.rerender(page("gaps", P));
    expect(screen.getByRole("button", { name: /^Module: Recovery/ })).toBeVisible();
  });
});

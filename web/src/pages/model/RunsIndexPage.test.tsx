import { render, screen, within } from "@testing-library/react";
import { App } from "@/App";
import type { LibraryData, LoadResult } from "@/data";
import { SourceContext } from "../source";
import { RunsIndexPage } from "./RunsIndexPage";
import { fixtureSlice, must } from "./slice/test-fixture";

function renderIndex(slice: unknown, hash = "#/model/runs") {
  window.location.hash = hash;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], model: slice },
  };
  return render(<App result={result} />);
}

describe("Runs index page", () => {
  it("draws one h1, Financial models, and the bleed padding", () => {
    renderIndex(fixtureSlice());
    const headings = screen.getAllByRole("heading", { level: 1 });
    expect(headings.map((h) => h.textContent)).toEqual(["Financial models"]);
    expect(must(screen.getByRole("main").firstElementChild)).toHaveClass("p-8");
  });

  it("lists the fixture run as a link to its front page with the delivered strings", () => {
    renderIndex(fixtureSlice());
    const link = screen.getByRole("link", { name: /TransDigm Group/ });
    expect(link).toHaveAttribute("href", "#/model/transdigm/2025-06-30/front");
    expect(link).toHaveTextContent("As of 30 June 2025");
  });

  it("lists every run the slice holds", () => {
    const slice = fixtureSlice() as { runs: Record<string, unknown>[] };
    const first = must(slice.runs[0]);
    const other = structuredClone(first) as { issuer: string; run: string; header: object };
    other.issuer = "other-issuer";
    other.run = "2024-12-31";
    other.header = {
      ...(first["header"] as object),
      issuerName: "Other Issuer plc",
      asOf: "As of 31 December 2024",
    };
    slice.runs.push(other);
    renderIndex(slice);
    const items = within(screen.getByRole("main")).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(within(must(items[1])).getByRole("link")).toHaveAttribute(
      "href",
      "#/model/other-issuer/2024-12-31/front",
    );
    expect(items[1]).toHaveTextContent("Other Issuer plc");
    expect(items[1]).toHaveTextContent("As of 31 December 2024");
  });

  it("draws issuer 'a/b' run 'c' and issuer 'a' run 'b/c' without a duplicate key", () => {
    const seen: string[] = [];
    const spy = vi.spyOn(console, "error").mockImplementation((...args: unknown[]) => {
      seen.push(args.map(String).join(" "));
    });
    const slice = fixtureSlice() as { runs: Record<string, unknown>[] };
    const first = structuredClone(must(slice.runs[0])) as { issuer: string; run: string };
    const second = structuredClone(first);
    first.issuer = "a/b";
    first.run = "c";
    second.issuer = "a";
    second.run = "b/c";
    slice.runs = [first, second];
    renderIndex(slice);
    spy.mockRestore();
    expect(seen.filter((m) => m.includes("same key"))).toEqual([]);
    expect(within(screen.getByRole("main")).getAllByRole("listitem")).toHaveLength(2);
  });

  it("draws the empty state when no model has been delivered", () => {
    renderIndex({ runs: [] });
    expect(screen.getByText("No model has been delivered yet")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(within(screen.getByRole("main")).queryAllByRole("listitem")).toHaveLength(0);
  });

  it("is the group's bare address", () => {
    renderIndex(fixtureSlice(), "#/model");
    expect(screen.getByRole("heading", { level: 1, name: "Financial models" })).toBeInTheDocument();
  });

  it("leaves an invalid slice to the app", () => {
    renderIndex({ runs: [], extra: 1 });
    expect(screen.getByText("extra: unknown field")).toBeInTheDocument();
  });

  it("lists a named unreadable run and counts an unnamed one, beside a readable run", () => {
    const slice = fixtureSlice() as { runs: unknown[] };
    const named = structuredClone(slice.runs[0]) as Record<string, unknown>;
    named["run"] = "2024-12-31";
    (named["header"] as Record<string, unknown>)["asOf"] = 5;
    slice.runs.push(named, "nope");
    renderIndex(slice);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    const items = within(screen.getByRole("main")).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("TransDigm Group");
    expect(items[1]).toHaveTextContent("transdigm");
    expect(items[1]).toHaveTextContent("2024-12-31");
    expect(items[1]).toHaveTextContent("Could not be read");
    expect(within(must(items[1])).getByRole("link")).toHaveAttribute(
      "href",
      "#/model/transdigm/2024-12-31/front",
    );
    expect(screen.getByText("1 run could not be read and cannot be listed")).toBeInTheDocument();
    expect(screen.queryByText("No model has been delivered yet")).not.toBeInTheDocument();
  });

  it("counts several unnamed unreadable runs and draws no empty state", () => {
    renderIndex({ runs: [1, "two"] });
    expect(screen.getByText("2 runs could not be read and cannot be listed")).toBeInTheDocument();
    expect(screen.queryByText("No model has been delivered yet")).not.toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("throws on an invalid slice that reaches it, never drawing 'no model'", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const data = {
      schema: "credit-os-data/1",
      issuers: [],
      model: { runs: [], extra: 1 },
    } as LibraryData;
    expect(() =>
      render(
        <SourceContext.Provider value={data}>
          <RunsIndexPage />
        </SourceContext.Provider>,
      ),
    ).toThrow("extra: unknown field");
    spy.mockRestore();
  });

  it("draws no list when every run is unreadable and none is named", () => {
    renderIndex({ runs: [1, "two"] });
    expect(within(screen.getByRole("main")).queryByRole("list")).toBeNull();
    expect(screen.getByText(/2 runs could not be read/)).toBeInTheDocument();
  });

  it("draws the empty state, one h1, when the data file holds no model", () => {
    renderIndex(undefined);
    expect(screen.getByText("No model has been delivered yet")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });
});

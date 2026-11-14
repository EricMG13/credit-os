import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { App } from "@/App";
import type { LoadResult } from "@/data";
import { fixtureSlice, must } from "./slice/test-fixture";

const ADDRESS = "#/library/transdigm/2025-06-30/evidence";
const PERIODS = ["FY22", "FY23", "FY24", "LTM", "FY25E", "FY26E", "FY27E"];

type Slice = {
  runs: {
    cases: { note: string | null }[];
    statements: {
      columns: unknown[];
      statements: { name: string; rows: { label: string; cells: unknown[] }[] }[];
    };
  }[];
};

function renderAt(slice: unknown, issuer = "transdigm", run = "2025-06-30") {
  window.location.hash = `#/model/${issuer}/${run}/statements`;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], model: slice },
  };
  return render(<App result={result} />);
}

/** The fixture's first run, to edit in a test-only slice. */
function draft(): { slice: Slice; run: Slice["runs"][number] } {
  const slice = fixtureSlice() as Slice;
  return { slice, run: must(slice.runs[0]) };
}

const rowOf = (label: string): HTMLElement =>
  must(
    within(screen.getByRole("table"))
      .getAllByRole("row")
      .find((r) => within(r).queryByRole("rowheader")?.textContent.startsWith(label)),
  );

/** The cell of `row` under the period column `period`. */
function cellAt(label: string, period: string): HTMLElement {
  const headers = within(screen.getByRole("table")).getAllByRole("columnheader");
  const at = headers.findIndex((h) => h.textContent.startsWith(period));
  if (at < 1) throw new Error(`no column ${period}`);
  return must(within(rowOf(label)).getAllByRole("cell")[at - 1]);
}

const choose = (name: string) => {
  fireEvent.click(screen.getByRole("radio", { name }));
};
const openTab = (name: string) => {
  fireEvent.click(screen.getByRole("tab", { name }));
};

describe("Model page: the two cases", () => {
  it("orders the headings h1 (the issuer), h2 (the sections) and marks the Model tab", () => {
    renderAt(fixtureSlice());
    const levels = screen
      .getAllByRole("heading")
      .map((h) => [h.tagName, h.textContent])
      .slice(0, 3);
    expect(levels).toEqual([
      ["H1", "TransDigm Group"],
      ["H2", "Two cases"],
      ["H2", "Statements"],
    ]);
    const tabs = within(screen.getByRole("navigation", { name: "Pages" }));
    expect(tabs.getByRole("link", { name: "Model" })).toHaveAttribute("aria-current", "page");
    expect(tabs.getByRole("link", { name: "Model" })).toHaveAttribute(
      "href",
      "#/model/transdigm/2025-06-30/statements",
    );
  });

  it("draws the choice line and two cards, the first chosen", () => {
    renderAt(fixtureSlice());
    expect(
      screen.getByText("Choose a case: the forecast columns and every chart below follow it."),
    ).toBeInTheDocument();
    const group = screen.getByRole("radiogroup", { name: "Case" });
    const radios = within(group).getAllByRole("radio");
    expect(radios.map((r) => r.getAttribute("aria-labelledby") !== null)).toEqual([true, true]);
    expect(screen.getByRole("radio", { name: "Base case" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Downside case" })).not.toBeChecked();
  });

  it.each([
    [
      "Base case",
      "Management plan, trimmed",
      "Aftermarket sales grow 8% a year and margins hold near 53%. Cash builds on the balance sheet.",
      "Leaves out: acquisitions and any further special dividend.",
    ],
    [
      "Downside case",
      "Traffic shock",
      "Flight hours fall 10% in FY26 and recover half in FY27; prices stay flat; floating debt costs 100 basis points more.",
      "Leaves out: covenant waivers and asset sales.",
    ],
  ])("draws the %s card: tag, assumption, what it leaves out", (name, tag, assumption, leaves) => {
    renderAt(fixtureSlice());
    const card = must(screen.getByRole("radio", { name }).closest("[data-case]"));
    expect(within(card as HTMLElement).getByText(tag)).toBeInTheDocument();
    expect(within(card as HTMLElement).getByText(assumption)).toBeInTheDocument();
    expect(within(card as HTMLElement).getByText(leaves)).toBeInTheDocument();
    expect(
      within(card as HTMLElement).getByRole("link", { name: `Show the sources for ${name}` }),
    ).toHaveAttribute("href", ADDRESS);
  });

  it("changes the case when its card is chosen, and not when a trace control is pressed", () => {
    renderAt(fixtureSlice());
    const second = must(
      screen.getByRole("radio", { name: "Downside case" }).closest("[data-case]"),
    );
    const link = within(second as HTMLElement).getByRole("link", {
      name: "Show the sources for Downside case",
    });
    link.addEventListener("click", (event) => {
      event.preventDefault();
    });
    fireEvent.click(link);
    expect(screen.getByRole("radio", { name: "Base case" })).toBeChecked();
    fireEvent.click(second.querySelector("label") as HTMLElement);
    expect(screen.getByRole("radio", { name: "Downside case" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Base case" })).not.toBeChecked();
  });

  it("draws a case's note under its card only when it has one", () => {
    const first = renderAt(fixtureSlice());
    expect(screen.queryByText(/is the stress case/)).toBeNull();
    first.unmount();
    const { slice, run } = draft();
    must(run.cases[1]).note =
      "Downside case is the stress case: a shock applied to the model’s own downside drivers.";
    renderAt(slice);
    const card = must(screen.getByRole("radio", { name: "Downside case" }).closest("[data-case]"));
    expect(
      within(card as HTMLElement).getByText(
        "Downside case is the stress case: a shock applied to the model’s own downside drivers.",
      ),
    ).toBeInTheDocument();
  });
});

describe("Model page: the statements", () => {
  it("draws the heading line, the Figures and Bars choice, four tabs and the basis line", () => {
    renderAt(fixtureSlice());
    expect(
      screen.getByText("USD millions unless a unit is shown. Fiscal years end 30 September."),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "n.a. means the figure is missing, not zero. A zero is written as 0. Shaded columns are forecast.",
      ),
    ).toBeInTheDocument();
    const tabs = within(screen.getByRole("tablist", { name: "Statement" })).getAllByRole("tab");
    expect(tabs.map((t) => t.textContent)).toEqual([
      "Income statement",
      "Cash flow",
      "Balance sheet",
      "Key measures",
    ]);
    expect(screen.getByRole("tab", { name: "Income statement" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    const toggle = screen.getByRole("radiogroup", { name: "Statements: Figures or Bars" });
    expect(
      within(toggle)
        .getAllByRole("radio")
        .map((b) => b.textContent),
    ).toEqual(["Figures", "Bars"]);
    expect(screen.getByRole("radio", { name: "Figures" })).toBeChecked();
  });

  it("draws the income statement: seven period columns, eight rows, the base case", () => {
    renderAt(fixtureSlice());
    const heads = within(screen.getByRole("table")).getAllByRole("columnheader");
    expect(heads).toHaveLength(9);
    expect(heads[0]).toHaveTextContent("Income statement");
    PERIODS.forEach((period, i) => {
      expect(must(heads[i + 1]).textContent.startsWith(period)).toBe(true);
    });
    const labels = within(screen.getByRole("table"))
      .getAllByRole("rowheader")
      .map((h) => h.textContent);
    expect(labels).toEqual([
      "Revenue",
      "Gross profit",
      "EBITDA as defined",
      "Depreciation and amortisation",
      "Operating income",
      "Net interest expense",
      "Income tax",
      "Net income",
    ]);
    expect(cellAt("Revenue", "FY22")).toHaveTextContent("5,429");
    expect(cellAt("Revenue", "LTM")).toHaveTextContent("8,580");
    expect(cellAt("Revenue", "FY25E")).toHaveTextContent("8,840");
    expect(cellAt("Revenue", "FY27E")).toHaveTextContent("10,190");
    expect(cellAt("Depreciation and amortisation", "FY27E")).toHaveTextContent("-385");
    expect(cellAt("Net income", "FY27E")).toHaveTextContent("2,370");
  });

  it("draws the header notes: Actual, To June 2025, and the chosen case on forecast columns", () => {
    renderAt(fixtureSlice());
    const head = (p: string) =>
      must(
        within(screen.getByRole("table"))
          .getAllByRole("columnheader")
          .find((h) => h.textContent.startsWith(p)),
      );
    expect(within(head("FY22")).getByText("Actual")).toBeInTheDocument();
    expect(within(head("LTM")).getByText("To June 2025")).toBeInTheDocument();
    for (const p of ["FY25E", "FY26E", "FY27E"]) {
      expect(within(head(p)).getByText("Base")).toBeInTheDocument();
      expect(within(head(p)).queryByText("Downside")).toBeNull();
    }
    choose("Downside case");
    for (const p of ["FY25E", "FY26E", "FY27E"]) {
      expect(within(head(p)).getByText("Downside")).toBeInTheDocument();
      expect(within(head(p)).queryByText("Base")).toBeNull();
    }
  });

  it("switches the forecast cells with the case and leaves the actual columns alone", () => {
    renderAt(fixtureSlice());
    const actual = PERIODS.slice(0, 4).map((p) => cellAt("EBITDA as defined", p).textContent);
    expect(actual).toEqual(["2,646", "3,395", "4,173", "4,560"]);
    expect(PERIODS.slice(4).map((p) => cellAt("EBITDA as defined", p).textContent)).toEqual([
      "4,690",
      "5,080",
      "5,460",
    ]);
    choose("Downside case");
    expect(PERIODS.slice(0, 4).map((p) => cellAt("EBITDA as defined", p).textContent)).toEqual(
      actual,
    );
    expect(PERIODS.slice(4).map((p) => cellAt("EBITDA as defined", p).textContent)).toEqual([
      "4,560",
      "4,120",
      "4,350",
    ]);
    expect(cellAt("Net income", "FY26E")).toHaveTextContent("1,180");
  });

  it("keeps the chosen case when another tab is opened", () => {
    renderAt(fixtureSlice());
    choose("Downside case");
    openTab("Cash flow");
    expect(cellAt("Free cash flow", "FY26E")).toHaveTextContent("1,810");
  });

  it("moves between the statement tabs with the arrow keys, Home and End", () => {
    renderAt(fixtureSlice());
    const tab = (name: string) => screen.getByRole("tab", { name });
    act(() => {
      tab("Income statement").focus();
    });
    fireEvent.keyDown(tab("Income statement"), { key: "ArrowRight" });
    expect(tab("Cash flow")).toHaveAttribute("aria-selected", "true");
    expect(
      within(screen.getByRole("table")).getByText("Dividends and buybacks"),
    ).toBeInTheDocument();
    fireEvent.keyDown(tab("Cash flow"), { key: "End" });
    expect(tab("Key measures")).toHaveAttribute("aria-selected", "true");
    expect(within(screen.getByRole("table")).getByText("Revenue growth")).toBeInTheDocument();
    fireEvent.keyDown(tab("Key measures"), { key: "ArrowLeft" });
    expect(tab("Balance sheet")).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(tab("Balance sheet"), { key: "Home" });
    expect(tab("Income statement")).toHaveAttribute("aria-selected", "true");
    expect(screen.getAllByRole("table")).toHaveLength(1);
  });

  it("draws the key measures with their units and three missing cells", () => {
    renderAt(fixtureSlice());
    openTab("Key measures");
    expect(cellAt("Net leverage", "FY27E")).toHaveTextContent("3.8x");
    expect(cellAt("EBITDA margin", "LTM")).toHaveTextContent("53.1%");
    expect(cellAt("Revenue growth", "FY22")).toHaveTextContent("n.a.");
    expect(cellAt("Interest cover", "FY23")).toHaveTextContent("n.a.");
    expect(cellAt("Free cash flow to debt", "FY23")).toHaveTextContent("n.a.");
    expect(within(screen.getByRole("table")).getAllByText("n.a.")).toHaveLength(3);
  });

  it("styles subtotal and total rows as the mock does and keeps plain rows plain", () => {
    renderAt(fixtureSlice());
    expect(rowOf("Gross profit")).toHaveAttribute("data-kind", "subtotal");
    expect(rowOf("EBITDA as defined")).toHaveAttribute("data-kind", "total");
    expect(rowOf("Revenue")).toHaveAttribute("data-kind", "plain");
    expect(rowOf("EBITDA as defined").className).toContain("font-semibold");
    expect(rowOf("Gross profit").className).not.toContain("font-semibold");
  });

  it("shades the forecast columns and nothing else", () => {
    renderAt(fixtureSlice());
    const shaded = within(rowOf("Revenue"))
      .getAllByRole("cell")
      .map((c) => c.hasAttribute("data-forecast"));
    expect(shaded).toEqual([false, false, false, false, true, true, true, false]);
  });

  it("gives every row one trace control and puts the address only in href", () => {
    const { container } = renderAt(fixtureSlice());
    const labels = [
      "Revenue",
      "Gross profit",
      "EBITDA as defined",
      "Depreciation and amortisation",
      "Operating income",
      "Net interest expense",
      "Income tax",
      "Net income",
    ];
    const table = within(screen.getByRole("table"));
    expect(table.getAllByRole("link")).toHaveLength(8);
    for (const label of labels) {
      expect(table.getByRole("link", { name: `Show the sources for ${label}` })).toHaveAttribute(
        "href",
        ADDRESS,
      );
    }
    expect(container.textContent).not.toContain("library/transdigm");
    for (const el of Array.from(container.querySelectorAll("[title], [aria-label]"))) {
      expect(`${el.getAttribute("title") ?? ""}${el.getAttribute("aria-label") ?? ""}`).not.toMatch(
        /#\/library|evidence|CP-/i,
      );
    }
  });

  it("keeps the table's scroll inside its wrapper and sets small text at the 13px caption size", () => {
    renderAt(fixtureSlice());
    const wrapper = must(screen.getByRole("table").parentElement);
    expect(wrapper).toHaveClass("overflow-x-auto", "relative");
    const note = must(screen.getAllByText("Actual", { selector: "span" })[0]);
    expect(note).toHaveClass("text-caption", "font-normal");
    expect(note).not.toHaveClass("text-xs");
    const tag = screen.getByText("Management plan, trimmed");
    expect(tag).toHaveClass("text-caption", "font-normal");
    expect(tag).not.toHaveClass("text-xs");
  });
});

import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { App } from "@/App";
import type { LoadResult } from "@/data";
import { fixtureSlice, must } from "./slice/test-fixture";

const ADDRESS = "#/library/transdigm/2025-06-30/evidence";
const NOT_CALCULABLE = "Not calculable: cash is negative before funding";
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

/**
 * The table's rows, headers and cells are found by their elements (`tr`, `th[scope]`, `td`), which
 * is what gives them the row, columnheader, rowheader and cell roles, and not by a role query per
 * lookup: each role query walks the accessibility tree, and a lookup of one cell made about 35 ms
 * of a test that needs a handful of them.
 */
const rowOf = (label: string): HTMLElement =>
  must(
    [...screen.getByRole("table").querySelectorAll<HTMLElement>("tbody tr")].find((r) =>
      r.querySelector('th[scope="row"]')?.textContent.startsWith(label),
    ),
  );

/** The cell of `row` under the period column `period`. */
function cellAt(label: string, period: string): HTMLElement {
  const headers = [...screen.getByRole("table").querySelectorAll('thead th[scope="col"]')];
  const at = headers.findIndex((h) => h.textContent.startsWith(period));
  if (at < 1) throw new Error(`no column ${period}`);
  return must([...rowOf(label).querySelectorAll<HTMLElement>("td")][at - 1]);
}

const choose = (name: string) => {
  fireEvent.click(screen.getByRole("radio", { name }));
};
const showBars = () => {
  fireEvent.click(screen.getByRole("radio", { name: "Bars" }));
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

  it("draws no bars in Figures and a bar under each figure in Bars", () => {
    renderAt(fixtureSlice());
    expect(screen.getByRole("table").querySelector("[data-bar]")).toBeNull();
    showBars();
    expect(screen.getByRole("radio", { name: "Bars" })).toBeChecked();
    const bars = within(rowOf("Revenue")).getAllByRole("cell").slice(0, 7);
    for (const cell of bars) expect(cell.querySelector("[data-bar]")).not.toBeNull();
    fireEvent.click(screen.getByRole("radio", { name: "Figures" }));
    expect(screen.getByRole("table").querySelector("[data-bar]")).toBeNull();
  });

  it("sizes a bar by the delivered position: 8,580 of 10,190 is 84.2 per cent of the cell", () => {
    renderAt(fixtureSlice());
    showBars();
    const bar = (label: string, period: string) =>
      must(cellAt(label, period).querySelector<HTMLElement>("[data-bar]")).style.width;
    expect(bar("Revenue", "LTM")).toBe("84.2%");
    expect(bar("Revenue", "FY27E")).toBe("100%");
    expect(bar("Revenue", "FY22")).toBe("53.28%");
  });

  it("draws equal values as equal bars in every period column, which share one width", () => {
    renderAt(fixtureSlice());
    openTab("Balance sheet");
    showBars();
    const widths = PERIODS.slice(3).map(
      (p) => must(cellAt("Gross debt", p).querySelector<HTMLElement>("[data-bar]")).style.width,
    );
    expect(widths).toEqual(Array<string>(4).fill("100%"));
    const heads = within(screen.getByRole("table"))
      .getAllByRole("columnheader")
      .slice(1, 8)
      .map((h) => h.className.match(/\bw-\[\d+px\]/)?.[0]);
    expect(new Set(heads).size).toBe(1);
    expect(heads[0]).toBeDefined();
  });

  it("draws a negative figure's bar in the below colour and a positive one in the series colour", () => {
    renderAt(fixtureSlice());
    showBars();
    const bar = (period: string) =>
      must(cellAt("Depreciation and amortisation", period).querySelector("[data-bar]"));
    expect(bar("FY27E")).toHaveAttribute("data-sign", "negative");
    expect(bar("FY27E").className).toContain("bg-chart-3");
    const positive = must(cellAt("Revenue", "FY27E").querySelector("[data-bar]"));
    expect(positive).toHaveAttribute("data-sign", "positive");
    expect(positive.className).toContain("bg-chart-1");
  });

  it("draws n.a. for a missing cell with no bar and no zero, beside a zero in the same column", () => {
    renderAt(fixtureSlice());
    openTab("Cash flow");
    showBars();
    const missing = cellAt("Cash interest", "FY23");
    expect(missing).toHaveTextContent("n.a.");
    expect(missing.textContent).not.toMatch(/\b0\b/);
    expect(missing.querySelector("[data-bar]")).toBeNull();
    const zero = cellAt("Dividends and buybacks", "FY23");
    expect(zero).toHaveTextContent(/^0/);
    expect(zero.querySelector("[data-bar]")).not.toBeNull();
    expect(cellAt("Free cash flow", "FY23")).toHaveTextContent("n.a.");
  });

  it("draws a withheld cell as Withheld, with no figure, no n.a. and no bar, beside a zero", () => {
    renderAt(fixtureSlice());
    openTab("Cash flow");
    showBars();
    const withheld = cellAt("Acquisitions", "FY25E");
    expect(within(withheld).getByText("Withheld")).toBeInTheDocument();
    expect(withheld).not.toHaveTextContent("n.a.");
    expect(withheld.querySelector("[data-bar]")).toBeNull();
    expect(cellAt("Acquisitions", "FY26E")).toHaveTextContent("0");
    choose("Downside case");
    expect(within(cellAt("Acquisitions", "FY25E")).getByText("Withheld")).toBeInTheDocument();
    expect(cellAt("Acquisitions", "LTM")).toHaveTextContent("-650");
  });

  it("draws the gap badge beside the pension deficit label and n.a. in every cell", () => {
    renderAt(fixtureSlice());
    openTab("Balance sheet");
    const row = rowOf("Pension deficit");
    expect(
      within(within(row).getByRole("rowheader")).getByText("Not established for this run"),
    ).toBeInTheDocument();
    expect(within(row).getAllByText("n.a.")).toHaveLength(7);
    expect(within(rowOf("Cash")).queryByText("Not established for this run")).toBeNull();
    expect(cellAt("Inventories", "FY22")).toHaveTextContent("n.a.");
    expect(cellAt("Shareholders’ equity", "LTM")).toHaveTextContent("-9,360");
  });

  // Per-test limit: this test renders the whole page once and switches the case twice, and each
  // switch re-renders every chart section (about 120 ms each here, about 70 % of the test). That is
  // production render work the test cannot skip, and it runs several times slower on the Windows
  // runner than here, close to the 5 s default.
  it("describes a missing cell by its reason, shows it on focus, and draws it n.a., never 0", async () => {
    const { slice, run } = draft();
    const rows = must(run.statements.statements[3]).rows;
    const lev = must(rows.find((r) => r.label === "Net leverage"));
    lev.cells[5] = [
      { kind: "figure", text: "5.9x", pos: 1 },
      { kind: "missing", reason: NOT_CALCULABLE },
    ];
    const bs = must(run.statements.statements[2]).rows;
    must(bs.find((r) => r.label === "Cash")).cells[5] = [
      { kind: "figure", text: "5,940", pos: 0.6 },
      { kind: "figure", text: "-1,200", pos: -0.1 },
    ];
    renderAt(slice);
    choose("Downside case");
    openTab("Balance sheet");
    expect(cellAt("Cash", "FY26E")).toHaveTextContent("-1,200");
    openTab("Key measures");
    const cell = cellAt("Net leverage", "FY26E");
    expect(cell).toHaveTextContent("n.a.");
    expect(cell.textContent).not.toMatch(/\b0\b/);
    const trigger = within(cell).getByRole("button");
    expect(trigger).toHaveAccessibleDescription(NOT_CALCULABLE);
    fireEvent.keyDown(document.body, { key: "Tab" });
    act(() => {
      trigger.focus();
    });
    expect(await screen.findByRole("tooltip")).toHaveTextContent(NOT_CALCULABLE);
    choose("Base case");
    expect(cellAt("Net leverage", "FY26E")).toHaveTextContent("5.9x");
    expect(within(cellAt("Net leverage", "FY26E")).queryByRole("button")).toBeNull();
  }, 20_000);

  it("draws a missing cell without a reason as plain n.a. with no control", () => {
    renderAt(fixtureSlice());
    openTab("Key measures");
    expect(within(cellAt("Interest cover", "FY23")).queryByRole("button")).toBeNull();
  });

  it("draws an empty pro forma column as its header and its reason, with no cells", () => {
    const { slice, run } = draft();
    const reason =
      "pro forma figures are not placed in this column; the financial foundation shows any it states";
    run.statements.columns.splice(4, 0, {
      kind: "empty",
      period: "Pro forma",
      note: null,
      reason,
    });
    renderAt(slice);
    const heads = within(screen.getByRole("table")).getAllByRole("columnheader");
    expect(heads.map((h) => h.textContent.slice(0, 9))).toContain("Pro forma");
    expect(screen.getAllByText(reason)).toHaveLength(1);
    expect(within(screen.getByRole("table")).getAllByRole("rowheader")).toHaveLength(8);
    expect(cellAt("Revenue", "FY25E")).toHaveTextContent("8,840");
    expect(within(rowOf("Gross profit")).getAllByRole("cell")).toHaveLength(8);
    expect(within(rowOf("Revenue")).getAllByRole("cell")).toHaveLength(9);
  });

  it("lets a long row label wrap while the figures stay on one line", () => {
    const { slice, run } = draft();
    const long =
      "Depreciation and amortisation of acquired intangible assets and capitalised software development costs";
    must(must(run.statements.statements[0]).rows[3]).label = long;
    renderAt(slice);
    const head = screen.getByRole("rowheader", { name: long });
    expect(head.className).toContain("whitespace-normal");
    expect(head.className).toContain("break-words");
    expect(cellAt(long, "LTM").className).toContain("whitespace-nowrap");
  });

  it("draws the not found state for an unknown issuer or run", () => {
    renderAt(fixtureSlice(), "nobody");
    expect(screen.getByText("Not found for this run")).toBeInTheDocument();
  });

  it("names the failing path when the statements are not readable", () => {
    const { slice, run } = draft();
    must(must(run.statements.statements[0]).rows[0]).cells[2] = { kind: "figure", text: "7,940" };
    renderAt(slice);
    expect(screen.getByText("This part of the library could not be read")).toBeInTheDocument();
    expect(
      screen.getByText("runs[0].statements.statements[0].rows[0].cells[2].pos: missing"),
    ).toBeInTheDocument();
  });
});

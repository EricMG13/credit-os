import { readFileSync } from "node:fs";
import path from "node:path";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { App } from "../../../App";
import type { LoadResult } from "../../../data";

const fixture = JSON.parse(
  readFileSync(path.join(import.meta.dirname, "../../../../fixtures/run.json"), "utf8"),
) as { slice: { drafts: Record<string, unknown>[] } };

function show(hash: string, run: unknown) {
  window.location.hash = `#${hash}`;
  const result: LoadResult = { kind: "ok", data: { schema: "credit-os-data/1", issuers: [], run } };
  return render(<App result={result} />);
}
afterEach(() => {
  window.location.hash = "";
});

describe("Purpose (frame 03)", () => {
  beforeEach(() => {
    show("/run/start/purpose", fixture.slice);
  });

  it("draws the heading, the sentence and three radios inside a labelled group", () => {
    expect(screen.getByRole("heading", { level: 2, name: "Purpose" })).toBeVisible();
    expect(
      screen.getByText(
        "The purpose decides which modules run, and so how much of the cap the run can use.",
      ),
    ).toBeVisible();
    const group = screen.getByRole("radiogroup", { name: "Purpose" });
    expect(within(group).getAllByRole("radio")).toHaveLength(3);
    for (const title of ["Full credit review", "Earnings update", "Event review"]) {
      expect(within(group).getByRole("radio", { name: new RegExp(title) })).toBeInTheDocument();
    }
  });

  it("checks the draft's chosen card and shows each card's module label", () => {
    expect(screen.getByRole("radio", { name: /Full credit review/ })).toBeChecked();
    expect(screen.getByRole("radio", { name: /Earnings update/ })).not.toBeChecked();
    expect(screen.getByText("13 modules")).toBeVisible();
    expect(screen.getByText("5 modules")).toBeVisible();
    expect(screen.getByText("4 modules")).toBeVisible();
    expect(
      screen.getByText(
        "Looks at one event, such as a refinancing, an acquisition or a rating action, and what it changes.",
      ),
    ).toBeVisible();
  });

  it("moves the selection on a click and on ArrowDown", () => {
    fireEvent.click(screen.getByRole("radio", { name: /Event review/ }));
    expect(screen.getByRole("radio", { name: /Event review/ })).toBeChecked();
    expect(screen.getByRole("radio", { name: /Full credit review/ })).not.toBeChecked();
    fireEvent.click(screen.getByRole("radio", { name: /Full credit review/ }));
    act(() => {
      screen.getByRole("radio", { name: /Full credit review/ }).focus();
    });
    fireEvent.keyDown(screen.getByRole("radio", { name: /Full credit review/ }), {
      key: "ArrowDown",
    });
    expect(screen.getByRole("radio", { name: /Earnings update/ })).toBeChecked();
    expect(screen.getByRole("radio", { name: /Full credit review/ })).not.toBeChecked();
  });
});

describe("Purpose with nothing chosen", () => {
  it("checks no radio when chosen is null", () => {
    const drafts = fixture.slice.drafts.map((d) =>
      d["id"] === "purpose" ? { ...d, chosen: null } : d,
    );
    show("/run/start/purpose", { drafts });
    const radios = screen.getAllByRole("radio");
    expect(radios).toHaveLength(3);
    for (const r of radios) expect(r).not.toBeChecked();
  });
});

describe("Confirm (frame 04)", () => {
  beforeEach(() => {
    show("/run/start/confirm", fixture.slice);
  });

  it("draws the heading, the sentence and the approval badge", () => {
    expect(screen.getByRole("heading", { level: 2, name: "Confirm what was read" })).toBeVisible();
    expect(
      screen.getByText(
        "This is what the documents say and what will run. Approving it costs nothing.",
      ),
    ).toBeVisible();
    expect(screen.getByText("Awaiting your approval")).toBeVisible();
  });

  it("draws one captioned details list per group", () => {
    for (const name of ["Issuer", "Documents", "Run"]) {
      expect(screen.getByRole("heading", { level: 3, name })).toBeVisible();
    }
    expect(screen.getByText("TransDigm Group Incorporated")).toBeVisible();
    expect(screen.getByText("Q3 FY2026, nine months to 28 June 2026")).toBeVisible();
    expect(screen.getByText("USD 20.00")).toBeVisible();
  });

  it("draws a null value as n.a., never 0 or a dash", () => {
    const term = screen.getByText("Guarantor group");
    const row = term.parentElement as HTMLElement;
    expect(row).toHaveTextContent("Guarantor groupn.a.not available");
    expect(row).not.toHaveTextContent("0");
    expect(row).not.toHaveTextContent("-");
  });

  it("names the next control Approve summary", () => {
    expect(screen.getByRole("link", { name: "Approve summary" })).toHaveAttribute(
      "href",
      "#/run/start/context",
    );
  });
});

// jsdom applies no stylesheet, so the kit Label's hidden required asterisk is part of the name here.
const LABEL = /^Anything the analysis should know/;

describe("More context (frame 05)", () => {
  beforeEach(() => {
    show("/run/start/context", fixture.slice);
  });

  it("draws the heading and the sentence", () => {
    expect(screen.getByRole("heading", { level: 2, name: "More context" })).toBeVisible();
    expect(
      screen.getByText("Optional. Skip this step if the documents say everything."),
    ).toBeVisible();
  });

  it("labels the text area, describes it with its hint and shows the placeholder", () => {
    const box = screen.getByRole("textbox", { name: LABEL });
    expect(box).toHaveAttribute(
      "placeholder",
      "For example: the committee wants a view on the 2028 maturities; the scanned presentation was left out.",
    );
    expect(box).toHaveAccessibleDescription(
      "What helps: the question behind this run, events after the latest report, documents you chose to leave out. Do not paste material from a private source. Not saved here: this page shows a saved example and is not connected to the run service.",
    );
    expect(box).toHaveValue("");
  });

  it("accepts typed text in memory", () => {
    const box = screen.getByRole("textbox", { name: LABEL });
    fireEvent.change(box, { target: { value: "Focus on 2028 maturities" } });
    expect(box).toHaveValue("Focus on 2028 maturities");
  });

  it("starts from the draft's note", () => {
    const drafts = fixture.slice.drafts.map((d) =>
      d["id"] === "context" ? { ...d, note: "Saved note" } : d,
    );
    cleanup();
    show("/run/start/context", { drafts });
    expect(screen.getByRole("textbox", { name: LABEL })).toHaveValue("Saved note");
  });
});

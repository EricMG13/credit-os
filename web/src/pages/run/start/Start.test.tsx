import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { App } from "../../../App";
import type { LoadResult } from "../../../data";

const fixture = JSON.parse(
  readFileSync(path.join(import.meta.dirname, "../../../../fixtures/run.json"), "utf8"),
) as { slice: unknown };

function show(hash: string, run: unknown = fixture.slice) {
  window.location.hash = `#${hash}`;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], run },
  };
  return render(<App result={result} />);
}
afterEach(() => {
  cleanup();
  window.location.hash = "";
});

const SUBMIT = "Submit, spend up to USD 20.00";

describe("Start (frame 06)", () => {
  beforeEach(() => {
    show("/run/start/start");
  });

  it("draws the heading, the sentence and the recap", () => {
    expect(screen.getByRole("heading", { level: 2, name: "Start" })).toBeVisible();
    expect(
      screen.getByText("Everything is ready. This is the only step that spends money."),
    ).toBeVisible();
    const expected: [string, string][] = [
      ["Issuer", "TransDigm Group Incorporated"],
      ["Purpose", "Full credit review, 13 modules"],
      ["Documents", "4, approved today at 14:36"],
      ["More context", "One note added"],
    ];
    for (const [label, value] of expected) {
      const term = screen.getAllByText(label).find((el) => el.tagName === "DT");
      expect(term?.parentElement).toHaveTextContent(`${label}${value}`);
    }
  });

  it("says Submit starts a paid run, under its own h3", () => {
    expect(
      screen.getByRole("heading", { level: 3, name: "Submit starts a paid run" }),
    ).toBeVisible();
    expect(
      screen.getByRole("heading", { level: 3, name: "Submit starts a paid run" }).parentElement,
    ).toHaveTextContent(
      "Submit starts a paid runIt can spend up to USD 20.00 and stops there. You confirm once more before anything is spent.",
    );
  });

  it("draws the amount in the paid sentence in bold, and the sentence whole", () => {
    const strong = screen.getByText("USD 20.00", { selector: "strong" });
    expect(strong.parentElement).toHaveTextContent(
      "It can spend up to USD 20.00 and stops there. You confirm once more before anything is spent.",
    );
  });

  it("draws the paid text unchanged when it lacks the amount", () => {
    cleanup();
    const slice = JSON.parse(JSON.stringify(fixture.slice)) as {
      drafts: { id: string; paid?: { amount: string } }[];
    };
    const paid = slice.drafts.find((d) => d.id === "start")?.paid;
    if (paid === undefined) throw new Error("fixture has no start draft");
    paid.amount = "USD 99.00";
    show("/run/start/start", slice);
    expect(document.querySelector("strong")).toBeNull();
    expect(
      screen.getByText(
        "It can spend up to USD 20.00 and stops there. You confirm once more before anything is spent.",
      ),
    ).toBeVisible();
  });

  it("draws Submit as the one button with the exact label and no Next link", () => {
    expect(screen.getByRole("button", { name: SUBMIT })).toBeEnabled();
    expect(screen.queryByRole("link", { name: SUBMIT })).toBeNull();
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("opens a dialog named by its title, with the text and both buttons", () => {
    fireEvent.click(screen.getByRole("button", { name: SUBMIT }));
    const dialog = screen.getByRole("dialog", { name: "Start a paid run?" });
    expect(
      within(dialog).getByText(
        "This run can spend up to USD 20.00 and stops when it reaches that cap. Once it starts, what it has spent cannot be taken back.",
      ),
    ).toBeVisible();
    expect(within(dialog).getByRole("button", { name: "Cancel" })).toBeEnabled();
    expect(
      within(dialog).getByRole("button", { name: "Start run, up to USD 20.00" }),
    ).toBeEnabled();
  });

  it("stacks the two dialog buttons in one column at the plain md size (probe: label must fit)", () => {
    fireEvent.click(screen.getByRole("button", { name: SUBMIT }));
    const dialog = screen.getByRole("dialog");
    const cancel = within(dialog).getByRole("button", { name: "Cancel" });
    const start = within(dialog).getByRole("button", { name: "Start run, up to USD 20.00" });
    const actions = start.parentElement;
    expect(actions).toBe(cancel.parentElement);
    expect(actions).toHaveClass("flex-col");
    expect(actions).not.toHaveClass("grid-cols-2");
    for (const b of [cancel, start]) {
      expect(b).toHaveClass("px-3.5"); // kit md; lg is px-4 text-md
      expect(b).not.toHaveClass("text-md");
    }
  });

  it("closes on Escape and returns focus to Submit", async () => {
    const submit = screen.getByRole("button", { name: SUBMIT });
    act(() => {
      submit.focus(); // a real press focuses the button first
    });
    fireEvent.click(submit);
    const dialog = screen.getByRole("dialog");
    fireEvent.keyDown(dialog, { key: "Escape" });
    act(() => {
      fireEvent.keyUp(dialog, { key: "Escape" });
    });
    expect(screen.queryByRole("dialog")).toBeNull();
    await waitFor(() => {
      expect(submit).toHaveFocus();
    });
  });

  it("closes on Cancel, returns focus to Submit and does not navigate", async () => {
    const submit = screen.getByRole("button", { name: SUBMIT });
    act(() => {
      submit.focus(); // a real press focuses the button first
    });
    fireEvent.click(submit);
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    await waitFor(() => {
      expect(submit).toHaveFocus();
    });
    expect(window.location.hash).toBe("#/run/start/start");
  });

  it("navigates to the started draft on confirm", () => {
    fireEvent.click(screen.getByRole("button", { name: SUBMIT }));
    fireEvent.click(screen.getByRole("button", { name: "Start run, up to USD 20.00" }));
    expect(window.location.hash).toBe("#/run/start/started");
  });

  it("draws Previous as before", () => {
    expect(screen.getByRole("link", { name: "Previous" })).toHaveAttribute(
      "href",
      "#/run/start/context",
    );
    expect(screen.getByText("Step 5 of 5")).toBeVisible();
  });
});

describe("Run started (frame 08)", () => {
  beforeEach(() => {
    show("/run/start/started");
  });

  it("draws the alert with its title and text", () => {
    const alert = screen.getByRole("status");
    expect(within(alert).getByText("Run started")).toBeVisible();
    expect(
      within(alert).getByText(
        "13 modules will read 4 documents for a full credit review of TransDigm Group. Spending stops at USD 20.00.",
      ),
    ).toBeVisible();
  });

  it("names the run started once, in the alert, with no hidden heading", () => {
    expect(screen.getAllByText("Run started")).toHaveLength(1);
    expect(screen.queryByRole("heading", { name: "Run started" })).toBeNull();
  });

  it("draws Back to the library in the grey secondary link colour", () => {
    const link = screen.getByRole("link", { name: "Back to the library" });
    expect(link).toHaveClass("text-text-tertiary");
    expect(link).not.toHaveClass("text-brand-secondary");
  });

  it("draws the cap bar and the two links", () => {
    const alert = screen.getByRole("status");
    expect(within(alert).getByRole("progressbar", { name: "USD 0.00 of USD 20.00" })).toBeVisible();
    expect(within(alert).getByRole("link", { name: "Watch run activity" })).toHaveAttribute(
      "href",
      "#/run/activity/running",
    );
    expect(within(alert).getByRole("link", { name: "Back to the library" })).toHaveAttribute(
      "href",
      "#/",
    );
  });

  it("says the page can be closed", () => {
    expect(
      screen.getByText(
        "You can close this page. The run carries on, and its library appears under TransDigm Group when it finishes.",
      ),
    ).toBeVisible();
  });

  it("has no Previous, Submit or next control and no dialog", () => {
    expect(screen.queryByText("Previous")).toBeNull();
    expect(screen.queryByRole("button", { name: SUBMIT })).toBeNull();
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = path.join(dir, name);
    if (statSync(p).isDirectory()) return sources(p);
    return /\.tsx?$/.test(name) && !/\.test\./.test(name) ? [p] : [];
  });
}

describe("the run pages reach no service, storage or timer", () => {
  it("names none in any non-test source file", () => {
    const files = sources(path.join(import.meta.dirname, ".."));
    expect(files.length).toBeGreaterThan(5);
    const banned =
      /\b(fetch|XMLHttpRequest|localStorage|sessionStorage|setTimeout|setInterval|requestAnimationFrame|requestIdleCallback|sendBeacon|indexedDB|WebSocket|EventSource)\b/;
    for (const f of files) {
      const text = readFileSync(f, "utf8");
      expect([f, banned.exec(text)?.[0]]).toEqual([f, undefined]);
      expect([f, /document\.cookie/.exec(text)?.[0]]).toEqual([f, undefined]);
    }
  });
});

describe("Start with a blocked draft", () => {
  it("disables Submit, shows the reason and describes Submit with it; the dialog cannot open", () => {
    const slice = structuredClone(fixture.slice) as { drafts: Record<string, unknown>[] };
    const d = slice.drafts.find((x) => x.id === "start") as Record<string, unknown>;
    d.next = null;
    d.nextBlocked = "The spending cap is used up.";
    show("/run/start/start", slice);
    const submit = screen.getByRole("button", { name: SUBMIT });
    expect(submit).toBeDisabled();
    const reason = screen.getByText("The spending cap is used up.");
    expect(submit.getAttribute("aria-describedby")).toBe(reason.id);
    fireEvent.click(submit);
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

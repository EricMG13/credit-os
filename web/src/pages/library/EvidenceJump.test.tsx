import { readFileSync } from "node:fs";
import path from "node:path";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

const BASE = "/library/:issuer/:run/evidence";
const FULL = "2026-09-30";

function renderEvidence(page: string, run = FULL, library: unknown = fixture.slice) {
  const data: LibraryData = { schema: "credit-os-data/1", issuers: fixture.issuers, library };
  const found = routes.find((r) => r.path === `${BASE}/${page}`);
  if (found === undefined) throw new Error(`no ${page} route`);
  return render(
    <SourceContext.Provider value={data}>
      {found.render({ issuer: "halden-aerostructures", run })}
    </SourceContext.Provider>,
  );
}

const field = () => screen.getByRole("button", { name: /^Jump to an item/ });
const dialog = () => screen.getByRole("dialog", { name: "Jump to an item" });
const search = () => within(dialog()).getByRole("searchbox");
const options = () =>
  within(dialog())
    .queryAllByRole("option")
    .map((o) => o.textContent);

/** Opens the menu by the shortcut, as a reader on Windows or macOS would. */
const press = (init: KeyboardEventInit, target: Element | Document = document) =>
  fireEvent.keyDown(target, init);

afterEach(() => {
  cleanup();
  window.location.hash = "";
  vi.restoreAllMocks();
});

describe("Jump to an item, the field", () => {
  it.each(["summary", "trace", "sources", "gaps", "record"])(
    "is drawn on the %s page, named as the mock names it, with its shortcut",
    (page) => {
      renderEvidence(page);
      expect(field()).toHaveTextContent("Jump to an item");
      expect(field()).toHaveAttribute("aria-haspopup", "dialog");
      expect(field()).toHaveAttribute("aria-keyshortcuts", "Control+K Meta+K");
      expect(within(field()).getByText(/^(⌘K|Ctrl K)$/)).toBeVisible();
    },
  );

  it("shows the shortcut in the words of the reader's system", () => {
    vi.spyOn(navigator, "userAgent", "get").mockReturnValue(
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0)",
    );
    renderEvidence("summary");
    expect(within(field()).getByText("⌘K")).toBeVisible();
    cleanup();
    vi.spyOn(navigator, "userAgent", "get").mockReturnValue(
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    );
    renderEvidence("summary");
    expect(within(field()).getByText("Ctrl K")).toBeVisible();
  });

  it("opens the menu on click, with three groups and the four items of the fixture", async () => {
    renderEvidence("summary");
    expect(screen.queryByRole("dialog")).toBeNull();
    fireEvent.click(field());
    expect(
      within(dialog())
        .getAllByRole("group")
        .map((g) => g.getAttribute("aria-label")),
    ).toEqual(["Figures", "Calculations", "Gaps"]);
    expect(options()).toEqual([
      "Net leverage 4.6xCapital structure · T-0014",
      "Secured leverage 3.3xCapital structure · T-0104",
      "Net debt ÷ EBITDAC-0412",
      "Peer figures on the same basisPeer comparison · G-03",
    ]);
    for (const hint of ["to move", "to open", "to close"]) {
      expect(within(dialog()).getByText(hint)).toBeVisible();
    }
    await waitFor(() => {
      expect(search()).toHaveFocus();
    });
  });

  it("adds no heading to the page: the groups are named groups, not headings", () => {
    renderEvidence("summary");
    fireEvent.click(field());
    expect(within(dialog()).queryAllByRole("heading")).toHaveLength(0);
  });
});

describe("Jump to an item, the shortcut", () => {
  it.each([
    ["Control+K", { key: "k", ctrlKey: true }],
    ["Command+K", { key: "k", metaKey: true }],
    ["Control+Shift K as a capital", { key: "K", ctrlKey: true }],
  ])("%s opens the menu, and the browser's own use of it is cancelled", (_, init) => {
    renderEvidence("trace");
    const event = new KeyboardEvent("keydown", { ...init, bubbles: true, cancelable: true });
    act(() => {
      document.dispatchEvent(event);
    });
    expect(event.defaultPrevented).toBe(true);
    expect(dialog()).toBeVisible();
  });

  it("does nothing for K alone or another chord", () => {
    renderEvidence("trace");
    press({ key: "k" });
    press({ key: "j", ctrlKey: true });
    press({ key: "k", ctrlKey: true, altKey: true });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("does not fire while focus is in another text field", () => {
    renderEvidence("trace");
    const input = document.createElement("input");
    document.body.append(input);
    input.focus();
    const event = new KeyboardEvent("keydown", {
      key: "k",
      ctrlKey: true,
      bubbles: true,
      cancelable: true,
    });
    act(() => {
      input.dispatchEvent(event);
    });
    expect(event.defaultPrevented).toBe(false);
    expect(screen.queryByRole("dialog")).toBeNull();
    input.remove();
  });

  it("is mounted only while an Evidence page is shown", () => {
    const add = vi.spyOn(document, "addEventListener");
    const remove = vi.spyOn(document, "removeEventListener");
    const view = renderEvidence("trace");
    const added = add.mock.calls.filter(([type]) => type === "keydown");
    expect(added).toHaveLength(1);
    view.unmount();
    expect(
      remove.mock.calls.filter(([type, fn]) => type === "keydown" && fn === added[0]?.[1]),
    ).toHaveLength(1);
    press({ key: "k", ctrlKey: true });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("opens with the field focused first, so closing returns to it", async () => {
    renderEvidence("record");
    press({ key: "k", ctrlKey: true });
    await waitFor(() => {
      expect(search()).toHaveFocus();
    });
    fireEvent.keyDown(search(), { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
    await waitFor(() => {
      expect(field()).toHaveFocus();
    });
  });
});

describe("Jump to an item, filtering and choosing", () => {
  /** What typing does: the browser announces the kind of edit, then the value changes. */
  const type = (text: string) => {
    const inputType = text === "" ? "deleteContentBackward" : "insertText";
    fireEvent(search(), new InputEvent("beforeinput", { inputType, bubbles: true }));
    fireEvent.change(search(), { target: { value: text } });
  };
  /** Enter is a press: the key goes down in the field and comes up there. */
  const enter = () => {
    fireEvent.keyDown(search(), { key: "Enter" });
    fireEvent.keyUp(search(), { key: "Enter" });
  };

  it("filters by a case-insensitive substring of the label, dropping a group that holds none", () => {
    renderEvidence("summary");
    fireEvent.click(field());
    type("LEVER");
    expect(options()).toEqual([
      "Net leverage 4.6xCapital structure · T-0014",
      "Secured leverage 3.3xCapital structure · T-0104",
    ]);
    expect(within(dialog()).getAllByRole("group")).toHaveLength(1);
    type("ebitda");
    expect(options()).toEqual(["Net debt ÷ EBITDAC-0412"]);
  });

  it("matches the label only, not the detail", () => {
    renderEvidence("summary");
    fireEvent.click(field());
    type("T-0014");
    expect(within(dialog()).queryAllByRole("group")).toHaveLength(0);
    expect(within(dialog()).getByText("No item matches")).toBeVisible();
  });

  it("says No item matches when nothing does, and lists everything again when cleared", () => {
    renderEvidence("summary");
    fireEvent.click(field());
    type("zzz");
    expect(within(dialog()).getByText("No item matches")).toBeVisible();
    type("");
    expect(options()).toHaveLength(4);
  });

  it("moves with the arrow keys and opens the Trace row with Enter", () => {
    renderEvidence("summary");
    fireEvent.click(field());
    fireEvent.keyDown(search(), { key: "ArrowDown" });
    fireEvent.keyDown(search(), { key: "ArrowDown" });
    enter();
    expect(window.location.hash).toBe(
      "#/library/halden-aerostructures/2026-09-30/evidence/trace/T-0104",
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("opens the first item with Enter when the reader has only typed", async () => {
    renderEvidence("summary");
    fireEvent.click(field());
    await waitFor(() => {
      expect(search()).toHaveFocus();
    });
    type("peer");
    await waitFor(() => {
      expect(search()).toHaveAttribute("aria-activedescendant");
    });
    enter();
    expect(window.location.hash).toBe(
      "#/library/halden-aerostructures/2026-09-30/evidence/gaps/G-03",
    );
  });

  it("opens an item on click, a calculation at its Trace row", () => {
    renderEvidence("summary");
    fireEvent.click(field());
    fireEvent.click(within(dialog()).getByRole("option", { name: /Net debt ÷ EBITDA/ }));
    expect(window.location.hash).toBe(
      "#/library/halden-aerostructures/2026-09-30/evidence/trace/T-0014",
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("closes on Escape with text typed, returns focus to the field and goes nowhere", async () => {
    renderEvidence("summary");
    fireEvent.click(field());
    type("net");
    fireEvent.keyDown(search(), { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
    await waitFor(() => {
      expect(field()).toHaveFocus();
    });
    expect(window.location.hash).toBe("");
  });

  it("starts afresh each time it opens", () => {
    renderEvidence("summary");
    fireEvent.click(field());
    type("net");
    fireEvent.keyDown(search(), { key: "Escape" });
    fireEvent.click(field());
    expect(search()).toHaveValue("");
    expect(options()).toHaveLength(4);
  });

  it("says a run with nothing to jump to has none", () => {
    const slice = structuredClone(fixture.slice) as { issuers: { runs: { evidence: Json }[] }[] };
    const run = slice.issuers[0]?.runs[3] as { evidence: Json };
    run.evidence["jump"] = [];
    renderEvidence("summary", "2025-09-30", slice);
    fireEvent.click(field());
    expect(within(dialog()).getByText("This run lists no item to jump to.")).toBeVisible();
  });
});
